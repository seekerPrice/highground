"""Owner-only policy intake, bounded extraction and exact-copy deletion lifecycle."""
import asyncio
from dataclasses import dataclass
from datetime import UTC,datetime
from hashlib import sha256
import subprocess
import sys
import threading
import httpx
from google.genai.errors import APIError
from typing import Protocol
from pydantic import Field
from api.alert_composer import render_danger
from api.agents.sessions import session_user_id
from api.media import IngestedMedia
from api.policy_models import (PolicyDTO,PolicyOriginal,PolicyReply,PolicyAssessment,
    FrozenPolicyInventory,compare_policy,MAX_POLICY_BYTES)

POLICY_EN={
 'policy_owner_required':'Only the registered shop owner can use /policy.',
 'policy_disclosure':'Before uploading: HighGround deletes its stored policy copy after extraction by default, retaining only extracted fields and a SHA-256 receipt. Choose Keep before your first document to retain a successful extraction privately. Failed or cancelled extraction deletes HighGround’s stored copy even if you chose Keep. This does not delete your Telegram message or copies processed by external providers. Send one PDF or up to 5 policy photos (20 MB total). Photos require Done; use Cancel to stop.',
 'policy_keep_selected':'Keep selected for successful extraction. Send one PDF or up to 5 policy photos; use Done after the last photo. Failed or cancelled extraction still deletes HighGround’s stored copy.',
 'policy_choice_frozen':'Your retention choice was frozen at the first accepted document. To choose Keep now, cancel and start /policy again, then re-upload.',
 'policy_photo_received':'Policy photo received privately. Send any remaining policy pages, then choose Done. No extraction has started.',
 'policy_invalid':'Document not accepted. Use one PDF or up to 5 readable policy photos, at most 20 MB total. Do not mix PDF and photos. Cancel and start /policy again to replace the documents.',
 'policy_not_disclosed':'Start /policy and read the retention notice before uploading policy documents.',
 'policy_pending':'Policy processing is still in progress. Try Done again later or Cancel.',
 'policy_failed':'Policy extraction is unavailable. HighGround’s stored copies are being deleted, including any Keep selection. Start /policy again to re-upload.',
 'policy_cancelled':'Policy intake cancelled. HighGround’s stored copies are being deleted; Keep applies only to successful extraction.',
 'policy_deleted':'HighGround’s stored policy copy deleted. Extracted fields and SHA-256 receipts remain. This does not delete the Telegram message or external provider copies.',
 'policy_delete_pending':'Deletion of HighGround’s stored policy copy is pending. It is unavailable for viewing and will be retried.',
 'policy_result':'Document extraction completed. Insurer: {insurer}. Type: {policy_type}. Quoted wording: {quote}. Flood wording: {coverage}. Stock/contents limit: {limit}. Excess: {excess}. Expiry: {expiry}. Comparison: {comparison}. This does not establish current coverage or a guaranteed payout. Scope may differ from the inventory replacement-price estimate; excess is not added to cover. Check with your insurer.',
 'policy_retained':'HighGround’s stored policy copy is retained privately under your pre-upload Keep choice. Only the owner can access it; use Delete copy to remove it.',
 'policy_unknown':'Unknown',
 'policy_keep_button':'Keep',
 'policy_done_button':'Done',
 'policy_cancel_button':'Cancel',
 'policy_copy_button':'Send kept page {page} to this Telegram chat',
 'policy_delete_button':'Delete HighGround’s stored copy',
 'policy_cover_yes':'Flood cover is indicated by the quoted wording; current coverage is unverified',
 'policy_cover_no':'The quoted wording explicitly excludes flood; check with your insurer',
 'policy_cover_unclear':'Flood cover is unclear from the supplied document',
 'policy_gap':'Estimated stock/contents limit shortfall ≈RM {gap}, compared with frozen inventory estimate ≈RM {estimate}',
 'policy_no_gap':'No estimated stock/contents limit shortfall against the frozen inventory estimate ≈RM {estimate}; coverage and scope remain unverified',
 'policy_not_covered':'Explicit flood exclusion is indicated. Ask your insurer whether flood or special-perils add-on cover is appropriate',
 'policy_unclear':'The supplied document does not establish flood cover. Ask your insurer about flood or special-perils add-on cover',
 'policy_expired':'The document expiry date is past; current coverage is unknown',
 'policy_baseline_unavailable':'No usable frozen inventory replacement-price estimate; shortfall is unknown',
 'policy_limit_unavailable':'No unambiguous MYR stock/contents insured limit; shortfall is unknown',
 'policy_expiry_unknown':'Expiry is unknown; any estimated comparison does not establish current cover',
}

class PolicyDocument(PolicyDTO):
    file_id:str=Field(min_length=1,max_length=512)
    file_unique_id:str=Field(min_length=1,max_length=256)
    file_size:int|None=Field(default=None,gt=0)
    mime_type:str=Field(min_length=1,max_length=100)

@dataclass(frozen=True)
class PolicyUpload:
    intake_id:str
    upload_key:str
    media_id:str
    shop_id:str
    sender_chat_id:int
    message_id:int
    file_id:str
    file_unique_id:str
    mime_type:str
    declared_size:int|None
    telegram_date:datetime
    received_at:datetime
    lat:float
    lng:float
    is_demo:bool

@dataclass(frozen=True)
class PolicyRecovery:
    original:PolicyOriginal|None=None
    absence_verified:bool=False

class PolicyOriginals(Protocol):
    """Adapter contract for existing media/storage boundaries, never public storage.

    ingest durably reserves ownership/hash before PUT; it enforces max_bytes and
    structural validation before PUT. retire first tombstones every reserved ID,
    coordinating with the media write lease. recover uses only reserved identity
    and expected hash/owned PUT metadata, never Telegram re-download or arbitrary
    current object generation. delete confirms absence of exactly that generation;
    replacement generations are untouched. read verifies stored hash/generation.
    """
    async def ingest(self,request:PolicyUpload,*,max_bytes:int)->IngestedMedia:...
    async def retire(self,job:dict)->None:...
    async def recover(self,job:dict,upload:dict)->PolicyRecovery:...
    async def delete(self,original:PolicyOriginal)->bool:...
    async def read(self,original:PolicyOriginal)->IngestedMedia:...

# No original is written to disk, parsed in the web worker, or text-extracted.
# These are application bounds, not a claimed provider PDF page limit.
_PDF_LOCK=threading.Lock()
_PDF_CHILD="""
import resource,sys
resource.setrlimit(resource.RLIMIT_CPU,(2,2))
if sys.platform!='darwin':resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
from io import BytesIO
from pypdf import PdfReader
source=sys.stdin.buffer.read(20000001)
if not source or len(source)>20000000:sys.exit(2)
try:
 reader=PdfReader(BytesIO(source),strict=True)
 if reader.is_encrypted:sys.exit(2)
 count=len(reader.pages)
 if not 1<=count<=100:sys.exit(2)
 sys.stdout.write(str(count))
except Exception:sys.exit(2)
"""

def _rss_kib(pid:int)->int|None:
    try:
        result=subprocess.run(['/bin/ps','-o','rss=','-p',str(pid)],capture_output=True,text=True,timeout=.2,check=False)
        value=result.stdout.strip()
        return int(value) if result.returncode==0 and value.isdigit() else None
    except (OSError,subprocess.TimeoutExpired):return None

def _monitor_pdf(child,stop,violation):
    # macOS does not implement our RLIMIT_AS request. Sampled resident memory
    # may overshoot between polls; this is a disposal threshold, not a hard AS cap.
    if sys.platform!='darwin':return
    while not stop.is_set():
        if child.poll() is not None:return
        rss=_rss_kib(child.pid)
        if child.poll() is not None:return
        if rss is None or rss>256*1024:
            violation.set()
            try:child.kill()
            except ProcessLookupError:pass
            return
        stop.wait(.02)

def validate_policy_pdf(data:bytes)->int:
    if not data or len(data)>MAX_POLICY_BYTES or not data.startswith(b'%PDF-'):raise ValueError('policy_invalid_pdf')
    if not _PDF_LOCK.acquire(timeout=.1):raise ValueError('policy_pdf_busy')
    child=None;stop=threading.Event();violation=threading.Event();monitor=None
    try:
        child=subprocess.Popen([sys.executable,'-c',_PDF_CHILD],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        monitor=threading.Thread(target=_monitor_pdf,args=(child,stop,violation),daemon=True);monitor.start()
        try:output,_=child.communicate(data,timeout=3)
        except subprocess.TimeoutExpired:
            child.kill();child.communicate();raise ValueError('policy_invalid_pdf') from None
        if violation.is_set() or child.returncode!=0 or len(output)>3 or not output.isdigit() or not 1<=int(output)<=100:raise ValueError('policy_invalid_pdf')
        return int(output)
    finally:
        stop.set()
        if child is not None and child.poll() is None:
            child.kill();child.communicate()
        if monitor is not None:monitor.join(timeout=.3)
        _PDF_LOCK.release()

class PolicyService:
    def __init__(self,store,originals:PolicyOriginals,assessor,*,destinations=None,translate=None,total_budget_seconds:float=35):
        if not 0<total_budget_seconds<=35:raise ValueError('Policy budget must be bounded')
        self.store,self.originals,self.assessor=store,originals,assessor
        self.destinations,self.translate,self.total_budget_seconds=destinations,translate,total_budget_seconds
    def _text(self,language,key,**values):
        from api.i18n import placeholders
        arguments={name:values[name] for name in placeholders(POLICY_EN[key])}
        return self.translate(language,key,**arguments) if self.translate else POLICY_EN[key].format(**arguments)
    async def danger_reply(self,shop):
        destination=await asyncio.to_thread(self.destinations.nearest,shop['lat'],shop['lng'],('pps','high_ground')) if self.destinations else None
        text,markup=render_danger(shop.get('language','en'),bool(shop.get('is_demo')),destination)
        return PolicyReply(text=text,reply_markup=markup,shop_id=shop['shop_id'],language=shop.get('language','en'),is_demo=bool(shop.get('is_demo')),kind='danger')
    async def _reply(self,job,key,*,disclosure=False,kind='policy_prompt',**values):
        job=job or {};shop=await asyncio.to_thread(self.store.shop_for_sender,values.pop('sender')) if 'sender' in values else None
        if not job and shop:job=shop
        if job.get('shop_id') and await asyncio.to_thread(self.store.danger_active,job['shop_id']):return await self.danger_reply(shop or job)
        language=job.get('language','en');markup=None
        if key in ('policy_disclosure','policy_keep_selected','policy_photo_received'):
            buttons=[]
            if not job.get('choice_frozen'):buttons.append({'text':self._text(language,'policy_keep_button'),'callback_data':'policy:keep:'+job['intake_id']})
            if job.get('mode')=='photos':buttons.append({'text':self._text(language,'policy_done_button'),'callback_data':'policy:done:'+job['intake_id']})
            buttons.append({'text':self._text(language,'policy_cancel_button'),'callback_data':'policy:cancel:'+job['intake_id']});markup={'inline_keyboard':[buttons]}
        from api.i18n import text,catalog
        rendered=self._text(language,key,**values)
        if job.get('is_demo'):rendered=text(language,'simulation_label')+'\n'+rendered
        if not catalog(language)['_reviewed']:rendered+='\n'+text(language,'translation_notice')
        return PolicyReply(text=rendered,reply_markup=markup,shop_id=job.get('shop_id'),language=language,is_demo=bool(job.get('is_demo')),kind=kind,intake_id=job.get('intake_id'),disclosure=disclosure)
    async def recheck_reply(self,sender,reply):
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        return reply
    async def start(self,sender,operation):
        try:job=await asyncio.to_thread(self.store.start,sender,operation)
        except PermissionError:return await self._reply(None,'policy_owner_required',sender=sender)
        return await self._reply(job,'policy_keep_selected' if job['choice']=='keep' else 'policy_disclosure',disclosure=not job['disclosed'],sender=sender)
    async def mark_disclosed(self,sender,intake_id,message_id):
        # Called only after Telegram accepted the non-Danger disclosure reply.
        return await asyncio.to_thread(self.store.disclose,intake_id,sender,message_id)
    async def choose_keep(self,sender,intake_id):
        try:job=await asyncio.to_thread(self.store.choose_keep,intake_id,sender)
        except ValueError:return await self._reply(await asyncio.to_thread(self.store.get,intake_id),'policy_choice_frozen',sender=sender)
        return await self._reply(job,'policy_keep_selected',sender=sender)
    async def active_context(self,sender,message_id=None,file_unique_id=None):
        if message_id is not None and file_unique_id:
            bound=await asyncio.to_thread(self.store.resolve_upload,sender,message_id,file_unique_id)
            if bound:return dict(bound,bound_upload=True)
        job=await asyncio.to_thread(self.store.current,sender)
        return job if job and job['status'] in ('awaiting_disclosure','collecting','extracting') else None
    async def cancel(self,sender,intake_id=None):
        try:job=await self._owned(sender,intake_id)
        except PermissionError:return await self._reply(None,'policy_owner_required',sender=sender)
        job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='cancelled')
        await self._delete(job)
        return await self._reply(job,'policy_cancelled',sender=sender)
    async def _owned(self,sender,intake_id=None):
        job=await asyncio.to_thread(self.store.get,intake_id) if intake_id else await asyncio.to_thread(self.store.current,sender)
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        if not job or not shop or shop['shop_id']!=job['shop_id'] or job.get('sender_hash')!=session_user_id(sender,self.store.hash_salt):raise PermissionError('Policy owner required')
        # Strong sender binding remains enforced transactionally on every mutation.
        return job
    async def handle_document(self,sender,update_id,message_id,telegram_date,document:PolicyDocument,processing_started_at=None):
        now=processing_started_at or datetime.now(UTC)
        job=await self.active_context(sender,message_id,document.file_unique_id)
        if not job:return await self._reply(None,'policy_not_disclosed',sender=sender)
        await self._owned(sender,job['intake_id'])
        # Durable replay resolves the original job; terminal IDs never re-download.
        if job['status'] in ('failed','cancelled','complete'):
            return await self._result(job,sender) if job['status']=='complete' else await self._reply(job,'policy_cancelled',sender=sender)
        reserved=False
        try:
            sent=datetime.fromtimestamp(telegram_date,UTC)
            if type(telegram_date) is not int or now.tzinfo is None or sent>now:raise ValueError('invalid_time')
            if await asyncio.to_thread(self.store.danger_active,job['shop_id']):return await self.danger_reply(await asyncio.to_thread(self.store.owner_shop,sender))
            job=await asyncio.to_thread(self.store.reserve_upload,job['intake_id'],sender,message_id,document.file_unique_id,document.mime_type,document.file_size,sent,now)
            reserved=True
            slot=next(row for row in job['uploads'] if row['key']==job['upload_key'])
            used=sum(row['bytes'] for row in job['originals'] if row['media_id']!=slot['media_id'])
            request=PolicyUpload(job['intake_id'],slot['key'],slot['media_id'],job['shop_id'],sender,message_id,document.file_id,document.file_unique_id,slot['mime_type'],document.file_size,slot['telegram_date'],slot['received_at'],slot['lat'],slot['lng'],job['is_demo'])
            media=await self.originals.ingest(request,max_bytes=MAX_POLICY_BYTES-used)
            record=media.record
            original=PolicyOriginal(media_id=record.media_id,sha256=record.sha256,bytes=record.bytes,mime_type=record.mime_type,object_generation=record.object_generation)
            job=await asyncio.to_thread(self.store.attach_original,job['intake_id'],sender,slot['key'],original)
            if job['status'] in ('failed','cancelled') or job['deletion_pending']:
                await self._delete(job);return await self._reply(job,'policy_cancelled',sender=sender)
            if job['mode']=='pdf':return await self.done(sender,job['intake_id'])
            return await self._reply(job,'policy_photo_received',sender=sender)
        except (ValueError,TypeError,OverflowError):
            if reserved:
                job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='failed');await self._delete(job)
                return await self._reply(job,'policy_failed',sender=sender)
            return await self._reply(job,'policy_invalid',sender=sender)
        except Exception:
            job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='failed')
            await self._delete(job);return await self._reply(job,'policy_failed',sender=sender)
    handle_photo=handle_document
    async def done(self,sender,intake_id=None):
        try:job=await self._owned(sender,intake_id)
        except PermissionError:return await self._reply(None,'policy_owner_required',sender=sender)
        if job['status']=='complete':return await self._result(job,sender)
        if await asyncio.to_thread(self.store.danger_active,job['shop_id']):return await self.danger_reply(await asyncio.to_thread(self.store.owner_shop,sender))
        try:job=await asyncio.to_thread(self.store.claim_extraction,job['intake_id'],sender)
        except ValueError:return await self._reply(job,'policy_pending',sender=sender)
        owner=job['owner']
        try:
            async with asyncio.timeout(self.total_budget_seconds):
                documents=[await self.originals.read(PolicyOriginal.model_validate(row)) for row in job['originals']]
                assessment=None
                for attempt in range(2):
                    if await asyncio.to_thread(self.store.danger_active,job['shop_id']):return await self.danger_reply(await asyncio.to_thread(self.store.owner_shop,sender))
                    try:assessment=PolicyAssessment.model_validate(await self.assessor.assess(documents,job['intake_id'],job['is_demo']));break
                    except (ValueError,TimeoutError,httpx.TransportError):
                        if attempt:raise
                    except APIError as error:
                        if attempt or not (isinstance(error.code,int) and (error.code==429 or 500<=error.code<600)):raise
                comparison=compare_policy(assessment,FrozenPolicyInventory.model_validate(job['baseline']),datetime.now(UTC).date())
                job=await asyncio.to_thread(self.store.complete,job['intake_id'],sender,assessment,comparison.model_dump(mode='json'),owner=owner)
            if job['choice']=='delete':
                job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='successful_default');await self._delete(job)
            return await self._result(await asyncio.to_thread(self.store.get,job['intake_id']),sender)
        except Exception:
            latest=await asyncio.to_thread(self.store.get,job['intake_id'])
            if latest['status']=='complete':
                await self._delete(latest);return await self._result(latest,sender)
            job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='failed');await self._delete(job)
            return await self._reply(job,'policy_failed',sender=sender)
        finally:await asyncio.to_thread(self.store.release,job['intake_id'],owner)
    def _result_values(self,job):
        assessment=PolicyAssessment.model_validate(job['assessment']);comparison=job['comparison'];language=job['language']
        unknown=self._text(language,'policy_unknown')
        return dict(insurer=assessment.insurer or unknown,policy_type=assessment.policy_type or unknown,quote=assessment.evidence_quote or unknown,coverage=self._text(language,'policy_cover_'+assessment.flood_covered),limit=f'RM {assessment.sum_insured_rm:.2f}' if assessment.sum_insured_rm is not None else unknown,excess=f'RM {assessment.excess_rm:.2f}' if assessment.excess_rm is not None else unknown,expiry=assessment.expiry_date.isoformat() if assessment.expiry_date else unknown,comparison=self._comparison_text(language,comparison))
    def _comparison_text(self,language,comparison):
        status=comparison['status']
        key='policy_gap' if status=='estimated_shortfall' else 'policy_no_gap' if status=='no_estimated_shortfall' else 'policy_'+status
        value=self._text(language,key,gap=f"{comparison['estimated_limit_gap_rm']:.2f}" if comparison['estimated_limit_gap_rm'] is not None else '',estimate=f"{comparison['inventory_estimate_rm']:.2f}" if comparison['inventory_estimate_rm'] is not None else '')
        if comparison['expiry_status']=='unknown':value+=' '+self._text(language,'policy_expiry_unknown')
        return value
    async def _result(self,job,sender):
        reply=await self._reply(job,'policy_result',kind='policy_result',sender=sender,**self._result_values(job))
        if reply.kind=='danger':return reply
        retention='policy_delete_pending' if job['deletion_pending'] else 'policy_deleted' if job.get('deletion_reason') else 'policy_retained'
        markup=None
        if retention=='policy_retained':
            markup={'inline_keyboard':[[{'text':self._text(reply.language,'policy_copy_button',page=index+1),'callback_data':f"policy:copy:{job['intake_id']}:{index}"}] for index in range(len(job['originals']))]+[[{'text':self._text(reply.language,'policy_delete_button'),'callback_data':'policy:delete:'+job['intake_id']}]]}
        return PolicyReply.model_validate(reply.model_dump()|{'text':reply.text+'\n'+self._text(reply.language,retention),'reply_markup':markup})
    async def _delete(self,job):
        if not job.get('deletion_pending'):return
        try:
            await self.originals.retire(job)
            for slot in job['uploads']:
                current=await asyncio.to_thread(self.store.get,job['intake_id'])
                row=next((row for row in current['originals'] if row['media_id']==slot['media_id']),None)
                if row is None:
                    recovered=await self.originals.recover(current,slot)
                    if recovered.original:
                        current=await asyncio.to_thread(self.store.attach_recovered,current['intake_id'],slot['key'],recovered.original)
                        row=recovered.original.model_dump()
                    elif recovered.absence_verified:
                        await asyncio.to_thread(self.store.absent,current['intake_id'],slot['key']);continue
                    else:continue
                original=PolicyOriginal.model_validate(row)
                if original.deletion_status=='deleted':continue
                for attempt in range(2):
                    try:
                        if await self.originals.delete(original):await asyncio.to_thread(self.store.deleted,job['intake_id'],original.media_id,original.object_generation)
                        break
                    except Exception:
                        if attempt:break
        except Exception:pass # Durable pending state remains; no false success.
    async def resume_deletions(self,*,limit=20):
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Bounded policy deletion batch required')
        ids=await asyncio.to_thread(self.store.pending_deletions,limit);completed=0
        for identity in ids:
            await self._delete(await asyncio.to_thread(self.store.get,identity))
            if not (await asyncio.to_thread(self.store.get,identity))['deletion_pending']:completed+=1
        return {'scanned':len(ids),'completed':completed,'pending':len(ids)-completed}
    async def delete_copy(self,sender,intake_id):
        job=await self._owned(sender,intake_id)
        job=await asyncio.to_thread(self.store.request_deletion,job['intake_id'],reason='owner_delete');await self._delete(job)
        current=await asyncio.to_thread(self.store.get,intake_id)
        return await self._reply(current,'policy_delete_pending' if current['deletion_pending'] else 'policy_deleted',sender=sender)
    async def copy_for_sender(self,sender,intake_id,index):
        job=await self._owned(sender,intake_id)
        if type(index) is not int or not 0<=index<len(job['originals']):raise PermissionError('Private policy copy unavailable')
        if await asyncio.to_thread(self.store.danger_active,job['shop_id']):return await self.danger_reply(await asyncio.to_thread(self.store.owner_shop,sender))
        return await self.read_kept(sender,intake_id,job['originals'][index]['media_id'])
    async def recheck_copy(self,sender,intake_id,index,media):
        job=await self._owned(sender,intake_id)
        if type(index) is not int or not 0<=index<len(job['originals']):raise PermissionError('Private policy copy unavailable')
        row=job['originals'][index]
        if job['status']!='complete' or job['choice']!='keep' or job.get('deletion_reason') or row['deletion_status']!='retained' or row['media_id']!=media.record.media_id:raise PermissionError('Private policy copy unavailable')
        return await self.recheck_reply(sender,PolicyReply(text='',kind='policy_result'))
    async def read_kept(self,sender,intake_id,media_id):
        job=await self._owned(sender,intake_id)
        if job['status']!='complete' or job['choice']!='keep' or job.get('deletion_reason'):raise PermissionError('Private policy copy unavailable')
        row=next((row for row in job['originals'] if row['media_id']==media_id and row['deletion_status']=='retained'),None)
        if not row:raise PermissionError('Private policy copy unavailable')
        media=await self.originals.read(PolicyOriginal.model_validate(row))
        if len(media.original_bytes)!=row['bytes'] or sha256(media.original_bytes).hexdigest()!=row['sha256']:raise ValueError('Policy file integrity mismatch')
        return media
    async def close(self):
        if self.assessor:await self.assessor.close()
        if getattr(self,'_http',None):await self._http.aclose()
        if getattr(self,'_storage',None):self._storage.close()
        if getattr(self,'_owns_clients',False):self.store.client.close()
        if getattr(self,'_ledger',None):self._ledger.close()


def create_policy_service(settings):
    from api.active_risk import ActiveRiskStore
    from api.destinations import DestinationLookup
    from api.policy_store import PolicyStore
    from api.policy_media import PolicyStorage,PolicyMediaStore,PolicyMediaGateway
    from api.media import MediaService,TelegramDownloader,EvidenceLedger
    from api.agents.policy import PolicyAssessor
    from api.tools.firestore import create_firestore_client
    from api.tools.storage import create_storage_client
    from api.tools.cloud_events import create_analytics_client
    from api.i18n import text
    client=create_firestore_client(settings)
    store=PolicyStore(client,settings.hash_salt,risks=ActiveRiskStore(client,max_age=settings.official_max_age))
    http=httpx.AsyncClient(timeout=3,follow_redirects=False)
    storage=PolicyStorage(create_storage_client(settings),settings.gcs_bucket,store.original_binding)
    class LazyLedger:
        def __init__(self):self.analytics=None
        def append(self,record):
            if self.analytics is None:self.analytics=create_analytics_client(settings)
            EvidenceLedger(self.analytics,settings.gcp_project,settings.bigquery_dataset).append(record)
        def close(self):
            if self.analytics is not None:self.analytics.close()
    ledger=LazyLedger()
    media=MediaService(PolicyMediaStore(client,settings.hash_salt),TelegramDownloader(settings.telegram_bot_token,http),storage,ledger,lambda request:False)
    gateway=PolicyMediaGateway(media,store);media.authorize=gateway.authorize_media
    service=PolicyService(store,gateway,PolicyAssessor(settings),destinations=DestinationLookup(client,radius_m=settings.destination_search_radius_m),translate=text)
    service._http=http;service._storage=storage;service._owns_clients=True;service._ledger=ledger
    return service

class LazyPolicyService:
    """Ordinary/fixed-Danger replies do not construct document or model clients."""
    def __init__(self,settings):self.settings=settings;self.active=None
    def _service(self):
        if self.active is None:self.active=create_policy_service(self.settings)
        return self.active
    async def _cold(self,method,*args):
        from api.tools.firestore import create_firestore_client
        from api.policy_store import PolicyStore
        from api.active_risk import ActiveRiskStore
        from api.destinations import DestinationLookup
        from api.i18n import text
        client=create_firestore_client(self.settings)
        try:
            store=PolicyStore(client,self.settings.hash_salt,risks=ActiveRiskStore(client,max_age=self.settings.official_max_age))
            service=PolicyService(store,None,None,destinations=DestinationLookup(client,radius_m=self.settings.destination_search_radius_m),translate=text)
            return await getattr(service,method)(*args)
        finally:client.close()
    async def start(self,*args):return await self.active.start(*args) if self.active else await self._cold('start',*args)
    async def mark_disclosed(self,*args):return await self.active.mark_disclosed(*args) if self.active else await self._cold('mark_disclosed',*args)
    async def choose_keep(self,*args):return await self.active.choose_keep(*args) if self.active else await self._cold('choose_keep',*args)
    async def active_context(self,*args):return await self.active.active_context(*args) if self.active else await self._cold('active_context',*args)
    async def recheck_reply(self,*args):return await self.active.recheck_reply(*args) if self.active else await self._cold('recheck_reply',*args)
    async def handle_document(self,*args,**kwargs):return await self._service().handle_document(*args,**kwargs)
    async def handle_photo(self,*args,**kwargs):return await self.handle_document(*args,**kwargs)
    async def done(self,*args):return await self._service().done(*args)
    async def cancel(self,*args):return await self._service().cancel(*args)
    async def copy_for_sender(self,*args):return await self._service().copy_for_sender(*args)
    async def delete_copy(self,*args):return await self._service().delete_copy(*args)
    async def recheck_copy(self,*args):return await self._service().recheck_copy(*args)
    async def resume_deletions(self,**kwargs):return await self._service().resume_deletions(**kwargs)
    async def close(self):
        if self.active:await self.active.close()
