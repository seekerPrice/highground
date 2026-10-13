"""Private derived-card snapshots and uncertain-send leases, separate from evidence."""
from datetime import UTC,datetime,timedelta
from uuid import uuid4
from google.cloud import firestore
from api.offline_card import CardContext

class FirestoreCardStore:
    def __init__(self,client,*,collection='offline_cards',shops='shops'):
        self.client,self.collection,self.shops=client,collection,shops

    def scenario(self):
        from api.demo_scenario import scenario_collection
        return self.client.collection(scenario_collection(self.shops)).document('current').get(timeout=8,retry=None).to_dict() or {}

    def get(self,identity):return self.client.collection(self.collection).document(identity).get(timeout=8,retry=None).to_dict()

    def begin(self,context:CardContext,chat_id:int,event:dict):
        ref=self.client.collection(self.collection).document(context.card_id)
        @firestore.transactional
        def create(tx):
            existing=ref.get(transaction=tx,timeout=8,retry=None).to_dict()
            if existing:
                if existing['chat_id']!=chat_id or existing['context']['shop_id']!=context.shop_id:raise ValueError('Private card identity conflict')
                return existing
            record={'card_id':context.card_id,'context':context.model_dump(mode='python'),'chat_id':chat_id,'event':event,'status':'pending','created_at':context.prepared_at}
            tx.create(ref,record);return record
        return create(self.client.transaction())

    def claim(self,identity):
        ref=self.client.collection(self.collection).document(identity);now=datetime.now(UTC);owner=uuid4().hex
        @firestore.transactional
        def claim(tx):
            value=ref.get(transaction=tx,timeout=8,retry=None).to_dict()
            if not value:raise ValueError('Card not found')
            if value['status'] not in ('pending','preparing','sending','retryable','accepted','uncertain','superseded','virtual_skipped'):raise ValueError('Invalid card delivery state')
            if value['status'] in ('accepted','uncertain','superseded','virtual_skipped'):return value['status'],None
            if value.get('lease_until',now)>now:return 'busy',None
            if value['status']=='sending':tx.update(ref,{'status':'uncertain'});return 'uncertain',None
            tx.update(ref,{'status':'preparing','owner':owner,'lease_until':now+timedelta(seconds=90)})
            return 'claimed',owner
        return claim(self.client.transaction())

    def update(self,identity,owner,**fields):
        ref=self.client.collection(self.collection).document(identity)
        @firestore.transactional
        def update(tx):
            value=ref.get(transaction=tx,timeout=8,retry=None).to_dict()
            if value.get('owner')!=owner:raise ValueError('Card claim ownership changed')
            for key in ('choice','asset_sha256','asset_path'):
                if key in fields and key in value and fields[key]!=value[key]:raise ValueError('Immutable card artifact conflict')
            tx.update(ref,fields)
        update(self.client.transaction())

    def pending_ids(self,limit=20):
        from google.cloud.firestore_v1.base_query import FieldFilter
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Card resume limit must be 1..20')
        return [doc.id for doc in self.client.collection(self.collection).where(filter=FieldFilter('status','in',['pending','preparing','retryable','sending'])).limit(limit).stream(timeout=8,retry=None)]
