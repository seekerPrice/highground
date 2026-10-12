import asyncio
from datetime import UTC,datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import os
import pytest
from pydantic import ValidationError
from api.inventory_models import InventoryAssessment,InventoryItem,VideoMedia
from api.lift_first import rank_lift_first
from api.inventory import InventoryService
from api.inventory_store import InventoryStore
from api.tools.firestore import create_firestore_client
from api.config import Settings
from api.tests.test_media import service as media_service

VIDEO=(Path(__file__).parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes()
def item(**updates):
    values=dict(name='Rice',category='food',qty=2.,est_unit_value_rm=10.,location_in_shop='shelf',height='low',lift_effort=1,timestamp_s=1.)
    values.update(updates);return InventoryItem(**values)
def assessment(items=None):return InventoryAssessment(items=items if items is not None else [item()],confidence=.8,confidence_note='Synthetic visual estimates only.')
def video():return VideoMedia(file_id='video',file_unique_id='unique-video',file_size=len(VIDEO),duration=30,width=1536,height=1024)

def test_rank_top_eight_height_score_stable_tie_and_exact_value():
    goods=[item(name=f'Item{i}',qty=1.,est_unit_value_rm=float(i+1),lift_effort=1) for i in range(10)]
    goods += [item(name='High',height='high',est_unit_value_rm=999.),item(name='Heavy',qty=1.,est_unit_value_rm=6.,lift_effort=3)]
    ranked=rank_lift_first(assessment(goods))
    assert len(ranked)==8 and ranked[0].item_name=='Item9' and all(i.item_name!='High' for i in ranked)
    assert sum(i.value_rm for i in ranked)==sum(range(3,11))
    tied=rank_lift_first(assessment([item(name='Z'),item(name='A')]))
    assert [i.item_name for i in tied]==['A','Z']
    assert tied==rank_lift_first(assessment([item(name='Z'),item(name='A')]))

@pytest.mark.parametrize('changes',[{'qty':float('nan')},{'est_unit_value_rm':float('inf')},{'qty':0},{'height':'unknown'},{'lift_effort':4},{'timestamp_s':-1}])
def test_inventory_invalid_values(changes):
    with pytest.raises(ValidationError):item(**changes)
def test_timestamp_must_fit_telegram_supplied_duration():
    with pytest.raises(ValueError):assessment([item(timestamp_s=31.)]).validate_duration(30)
    assert assessment([item(timestamp_s=30.)]).validate_duration(30)

class Assessor:
    def __init__(self,result,hook=None):self.result=result;self.calls=0;self.hook=hook
    async def assess(self,*args):
        self.calls+=1
        if self.hook:self.hook()
        if isinstance(self.result,Exception):raise self.result
        return self.result
    async def close(self):pass

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
@pytest.mark.parametrize('danger_stage',[None,'before','during','before_send'])
def test_native_video_immutable_inventory_retry_and_danger_guards(danger_stage):
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='inventory-'+uuid4().hex+'-'
    store=InventoryStore(client,'synthetic',prefix)
    shop=store.collection('shops').document('shop')
    shop.set(dict(shop_name='Synthetic',floor='ground',risk_score_missing=['inventory','river_or_past_event_exposure'],lat=3.,lng=101.,is_demo=True,
        recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,media_store,download,storage,ledger=media_service();download.data=VIDEO;media.authorize=store.authorize_media
    model=Assessor(assessment([item(name=f'Item{i}') for i in range(8)]),hook=(lambda:shop.update({'active_danger':True})) if danger_stage=='during' else None)
    active=InventoryService(store,media,model)
    if danger_stage=='before':shop.update({'active_danger':True})
    async def run():
        now=datetime.now(UTC)
        reply=await active.handle_video(123,1,1,int(now.timestamp()),video())
        assert media_store.record.sha256==sha256(VIDEO).hexdigest() and ledger.ids
        if danger_stage in ('before','during'):
            assert reply.kind=='danger' and 'refresh' not in reply.text
            assert model.calls==(0 if danger_stage=='before' else 1)
        else:
            assert reply.kind=='inventory' and 'File integrity verified' in reply.text
            saved=store.collection('inventories').document(reply.inventory_id).get().to_dict()
            assert len(saved['lift_first'])==8 and saved['lift_first_value_rm']==160.
            assert all(i['item_name'] in reply.text for i in saved['lift_first'])
            assert 'river_or_past_event_exposure' in shop.get().to_dict()['risk_score_missing']
            again=await active.handle_video(123,1,1,int(now.timestamp()),video())
            assert again.inventory_id==reply.inventory_id and model.calls==1 and download.calls==1
            if danger_stage=='before_send':
                shop.update({'active_danger':True})
                assert (await active.recheck_reply(123,reply)).kind=='danger'
    try:asyncio.run(run())
    finally:
        for name in ('shops','inventories','inventory_jobs','inventory_pending','active_risks'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_empty_assessment_preserves_known_baseline_and_unknown_risk():
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='empty-'+uuid4().hex+'-'
    store=InventoryStore(client,'synthetic',prefix)
    shop=store.collection('shops').document('shop')
    shop.set(dict(lat=3.,lng=101.,is_demo=True,baseline_inventory_id='known',lift_first_value_rm=80.,
        risk_score_provisional=True,risk_score_missing=['river_or_past_event_exposure'],
        recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,*_=media_service();media.downloader.data=VIDEO;media.authorize=store.authorize_media
    active=InventoryService(store,media,Assessor(assessment([])))
    try:
        reply=asyncio.run(active.handle_video(123,1,1,int(datetime.now(UTC).timestamp()),video()))
        assert reply.kind=='unavailable' and shop.get().to_dict()['baseline_inventory_id']=='known'
        assert shop.get().to_dict()['risk_score_provisional']
        assert not list(store.collection('inventories').stream())
        assert next(store.collection('inventory_jobs').stream()).to_dict()['assessment']['items']==[]
    finally:
        for name in ('shops','inventories','inventory_jobs','inventory_pending'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.skipif(not all(os.environ.get(name) for name in ('FIRESTORE_EMULATOR_HOST','STORAGE_EMULATOR_HOST')),reason='local Firestore/GCS required')
def test_public_onboarding_native_video_actual_original_storage_and_refresh():
    import httpx
    from api.tests.test_onboarding import Harness,HEADERS,SETTINGS
    from api.media import MediaService
    from api.media_store import MediaStore
    from api.tools.storage import create_storage_client,OriginalStorage
    from api.tests.test_media import Download,Ledger
    async def run():
        h=Harness();await h.initialize()
        storage_client=create_storage_client(SETTINGS);bucket='inventory-'+uuid4().hex
        storage_client.create_bucket(bucket,timeout=8,retry=None);storage=OriginalStorage(storage_client,bucket)
        try:
            completed=await h.owner_flow(vehicle=False)
            assert '30–45 second' in completed
            store=InventoryStore(h.client,SETTINGS.hash_salt,h.prefix)
            ledger=Ledger();download=Download(VIDEO)
            media=MediaService(MediaStore(h.client,SETTINGS.hash_salt,h.prefix+'media'),download,storage,ledger,store.authorize_media)
            active=InventoryService(store,media,Assessor(assessment()))
            h.app.state.telegram_handler.inventory=active
            h.update_id+=1;update_id=h.update_id
            payload=dict(update_id=update_id,message=dict(message_id=update_id,date=int(datetime.now(UTC).timestamp()),
                chat=dict(id=9,type='private'),video=video().model_dump()))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app),base_url='http://test') as api:
                result=await api.post('/telegram/webhook',headers=HEADERS,json=payload)
                assert result.status_code==200
                result=await api.post('/telegram/webhook',headers=HEADERS,json=payload)
                assert result.status_code==200
            assert 'File integrity verified' in h.calls[-1]['text'] and download.calls==1
            job=next(store.collection('inventory_jobs').stream()).to_dict()
            assert job['processing_elapsed_ms']>=0 and job['model_elapsed_ms']>=0
            assert storage.read_original(job['media_id'])==VIDEO and ledger.ids
            await h.send('/refresh')
            assert '30–45 second' in h.calls[-1]['text']
            state=await h.state();assert state['stage']=='done'
            h.store.collection('shops').document(state['shop_id']).update({'active_danger':True})
            await h.send('/refresh')
            assert 'DANGER' in h.calls[-1]['text'] and 'record video' in h.calls[-1]['text']
            assert '30–45 second' not in h.calls[-1]['text']
        finally:
            for blob in storage_client.list_blobs(bucket):blob.delete(timeout=8,retry=None)
            storage_client.bucket(bucket).delete(timeout=8,retry=None);storage.close();await h.close()
    asyncio.run(run())

@pytest.mark.parametrize('mode',['invalid_once','invalid_twice','timeout'])
@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_model_failure_bounded_retry_keeps_honest_inventory_status(mode):
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='model-failure-'+uuid4().hex+'-'
    store=InventoryStore(client,'synthetic',prefix)
    store.collection('shops').document('shop').set(dict(lat=3.,lng=101.,is_demo=True,
        recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,*_=media_service();media.downloader.data=VIDEO;media.authorize=store.authorize_media
    class Faults(Assessor):
        async def assess(self,*args):
            self.calls+=1
            if mode=='timeout':await asyncio.sleep(1)
            if mode=='invalid_twice' or self.calls==1:raise ValueError('Synthetic invalid structured output')
            return assessment()
    model=Faults(None);active=InventoryService(store,media,model,total_budget_seconds=.1 if mode=='timeout' else 35)
    try:
        result=asyncio.run(active.handle_video(123,1,1,int(datetime.now(UTC).timestamp()),video()))
        assert model.calls==(1 if mode=='timeout' else 2)
        if mode=='invalid_once':assert result.kind=='inventory'
        else:
            assert result.kind=='unavailable' and not list(store.collection('inventories').stream())
            assert not store.collection('shops').document('shop').get().to_dict().get('baseline_inventory_id')
    finally:
        for name in ('shops','inventories','inventory_jobs','inventory_pending'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()
