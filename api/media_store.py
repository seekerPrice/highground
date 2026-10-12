"""Immutable upload records and recoverable per-sink progress; no deletes/updates to evidence facts."""
from datetime import UTC,datetime,timedelta
from hashlib import sha256
from uuid import uuid4
from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists
from api.media_models import MediaRecord,MediaRequest,MediaIngestError
from api.agents.sessions import session_user_id

class MediaStore:
    def __init__(self,client:firestore.Client,hash_salt:str,collection:str='media'):
        self.client,self.hash_salt,self.collection=client,hash_salt,collection
    def ensure(self,request:MediaRequest)->MediaRecord:
        sender_hash=session_user_id(request.sender_chat_id,self.hash_salt)
        identity=f'{request.shop_id}:{sender_hash}:{request.message_id}:{request.file_unique_id}:{request.kind}'
        media_id=sha256(identity.encode()).hexdigest()
        record=MediaRecord(media_id=media_id,shop_id=request.shop_id,kind=request.kind,sender_hash=sender_hash,
                           uploaded_at=datetime.now(UTC),received_at=request.received_at,
                           telegram_date=request.telegram_date,lat=request.lat,lng=request.lng,is_demo=request.is_demo,location_attribution=request.location_attribution)
        reference=self.client.collection(self.collection).document(media_id)
        try:reference.create(record.model_dump())
        except AlreadyExists:
            record=MediaRecord.model_validate(reference.get().to_dict())
            if (record.lat,record.lng,record.telegram_date,record.is_demo,record.location_attribution)!=(request.lat,request.lng,request.telegram_date,request.is_demo,request.location_attribution):
                raise MediaIngestError('metadata_conflict')
        return record
    def get(self,media_id:str)->MediaRecord:
        return MediaRecord.model_validate(self.client.collection(self.collection).document(media_id).get().to_dict())
    def pending_ledger_ids(self,limit:int=20) -> list[str]:
        from google.cloud.firestore_v1.base_query import FieldFilter
        query=self.client.collection(self.collection).where(filter=FieldFilter('storage_status','==','done')).where(filter=FieldFilter('ledger_status','==','pending'))
        return [doc.id for doc in query.limit(limit).stream(timeout=5,retry=None)]

    def claim(self,media_id:str)->str:
        ref=self.client.collection(self.collection).document(media_id);owner=uuid4().hex;now=datetime.now(UTC)
        @firestore.transactional
        def acquire(tx):
            record=ref.get(transaction=tx).to_dict()
            if record.get('lease_until',now)>now:raise MediaIngestError('ingest_busy')
            tx.update(ref,{'owner':owner,'lease_until':now+timedelta(seconds=30)})
        acquire(self.client.transaction());return owner
    def transition(self,media_id:str,owner:str,**fields)->None:
        ref=self.client.collection(self.collection).document(media_id)
        @firestore.transactional
        def change(tx):
            current=ref.get(transaction=tx).to_dict()
            if current.get('owner')!=owner:raise MediaIngestError('ingest_claim_changed')
            for immutable in ('sha256','bytes','mime_type','gcs_uri'):
                if immutable in fields and current.get(immutable) is not None and current[immutable]!=fields[immutable]:
                    raise MediaIngestError('original_conflict')
            tx.update(ref,dict(fields,lease_until=datetime.now(UTC)+timedelta(seconds=30)))
        change(self.client.transaction())
    def release(self,media_id:str,owner:str)->None:
        ref=self.client.collection(self.collection).document(media_id)
        @firestore.transactional
        def release(tx):
            if ref.get(transaction=tx).to_dict().get('owner')==owner:tx.update(ref,{'lease_until':datetime.now(UTC)})
        release(self.client.transaction())
