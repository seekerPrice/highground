"""Explicit owner recovery; original after-media never refreshes the baseline."""
import asyncio
from datetime import UTC,datetime
import time
import httpx
from google.genai.errors import APIError
from api.inventory import InventoryService
from api.inventory_models import InventoryReply,VideoMedia
from api.photo_models import PhotoMedia
from api.media_models import MediaRequest,MediaIngestError
from api.report_models import LossAssessment
from api.i18n import text,catalog

class RecoveryService(InventoryService):
    def __init__(self,store,media,assessor,*,web_base_url,**kwargs):
        super().__init__(store,media,assessor,**kwargs)
        from urllib.parse import urlsplit
        parsed=urlsplit(web_base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:raise ValueError('Explicit web origin required')
        self.web_base_url=web_base_url.rstrip('/')

    async def active_context(self,sender: int,message_id: int|None=None,file_unique_id: str|None=None) -> dict|None:
        return await asyncio.to_thread(self.store.resolve_context,sender,message_id,file_unique_id)

    async def exit(self,sender: int) -> InventoryReply:
        await asyncio.to_thread(self.store.exit,sender)
        return await self.reply(await asyncio.to_thread(self.store.owner_shop,sender),'recovery_exited')

    async def request_photo(self,sender: int) -> InventoryReply:
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        job=await asyncio.to_thread(self.store.request_attachment,sender)
        return await self.reply(shop,'recovery_photo_request' if job else 'recovery_owner_required')

    async def start(self,sender: int,operation: str) -> InventoryReply:
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        if not shop:return await self.reply(None,'recovery_owner_required')
        try:job=await asyncio.to_thread(self.store.start,shop,sender,operation)
        except ValueError:return await self.reply(shop,'recovery_baseline_required')
        # Declaration itself requests no media, and is guarded by canonical Danger.
        reply=await self.reply(shop,'recovery_declaration')
        if reply.kind!='danger':reply=reply.model_copy(update={'reply_markup':{'inline_keyboard':[[{'text':text(shop['language'],'recovery_declare_button'),'callback_data':'recovery:'+job['report_id']}]]}})
        return reply

    async def declare(self,sender: int,report_id: str) -> InventoryReply:
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        if not shop:return await self.reply(None,'recovery_owner_required')
        try:job=await asyncio.to_thread(self.store.declare,report_id,sender)
        except MediaIngestError:return await self.reply(shop,'recovery_owner_required')
        return await self.reply(shop,'recovery_after_request' if job['status']!='awaiting_declaration' else 'recovery_blocked')

    async def handle_video(self,sender: int,update_id: int,message_id: int,telegram_date: int,video: VideoMedia,processing_started_at: datetime|None=None) -> InventoryReply:
        start=time.monotonic();shop=await asyncio.to_thread(self.store.owner_shop,sender)
        job=await self.active_context(sender,message_id,video.file_unique_id)
        if not shop or not job:return await self.reply(shop,'recovery_owner_required')
        now=processing_started_at or datetime.now(UTC)
        try:
            sent=datetime.fromtimestamp(telegram_date,UTC)
            if sent>now:raise ValueError()
            job=await asyncio.to_thread(self.store.bind_upload,job['report_id'],sender,message_id,sent,video,now)
        except (ValueError,OverflowError,MediaIngestError):return await self.reply(shop,'recovery_processing_unavailable')
        owner=await asyncio.to_thread(self.store.claim_job,job['report_id'])
        try:
            upload=job['upload']
            request=MediaRequest(shop_id=shop['shop_id'],kind='after_video',sender_chat_id=sender,message_id=message_id,file_id=video.file_id,file_unique_id=video.file_unique_id,
                declared_size=video.file_size,declared_mime=video.mime_type,received_at=upload['received_at'],telegram_date=upload['telegram_date'],lat=job['lat'],lng=job['lng'],location_attribution='confirmed_shop',is_demo=job['is_demo'])
            try:media=await self.media.ingest_media(request)
            except MediaIngestError:
                if job['status']!='awaiting_declaration':
                    await asyncio.to_thread(self.store.update_job,job['report_id'],owner,status='assessment_unavailable')
                return await self.reply(shop,'recovery_processing_unavailable' if job['status']!='awaiting_declaration' else 'recovery_declaration')
            await asyncio.to_thread(self.store.update_job,job['report_id'],owner,media_id=media.record.media_id)
            await asyncio.to_thread(self.store.attach_photo,job['report_id'],media.record.media_id)
            if await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
            if job['status']=='awaiting_declaration':return await self.reply(shop,'recovery_declaration')
            assessment=LossAssessment.model_validate(job['assessment']).validate_baseline(job['baseline'],upload['duration']) if job.get('assessment') else None
            if assessment is None:
                try:
                    async with asyncio.timeout(max(.001,self.total_budget_seconds-(time.monotonic()-start))):
                        for attempt in range(2):
                            if await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
                            try:
                                assessment=await self.assessor.assess(media,job['report_id'],job['is_demo'],upload['duration'],job['baseline'])
                                assessment.validate_baseline(job['baseline'],upload['duration']);break
                            except (ValueError,httpx.TransportError,TimeoutError):
                                if attempt:raise
                            except APIError as error:
                                if attempt or not (isinstance(error.code,int) and (error.code==429 or 500<=error.code<600)):raise
                except Exception:
                    await asyncio.to_thread(self.store.update_job,job['report_id'],owner,status='assessment_unavailable')
                    return await self.reply(shop,'recovery_processing_unavailable')
            await asyncio.to_thread(self.store.update_job,job['report_id'],owner,status='complete',assessment=assessment.model_dump())
            if await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
            value=text(shop['language'],'recovery_estimate',value_rm=f'{assessment.total_loss_rm:.2f}') if assessment.total_loss_rm is not None else text(shop['language'],'recovery_estimate_unavailable')
            token=await asyncio.to_thread(self.store.token,job['report_id'])
            reply=await self.reply(shop,'recovery_complete')
            if reply.kind=='danger':return reply
            return reply.model_copy(update={'text':reply.text+'\n'+value+'\n'+self.web_base_url+'/report/'+job['report_id']+'#key='+token})
        finally:await asyncio.to_thread(self.store.release_job,job['report_id'],owner)

    async def handle_photo(self,sender: int,update_id: int,message_id: int,telegram_date: int,photo: PhotoMedia,processing_started_at: datetime|None=None) -> InventoryReply:
        shop=await asyncio.to_thread(self.store.owner_shop,sender);job=await self.active_context(sender,message_id,photo.file_unique_id)
        if not shop or not job or job['status']=='awaiting_declaration':return await self.reply(shop,'recovery_owner_required')
        now=processing_started_at or datetime.now(UTC)
        try:
            sent=datetime.fromtimestamp(telegram_date,UTC)
            if sent>now:raise ValueError()
            job=await asyncio.to_thread(self.store.bind_photo,job['report_id'],sender,message_id,photo.file_unique_id)
            request=MediaRequest(shop_id=shop['shop_id'],kind='waterline_photo',sender_chat_id=sender,message_id=message_id,file_id=photo.file_id,file_unique_id=photo.file_unique_id,
                declared_size=photo.file_size,received_at=now,telegram_date=sent,lat=job['lat'],lng=job['lng'],location_attribution='confirmed_shop',is_demo=job['is_demo'])
            media=await self.media.ingest_media(request)
            await asyncio.to_thread(self.store.attach_photo,job['report_id'],media.record.media_id)
            await asyncio.to_thread(self.store.collection('recovery_jobs').document(job['report_id']).update,{'attachment_pending':False})
        except (ValueError,MediaIngestError):return await self.reply(shop,'recovery_processing_unavailable')
        return await self.reply(shop,'recovery_photo_received')


def create_recovery_service(settings):
    from api.inventory import create_inventory_service
    from api.report_store import ReportStore
    from api.active_risk import ActiveRiskStore
    from api.agents.loss_comparison import LossAssessor
    original=create_inventory_service(settings)
    # Reuse ingestion resources; replace only the owned store and assessment agent.
    store=ReportStore(original.store.client,settings.hash_salt,risks=ActiveRiskStore(original.store.client,max_age=settings.official_max_age))
    original.media.authorize=store.authorize_media
    active=RecoveryService(store,original.media,LossAssessor(settings),web_base_url=settings.web_base_url,destinations=original.destinations)
    for name in ('_http','_storage','_sinks','_owned'):setattr(active,name,getattr(original,name))
    return active

class LazyRecoveryService:
    def __init__(self,settings):self.settings=settings;self.active=None
    def _service(self):
        if self.active is None:self.active=create_recovery_service(self.settings)
        return self.active
    async def active_context(self,sender: int,message_id: int|None=None,file_unique_id: str|None=None) -> dict|None:
        # Lookup does not initialize the model/downloader just to route a message.
        if self.active:return await self.active.active_context(sender,message_id,file_unique_id)
        from api.tools.firestore import create_firestore_client
        from api.report_store import ReportStore
        client=create_firestore_client(self.settings)
        try:
            store=ReportStore(client,self.settings.hash_salt)
            return await asyncio.to_thread(store.resolve_context,sender,message_id,file_unique_id)
        finally:client.close()
    async def exit(self,*args):return await self._service().exit(*args)
    async def request_photo(self,*args):return await self._service().request_photo(*args)
    async def start(self,*args):return await self._service().start(*args)
    async def declare(self,*args):return await self._service().declare(*args)
    async def handle_video(self,*args,**kwargs):return await self._service().handle_video(*args,**kwargs)
    async def handle_photo(self,*args,**kwargs):return await self._service().handle_photo(*args,**kwargs)
    async def recheck_reply(self,*args):return await self._service().recheck_reply(*args)
    async def close(self):
        if self.active:await self.active.close()
