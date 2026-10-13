"""Policy-only storage retirement around the existing immutable ingestion boundary."""
from hashlib import sha256
import asyncio
from google.api_core.exceptions import NotFound,PreconditionFailed,Conflict
from google.cloud import firestore
from api.media import IngestedMedia
from api.media_models import MediaIngestError,MediaRequest
from api.media_store import MediaStore
from api.tools.storage import OriginalStorage
from api.policy import PolicyUpload,PolicyRecovery
from api.policy_models import PolicyOriginal,MAX_POLICY_BYTES

class PolicyStorage(OriginalStorage):
    """Zero-byte same-name fence defeats delayed create-only policy PUTs.

    Original-generation absence does not claim erasure of external provider
    processing, storage soft-delete/backups, or the Telegram message.
    """
    def __init__(self,client,bucket,binding):
        super().__init__(client,bucket);self.binding=binding
    def _ownership(self,media_id):
        binding=self.binding(media_id)
        if not binding or binding.get('media_id')!=media_id:raise MediaIngestError('unauthorized_media')
        return {'policy_media_id':media_id,'policy_intake_id':binding['intake_id'],'policy_upload_key':binding['upload_key']}
    def _matches(self,blob,owner):return all((blob.metadata or {}).get(key)==value for key,value in owner.items())
    def _current(self,media_id):
        blob=self.client.bucket(self.bucket).blob('originals/'+media_id)
        try:blob.reload(timeout=5,retry=None);return blob
        except NotFound:return None
    def create_original(self,media_id,data,mime_type,expected_hash):
        owner=self._ownership(media_id)
        if sha256(data).hexdigest()!=expected_hash:raise MediaIngestError('original_conflict')
        blob=self.client.bucket(self.bucket).blob('originals/'+media_id)
        blob.metadata=owner|{'sha256':expected_hash}
        try:blob.upload_from_string(data,content_type=mime_type,if_generation_match=0,timeout=8,retry=None)
        except (PreconditionFailed,Conflict):
            current=self._current(media_id)
            if not current or not self._matches(current,owner) or (current.metadata or {}).get('policy_deleted')=='true':raise MediaIngestError('policy_copy_deleted') from None
            if sha256(self.read_original(media_id,generation=str(current.generation))).hexdigest()!=expected_hash:raise MediaIngestError('original_conflict') from None
            return str(current.generation)
        return str(blob.generation)
    def read_original(self,media_id,*,generation=None):
        owner=self._ownership(media_id);current=self._current(media_id)
        if not current or not self._matches(current,owner) or (current.metadata or {}).get('policy_deleted')=='true':raise MediaIngestError('policy_copy_deleted')
        if generation is not None and str(current.generation)!=generation:raise MediaIngestError('original_conflict')
        blob=self.client.bucket(self.bucket).blob('originals/'+media_id,generation=int(generation or current.generation))
        data=blob.download_as_bytes(start=0,end=MAX_POLICY_BYTES,timeout=8,retry=None)
        if len(data)>MAX_POLICY_BYTES:raise MediaIngestError('upload_too_large')
        return data
    def recover_generation(self,media_id,expected_hash,expected_size):
        owner=self._ownership(media_id);current=self._current(media_id)
        if not current:return None
        if not self._matches(current,owner):raise MediaIngestError('original_conflict')
        metadata=current.metadata or {}
        if metadata.get('policy_deleted')=='true':
            if current.size!=0:raise MediaIngestError('original_conflict')
            generation=metadata.get('policy_deleted_generation')
            if generation is None and metadata.get('sha256') is None:return None
            if not generation or not generation.isdigit() or metadata.get('sha256')!=expected_hash:raise MediaIngestError('original_conflict')
            return generation
        if metadata.get('sha256')!=expected_hash:raise MediaIngestError('original_conflict')
        data=self.read_original(media_id,generation=str(current.generation))
        if len(data)!=expected_size or sha256(data).hexdigest()!=expected_hash:raise MediaIngestError('file_integrity_mismatch')
        return str(current.generation)
    def _absent_generation(self,media_id,generation):
        blob=self.client.bucket(self.bucket).blob('originals/'+media_id,generation=int(generation))
        try:blob.reload(timeout=5,retry=None);return False
        except NotFound:return True
    def fence_and_delete(self,media_id,original:PolicyOriginal|None):
        owner=self._ownership(media_id)
        for _ in range(2):
            current=self._current(media_id)
            if current and not self._matches(current,owner):raise MediaIngestError('original_conflict')
            metadata=current.metadata or {} if current else {}
            if metadata.get('policy_deleted')=='true':
                if current.size!=0:raise MediaIngestError('original_conflict')
                if original and metadata.get('policy_deleted_generation')!=original.object_generation:raise MediaIngestError('original_conflict')
                break
            if current:
                if original is None or str(current.generation)!=original.object_generation or metadata.get('sha256')!=original.sha256:raise MediaIngestError('original_conflict')
            marker=self.client.bucket(self.bucket).blob('originals/'+media_id)
            marker.metadata=owner|{'policy_deleted':'true'}|({'sha256':original.sha256,'policy_deleted_generation':original.object_generation} if original else {})
            try:
                marker.upload_from_string(b'',content_type='application/octet-stream',if_generation_match=int(current.generation) if current else 0,timeout=8,retry=None)
                break
            except (PreconditionFailed,Conflict):continue
        else:return False
        if original:
            blob=self.client.bucket(self.bucket).blob('originals/'+media_id,generation=int(original.object_generation))
            try:blob.delete(if_generation_match=int(original.object_generation),timeout=8,retry=None)
            except NotFound:pass
            return self._absent_generation(media_id,original.object_generation)
        # Fence installed for a never-PUT reservation; no original generation claimed.
        current=self._current(media_id)
        return bool(current and current.size==0 and self._matches(current,owner) and (current.metadata or {}).get('policy_deleted')=='true' and not (current.metadata or {}).get('policy_deleted_generation'))

class PolicyMediaStore(MediaStore):
    """Permanent private gate and existing per-original lease, policy records only."""
    def __init__(self,client,hash_salt,collection='media',retirements='policy_media_retirements'):
        super().__init__(client,hash_salt,collection);self.retirements=retirements
    def _retired(self,media_id):return self.client.collection(self.retirements).document(media_id).get(timeout=5,retry=None).exists
    def ensure(self,request):
        if request.kind not in ('policy_photo','policy_pdf'):raise MediaIngestError('unauthorized_media')
        record=super().ensure(request)
        if self._retired(record.media_id):raise MediaIngestError('policy_copy_deleted')
        return record
    def claim(self,media_id):
        if self._retired(media_id):raise MediaIngestError('policy_copy_deleted')
        return super().claim(media_id)
    def retire(self,media_id,binding):
        gate=self.client.collection(self.retirements).document(media_id);ref=self.client.collection(self.collection).document(media_id)
        @firestore.transactional
        def retire(tx):
            existing=gate.get(transaction=tx).to_dict();record=ref.get(transaction=tx)
            expected={'media_id':media_id,'intake_id':binding['intake_id'],'upload_key':binding['upload_key']}
            if existing and existing!=expected:raise MediaIngestError('original_conflict')
            if record.exists:
                data=record.to_dict()
                if data['kind'] not in ('policy_photo','policy_pdf') or data['shop_id']!=binding['shop_id']:raise MediaIngestError('unauthorized_media')
                if data.get('retention_status')!='deleted':tx.update(ref,{'retention_status':'deletion_pending'})
            tx.set(gate,expected)
        retire(self.client.transaction())
    def raw(self,media_id):return self.client.collection(self.collection).document(media_id).get(timeout=5,retry=None).to_dict()
    def claim_retirement(self,media_id):
        if not self._retired(media_id):raise MediaIngestError('unauthorized_media')
        if self.raw(media_id) is None:return None
        return super().claim(media_id)

class PolicyMediaGateway:
    """Uses MediaService download/hash/receipt/ledger; retirement never downloads."""
    def __init__(self,media,policy_store):self.media,self.policy_store=media,policy_store
    def authorize_media(self,request):
        job=self.policy_store.resolve_upload(request.sender_chat_id,request.message_id,request.file_unique_id)
        shop=self.policy_store.owner_shop(request.sender_chat_id)
        return bool(job and shop and job['shop_id']==shop['shop_id']==request.shop_id and job['status']=='collecting' and not job['deletion_pending'] and any(slot['message_id']==request.message_id and slot['file_unique_id']==request.file_unique_id for slot in job['uploads']))
    async def ingest(self,request:PolicyUpload,*,max_bytes):
        media_request=MediaRequest(shop_id=request.shop_id,kind='policy_pdf' if request.mime_type=='application/pdf' else 'policy_photo',sender_chat_id=request.sender_chat_id,message_id=request.message_id,file_id=request.file_id,file_unique_id=request.file_unique_id,declared_size=request.declared_size,declared_mime=request.mime_type,telegram_date=request.telegram_date,received_at=request.received_at,lat=request.lat,lng=request.lng,location_attribution='confirmed_shop',is_demo=request.is_demo)
        media=await self.media.ingest_media(media_request,max_bytes=max_bytes)
        if media.record.media_id!=request.media_id:raise MediaIngestError('original_conflict')
        return media
    async def retire(self,job):
        for slot in job['uploads']:
            binding=self.policy_store.original_binding(slot['media_id'])
            await asyncio.to_thread(self.media.store.retire,slot['media_id'],binding)
    async def recover(self,job,upload):
        media_id=upload['media_id'];owner=await asyncio.to_thread(self.media.store.claim_retirement,media_id)
        try:
            record=await asyncio.to_thread(self.media.store.raw,media_id)
            if not record or not record.get('sha256'):
                absent=await asyncio.to_thread(self.media.storage.fence_and_delete,media_id,None)
                return PolicyRecovery(absence_verified=absent)
            generation=record.get('object_generation') or await asyncio.to_thread(self.media.storage.recover_generation,media_id,record['sha256'],record['bytes'])
            if generation is None:
                absent=await asyncio.to_thread(self.media.storage.fence_and_delete,media_id,None)
                if absent and owner is not None:
                    await asyncio.to_thread(self.media.store.transition,media_id,owner,retention_status='deleted')
                    await self._receipt_ledger(media_id,owner)
                return PolicyRecovery(absence_verified=absent)
            if not record.get('object_generation'):await asyncio.to_thread(self.media.store.transition,media_id,owner,object_generation=generation)
            return PolicyRecovery(original=PolicyOriginal(media_id=media_id,sha256=record['sha256'],bytes=record['bytes'],mime_type=record['mime_type'],object_generation=generation))
        finally:
            if owner is not None:await asyncio.to_thread(self.media.store.release,media_id,owner)
    async def delete(self,original):
        owner=await asyncio.to_thread(self.media.store.claim_retirement,original.media_id)
        try:
            absent=await asyncio.to_thread(self.media.storage.fence_and_delete,original.media_id,original)
            if absent and owner is not None:
                await asyncio.to_thread(self.media.store.transition,original.media_id,owner,retention_status='deleted')
                await self._receipt_ledger(original.media_id,owner)
            return absent
        finally:
            if owner is not None:await asyncio.to_thread(self.media.store.release,original.media_id,owner)
    async def _receipt_ledger(self,media_id,owner):
        record=await asyncio.to_thread(self.media.store.get,media_id)
        if record.sha256 and record.ledger_status!='done':
            await asyncio.to_thread(self.media.ledger.append,record)
            await asyncio.to_thread(self.media.store.transition,media_id,owner,ledger_status='done')
    async def read(self,original):
        record=await asyncio.to_thread(self.media.store.get,original.media_id)
        if getattr(record,'retention_status','retained')!='retained':raise MediaIngestError('policy_copy_deleted')
        data=await asyncio.to_thread(self.media.storage.read_original,original.media_id,generation=original.object_generation)
        if len(data)!=original.bytes or sha256(data).hexdigest()!=original.sha256:raise MediaIngestError('file_integrity_mismatch')
        return IngestedMedia(record,data)
