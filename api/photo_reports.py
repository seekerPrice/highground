"""Confirmed-location reports; deterministic risk rules consume uncertain ADK depiction."""
import asyncio
from datetime import UTC,datetime,timedelta
import time
from hashlib import sha256
from typing import Callable, TYPE_CHECKING
from api.config import Settings
if TYPE_CHECKING:
    from api.photo_store import PhotoStore
    from api.media import MediaService
    from api.agents.photo_triage import PhotoAssessor
    from api.dispatch import DispatchService

from api.photo_models import PhotoMedia,PhotoReply,PhotoAssessment
from api.media_models import MediaRequest,MediaIngestError
from api.dispatch_models import EventRequest
from api.i18n import text,catalog
from api.alert_composer import render_danger
from api.tools.geo import distance_m


def triage_photo(assessment:PhotoAssessment|None,reports:list[dict])->tuple[str,int,float,str]:
    if assessment and assessment.assessment_status=='assessed' and assessment.is_flooding and assessment.confidence>=.7:
        if assessment.water_location=='inside_premises':return 'danger',500,assessment.confidence,'High-confidence flooding depiction inside premises; location confirmed by reporter.'
        return 'warning',500,assessment.confidence,'High-confidence flooding depiction; location confirmed by reporter.'
    eligible=[r for r in reports if r.get('corroboration_eligible') and r.get('sha256')]
    # Two distinct shops AND distinct original-byte identities, not duplicate forwarded photos.
    if any(a['shop_id']!=b['shop_id'] and a['sha256']!=b['sha256'] for i,a in enumerate(eligible) for b in eligible[i+1:]):
        return 'warning',500,max((r.get('confidence',0) for r in eligible),default=0),'Two independent unverified nearby shop reports within 30 minutes; locations confirmed by reporters.'
    return 'watch',300,assessment.confidence if assessment else 0,'Single unverified shop report; scene assessment uncertain.'


class PhotoReportService:
    def __init__(self, store: 'PhotoStore', media: 'MediaService', assessor: 'PhotoAssessor',
                 dispatch: 'DispatchService', *, clock: Callable[[], datetime]=lambda:datetime.now(UTC),
                 total_budget_seconds:float=8):
        self.store,self.media,self.assessor,self.dispatch,self.clock=store,media,assessor,dispatch,clock
        if not 0<total_budget_seconds<=8:raise ValueError('Photo processing budget must be bounded')
        self.total_budget_seconds=total_budget_seconds
    async def _reply(self,code:str,record:dict|None=None,**values)->PhotoReply:
        record=record or {};language=record.get('language','en');demo=record.get('is_demo',False)
        shop_id=record.get('shop_id')
        if code=='danger' or (shop_id and await asyncio.to_thread(self.store.danger_active,shop_id)):
            lookup=getattr(getattr(self.dispatch,'composer',None),'destinations',None)
            lat=record.get('lat',record.get('default_lat'));lng=record.get('lng',record.get('default_lng'))
            destination=await asyncio.to_thread(lookup.nearest,lat,lng,('pps','high_ground')) if lookup and lat is not None and lng is not None else None
            rendered,markup=render_danger(language,demo,destination)
            return PhotoReply(code='danger',language=language,is_demo=demo,text=rendered,reply_markup=markup)
        key={'registration_required':'photo_registration_required','confirm_at_shop':'photo_confirm_at_shop',
             'share_location':'photo_share_location','confirm_shared_location':'photo_confirm_shared_location',
             'rate_limited':'photo_rate_limited','invalid_photo':'photo_invalid','upload_too_large':'media_oversize',
             'source_unavailable':'photo_unavailable','report_recorded':'photo_recorded','report_rejected':'photo_rejected',
             'report_stale':'photo_stale','location_invalid':'photo_location_invalid'}[code]
        arguments={}
        if code=='report_recorded':
            confidence=values.get('confidence')
            arguments={'confidence':f'{confidence:.2f}' if confidence is not None else text(language,'assessment_unavailable'),
                       'level':text(language,'level_'+values.get('level','watch'))}
        rendered=text(language,key,**arguments);markup=None
        if demo:rendered=text(language,'simulation_label')+'\n'+rendered
        if not catalog(language)['_reviewed']:rendered+='\n'+text(language,'translation_notice')
        report_id=record.get('report_id')
        if code in ('confirm_at_shop','confirm_shared_location'):
            markup={'inline_keyboard':[[{'text':text(language,'yes'),'callback_data':f'photo:{report_id}:yes'},
                                       {'text':text(language,'no'),'callback_data':f'photo:{report_id}:no'}]]}
        elif code=='share_location':markup={'keyboard':[[{'text':text(language,'photo_share_location'),'request_location':True}]],'one_time_keyboard':True,'resize_keyboard':True}
        return PhotoReply(code=code,text=rendered,reply_markup=markup,language=language,is_demo=demo,report_id=report_id,**values)
    async def recheck_reply(self,sender_chat_id:int,reply:PhotoReply)->PhotoReply:
        record=await asyncio.to_thread(self.store.get,reply.report_id) if reply.report_id else None
        if record is None:record=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if record and await asyncio.to_thread(self.store.danger_active,record['shop_id']):
            return await self._reply('danger',record)
        return reply

    async def bound_photo_report(self,sender:int,message_id:int,file_unique_id:str):
        return await asyncio.to_thread(self.store.bound_photo_report,sender,message_id,file_unique_id)
    async def handle_photo(self,sender_chat_id:int,update_id:int,message_id:int,telegram_date:int,photo:PhotoMedia,
                           processing_started_at:datetime|None=None)->PhotoReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if not shop:return await self._reply('registration_required')
        now=processing_started_at or self.clock()
        if type(telegram_date) is not int or telegram_date<0 or now.tzinfo is None:
            return await self._reply('invalid_photo',shop)
        try:
            sent_at=datetime.fromtimestamp(telegram_date,UTC)
            if sent_at>now:return await self._reply('invalid_photo',shop)
            record=await asyncio.to_thread(self.store.begin,shop,sender_chat_id,message_id,sent_at,photo,now)
        except (ValueError,OverflowError):return await self._reply('invalid_photo',shop)
        except MediaIngestError as error:return await self._reply('rate_limited' if error.code=='rate_limited' else 'invalid_photo',shop)
        if record.get('event_id'):
            return await self._reply('danger' if record.get('level')=='danger' else 'report_recorded',record,
                                     confidence=record.get('assessment',{}).get('confidence') if record.get('assessment') else None,
                                     level=record['level'],event_id=record['event_id'])
        owner=await asyncio.to_thread(self.store.claim,record['report_id'])
        upload_start=time.monotonic()
        try:
            media=await self.media.ingest_media(self._media_request(record,sender_chat_id,
                                        await asyncio.to_thread(self.store.private,record['report_id'])),defer_ledger=True)
            await asyncio.to_thread(self.store.update,record['report_id'],owner,media_id=media.record.media_id,sha256=media.record.sha256)
            try:await self.media.resume_ledger(media.record.media_id)
            except MediaIngestError:pass
            if 'confirmation_requested_at' not in record:
                await asyncio.to_thread(self.store.update,record['report_id'],owner,confirmation_requested_at=self.clock(),
                                        ingest_elapsed_ms=int((time.monotonic()-upload_start)*1000))
        except MediaIngestError as error:
            code = ('upload_too_large' if error.code=='upload_too_large' else
                    'invalid_photo' if error.code in ('invalid_media','mime_mismatch','file_identity_mismatch',
                                                     'file_size_mismatch','invalid_file_path','metadata_conflict') else
                    'source_unavailable')
            return await self._reply(code,record)
        finally:await asyncio.to_thread(self.store.release,record['report_id'],owner)
        return await self._reply('confirm_at_shop',record)
    async def pending_location_report_id(self,chat_id:int)->str|None:
        if not await asyncio.to_thread(self.store.shop_for_sender,chat_id):return None
        return await asyncio.to_thread(self.store.pending_location_report_id,chat_id)
    async def confirm_report_location(self,sender_chat_id:int,pending_report_id:str,at_shop:bool|None=None,
                                      lat:float|None=None,lng:float|None=None)->PhotoReply:
        record=await asyncio.to_thread(self.store.get,pending_report_id)
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if not record or not shop or record['shop_id']!=shop['shop_id']:return await self._reply('registration_required')
        try:
            if at_shop is False:
                await asyncio.to_thread(self.store.request_shared,pending_report_id,sender_chat_id)
                return await self._reply('share_location',record)
            if at_shop is None:
                if lat is None or lng is None:raise ValueError()
                distance_m(lat,lng,lat,lng)
                await asyncio.to_thread(self.store.propose_shared,pending_report_id,sender_chat_id,lat,lng)
                return await self._reply('confirm_shared_location',record,lat=lat,lng=lng)
            # yes confirms either the proposed shared pin or the original shop location.
            shared=record.get('status')=='awaiting_shared_confirmation'
            if 'confirmed_at' in record:
                shared=record['location_attribution']=='confirmed_shared'
            lat,lng=(record.get('proposed_lat',record.get('lat')),record.get('proposed_lng',record.get('lng'))) if shared else (record['default_lat'],record['default_lng'])
            distance_m(lat,lng,lat,lng)
            attribution='confirmed_shared' if shared else 'confirmed_shop'
            record=await asyncio.to_thread(self.store.confirm,pending_report_id,sender_chat_id,lat,lng,attribution,self.clock())
        except (MediaIngestError,ValueError):return await self._reply('location_invalid',record)
        return await self._process(record,sender_chat_id)
    def _media_request(self,record:dict,sender:int,private:dict)->MediaRequest:
        return MediaRequest(shop_id=record['shop_id'],kind='flood_photo',sender_chat_id=sender,
            message_id=private['message_id'],file_id=private['file_id'],file_unique_id=private['file_unique_id'],
            declared_size=private.get('file_size'),telegram_date=record['telegram_date'],received_at=record['received_at'],
            lat=record['default_lat'],lng=record['default_lng'],location_attribution='unconfirmed_shop',is_demo=record['is_demo'])

    async def _process(self,record:dict,sender:int)->PhotoReply:
        owner=await asyncio.to_thread(self.store.claim,record['report_id'])
        prior_elapsed=record.get('ingest_elapsed_ms',0)/1000+max(0,(self.clock()-record['confirmed_at']).total_seconds())
        start=time.monotonic()-prior_elapsed
        # Persisted immutable Danger triage is this report's prepared dispatch intent.
        # It may resume its same Danger event after reporter invalidation; no lower level may bypass the guard.
        resume_danger = record.get('triage', {}).get('level') == 'danger'
        try:
            # The first confirmed processing clock persists across retries; confirmation wait remains separate.
            if self.clock()-record['received_at']>timedelta(minutes=30):
                return await self._reply('report_stale',record)
            private=await asyncio.to_thread(self.store.private,record['report_id'])
            request=self._media_request(record,sender,private)
            try:media=await self.media.ingest_media(request,defer_ledger=True)
            except MediaIngestError as error:return await self._reply('upload_too_large' if error.code=='upload_too_large' else 'source_unavailable',record)
            await asyncio.to_thread(self.store.update,record['report_id'],owner,media_id=media.record.media_id,sha256=media.record.sha256)
            if not resume_danger and await asyncio.to_thread(self.store.danger_active,record['shop_id']):
                return await self._reply('danger',record)
            assessment=PhotoAssessment.model_validate(record['assessment']) if record.get('assessment') else None
            if assessment is None and not record.get('assessment_attempted'):
                remaining=self.total_budget_seconds-(time.monotonic()-start)-1
                if remaining>0:
                    try:
                        async with asyncio.timeout(remaining):
                            for attempt in range(2):
                                try:
                                    assessment=await self.assessor.assess(media,record['report_id'],record['is_demo'])
                                    break
                                except ValueError:
                                    if attempt==1:raise
                    except Exception:assessment=None
                await asyncio.to_thread(self.store.update,record['report_id'],owner,assessment=assessment.model_dump() if assessment else None,assessment_attempted=True)
            rejected=assessment and assessment.assessment_status=='assessed' and not assessment.is_flooding
            positive=bool(assessment and assessment.assessment_status=='assessed' and assessment.is_flooding)
            eligible=not bool(rejected)
            evidence_status='rejected' if rejected else ('positive' if positive else 'unverified')
            await asyncio.to_thread(self.store.update,record['report_id'],owner,evidence_status=evidence_status,
                                    corroboration_eligible=eligible,confidence=assessment.confidence if assessment else 0)
            if rejected:return await self._reply('report_rejected',record)
            # A Danger arriving during assessment cannot be reduced by this report.
            if not resume_danger and await asyncio.to_thread(self.store.danger_active,record['shop_id']):
                return await self._reply('danger',record)
            if record.get('triage'):
                rule=record['triage']
                level,radius,confidence,reason=rule['level'],rule['radius'],rule['confidence'],rule['reason']
            else:
                reports=await asyncio.to_thread(self.store.recent_reports,record['lat'],record['lng'],self.clock(),record['is_demo'])
                level,radius,confidence,reason=triage_photo(assessment,reports)
                await asyncio.to_thread(self.store.update,record['report_id'],owner,
                    triage={'level':level,'radius':radius,'confidence':confidence,'reason':reason})
            event=EventRequest(request_id='photo:'+record['report_id'],source='shop_report',simulation=record['is_demo'],
                reporter_shop_id=record['shop_id'],processing_started_at=record['processing_started_at'],
                warning_structure='warning_intro_fallback',level=level,lat=record['lat'],lng=record['lng'],
                radius_m=radius,confidence=confidence,reason=reason)
            if level=='danger' and getattr(self.dispatch,'vehicle_actions',None) and getattr(self.dispatch,'active_risk',None) is None:
                event_id=sha256(f'{event.source}:{event.request_id}'.encode()).hexdigest()
                await asyncio.to_thread(self.dispatch.vehicle_actions.supersede,record['shop_id'],event_id=event_id,
                                        episode_id=event_id,at=record['processing_started_at'])
            result=await self.dispatch.process(event)
            await asyncio.to_thread(self.store.update,record['report_id'],owner,event_id=result['event_id'],level=level,status='dispatched',
                                    processing_elapsed_ms=int((time.monotonic()-start)*1000))
            # Ledger completion is recoverable and follows urgent neighbor dispatch.
            try:await self.media.resume_ledger(media.record.media_id)
            except MediaIngestError:pass
            return await self._reply('danger' if level=='danger' else 'report_recorded',record,level=level,confidence=assessment.confidence if assessment else None,event_id=result['event_id'])
        finally:await asyncio.to_thread(self.store.release,record['report_id'],owner)
    async def close(self) -> None:
        await self.assessor.close()
        if getattr(self,'_owned_http',None):await self._owned_http.aclose()
        if getattr(self,'_owned_storage',None):self._owned_storage.close()
        if getattr(self,'_owns_dispatch',False):await self.dispatch.close()
        if getattr(self,'_owned_http',None):self.store.client.close()


def create_photo_report_service(settings: Settings, dispatch_service: 'DispatchService | None'=None)->PhotoReportService:
    import httpx
    from api.media import MediaService,TelegramDownloader,EvidenceLedger
    from api.media_store import MediaStore
    from api.photo_store import PhotoStore
    from api.agents.photo_triage import PhotoAssessor
    from api.tools.storage import OriginalStorage,create_storage_client
    from api.tools.firestore import create_firestore_client
    from api.dispatch import create_dispatch_service
    client=create_firestore_client(settings)
    store=PhotoStore(client,settings.hash_salt)
    http=httpx.AsyncClient(follow_redirects=False,timeout=3)
    storage=OriginalStorage(create_storage_client(settings),settings.gcs_bucket)
    dispatch=dispatch_service or create_dispatch_service(settings)
    ledger=EvidenceLedger(dispatch.sinks.analytics,settings.gcp_project,settings.bigquery_dataset)
    media=MediaService(MediaStore(client,settings.hash_salt),TelegramDownloader(settings.telegram_bot_token,http),
                       storage,ledger,store.authorize_media)
    service=PhotoReportService(store,media,PhotoAssessor(settings),dispatch)
    service._owned_http=http;service._owned_storage=storage;service._owns_dispatch=dispatch_service is None
    return service


class LazyPhotoReportService:
    """Create upload/model clients only for an actual report operation."""
    def __init__(self, settings: Settings, dispatch_service: 'DispatchService | None'=None):
        self.settings, self.dispatch_service = settings, dispatch_service
        self.active = None

    def _service(self) -> PhotoReportService:
        if self.active is None:
            self.active = create_photo_report_service(self.settings, self.dispatch_service)
        return self.active

    async def bound_photo_report(self,sender:int,message_id:int,file_unique_id:str):
        if self.active:return await self.active.bound_photo_report(sender,message_id,file_unique_id)
        from api.photo_store import PhotoStore
        from api.tools.firestore import create_firestore_client
        client=create_firestore_client(self.settings)
        try:return await asyncio.to_thread(PhotoStore(client,self.settings.hash_salt).bound_photo_report,sender,message_id,file_unique_id)
        finally:client.close()

    async def handle_photo(self, sender_chat_id: int, update_id: int, message_id: int, telegram_date: int,
                           photo: PhotoMedia, processing_started_at: datetime | None=None) -> PhotoReply:
        return await self._service().handle_photo(sender_chat_id, update_id, message_id, telegram_date, photo, processing_started_at)

    async def confirm_report_location(self, sender_chat_id: int, pending_report_id: str,
                                      at_shop: bool | None=None, lat: float | None=None, lng: float | None=None) -> PhotoReply:
        return await self._service().confirm_report_location(sender_chat_id, pending_report_id, at_shop, lat, lng)

    async def pending_location_report_id(self, chat_id: int) -> str | None:
        if self.active is not None:
            return await self.active.pending_location_report_id(chat_id)
        from api.photo_store import PhotoStore
        from api.tools.firestore import create_firestore_client
        client = create_firestore_client(self.settings)
        try:
            return await asyncio.to_thread(PhotoStore(client, self.settings.hash_salt).pending_location_report_id, chat_id)
        finally:
            client.close()

    async def recheck_reply(self,chat_id: int,reply: PhotoReply) -> PhotoReply:
        if self.active is not None:return await self.active.recheck_reply(chat_id,reply)
        from api.photo_store import PhotoStore
        from api.tools.firestore import create_firestore_client
        from api.destinations import DestinationLookup
        client=create_firestore_client(self.settings)
        try:
            store=PhotoStore(client,self.settings.hash_salt)
            record=await asyncio.to_thread(store.get,reply.report_id) if reply.report_id else await asyncio.to_thread(store.shop_for_sender,chat_id)
            if record and await asyncio.to_thread(store.danger_active,record['shop_id']):
                lat=record.get('lat',record.get('default_lat'));lng=record.get('lng',record.get('default_lng'))
                lookup=DestinationLookup(client,radius_m=self.settings.destination_search_radius_m)
                destination=await asyncio.to_thread(lookup.nearest,lat,lng,('pps','high_ground')) if lat is not None and lng is not None else None
                rendered,markup=render_danger(reply.language,record.get('is_demo',False),destination)
                return PhotoReply(code='danger',text=rendered,reply_markup=markup,language=reply.language,is_demo=record.get('is_demo',False))
            return reply
        finally:client.close()

    async def close(self) -> None:
        if self.active is not None:
            await self.active.close()
