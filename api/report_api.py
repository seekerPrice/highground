"""Private report reads: capability checked before any original media access."""
import asyncio
from hashlib import sha256
import re
from contextlib import asynccontextmanager
from fastapi import APIRouter,HTTPException,Request,Response
from api.report_models import Report,ReportItem,EvidenceReceipt,IntegrityResult,LossAssessment
from api.media_models import MAX_UPLOAD_BYTES,MediaIngestError

class ReportReader:
    def __init__(self,store,media_store,storage):self.store,self.media_store,self.storage=store,media_store,storage
    def authorize(self,report_id: str,authorization: str) -> dict:
        if not re.fullmatch(r'[0-9a-f]{32}',report_id) or not authorization.startswith('Bearer ') or len(authorization)>128:raise PermissionError()
        job=self.store.authorized(report_id,authorization[7:])
        if not job:raise PermissionError()
        return job
    def member_media(self,job: dict,media_id: str):
        if not re.fullmatch(r'[0-9a-f]{64}',media_id) or media_id not in job['evidence_media_ids']:raise PermissionError()
        record=self.media_store.get(media_id)
        if record.media_id!=media_id or record.shop_id!=job['shop_id'] or record.is_demo!=job['is_demo']:raise PermissionError()
        return record
    def report(self,report_id: str,authorization: str) -> Report:
        job=self.authorize(report_id,authorization);baseline=job['baseline'];assessment=LossAssessment.model_validate(job['assessment']).validate_baseline(baseline,job['upload']['duration'])
        rows=[];found={i.item_id:i for i in assessment.items}
        for index,row in enumerate(baseline['items']):
            identity=f"{baseline['inventory_id']}:{index}"
            item=found.get(identity)
            # Display only validated facts and canonical uncertainty, never model-generated advice.
            data=dict(item_id=identity,condition=item.condition if item else 'unassessed',estimated_loss_rm=item.estimated_loss_rm if item else None,
                evidence_timestamp_s=item.evidence_timestamp_s if item else None,uncertainty='Visible evidence supports an estimate; valuation remains uncertain.' if item and item.estimated_loss_rm is not None else 'Not assessed in the after-video; loss is unknown.')
            rows.append(ReportItem(**data,name=row['name'],qty=row['qty'],baseline_estimate_rm=round(row['qty']*row['est_unit_value_rm'],2)))
        assessed=sum(i.estimated_loss_rm is not None for i in rows);coverage='none' if not assessed else 'complete' if assessed==len(rows) else 'partial'
        receipts=[]
        for identity in job['evidence_media_ids']:
            record=self.member_media(job,identity)
            if record.storage_status!='done' or record.ledger_status!='done':continue
            receipts.append(EvidenceReceipt(**{k:getattr(record,k) for k in EvidenceReceipt.model_fields if k!='integrity_status'}))
        total=assessment.total_loss_rm
        summary=(f"{assessed} of {len(rows)} baseline items were assessed. "+(f"Assessed estimated loss is RM{total:.2f}. " if total is not None else 'The loss estimate is unavailable. ')+('Unknown losses are excluded; this estimate is partial.' if coverage!='complete' else 'Replacement-price estimates remain uncertain.'))
        return Report(report_id=report_id,assessment_media_id=job['media_id'],created_at=job['created_at'],shop_name=job['shop_name'],is_demo=job['is_demo'],baseline_estimate_rm=baseline['total_est_value_rm'],estimated_loss_rm=total,
            estimate_status='available' if total is not None else 'unavailable',coverage=coverage,assessed_items=assessed,baseline_items=len(rows),confidence=assessment.confidence,
            confidence_note='Visual model assessment only; replacement prices, camera coverage and damage estimates remain uncertain.',summary_text=summary,
            recovery_attribution=job['recovery_attribution'],items=rows,evidence=receipts)
    def read(self,job: dict,media_id: str) -> tuple:
        record=self.member_media(job,media_id)
        if record.storage_status!='done' or record.ledger_status!='done':raise OSError()
        try:data=self.storage.read_original(media_id)
        except MediaIngestError as error:
            if error.code=='upload_too_large':raise ValueError('integrity_mismatch') from None
            raise
        if len(data)>MAX_UPLOAD_BYTES or len(data)!=record.bytes or sha256(data).hexdigest()!=record.sha256:raise ValueError('integrity_mismatch')
        return record,data
    def verify(self,job: dict,media_id: str) -> IntegrityResult:
        record=self.member_media(job,media_id)
        try:self.read(job,media_id);status='verified'
        except ValueError:status='mismatch'
        except Exception:status='unavailable'
        return IntegrityResult(media_id=media_id,status=status,sha256=record.sha256 or '')
    def close(self) -> None:self.store.client.close();self.storage.close()

def create_report_reader(settings):
    from api.tools.firestore import create_firestore_client
    from api.tools.storage import OriginalStorage,create_storage_client
    from api.report_store import ReportStore
    from api.media_store import MediaStore
    client=create_firestore_client(settings)
    return ReportReader(ReportStore(client,settings.hash_salt),MediaStore(client,settings.hash_salt),OriginalStorage(create_storage_client(settings),settings.gcs_bucket))

HEADERS={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'}
def create_report_router(settings,reader=None):
    active=reader;owns=reader is None
    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns and active:await asyncio.to_thread(active.close)
    router=APIRouter(lifespan=lifespan)
    def service():
        nonlocal active
        if active is None:active=create_report_reader(settings() if callable(settings) else settings)
        return active
    async def scoped(report_id,request):
        try:return await asyncio.to_thread(service().authorize,report_id,request.headers.get('Authorization',''))
        except PermissionError:raise HTTPException(404,'Report unavailable',headers=HEADERS) from None
        except Exception:raise HTTPException(503,'Report temporarily unavailable',headers=HEADERS) from None
    @router.get('/api/report/{report_id}',response_model=Report)
    async def report(report_id:str,request:Request,response:Response):
        await scoped(report_id,request)
        try:result=await asyncio.to_thread(service().report,report_id,request.headers.get('Authorization',''))
        except Exception:raise HTTPException(503,'Report temporarily unavailable',headers=HEADERS) from None
        response.headers.update(HEADERS);return result
    @router.get('/api/report/{report_id}/media/{media_id}')
    async def media(report_id:str,media_id:str,request:Request):
        job=await scoped(report_id,request)
        try:record,data=await asyncio.to_thread(service().read,job,media_id)
        except PermissionError:raise HTTPException(404,'Media unavailable',headers=HEADERS) from None
        except ValueError:raise HTTPException(409,'Stored file integrity mismatch',headers=HEADERS) from None
        except Exception:raise HTTPException(503,'Media unavailable',headers=HEADERS) from None
        return Response(data,media_type=record.mime_type,headers=HEADERS)
    @router.post('/api/report/{report_id}/media/{media_id}/verify',response_model=IntegrityResult)
    async def verify(report_id:str,media_id:str,request:Request,response:Response):
        job=await scoped(report_id,request)
        try:result=await asyncio.to_thread(service().verify,job,media_id)
        except PermissionError:raise HTTPException(404,'Media unavailable',headers=HEADERS) from None
        except Exception:raise HTTPException(503,'Verification unavailable',headers=HEADERS) from None
        response.headers.update(HEADERS);return result
    return router
