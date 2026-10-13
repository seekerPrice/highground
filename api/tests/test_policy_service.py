"""Real Firestore policy lifecycle; original/model transports deliberately fake."""
import asyncio
from datetime import UTC,datetime
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
import os
import pytest
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.agents.sessions import session_user_id
from api.policy import PolicyService,PolicyDocument,PolicyRecovery
from api.policy_store import PolicyStore
from api.policy_models import PolicyOriginal
from api.media import IngestedMedia
from api.tests.test_policy_models import assessment

@pytest.fixture
def policy():
    if not os.environ.get('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore emulator required')
    client=create_firestore_client(Settings(gcp_project='highground-policy-tests'));prefix='policy-'+uuid4().hex+'-'
    store=PolicyStore(client,'synthetic',prefix)
    store.collection('shops').document('shop').set(dict(lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=123,role='owner',language='en'),dict(telegram_chat_id=456,role='worker',language='en')]))
    gateway=Originals();model=Model();active=PolicyService(store,gateway,model)
    try:yield active,store,gateway,model
    finally:
        for name in ('shops','policy_current','policy_jobs','policy_intents','policy_uploads','policy_originals','policies','inventories','active_risks'):
            for doc in store.collection(name).stream(timeout=5,retry=None):doc.reference.delete(timeout=5,retry=None)
        client.close()

class Originals:
    def __init__(self):self.objects={};self.deleted=[];self.calls=0;self.hook=None;self.retired=set();self.outage=False
    async def ingest(self,request,*,max_bytes):
        self.calls+=1
        if request.media_id in self.retired:raise ValueError('Tombstoned original')
        data=b'synthetic policy page'+request.media_id.encode()
        assert len(data)<=max_bytes
        row=PolicyOriginal(media_id=request.media_id,sha256=sha256(data).hexdigest(),bytes=len(data),mime_type=request.mime_type,object_generation='7')
        self.objects[request.media_id]=(row,data)
        if self.hook:await self.hook(request)
        return IngestedMedia(SimpleNamespace(**row.model_dump()),data)
    async def retire(self,job):self.retired.update(row['media_id'] for row in job['uploads'])
    async def recover(self,job,upload):
        existing=self.objects.get(upload['media_id'])
        return PolicyRecovery(original=existing[0]) if existing else PolicyRecovery(absence_verified=True)
    async def delete(self,original):
        if self.outage:raise RuntimeError('Storage unavailable')
        existing=self.objects.get(original.media_id)
        if existing and existing[0].object_generation!=original.object_generation:return False
        self.objects.pop(original.media_id,None);self.deleted.append((original.media_id,original.object_generation));return True
    async def read(self,original):
        row,data=self.objects[original.media_id]
        assert row.object_generation==original.object_generation
        return IngestedMedia(SimpleNamespace(**row.model_dump()),data)
class Model:
    def __init__(self):self.calls=0;self.result=assessment()
    async def assess(self,*args):
        self.calls+=1
        if isinstance(self.result,Exception):raise self.result
        return self.result
    async def close(self):pass

def document(unique='page',mime='image/jpeg'):return PolicyDocument(file_id=unique,file_unique_id=unique,mime_type=mime,file_size=100)
async def start(active):
    reply=await active.start(123,'start')
    assert reply.disclosure and 'before your first document' in reply.text and 'Telegram message' in reply.text
    await active.mark_disclosed(123,reply.intake_id,10)
    return reply.intake_id
async def upload(active,number=1,unique=None,mime='image/jpeg'):
    return await active.handle_document(123,number,number,int(datetime.now(UTC).timestamp()),document(unique or str(number),mime))

def test_owner_disclosure_multiphoto_keep_and_cancel_contract(policy):
    active,store,gateway,model=policy
    async def run():
        assert 'Only the registered' in (await active.start(456,'worker')).text
        reply=await active.start(123,'start')
        assert 'Document not accepted' in (await upload(active)).text and gateway.calls==0
        await active.mark_disclosed(123,reply.intake_id,10)
        await active.choose_keep(123,reply.intake_id)
        for n in range(1,6):assert 'Policy photo received' in (await upload(active,n)).text
        assert model.calls==0 and len(store.get(reply.intake_id)['originals'])==5
        assert 'Document not accepted' in (await upload(active,6)).text and gateway.calls==5
        frozen=await active.choose_keep(123,reply.intake_id);assert 'frozen' in frozen.text
        result=await active.done(123,reply.intake_id)
        assert result.kind=='policy_result' and '≈RM 40.00' not in result.text # no baseline
        assert 'shortfall is unknown' in result.text and 'estimated_shortfall' not in result.text
        assert len(gateway.objects)==5 and model.calls==1
        with pytest.raises(PermissionError):await active.read_kept(456,reply.intake_id,store.get(reply.intake_id)['originals'][0]['media_id'])
        await active.delete_copy(123,reply.intake_id)
        assert not gateway.objects and not store.get(reply.intake_id)['deletion_pending']
        calls=gateway.calls;await upload(active,1);assert gateway.calls==calls # no resurrection
    asyncio.run(run())

def test_cancel_during_put_late_receipt_is_deleted_and_replay_never_downloads(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active)
        await active.choose_keep(123,identity)
        async def cancel(request):store.request_deletion(identity,reason='cancelled')
        gateway.hook=cancel
        reply=await upload(active)
        job=store.get(identity)
        assert job['status']=='cancelled' and job['originals'][0]['deletion_status']=='deleted'
        assert not gateway.objects and model.calls==0 and 'cancelled' in reply.text
        gateway.hook=None;await upload(active);assert gateway.calls==1
    asyncio.run(run())

def test_success_commit_crash_is_discoverable_for_default_deletion_without_model_rerun(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active);await upload(active)
        complete=store.complete
        def crash(*args,**kwargs):
            complete(*args,**kwargs);raise SystemExit('process interrupted after commit')
        store.complete=crash
        with pytest.raises(SystemExit):await active.done(123,identity)
        job=store.get(identity)
        assert job['status']=='complete' and job['deletion_pending'] and identity in store.pending_deletions()
        store.complete=complete
        fresh=PolicyService(store,gateway,model)
        result=await fresh.resume_deletions()
        assert result=={'scanned':1,'completed':1,'pending':0} and not gateway.objects and model.calls==1
        assert await fresh.resume_deletions()=={'scanned':0,'completed':0,'pending':0}
    asyncio.run(run())

def test_put_before_receipt_crash_cancel_recovers_owned_generation_and_pending_outage(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active)
        async def crash(request):raise SystemExit('PUT committed before receipt attachment')
        gateway.hook=crash
        with pytest.raises(SystemExit):await upload(active)
        assert not store.get(identity)['originals'] and len(gateway.objects)==1
        store.request_deletion(identity,reason='cancelled');gateway.outage=True
        result=await active.resume_deletions();assert result['pending']==1
        recovered=store.get(identity);assert recovered['originals'][0]['object_generation']=='7'
        gateway.outage=False;assert (await active.resume_deletions())['completed']==1
        assert not gateway.objects and model.calls==0
    asyncio.run(run())

def test_completed_kept_projection_cannot_be_cancelled_by_stale_extraction_commit(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active);await upload(active)
        job=store.claim_extraction(identity,123)
        store.request_deletion(identity,reason='cancelled')
        with pytest.raises(ValueError):store.complete(identity,123,assessment(),{},owner=job['owner'])
        assert not store.collection('policies').document(identity).get().exists
        await active.resume_deletions();assert not gateway.objects
    asyncio.run(run())

def test_frozen_baseline_gap_and_danger_never_shows_capture_or_model_request(policy):
    from api.tests.test_inventory import assessment as inventory_assessment
    active,store,gateway,model=policy
    frozen=inventory_assessment().model_dump()|dict(inventory_id='baseline',media_id='b'*64,total_est_value_rm=100.,shop_id='shop')
    frozen['items'][0]['qty']=10.
    store.collection('inventories').document('baseline').set(frozen)
    shop=store.collection('shops').document('shop');shop.update({'baseline_inventory_id':'baseline'})
    async def run():
        identity=await start(active);await upload(active)
        shop.update({'baseline_inventory_id':'changed-after-first-document'})
        result=await active.done(123,identity)
        assert '≈RM 40.00' in result.text and '≈RM 100.00' in result.text and 'estimated_shortfall' not in result.text
        assert store.get(identity)['baseline']['inventory_id']=='baseline'
        assert not gateway.objects
        assert model.calls==1
        shop.update({'active_danger':True})
        danger=await active.start(123,'next')
        assert danger.kind=='danger' and not danger.disclosure and 'policy' not in danger.text.lower()
        # A reply generated just before Danger must be replaced by fixed output.
        assert (await active.recheck_reply(123,result)).kind=='danger'
    asyncio.run(run())

def test_keep_failed_extraction_deletes_all_originals_and_unknown_no_money_claim(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active);await active.choose_keep(123,identity);await upload(active)
        model.result=ValueError('Invalid extraction')
        reply=await active.done(123,identity)
        assert model.calls==2 and 'unavailable' in reply.text and not gateway.objects
        job=store.get(identity);assert job['status']=='failed' and job['originals'][0]['deletion_status']=='deleted'
        with pytest.raises(PermissionError):await active.read_kept(123,identity,job['originals'][0]['media_id'])
    asyncio.run(run())

def test_post_put_validation_failure_cannot_orphan_an_unattached_original(policy):
    active,store,gateway,model=policy
    async def run():
        identity=await start(active)
        async def invalid(request):raise ValueError('Receipt validation failed after PUT')
        gateway.hook=invalid
        await upload(active)
        job=store.get(identity)
        assert job['status']=='failed' and not job['deletion_pending']
        assert job['originals'][0]['deletion_status']=='deleted' and not gateway.objects and model.calls==0
    asyncio.run(run())
