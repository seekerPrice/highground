"""Native-video inventory, exact lift-first display and final Danger prompt guard."""
import asyncio
from datetime import UTC,datetime
import time
from api.config import Settings
from api.inventory_models import VideoMedia,InventoryAssessment,InventoryReply
from api.inventory_store import InventoryStore
from api.media import MediaService
from api.media_models import MediaRequest,MediaIngestError
from api.agents.inventory_loss import InventoryAssessor
from api.i18n import text,catalog
from api.alert_composer import render_danger

class InventoryService:
    def __init__(self,store:InventoryStore,media:MediaService,assessor:InventoryAssessor,*,destinations=None,total_budget_seconds:float=35):
        if not 0<total_budget_seconds<=35:raise ValueError('Inventory budget must be bounded')
        self.store,self.media,self.assessor,self.destinations=store,media,assessor,destinations
        self.total_budget_seconds=total_budget_seconds

    async def danger_reply(self,shop:dict)->InventoryReply:
        destination=await asyncio.to_thread(self.destinations.nearest,shop['lat'],shop['lng'],('pps','high_ground')) if self.destinations else None
        rendered,markup=render_danger(shop.get('language','en'),bool(shop.get('is_demo')),destination)
        return InventoryReply(text=rendered,reply_markup=markup,shop_id=shop['shop_id'],language=shop.get('language','en'),is_demo=bool(shop.get('is_demo')),kind='danger')

    async def reply(self,shop:dict|None,key:str,*,inventory:dict|None=None,integrity:bool=False)->InventoryReply:
        shop=shop or {};language=shop.get('language','en')
        if shop.get('shop_id') and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        pieces=[text(language,'simulation_label')] if shop.get('is_demo') else []
        pieces.append(text(language,key))
        if inventory:
            pieces.append(text(language,'inventory_total',value_rm=f"{inventory['total_est_value_rm']:.2f}",confidence=f"{inventory['confidence']:.2f}"))
            pieces.append(text(language,'lift_first_heading'))
            for item in inventory['lift_first']:
                pieces.append(text(language,'item_estimate_line',item_name=item['item_name'],qty=f"{item['qty']:g}",value_rm=f"{item['value_rm']:.2f}"))
            pieces.append(text(language,'stock_value_estimate',value_rm=f"{inventory['lift_first_value_rm']:.2f}"))
            pieces.append(text(language,'rm_estimate_note'))
            pieces.append(text(language,'integrity_verified' if integrity else 'integrity_pending'))
        if not catalog(language)['_reviewed']:pieces.append(text(language,'translation_notice'))
        rendered='\n'.join(pieces)
        if len(rendered)>4096:raise ValueError('Inventory reply exceeds Telegram limit; no displayed items truncated')
        return InventoryReply(text=rendered,shop_id=shop.get('shop_id'),language=language,is_demo=bool(shop.get('is_demo')),
            inventory_id=inventory['inventory_id'] if inventory else None,kind='inventory' if inventory else ('prompt' if key=='inventory_request' else 'unavailable'))

    async def request_video(self,sender_chat_id:int)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        return await self.reply(shop,'inventory_request' if shop else 'photo_registration_required')

    async def recheck_reply(self,sender_chat_id:int,reply:InventoryReply)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        return reply

    async def handle_video(self,sender_chat_id:int,update_id:int,message_id:int,telegram_date:int,video:VideoMedia,
                           processing_started_at:datetime|None=None)->InventoryReply:
        start=time.monotonic();shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if not shop:return await self.reply(None,'photo_registration_required')
        now=processing_started_at or datetime.now(UTC)
        if type(telegram_date) is not int or now.tzinfo is None:return await self.reply(shop,'inventory_invalid')
        try:
            sent=datetime.fromtimestamp(telegram_date,UTC)
            if sent>now:raise ValueError()
            job=await asyncio.to_thread(self.store.begin_video,shop,sender_chat_id,message_id,sent,video,now)
        except (ValueError,OverflowError):return await self.reply(shop,'inventory_invalid')
        owner=await asyncio.to_thread(self.store.claim_job,job['inventory_id'])
        try:
            request=MediaRequest(shop_id=shop['shop_id'],kind=job['kind']+'_video',sender_chat_id=sender_chat_id,
                message_id=message_id,file_id=video.file_id,file_unique_id=video.file_unique_id,declared_size=video.file_size,
                declared_mime=video.mime_type,received_at=job['received_at'],telegram_date=job['telegram_date'],
                lat=job['lat'],lng=job['lng'],location_attribution='confirmed_shop',is_demo=job['is_demo'])
            try:media=await self.media.ingest_media(request)
            except MediaIngestError as error:
                return await self.reply(shop,'inventory_oversize' if error.code=='upload_too_large' else 'inventory_processing_unavailable')
            await asyncio.to_thread(self.store.update_job,job['inventory_id'],owner,media_id=media.record.media_id)
            job['media_id']=media.record.media_id
            # Preserve unsolicited bytes at Danger but never run stock analysis or request further evidence.
            if await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
            assessment=InventoryAssessment.model_validate(job['assessment']).validate_duration(job['duration']) if job.get('assessment') else None
            model_start=time.monotonic()
            if assessment is None:
                try:
                    remaining=self.total_budget_seconds-(time.monotonic()-start)
                    async with asyncio.timeout(max(.001,remaining)):
                        for attempt in range(2):
                            try:
                                assessment=await self.assessor.assess(media,job['inventory_id'],job['is_demo'],job['duration'])
                                assessment.validate_duration(job['duration'])
                                break
                            except ValueError:
                                if attempt==1:raise
                except Exception:
                    await asyncio.to_thread(self.store.update_job,job['inventory_id'],owner,status='assessment_unavailable',model_elapsed_ms=int((time.monotonic()-model_start)*1000))
                    return await self.reply(shop,'inventory_processing_unavailable')
            await asyncio.to_thread(self.store.update_job,job['inventory_id'],owner,assessment=assessment.model_dump(),model_elapsed_ms=job.get('model_elapsed_ms',int((time.monotonic()-model_start)*1000)))
            if not assessment.items:
                # An empty extraction means unavailable visual inventory, never verified zero stock.
                await asyncio.to_thread(self.store.update_job,job['inventory_id'],owner,status='assessment_unavailable')
                return await self.reply(shop,'inventory_processing_unavailable')
            # Model results remain private even when Danger arrives during processing; suppress stock display.
            inventory=await asyncio.to_thread(self.store.save_inventory,job,owner,assessment)
            integrity=await self.media.verify_integrity(media.record.media_id)
            await asyncio.to_thread(self.store.update_job,job['inventory_id'],owner,processing_elapsed_ms=int((time.monotonic()-start)*1000),
                receipt_to_completion_ms=max(0,int((datetime.now(UTC)-job['received_at']).total_seconds()*1000)))
            return await self.reply(shop,'inventory_complete',inventory=inventory,integrity=integrity)
        finally:await asyncio.to_thread(self.store.release_job,job['inventory_id'],owner)

    async def close(self)->None:
        await self.assessor.close()
        if getattr(self,'_http',None):await self._http.aclose()
        if getattr(self,'_storage',None):self._storage.close()
        if getattr(self,'_owned',False):self.store.client.close();self._sinks.close()


def create_inventory_service(settings:Settings)->InventoryService:
    import httpx
    from api.media import TelegramDownloader,EvidenceLedger
    from api.media_store import MediaStore
    from api.tools.firestore import create_firestore_client
    from api.tools.storage import OriginalStorage,create_storage_client
    from api.tools.cloud_events import create_event_sinks
    from api.destinations import DestinationLookup
    client=create_firestore_client(settings);store=InventoryStore(client,settings.hash_salt)
    http=httpx.AsyncClient(timeout=3,follow_redirects=False);storage=OriginalStorage(create_storage_client(settings),settings.gcs_bucket)
    sinks=create_event_sinks(settings)
    media=MediaService(MediaStore(client,settings.hash_salt),TelegramDownloader(settings.telegram_bot_token,http),storage,
        EvidenceLedger(sinks.analytics,settings.gcp_project,settings.bigquery_dataset),store.authorize_media)
    active=InventoryService(store,media,InventoryAssessor(settings),destinations=DestinationLookup(client,radius_m=settings.destination_search_radius_m))
    active._http=http;active._storage=storage;active._sinks=sinks;active._owned=True
    return active

class LazyInventoryService:
    """Create media/model clients only when a registered user actually sends video."""
    def __init__(self,settings:Settings):self.settings=settings;self.active=None
    def _service(self)->InventoryService:
        if self.active is None:self.active=create_inventory_service(self.settings)
        return self.active
    async def handle_video(self,sender_chat_id:int,update_id:int,message_id:int,telegram_date:int,video:VideoMedia,processing_started_at:datetime|None=None)->InventoryReply:
        return await self._service().handle_video(sender_chat_id,update_id,message_id,telegram_date,video,processing_started_at)
    async def _cold_reply(self,chat_id:int,reply:InventoryReply|None)->InventoryReply:
        from api.tools.firestore import create_firestore_client
        from api.destinations import DestinationLookup
        client=create_firestore_client(self.settings)
        try:
            store=InventoryStore(client,self.settings.hash_salt)
            helper=InventoryService(store,None,None,destinations=DestinationLookup(client,radius_m=self.settings.destination_search_radius_m))
            return await helper.recheck_reply(chat_id,reply) if reply else await helper.request_video(chat_id)
        finally:client.close()
    async def request_video(self,chat_id:int)->InventoryReply:
        return await self.active.request_video(chat_id) if self.active else await self._cold_reply(chat_id,None)
    async def recheck_reply(self,chat_id:int,reply:InventoryReply)->InventoryReply:
        return await self.active.recheck_reply(chat_id,reply) if self.active else await self._cold_reply(chat_id,reply)
    async def close(self)->None:
        if self.active:await self.active.close()
