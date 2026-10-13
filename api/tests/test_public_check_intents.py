"""Public intent operations over a deterministic atomic SDK boundary double."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import RLock
from unittest.mock import patch
from api.public_check_store import FirestoreCheckIntentStore
from api.tests.test_public_check import NOW,LOCATION,project_check

class Snapshot:
    def __init__(self,value):self.value=value
    def to_dict(self):return deepcopy(self.value)
class Ref:
    def __init__(self,client,key):self.client,self.key=client,key
    def get(self,**kwargs):return Snapshot(self.client.data.get(self.key))
class Collection:
    def __init__(self,client,name):self.client,self.name=client,name
    def document(self,identity):return Ref(self.client,(self.name,identity))
class Transaction:
    def __init__(self,client):self.client,self.writes=client,[]
    def create(self,ref,value):
        if ref.key in self.client.data:raise ValueError('already exists')
        self.writes.append((ref.key,deepcopy(value),False))
    def set(self,ref,value):self.writes.append((ref.key,deepcopy(value),False))
    def update(self,ref,value):self.writes.append((ref.key,deepcopy(value),True))
class Client:
    def __init__(self):self.data={};self.lock=RLock()
    def collection(self,name):return Collection(self,name)
    def transaction(self,**kwargs):return Transaction(self)
def transactional(function):
    def run(tx):
        with tx.client.lock:
            result=function(tx)
            for key,value,merge in tx.writes:
                tx.client.data[key]={**tx.client.data[key],**value} if merge else value
            return result
    return run


def test_sender_bound_five_minute_expiry_and_thirty_second_rate_do_not_refresh_on_replay():
    client=Client();store=FirestoreCheckIntentStore(client,'private-test-salt')
    with patch('api.public_check_store.firestore.transactional',transactional):
        first=store.open(101,'check-one',NOW)
        assert first.status=='waiting_location'
        assert store.open(101,'check-one',NOW+timedelta(minutes=4)).intent_id==first.intent_id
        assert store.claim(102,first.intent_id,'location-one',NOW).status=='unauthorized'
        claim=store.claim(101,first.intent_id,'location-one',NOW)
        assert claim.status=='claimed'
        result=project_check(LOCATION,(),(),(),now=NOW,report_source_available=False)
        assert store.finish(101,first.intent_id,claim.owner,result,NOW).status=='complete'
        replay=store.claim(101,first.intent_id,'location-one',NOW+timedelta(seconds=1))
        assert replay.result==result and replay.status=='complete'
        assert store.claim(101,first.intent_id,'different-location',NOW+timedelta(seconds=1)).status=='consumed'
        second=store.open(101,'check-two',NOW+timedelta(seconds=10))
        assert store.claim(101,second.intent_id,'location-two',NOW+timedelta(seconds=29)).status=='rate_limited'
        assert store.claim(101,second.intent_id,'location-two',NOW+timedelta(seconds=30)).status=='claimed'
        assert store.open(101,'check-one',NOW+timedelta(minutes=5)).status=='expired'
        assert store.active(101,NOW+timedelta(minutes=6)).status=='expired'
    private=str(client.data)
    assert 'latitude' not in private and 'longitude' not in private and "'lat'" not in private and "'lng'" not in private
    assert 'check-one' not in private and 'private-test-salt' not in private


def test_competing_claims_have_one_owner_and_failed_processing_retry_keeps_same_operation():
    client=Client();store=FirestoreCheckIntentStore(client,'private-test-salt')
    with patch('api.public_check_store.firestore.transactional',transactional):
        intent=store.open(101,'check',NOW)
        with ThreadPoolExecutor(max_workers=8) as pool:claims=list(pool.map(lambda _:store.claim(101,intent.intent_id,'location',NOW),range(8)))
        assert sum(c.status=='claimed' for c in claims)==1
        assert sum(c.status=='busy' for c in claims)==7
        owner=next(c.owner for c in claims if c.status=='claimed')
        store.retryable(101,intent.intent_id,owner,NOW)
        assert store.claim(101,intent.intent_id,'location',NOW).status=='claimed'
        assert store.claim(101,intent.intent_id,'other-location',NOW).status=='consumed'
        assert store.claim(101,intent.intent_id,'location',NOW+timedelta(minutes=5)).status=='expired'


def test_actual_firestore_intent_concurrency_sanitized_replay_and_exact_expiry():
    import os
    from uuid import uuid4
    import pytest
    from google.auth.credentials import AnonymousCredentials
    from google.cloud import firestore
    if not os.getenv('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore required')
    if os.environ['FIRESTORE_EMULATOR_HOST']!='127.0.0.1:8787':pytest.fail('Dedicated loopback Firestore required')
    client=firestore.Client(project='highground-public-check-tests',credentials=AnonymousCredentials())
    prefix='check_'+uuid4().hex+'_'
    store=FirestoreCheckIntentStore(client,'isolated-test-salt',intents=prefix+'intents',senders=prefix+'senders',operations=prefix+'operations')
    try:
        intent=store.open(101,'check',NOW,language='ms')
        with ThreadPoolExecutor(max_workers=2) as pool:claims=list(pool.map(lambda _:store.claim(101,intent.intent_id,'location',NOW),range(2)))
        assert sorted(c.status for c in claims)==['busy','claimed']
        claimed=next(c for c in claims if c.status=='claimed')
        result=project_check(LOCATION,(),(),(),now=NOW,report_source_available=False)
        assert store.finish(101,intent.intent_id,claimed.owner,result,NOW).result==result
        assert store.claim(101,intent.intent_id,'location',NOW+timedelta(seconds=1)).result==result
        assert store.claim(102,intent.intent_id,'location',NOW).status=='unauthorized'
        assert store.claim(101,intent.intent_id,'location',NOW+timedelta(minutes=5)).status=='expired'
        records=[doc.to_dict() for doc in client.collection(store.intents).stream(timeout=5,retry=None)]
        assert len(records)==1
        assert set(records[0])=={'sender_hash','created_at','expires_at','status','language','lookup_operation_hash','owner','lease_until','result_json','completed_at'}
        assert '"lat"' not in records[0]['result_json'] and '"lng"' not in records[0]['result_json']
        assert store.bound(101,'location',NOW+timedelta(seconds=1)).language=='ms'
        new=store.open(101,'new-request',NOW+timedelta(seconds=2),language='zh')
        assert store.bound(101,'location',NOW+timedelta(seconds=3)).status=='expired'
        assert store.claim(101,new.intent_id,'location',NOW+timedelta(seconds=31)).status=='consumed'
        assert store.active(101,NOW+timedelta(seconds=3)).status=='waiting_location'
        bindings=[doc.to_dict() for doc in client.collection(store.operations).stream(timeout=5,retry=None)]
        assert bindings==[{'intent_id':intent.intent_id}]
    finally:
        try:
            for collection in (store.intents,store.senders,store.operations):
                for doc in client.collection(collection).stream(timeout=5,retry=None):doc.reference.delete(timeout=5,retry=None)
        finally:client.close()


def test_original_location_binding_cannot_attach_to_new_request_and_locale_is_frozen():
    client=Client();store=FirestoreCheckIntentStore(client,'private-test-salt')
    with patch('api.public_check_store.firestore.transactional',transactional):
        old=store.open(101,'old-request',NOW,language='ms')
        claimed=store.claim(101,old.intent_id,'original-location-message',NOW)
        result=project_check(LOCATION,(),(),(),now=NOW,report_source_available=False)
        store.finish(101,old.intent_id,claimed.owner,result,NOW)
        assert store.bound(101,'original-location-message',NOW).language=='ms'
        new=store.open(101,'new-request',NOW+timedelta(seconds=1),language='zh')
        assert store.bound(101,'original-location-message',NOW+timedelta(seconds=2)).status=='expired'
        assert store.claim(101,new.intent_id,'original-location-message',NOW+timedelta(seconds=31)).status=='consumed'
        assert store.active(101,NOW+timedelta(seconds=2)).intent_id==new.intent_id
        assert store.active(101,NOW+timedelta(seconds=2)).status=='waiting_location'
        assert store.active(101,NOW+timedelta(seconds=2)).language=='zh'
        bindings=[value for (collection,_),value in client.data.items() if collection==store.operations]
        assert bindings==[{'intent_id':old.intent_id}]
