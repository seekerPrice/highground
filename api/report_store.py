"""Owner-only frozen recovery workflows and opaque capability-bound reports."""
from datetime import UTC, datetime
from hashlib import sha256
import hmac
import secrets
from google.cloud import firestore
from api.inventory_store import InventoryStore
from api.agents.sessions import session_user_id
from api.report_models import freeze_baseline
from api.media_models import MediaIngestError

class ReportStore(InventoryStore):
    def owner_shop(self, sender: int) -> dict | None:
        shop=self.shop_for_sender(sender)
        if shop and any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop['recipients']): return shop
        return None

    def current(self, sender: int) -> dict | None:
        identity=session_user_id(sender,self.hash_salt)
        pointer=self.collection('recovery_current').document(identity).get().to_dict() or {}
        return self.collection('recovery_jobs').document(pointer['report_id']).get().to_dict() if pointer.get('report_id') else None

    def upload_reference(self,sender: int,message_id: int,file_unique_id: str):
        identity=sha256(f"{session_user_id(sender,self.hash_salt)}:{message_id}:{file_unique_id}".encode()).hexdigest()
        return self.collection('recovery_uploads').document(identity)

    def resolve_context(self,sender: int,message_id: int|None=None,file_unique_id: str|None=None) -> dict|None:
        if message_id is not None and file_unique_id:
            bound=self.upload_reference(sender,message_id,file_unique_id).get().to_dict() or {}
            if bound.get('report_id'):
                return self.collection('recovery_jobs').document(bound['report_id']).get().to_dict()
        job=self.current(sender)
        return job if job and (job['status']!='complete' or job.get('attachment_pending')) else None

    def bind_photo(self,report_id: str,sender: int,message_id: int,file_unique_id: str) -> dict:
        ref=self.collection('recovery_jobs').document(report_id);binding=self.upload_reference(sender,message_id,file_unique_id)
        @firestore.transactional
        def bind(tx):
            old=binding.get(transaction=tx).to_dict()
            job=ref.get(transaction=tx).to_dict()
            if old:
                if old['report_id']!=report_id or old['kind']!='waterline_photo':raise MediaIngestError('recovery_upload_bound')
                return job
            if job['sender_hash']!=session_user_id(sender,self.hash_salt):raise MediaIngestError('unauthorized_media')
            tx.create(binding,{'report_id':report_id,'kind':'waterline_photo'})
            return job
        return bind(self.client.transaction())

    def start(self, shop: dict, sender: int, operation: str) -> dict:
        identity=sha256(f"{shop['shop_id']}:{session_user_id(sender,self.hash_salt)}:{operation}".encode()).hexdigest()
        intent=self.collection('recovery_intents').document(identity)
        current=self.collection('recovery_current').document(session_user_id(sender,self.hash_salt))
        report_id=secrets.token_hex(16); token=secrets.token_urlsafe(32)
        ref=self.collection('recovery_jobs').document(report_id)
        private=self.collection('recovery_private').document(report_id)
        baseline_ref=self.collection('inventories').document(shop.get('baseline_inventory_id') or 'unavailable')
        @firestore.transactional
        def create(tx):
            old=intent.get(transaction=tx).to_dict()
            if old:return self.collection('recovery_jobs').document(old['report_id']).get(transaction=tx).to_dict()
            prior=current.get(transaction=tx).to_dict() or {}
            prior_job=self.collection('recovery_jobs').document(prior['report_id']).get(transaction=tx).to_dict() if prior.get('report_id') else None
            baseline=baseline_ref.get(transaction=tx).to_dict()
            if prior_job and prior_job.get('status') in ('awaiting_declaration','awaiting_video'): return prior_job
            if not baseline or baseline.get('shop_id')!=shop['shop_id']:raise ValueError('Baseline unavailable')
            frozen=freeze_baseline(dict(baseline,inventory_id=baseline_ref.id))
            record=dict(report_id=report_id,inventory_id=report_id,shop_id=shop['shop_id'],shop_name=shop.get('shop_name','Shop'),
                language=shop['language'],is_demo=bool(shop.get('is_demo')),sender_hash=session_user_id(sender,self.hash_salt),
                created_at=datetime.now(UTC),status='awaiting_declaration',baseline=frozen,lat=shop['lat'],lng=shop['lng'],
                capability_hash=sha256(token.encode()).hexdigest(),evidence_media_ids=[frozen['media_id']])
            tx.create(ref,record);tx.create(private,{'capability':token});tx.create(intent,{'report_id':report_id});tx.set(current,{'report_id':report_id})
            return record
        return create(self.client.transaction())

    def declare(self, report_id: str, sender: int) -> dict:
        ref=self.collection('recovery_jobs').document(report_id)
        job=ref.get().to_dict(); shop=self.owner_shop(sender)
        if not job or not shop or shop['shop_id']!=job['shop_id'] or job['sender_hash']!=session_user_id(sender,self.hash_salt): raise MediaIngestError('unauthorized_media')
        state=self.risk_store.get(shop['shop_id'])
        if state.official_danger or state.legacy_unknown:return job
        if not shop.get('is_demo'): self.risk_store.owner_declared_recovery(shop['shop_id'],sender)
        if self.danger_active(shop['shop_id']):return job
        @firestore.transactional
        def transition(tx):
            current=ref.get(transaction=tx).to_dict()
            if current['status']=='awaiting_declaration':
                tx.update(ref,{'status':'awaiting_video','recovery_attribution':'Owner declared recovery; not independent proof of flood clearance.','declared_at':datetime.now(UTC)})
            return dict(current,status='awaiting_video') if current['status']=='awaiting_declaration' else current
        return transition(self.client.transaction())

    def exit(self,sender):
        self.collection('recovery_current').document(session_user_id(sender,self.hash_salt)).delete()

    def request_attachment(self,sender):
        job=self.current(sender);shop=self.owner_shop(sender)
        if not job or not shop or job['status']!='complete':return None
        self.collection('recovery_jobs').document(job['report_id']).update({'attachment_pending':True})
        return job

    def bind_upload(self, report_id: str, sender: int, message_id: int, sent: datetime, video, now: datetime) -> dict:
        ref=self.collection('recovery_jobs').document(report_id)
        binding=self.upload_reference(sender,message_id,video.file_unique_id)
        @firestore.transactional
        def bind(tx):
            prior=binding.get(transaction=tx).to_dict()
            job=ref.get(transaction=tx).to_dict()
            if prior and (prior['report_id']!=report_id or prior['kind']!='after_video'):raise MediaIngestError('recovery_upload_bound')
            if job['sender_hash']!=session_user_id(sender,self.hash_salt):raise MediaIngestError('unauthorized_media')
            upload=dict(message_id=message_id,telegram_date=sent,received_at=now,duration=video.duration,file_unique_id=video.file_unique_id)
            if job.get('upload'):
                if job['upload']['message_id']!=message_id or job['upload']['file_unique_id']!=video.file_unique_id: raise MediaIngestError('recovery_upload_bound')
                return job
            tx.update(ref,{'upload':upload})
            tx.create(binding,{'report_id':report_id,'kind':'after_video'})
            return dict(job,upload=upload)
        return bind(self.client.transaction())

    # InventoryStore's bounded transaction lease methods operate on the recovery job collection.
    def collection(self, name):
        return super().collection('recovery_jobs' if name=='inventory_jobs' else name)

    def authorized(self, report_id: str, token: str) -> dict | None:
        job=self.collection('recovery_jobs').document(report_id).get().to_dict() or {}
        supplied=sha256(token.encode()).hexdigest()
        if not hmac.compare_digest(supplied,job.get('capability_hash','0'*64)):return None
        return job if job.get('status')=='complete' else None

    def token(self, report_id: str) -> str:
        return self.collection('recovery_private').document(report_id).get().to_dict()['capability']

    def attach_photo(self, report_id: str, media_id: str) -> None:
        ref=self.collection('recovery_jobs').document(report_id)
        @firestore.transactional
        def attach(tx):
            job=ref.get(transaction=tx).to_dict()
            values=job['evidence_media_ids']
            if media_id not in values:
                if len(values)>=10:raise ValueError('Evidence limit reached')
                tx.update(ref,{'evidence_media_ids':values+[media_id]})
        attach(self.client.transaction())
