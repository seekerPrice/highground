"""Private pending photos, atomic rate limits and attributed report windows."""
from datetime import UTC,datetime,timedelta
from hashlib import sha256
from uuid import uuid4
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from api.agents.sessions import session_user_id
from api.demo_scenario import alerts_only_fixture
from api.photo_models import PhotoMedia
from api.tools.geo import distance_m
from api.media_models import MediaIngestError, MediaRequest

class PhotoStore:
    def __init__(self,client: firestore.Client,hash_salt:str,prefix:str='',risks=None):
        self.client,self.hash_salt,self.prefix=client,hash_salt,prefix
        from api.active_risk import ActiveRiskStore
        self.risk_store=risks or ActiveRiskStore(client,risks=prefix+'active_risks',shops=prefix+'shops')
    def collection(self,name: str) -> firestore.CollectionReference:return self.client.collection(self.prefix+name)
    def shop_for_sender(self,chat_id:int)->dict|None:
        matches=[]
        documents=list(self.collection('shops').limit(1001).stream(timeout=8,retry=None))
        if len(documents)>1000:return None # Incomplete membership cannot establish unique authorization.
        for doc in documents:
            value=doc.to_dict()
            if alerts_only_fixture(doc.id,value):continue
            member=next((r for r in value.get('recipients',[]) if r.get('telegram_chat_id')==chat_id),None)
            if member:matches.append(dict(value,shop_id=doc.id,language=member['language']))
        # Do not guess which shop when membership is ambiguous.
        return matches[0] if len(matches)==1 else None
    def bound_photo_report(self,sender:int,message_id:int,file_unique_id:str)->dict|None:
        shop=self.shop_for_sender(sender)
        if not shop:return None
        sender_hash=session_user_id(sender,self.hash_salt)
        report_id=sha256(f'{shop["shop_id"]}:{sender_hash}:{message_id}:{file_unique_id}'.encode()).hexdigest()[:32]
        row=self.collection('photo_reports').document(report_id).get(timeout=5,retry=None).to_dict()
        return row if row and row.get('sender_hash')==sender_hash and row.get('file_unique_id')==file_unique_id else None
    def authorize_media(self,request: MediaRequest)->bool:
        shop=self.collection('shops').document(request.shop_id).get().to_dict()
        return bool(shop and not alerts_only_fixture(request.shop_id,shop) and bool(shop.get('is_demo',False))==request.is_demo
                    and any(r.get('telegram_chat_id')==request.sender_chat_id for r in shop.get('recipients',[])))
    def begin(self,shop:dict,sender:int,message_id:int,telegram_date:datetime,photo:PhotoMedia,now:datetime)->dict:
        sender_hash=session_user_id(sender,self.hash_salt)
        report_id=sha256(f'{shop["shop_id"]}:{sender_hash}:{message_id}:{photo.file_unique_id}'.encode()).hexdigest()[:32]
        ref=self.collection('photo_reports').document(report_id)
        gate=self.collection('photo_rate').document(shop['shop_id'])
        private=self.collection('photo_pending').document(report_id)
        @firestore.transactional
        def begin(tx):
            existing=ref.get(transaction=tx)
            rate=gate.get(transaction=tx).to_dict() or {}
            if existing.exists:return existing.to_dict()
            if rate.get('next_at',now)>now:raise MediaIngestError('rate_limited')
            record=dict(report_id=report_id,shop_id=shop['shop_id'],sender_hash=sender_hash,
                        language=shop['language'],is_demo=bool(shop.get('is_demo',False)),
                        received_at=now,telegram_date=telegram_date,status='awaiting_location',processing_started_at=now,
                        default_lat=shop['lat'],default_lng=shop['lng'],file_unique_id=photo.file_unique_id)
            tx.set(ref,record)
            tx.set(private,dict(sender_chat_id=sender,message_id=message_id,**photo.model_dump()))
            tx.set(gate,{'next_at':now+timedelta(minutes=10)})
            return record
        return begin(self.client.transaction())
    def get(self,report_id:str)->dict|None:return self.collection('photo_reports').document(report_id).get().to_dict()
    def private(self,report_id:str)->dict|None:return self.collection('photo_pending').document(report_id).get().to_dict()
    def update(self,report_id:str,owner:str,**fields) -> None:
        ref=self.collection('photo_reports').document(report_id)
        @firestore.transactional
        def update(tx):
            current=ref.get(transaction=tx).to_dict()
            if current.get('owner')!=owner:raise MediaIngestError('report_claim_changed')
            for key in ('media_id','sha256','ingest_elapsed_ms','confirmation_requested_at','triage'):
                if key in fields and key in current and current[key]!=fields[key]:raise MediaIngestError('metadata_conflict')
            tx.update(ref,dict(fields,lease_until=datetime.now(UTC)+timedelta(seconds=30)))
        update(self.client.transaction())
    def confirm(self,report_id:str,sender:int,lat:float,lng:float,attribution:str,now:datetime)->dict:
        ref=self.collection('photo_reports').document(report_id)
        sender_hash=session_user_id(sender,self.hash_salt)
        @firestore.transactional
        def confirm(tx):
            data=ref.get(transaction=tx).to_dict()
            if not data or data['sender_hash']!=sender_hash:raise MediaIngestError('unauthorized_media')
            if 'lat' in data and (data['lat'],data['lng'],data['location_attribution'])!=(lat,lng,attribution):raise MediaIngestError('metadata_conflict')
            if 'confirmed_at' not in data:
                wait_from=data.get('confirmation_requested_at',data['received_at'])
                values=dict(lat=lat,lng=lng,location_attribution=attribution,confirmed_at=now,
                            confirmation_wait_ms=max(0,int((now-wait_from).total_seconds()*1000)),status='ready')
                tx.update(ref,values);data.update(values)
            return data
        return confirm(self.client.transaction())
    def claim(self,report_id:str)->str:
        ref=self.collection('photo_reports').document(report_id);owner=uuid4().hex;now=datetime.now(UTC)
        @firestore.transactional
        def claim(tx):
            data=ref.get(transaction=tx).to_dict()
            if data.get('lease_until',now)>now:raise MediaIngestError('report_busy')
            tx.update(ref,{'owner':owner,'lease_until':now+timedelta(seconds=30)})
        claim(self.client.transaction());return owner
    def release(self,report_id:str,owner:str) -> None:
        ref=self.collection('photo_reports').document(report_id)
        @firestore.transactional
        def release(tx):
            if ref.get(transaction=tx).to_dict().get('owner')==owner:tx.update(ref,{'lease_until':datetime.now(UTC)})
        release(self.client.transaction())
    def recent_reports(self,lat:float,lng:float,now:datetime,is_demo:bool)->list[dict]:
        start=now-timedelta(minutes=30);result=[]
        query=self.collection('photo_reports').where(filter=FieldFilter('is_demo','==',is_demo))
        for doc in query.stream():
            record=doc.to_dict()
            if record.get('evidence_status') not in ('positive','unverified'):continue
            reported_at=record.get('received_at')
            if not reported_at or not start<=reported_at<=now:continue
            if 'lat' not in record or 'lng' not in record:continue
            if distance_m(lat,lng,record['lat'],record['lng'])<=500:result.append(record)
        return result
    def danger_active(self,shop_id:str)->bool:
        return self.risk_store.get(shop_id).active_danger
    def request_shared(self,report_id:str,sender:int)->None:
        ref=self.collection('photo_reports').document(report_id)
        identity=session_user_id(sender,self.hash_salt)
        @firestore.transactional
        def update(tx):
            record=ref.get(transaction=tx).to_dict()
            if not record or record['sender_hash']!=identity:raise MediaIngestError('unauthorized_media')
            if 'lat' in record:raise MediaIngestError('metadata_conflict')
            tx.update(ref,{'status':'awaiting_shared'})
        update(self.client.transaction())
    def propose_shared(self,report_id:str,sender:int,lat:float,lng:float)->None:
        ref=self.collection('photo_reports').document(report_id)
        identity=session_user_id(sender,self.hash_salt)
        @firestore.transactional
        def update(tx):
            record=ref.get(transaction=tx).to_dict()
            if not record or record['sender_hash']!=identity or record['status']!='awaiting_shared':
                raise MediaIngestError('unauthorized_media')
            tx.update(ref,{'status':'awaiting_shared_confirmation','proposed_lat':lat,'proposed_lng':lng})
        update(self.client.transaction())
    def pending_location_report_id(self,sender:int)->str|None:
        identity=session_user_id(sender,self.hash_salt)
        query=self.collection('photo_reports').where(filter=FieldFilter('sender_hash','==',identity))
        matches=[doc.id for doc in query.stream() if doc.to_dict().get('status') in ('awaiting_shared','awaiting_shared_confirmation')]
        return matches[0] if len(matches)==1 else None
