"""Private resumable video intent and immutable inventory snapshots."""
from datetime import UTC,datetime,timedelta
from hashlib import sha256
from uuid import uuid4
from google.cloud import firestore
from api.photo_store import PhotoStore
from api.inventory_models import VideoMedia,InventoryAssessment
from api.lift_first import rank_lift_first
from api.media_models import MediaIngestError
from api.agents.sessions import session_user_id

class InventoryStore(PhotoStore):
    def begin_video(self,shop:dict,sender:int,message_id:int,telegram_date:datetime,video:VideoMedia,now:datetime)->dict:
        identity=sha256(f"{shop['shop_id']}:{session_user_id(sender,self.hash_salt)}:{message_id}:{video.file_unique_id}".encode()).hexdigest()
        ref=self.collection('inventory_jobs').document(identity)
        private=self.collection('inventory_pending').document(identity)
        @firestore.transactional
        def begin(tx):
            existing=ref.get(transaction=tx)
            if existing.exists:return existing.to_dict()
            record=dict(inventory_id=identity,shop_id=shop['shop_id'],language=shop['language'],is_demo=bool(shop.get('is_demo')),
                sender_hash=session_user_id(sender,self.hash_salt),received_at=now,telegram_date=telegram_date,
                lat=shop['lat'],lng=shop['lng'],duration=video.duration,status='pending',
                kind='update' if shop.get('baseline_inventory_id') else 'baseline')
            tx.create(ref,record);tx.create(private,dict(sender_chat_id=sender,message_id=message_id,**video.model_dump()))
            return record
        return begin(self.client.transaction())

    def claim_job(self,identity:str)->str:
        owner=uuid4().hex;now=datetime.now(UTC);ref=self.collection('inventory_jobs').document(identity)
        @firestore.transactional
        def claim(tx):
            job=ref.get(transaction=tx).to_dict()
            if job.get('lease_until',now)>now:raise MediaIngestError('inventory_busy')
            tx.update(ref,dict(owner=owner,lease_until=now+timedelta(seconds=60)))
        claim(self.client.transaction());return owner

    def update_job(self,identity:str,owner:str,**values)->None:
        ref=self.collection('inventory_jobs').document(identity)
        @firestore.transactional
        def update(tx):
            job=ref.get(transaction=tx).to_dict()
            if job.get('owner')!=owner:raise MediaIngestError('inventory_claim_changed')
            for field in ('media_id','assessment'):
                if field in values and field in job and job[field]!=values[field]:raise MediaIngestError('metadata_conflict')
            tx.update(ref,dict(values,lease_until=datetime.now(UTC)+timedelta(seconds=60)))
        update(self.client.transaction())

    def release_job(self,identity:str,owner:str)->None:
        ref=self.collection('inventory_jobs').document(identity)
        @firestore.transactional
        def release(tx):
            if ref.get(transaction=tx).to_dict().get('owner')==owner:tx.update(ref,{'lease_until':datetime.now(UTC)})
        release(self.client.transaction())

    def save_inventory(self,job:dict,owner:str,assessment:InventoryAssessment)->dict:
        ref=self.collection('inventories').document(job['inventory_id'])
        shop_ref=self.collection('shops').document(job['shop_id'])
        job_ref=self.collection('inventory_jobs').document(job['inventory_id'])
        items=rank_lift_first(assessment)
        record=dict(inventory_id=job['inventory_id'],shop_id=job['shop_id'],kind=job['kind'],media_id=job['media_id'],
            created_at=job['received_at'],items=[i.model_dump() for i in assessment.items],
            total_est_value_rm=round(sum(i.qty*i.est_unit_value_rm for i in assessment.items),2),
            lift_first=[i.model_dump() for i in items],lift_first_value_rm=round(sum(i.value_rm for i in items),2),
            confidence=assessment.confidence,confidence_note=assessment.confidence_note,is_demo=job['is_demo'])
        @firestore.transactional
        def save(tx):
            current=job_ref.get(transaction=tx).to_dict();existing=ref.get(transaction=tx)
            shop=shop_ref.get(transaction=tx).to_dict()
            if current.get('owner')!=owner:raise MediaIngestError('inventory_claim_changed')
            if existing.exists:return existing.to_dict()
            tx.create(ref,record)
            # An older retry cannot replace a newer inventory refresh.
            if not shop.get('inventory_at') or shop['inventory_at']<=job['received_at']:
                tx.update(shop_ref,dict(baseline_inventory_id=job['inventory_id'],inventory_at=job['received_at'],
                                       lift_first=record['lift_first'],lift_first_value_rm=record['lift_first_value_rm'],
                                       risk_score=min(100,(40 if shop.get('floor')=='ground' else 0)+(20 if shop.get('has_vehicle') else 0)
                                           +(20 if record['lift_first_value_rm']>2000 else 0)+(20 if shop.get('river_or_past_event_exposure') is True else 0)),
                                       risk_score_missing=[v for v in shop.get('risk_score_missing',[]) if v!='inventory'],
                                       risk_score_provisional=bool([v for v in shop.get('risk_score_missing',[]) if v!='inventory'])))
            tx.update(job_ref,dict(status='complete',assessment=assessment.model_dump()))
            return record
        return save(self.client.transaction())
