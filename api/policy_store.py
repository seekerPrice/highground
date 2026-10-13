"""Owner-bound policy intake and durable exact-original deletion receipts."""
from datetime import UTC,datetime,timedelta
from hashlib import sha256
import secrets
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from api.photo_store import PhotoStore
from api.agents.sessions import session_user_id
from api.policy_models import FrozenPolicyInventory,PolicyAssessment,PolicyOriginal,MAX_POLICY_PHOTOS,MAX_POLICY_BYTES,aggregate_policies
from api.report_models import freeze_baseline

class PolicyStore(PhotoStore):
    def owner_shop(self,sender:int) -> dict|None:
        shop=self.shop_for_sender(sender)
        return shop if shop and any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop['recipients']) else None

    def current(self,sender:int) -> dict|None:
        pointer=self.collection('policy_current').document(session_user_id(sender,self.hash_salt)).get(timeout=5,retry=None).to_dict() or {}
        return self.get(pointer['intake_id']) if pointer.get('intake_id') else None
    def get(self,intake_id:str) -> dict|None:
        return self.collection('policy_jobs').document(intake_id).get(timeout=5,retry=None).to_dict()

    def _guard(self,tx,job:dict,sender:int) -> dict:
        if not job:raise PermissionError('Policy owner required')
        shop=self.collection('shops').document(job['shop_id']).get(transaction=tx).to_dict() or {}
        if job.get('sender_hash')!=session_user_id(sender,self.hash_salt) or not any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop.get('recipients',[])):raise PermissionError('Policy owner required')
        return shop

    def start(self,sender:int,operation:str) -> dict:
        shop=self.owner_shop(sender)
        if not shop:raise PermissionError('Policy owner required')
        identity=sha256(f'{shop["shop_id"]}:{session_user_id(sender,self.hash_salt)}:{operation}'.encode()).hexdigest()
        intent=self.collection('policy_intents').document(identity)
        current=self.collection('policy_current').document(session_user_id(sender,self.hash_salt));intake_id=secrets.token_hex(16)
        ref=self.collection('policy_jobs').document(intake_id)
        @firestore.transactional
        def begin(tx):
            old=intent.get(transaction=tx).to_dict();pointer=current.get(transaction=tx).to_dict() or {}
            previous=self.collection('policy_jobs').document(pointer['intake_id']).get(transaction=tx).to_dict() if pointer.get('intake_id') else None
            if old:return self.collection('policy_jobs').document(old['intake_id']).get(transaction=tx).to_dict()
            if previous and previous['status'] in ('awaiting_disclosure','collecting','extracting'):return previous
            record=dict(intake_id=intake_id,policy_id=intake_id,shop_id=shop['shop_id'],sender_hash=session_user_id(sender,self.hash_salt),language=shop['language'],is_demo=bool(shop.get('is_demo')),status='awaiting_disclosure',disclosed=False,choice='delete',choice_frozen=False,created_at=datetime.now(UTC),uploads=[],originals=[],baseline=None,deletion_pending=False)
            self._guard(tx,record,sender)
            tx.create(ref,record);tx.create(intent,{'intake_id':intake_id});tx.set(current,{'intake_id':intake_id})
            return record
        return begin(self.client.transaction())

    def disclose(self,intake_id:str,sender:int,message_id:int) -> dict:
        return self._change(intake_id,sender,lambda job: {'disclosed':True,'disclosure_message_id':message_id,'status':'collecting'} if job['status']=='awaiting_disclosure' else {})
    def choose_keep(self,intake_id:str,sender:int) -> dict:
        def change(job):
            if job['choice_frozen'] or job['status'] not in ('awaiting_disclosure','collecting'):raise ValueError('choice_frozen_reupload')
            return {'choice':'keep'}
        return self._change(intake_id,sender,change)
    def _change(self,intake_id:str,sender:int,change) -> dict:
        ref=self.collection('policy_jobs').document(intake_id)
        @firestore.transactional
        def update(tx):
            job=ref.get(transaction=tx).to_dict()
            if not job:raise PermissionError('Policy owner required')
            self._guard(tx,job,sender);values=change(job)
            if values:tx.update(ref,values)
            return {**job,**values}
        return update(self.client.transaction())

    def reserve_upload(self,intake_id:str,sender:int,message_id:int,file_unique_id:str,mime_type:str,declared_size:int|None,telegram_date:datetime,received_at:datetime) -> dict:
        key=sha256(f'{session_user_id(sender,self.hash_salt)}:{message_id}:{file_unique_id}'.encode()).hexdigest()
        binding=self.collection('policy_uploads').document(key);ref=self.collection('policy_jobs').document(intake_id)
        @firestore.transactional
        def reserve(tx):
            old=binding.get(transaction=tx).to_dict();job=ref.get(transaction=tx).to_dict()
            shop=self._guard(tx,job,sender)
            if old:
                if old['intake_id']!=intake_id:raise ValueError('policy_upload_bound')
                return {**job,'upload_key':key}
            if not job['disclosed'] or job['status']!='collecting':raise ValueError('policy_disclosure_required')
            if mime_type not in ('application/pdf','image/jpeg','image/png','image/webp'):raise ValueError('policy_invalid_document')
            mode='pdf' if mime_type=='application/pdf' else 'photos'
            if job.get('mode') not in (None,mode) or (mode=='pdf' and job['uploads']) or len(job['uploads'])>=MAX_POLICY_PHOTOS:raise ValueError('policy_document_limit')
            if len(job['uploads'])>len(job['originals']):raise ValueError('policy_upload_pending')
            total=sum(row['bytes'] for row in job['originals'])
            if declared_size is not None and (type(declared_size) is not int or declared_size<=0 or total+declared_size>MAX_POLICY_BYTES):raise ValueError('policy_byte_limit')
            baseline=job['baseline']
            if baseline is None:
                record=self.collection('inventories').document(shop.get('baseline_inventory_id') or 'unavailable').get(transaction=tx).to_dict()
                baseline=FrozenPolicyInventory(inventory_id=None,total_est_value_rm=None,confidence=None,status='unavailable').model_dump()
                if record and record.get('shop_id')==job['shop_id']:
                    try:
                        frozen=freeze_baseline(record)
                        baseline=FrozenPolicyInventory(inventory_id=frozen['inventory_id'],total_est_value_rm=frozen['total_est_value_rm'],confidence=frozen['confidence'],status='available').model_dump()
                    except (ValueError,KeyError,TypeError):pass
            media_id=sha256(f'{job["shop_id"]}:{session_user_id(sender,self.hash_salt)}:{message_id}:{file_unique_id}:policy_{"pdf" if mode=="pdf" else "photo"}'.encode()).hexdigest()
            upload=dict(key=key,media_id=media_id,message_id=message_id,file_unique_id=file_unique_id,mime_type=mime_type,telegram_date=telegram_date,received_at=received_at,lat=shop['lat'],lng=shop['lng'])
            values=dict(mode=mode,choice_frozen=True,baseline=baseline,uploads=job['uploads']+[upload])
            tx.update(ref,values);tx.create(binding,{'intake_id':intake_id,'key':key})
            tx.create(self.collection('policy_originals').document(media_id),{'media_id':media_id,'intake_id':intake_id,'upload_key':key,'shop_id':job['shop_id']})
            return {**job,**values,'upload_key':key}
        return reserve(self.client.transaction())

    def attach_original(self,intake_id:str,sender:int,upload_key:str,original:PolicyOriginal) -> dict:
        def attach(job):
            uploads=[dict(row) for row in job['uploads']]
            upload=next((row for row in uploads if row['key']==upload_key),None)
            if upload is None or upload.get('absence_verified'):raise ValueError('Unbound policy original')
            if upload['media_id'] and upload['media_id']!=original.media_id:raise ValueError('Immutable policy original changed')
            previous=next((row for row in job['originals'] if row['media_id']==original.media_id),None)
            if previous:
                if {k:previous[k] for k in ('media_id','sha256','bytes','mime_type','object_generation')}!={k:original.model_dump()[k] for k in ('media_id','sha256','bytes','mime_type','object_generation')}:raise ValueError('Immutable policy receipt changed')
                return {}
            if sum(row['bytes'] for row in job['originals'])+original.bytes>MAX_POLICY_BYTES:raise ValueError('policy_byte_limit')
            upload['media_id']=original.media_id
            late=job['status'] in ('failed','cancelled') or job.get('deletion_pending')
            receipt=original.model_copy(update={'deletion_status':'deletion_pending'}).model_dump() if late else original.model_dump()
            return {'uploads':uploads,'originals':job['originals']+[receipt],**({'deletion_pending':True} if late else {})}
        return self._change(intake_id,sender,attach)

    def resolve_upload(self,sender:int,message_id:int,file_unique_id:str) -> dict|None:
        key=sha256(f'{session_user_id(sender,self.hash_salt)}:{message_id}:{file_unique_id}'.encode()).hexdigest()
        binding=self.collection('policy_uploads').document(key).get(timeout=5,retry=None).to_dict() or {}
        return self.get(binding['intake_id']) if binding.get('intake_id') else None

    def claim_extraction(self,intake_id:str,sender:int) -> dict:
        now=datetime.now(UTC);owner=secrets.token_hex(16)
        def begin(job):
            if job['status'] not in ('collecting','extracting') or not job['originals'] or len(job['uploads'])!=len(job['originals']):raise ValueError('policy_incomplete_uploads')
            if job.get('lease_until',now)>now:raise ValueError('policy_busy')
            return {'status':'extracting','owner':owner,'lease_until':now+timedelta(seconds=45)}
        return self._change(intake_id,sender,begin)
    def release(self,intake_id:str,owner:str) -> None:
        ref=self.collection('policy_jobs').document(intake_id)
        @firestore.transactional
        def release(tx):
            job=ref.get(transaction=tx).to_dict() or {}
            if job.get('owner')==owner:tx.update(ref,{'lease_until':datetime.now(UTC)})
        release(self.client.transaction())

    def complete(self,intake_id:str,sender:int,assessment:PolicyAssessment,comparison:dict,*,owner:str) -> dict:
        ref=self.collection('policy_jobs').document(intake_id);projection=self.collection('policies').document(intake_id)
        @firestore.transactional
        def complete(tx):
            job=ref.get(transaction=tx).to_dict();shop=self._guard(tx,job,sender)
            previous=self.collection('policies').document(shop['latest_policy_id']).get(transaction=tx).to_dict() if shop.get('latest_policy_id') else None
            if job['status']=='complete':return job
            if job['status']!='extracting' or job.get('owner')!=owner:raise ValueError('Policy extraction no longer active')
            values={'status':'complete','assessment':assessment.model_dump(mode='json'),'comparison':comparison}
            if job['choice']=='delete':
                values.update(originals=[dict(row,deletion_status='deletion_pending') for row in job['originals']],deletion_pending=True,deletion_reason='successful_default')
            updated={**job,**values}
            tx.update(ref,values)
            if previous is None or (job['created_at'],intake_id)>(previous['created_at'],previous['policy_id']):tx.update(self.collection('shops').document(job['shop_id']),{'latest_policy_id':intake_id})
            tx.set(projection,{k:updated[k] for k in ('policy_id','shop_id','is_demo','created_at','status','assessment','comparison','baseline')}|{'media_sha256':[row['sha256'] for row in job['originals']],'original_deleted':False})
            return updated
        return complete(self.client.transaction())

    def request_deletion(self,intake_id:str,*,reason:str) -> dict:
        ref=self.collection('policy_jobs').document(intake_id);projection=self.collection('policies').document(intake_id)
        @firestore.transactional
        def request(tx):
            job=ref.get(transaction=tx).to_dict();existing=projection.get(transaction=tx)
            if reason=='successful_default' and (job['status']!='complete' or job['choice']=='keep'):return job
            originals=[dict(row,deletion_status='deletion_pending') if row['deletion_status']!='deleted' else row for row in job['originals']]
            values=dict(originals=originals,deletion_pending=bool(job['uploads']) and (any(row['deletion_status']!='deleted' for row in originals) or len(originals)+sum(bool(slot.get('absence_verified')) for slot in job['uploads'])<len(job['uploads'])),deletion_reason=reason)
            if reason in ('failed','cancelled') and job['status'] not in ('complete','failed','cancelled'):values['status']=reason
            if existing.exists and values.get('status') in ('failed','cancelled'):tx.update(projection,{'status':values['status']})
            tx.update(ref,values);return {**job,**values}
        return request(self.client.transaction())

    def deleted(self,intake_id:str,media_id:str,generation:str) -> dict:
        ref=self.collection('policy_jobs').document(intake_id);projection=self.collection('policies').document(intake_id)
        @firestore.transactional
        def finish(tx):
            job=ref.get(transaction=tx).to_dict();existing=projection.get(transaction=tx);originals=[]
            for row in job['originals']:
                if row['media_id']==media_id:
                    if row['object_generation']!=generation:raise ValueError('Policy original generation changed')
                    row={**row,'deletion_status':'deleted'}
                originals.append(row)
            pending=any(row['deletion_status']!='deleted' for row in originals) or len(originals)+sum(bool(slot.get('absence_verified')) for slot in job['uploads'])<len(job['uploads'])
            values=dict(originals=originals,deletion_pending=pending)
            tx.update(ref,values)
            if existing.exists:tx.update(projection,{'original_deleted':not pending})
            return {**job,**values}
        return finish(self.client.transaction())
    def pending_deletions(self,limit:int=20) -> list[str]:
        return [doc.id for doc in self.collection('policy_jobs').where(filter=FieldFilter('deletion_pending','==',True)).limit(limit).stream(timeout=5,retry=None)]

    def attach_recovered(self,intake_id:str,upload_key:str,original:PolicyOriginal) -> dict:
        """Resumer attachment; storage adapter has verified the reserved PUT identity."""
        ref=self.collection('policy_jobs').document(intake_id)
        @firestore.transactional
        def attach(tx):
            job=ref.get(transaction=tx).to_dict()
            slot=next((row for row in job['uploads'] if row['key']==upload_key),None)
            if not job['deletion_pending'] or not slot or slot.get('absence_verified') or slot['media_id']!=original.media_id or slot['mime_type']!=original.mime_type:raise ValueError('Unbound policy original')
            previous=next((row for row in job['originals'] if row['media_id']==original.media_id),None)
            if previous:
                if any(previous[k]!=original.model_dump()[k] for k in ('sha256','bytes','mime_type','object_generation')):raise ValueError('Immutable policy receipt changed')
                return job
            values={'originals':job['originals']+[original.model_copy(update={'deletion_status':'deletion_pending'}).model_dump()]}
            tx.update(ref,values);return {**job,**values}
        return attach(self.client.transaction())

    def absent(self,intake_id:str,upload_key:str) -> dict:
        """Only after shared media tombstone/write fencing and owned-object absence."""
        ref=self.collection('policy_jobs').document(intake_id);projection=self.collection('policies').document(intake_id)
        @firestore.transactional
        def absent(tx):
            job=ref.get(transaction=tx).to_dict();existing=projection.get(transaction=tx)
            if not job['deletion_pending']:return job
            uploads=[dict(row) for row in job['uploads']]
            slot=next((row for row in uploads if row['key']==upload_key),None)
            if not slot or any(row['media_id']==slot['media_id'] for row in job['originals']):raise ValueError('Policy receipt already exists')
            slot['absence_verified']=True
            pending=any(row['deletion_status']!='deleted' for row in job['originals']) or len(job['originals'])+sum(bool(row.get('absence_verified')) for row in uploads)<len(uploads)
            values={'uploads':uploads,'deletion_pending':pending}
            tx.update(ref,values)
            if existing.exists:tx.update(projection,{'original_deleted':not pending})
            return {**job,**values}
        return absent(self.client.transaction())

    def original_binding(self,media_id:str) -> dict|None:
        return self.collection('policy_originals').document(media_id).get(timeout=5,retry=None).to_dict()

    def synthetic_aggregate(self,shops:list[dict],as_of):
        if len(shops)>50 or any(shop.get('is_demo') is not True for shop in shops):raise ValueError('Synthetic policy projection exceeds bound')
        references=[];ids={shop['shop_id'] for shop in shops}
        for shop in shops:
            policy_id=shop.get('latest_policy_id')
            if policy_id:
                if len(policy_id)!=32 or any(c not in '0123456789abcdef' for c in policy_id):raise ValueError('Invalid policy projection pointer')
                references.append(self.collection('policies').document(policy_id))
        rows=[doc.to_dict() for doc in self.client.get_all(references,timeout=5,retry=None) if doc.exists] if references else []
        if len(rows)!=len(references):raise ValueError('Incomplete policy projection')
        return aggregate_policies(ids,rows,as_of)
