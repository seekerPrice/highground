import asyncio
from datetime import UTC,datetime
from hashlib import sha256
import os
from uuid import uuid4
import pytest
from pydantic import ValidationError
from api.report_models import LossAssessment,freeze_baseline
from api.report_store import ReportStore
from api.report_api import ReportReader,create_report_router
from api.recovery import RecoveryService
from api.tests.test_inventory import item,assessment,video,VIDEO
from api.tests.test_media import service as media_service
from api.tools.firestore import create_firestore_client
from api.config import Settings
from api.active_risk import ActiveRiskStore
from fastapi import FastAPI
import httpx

BASE=dict(inventory_id='baseline',media_id='a'*64,items=[item().model_dump(),item(name='Fan').model_dump()],total_est_value_rm=40.,confidence=.8,confidence_note='Synthetic estimates')
def loss(**updates):
    data=dict(items=[dict(item_id='baseline:0',condition='damaged',estimated_loss_rm=10.,evidence_timestamp_s=2.,uncertainty='Synthetic')],total_loss_rm=10.,summary_text='Untrusted text',confidence=.7,confidence_note='Synthetic')
    data.update(updates);return LossAssessment.model_validate(data)

@pytest.mark.parametrize('change',[{'item_id':'invented'},{'estimated_loss_rm':21.},{'estimated_loss_rm':float('nan')},{'evidence_timestamp_s':31.},{'condition':'missing'},{'condition':'ok'},{'estimated_loss_rm':10.001}])
def test_strict_loss_domain(change):
    row=loss().items[0].model_dump();row.update(change)
    with pytest.raises(ValueError):loss(items=[row]).validate_baseline(BASE,30)

def test_aggregate_duplicate_unknown_and_unavailable():
    with pytest.raises(ValueError):loss(total_loss_rm=9.).validate_baseline(BASE,30)
    with pytest.raises(ValueError):loss(items=[loss().items[0].model_dump()]*2,total_loss_rm=20.).validate_baseline(BASE,30)
    assert loss(items=[],total_loss_rm=None).validate_baseline(BASE,30)
    with pytest.raises(ValueError):loss(items=[],total_loss_rm=0.).validate_baseline(BASE,30)
    with pytest.raises(ValueError):freeze_baseline(dict(BASE,total_est_value_rm=41.))

class Assessor:
    def __init__(self,hook=None,result=None):self.calls=0;self.hook=hook;self.result=result or loss()
    async def assess(self,*args):
        self.calls+=1
        if self.hook:self.hook()
        return self.result
    async def close(self):pass

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
@pytest.mark.parametrize('danger_stage',[None,'before','during','declaration'])
def test_owner_recovery_freeze_replay_restart_and_danger(danger_stage):
    client=create_firestore_client(Settings(gcp_project='highground-recovery-tests'));prefix='recovery-'+uuid4().hex+'-'
    risks=ActiveRiskStore(client,risks=prefix+'active_risks',shops=prefix+'shops',current_actions=prefix+'current_vehicle_actions',max_age=Settings(official_max_age_minutes=7).official_max_age)
    store=ReportStore(client,'synthetic',prefix,risks=risks)
    shop=store.collection('shops').document('shop')
    shop.set(dict(shop_name='Synthetic',floor='ground',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='baseline',recipients=[dict(telegram_chat_id=123,language='en',role='owner'),dict(telegram_chat_id=456,language='en',role='worker')]))
    store.collection('inventories').document('baseline').set(dict(BASE,shop_id='shop'))
    media,media_store,download,storage,ledger=media_service();download.data=VIDEO;media.authorize=store.authorize_media
    model=Assessor(hook=lambda:shop.update({'active_danger':True}) if danger_stage=='during' else None)
    active=RecoveryService(store,media,model,web_base_url='http://localhost:3000')
    async def run():
        assert store.risk_store.max_age.total_seconds()==420
        assert (await active.start(456,'worker')).kind=='unavailable'
        assert (await active.start(999,'outsider')).kind=='unavailable'
        start=await active.start(123,'start');job=store.current(123);identity=job['report_id']
        assert store.start(store.owner_shop(123),123,'start')['report_id']==identity
        if danger_stage=='declaration':shop.update({'active_danger':True})
        else:await active.declare(123,identity)
        shop.update({'baseline_inventory_id':'refreshed'})
        if danger_stage=='before':shop.update({'active_danger':True})
        now=datetime.now(UTC)
        reply=await active.handle_video(123,9,9,int(now.timestamp()),video())
        assert download.calls==1 and ledger.ids and media_store.record.sha256==sha256(VIDEO).hexdigest()
        assert shop.get().to_dict()['baseline_inventory_id']=='refreshed'
        if danger_stage:
            assert reply.kind=='danger' and '#key=' not in reply.text
            assert model.calls==(1 if danger_stage=='during' else 0)
            assert store.current(123)['status']!='complete' if danger_stage in ('before','declaration') else True
        else:
            assert '#key=' in reply.text and model.calls==1
            restarted=RecoveryService(ReportStore(client,'synthetic',prefix,risks=risks),media,model,web_base_url='http://localhost:3000')
            # Completed report closes generic media context; replay addresses the current logical upload explicitly.
            assert await restarted.active_context(123) is None
            replay=await restarted.handle_video(123,10,9,int(now.timestamp()),video())
            assert '#key=' in replay.text and model.calls==1 and download.calls==1
            assert await restarted.active_context(123,9,video().file_unique_id)
            job=store.current(123);assert job['baseline']['inventory_id']=='baseline'
            assert store.authorized(identity,store.token(identity))
            assert not store.authorized(identity,'wrong')
            assert (await active.request_photo(123)).kind!='danger'
            assert await active.active_context(123)
            await active.exit(123);assert await active.active_context(123) is None
    try:asyncio.run(run())
    finally:
        for name in ('shops','inventories','recovery_jobs','recovery_current','recovery_private','recovery_intents','recovery_uploads','active_risks','current_vehicle_actions'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

class ReaderStore:
    def __init__(self):self.jobs={}
    def authorized(self,identity,token):return self.jobs.get(identity) if token==identity+'-token' else None
class Records:
    def __init__(self,record):self.record=record
    def get(self,identity):return self.record

def test_private_api_report_binding_unknown_rows_and_integrity():
    from api.media_models import MediaRecord
    now=datetime.now(UTC);media_id='a'*64;data=b'synthetic bytes'
    record=MediaRecord(media_id=media_id,shop_id='shop',kind='baseline_video',sender_hash='PRIVATE-SENDER',sha256=sha256(data).hexdigest(),bytes=len(data),mime_type='video/mp4',uploaded_at=now,telegram_date=now,received_at=now,lat=3.,lng=101.,location_attribution='confirmed_shop',is_demo=True,storage_status='done',ledger_status='done',gcs_uri='PRIVATE-STORAGE')
    class Storage:
        calls=0
        def read_original(self,identity):self.calls+=1;return data
    store=ReaderStore();storage=Storage();identity='b'*32;other='c'*32
    store.jobs[identity]=dict(report_id=identity,shop_id='shop',shop_name='Synthetic',is_demo=True,created_at=now,baseline=BASE,assessment=loss(summary_text='Insurer accepts. Reopen safely.',confidence_note='Authentic recording').model_dump(),upload={'duration':30},recovery_attribution='Owner declared recovery',evidence_media_ids=[media_id])
    store.jobs[other]=dict(store.jobs[identity],report_id=other,evidence_media_ids=[])
    reader=ReportReader(store,Records(record),storage);app=FastAPI();app.include_router(create_report_router(Settings(),reader))
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            path=f'/api/report/{identity}'
            assert (await api.get(path)).status_code==404
            assert (await api.get(path,headers={'Authorization':'Bearer '+other+'-token'})).status_code==404
            headers={'Authorization':'Bearer '+identity+'-token'}
            result=await api.get(path,headers=headers);assert result.status_code==200
            dto=result.json();assert dto['coverage']=='partial' and len(dto['items'])==2 and dto['items'][1]['estimated_loss_rm'] is None
            assert 'Insurer' not in result.text and 'PRIVATE' not in result.text and result.headers['cache-control']=='no-store'
            wrong=await api.get(f'/api/report/{other}/media/{media_id}',headers={'Authorization':'Bearer '+other+'-token'})
            assert wrong.status_code==404 and storage.calls==0
            assert (await api.get(path+'/media/'+media_id,headers=headers)).content==data
            verified=await api.post(path+'/media/'+media_id+'/verify',headers=headers);assert verified.json()['status']=='verified'
            record_bytes=record.model_copy(update={'bytes':len(data)+1});reader.media_store=Records(record_bytes)
            assert (await api.post(path+'/media/'+media_id+'/verify',headers=headers)).json()['status']=='mismatch'
            assert (await api.get(path+'/media/'+media_id,headers=headers)).status_code==409
    asyncio.run(run())


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
@pytest.mark.parametrize('next_action',['exit','new_workflow','photo_complete'])
def test_recovery_media_replay_routes_original_workflow_after_pointer_changes(next_action):
    from api.telegram_webhook import TelegramHandler,Update
    from api.telegram_inbox import FirestoreInbox
    from api.inventory_models import InventoryReply
    from api.photo_models import PhotoMedia
    from api.tests.test_media import image_bytes
    PHOTO=image_bytes()
    client=create_firestore_client(Settings(gcp_project='highground-replay-tests'));prefix='replay-'+uuid4().hex+'-'
    store=ReportStore(client,'synthetic',prefix)
    store.collection('shops').document('shop').set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='baseline',recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    store.collection('inventories').document('baseline').set(dict(BASE,shop_id='shop'))
    media,media_store,download,storage,ledger=media_service();download.data=VIDEO;media.authorize=store.authorize_media
    model=Assessor();active=RecoveryService(store,media,model,web_base_url='http://localhost:3000')
    calls=[]
    class OtherMedia:
        async def handle_video(self,*args,**kwargs):calls.append('baseline');return InventoryReply(text='WRONG baseline',kind='inventory')
        async def handle_photo(self,*args,**kwargs):calls.append('neighbour');return InventoryReply(text='WRONG neighbour',kind='unavailable')
        async def recheck_reply(self,sender,reply):return reply
    class API:
        def send_message(self,*args,**kwargs):return 999
    inbox=FirestoreInbox(client,prefix+'inbox');handler=TelegramHandler(inbox,API(),inventory=OtherMedia(),photos=OtherMedia(),recovery=active)
    async def run():
        now=datetime.now(UTC);date=int(now.timestamp())
        await active.start(123,'start');original=store.current(123)['report_id'];await active.declare(123,original)
        await active.handle_video(123,1,10,date,video())
        if next_action=='photo_complete':
            await active.request_photo(123);download.data=PHOTO
            photo=PhotoMedia(file_id='photo',file_unique_id='unique-photo',file_size=len(PHOTO))
            await active.handle_photo(123,2,11,date,photo)
            payload=dict(update_id=99,message=dict(message_id=11,date=date,chat=dict(id=123,type='private'),photo=[dict(**photo.model_dump(),width=100,height=100)]))
        else:
            await active.exit(123)
            if next_action=='new_workflow':await active.start(123,'new-workflow')
            payload=dict(update_id=99,message=dict(message_id=10,date=date,chat=dict(id=123,type='private'),video=video().model_dump()))
        await handler.handle(Update.model_validate(payload))
        assert calls==[], 'Recovery replay must never overwrite baseline or fan out neighbour alerts'
        assert model.calls==1
        if next_action=='new_workflow':assert store.current(123)['report_id']!=original and not store.current(123).get('upload')
    try:asyncio.run(run())
    finally:
        for name in ('shops','inventories','recovery_jobs','recovery_current','recovery_private','recovery_intents','recovery_uploads','inbox'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_failed_media_allows_new_workflow_without_overwriting_original_job():
    client=create_firestore_client(Settings(gcp_project='highground-recovery-tests'));prefix='failed-upload-'+uuid4().hex+'-';store=ReportStore(client,'synthetic',prefix)
    store.collection('shops').document('shop').set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='baseline',recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    store.collection('inventories').document('baseline').set(dict(BASE,shop_id='shop'))
    media,*_=media_service();media.authorize=store.authorize_media;model=Assessor();active=RecoveryService(store,media,model,web_base_url='http://localhost:3000')
    async def run():
        await active.start(123,'first');original=store.current(123)['report_id'];await active.declare(123,original)
        oversized=video().model_copy(update={'file_size':20_000_001})
        result=await active.handle_video(123,1,1,int(datetime.now(UTC).timestamp()),oversized)
        assert result.kind=='unavailable' and model.calls==0
        assert store.current(123)['status']=='assessment_unavailable'
        await active.start(123,'replacement');replacement=store.current(123)
        assert replacement['report_id']!=original and not replacement.get('upload')
        original_job=store.collection('recovery_jobs').document(original).get().to_dict()
        assert store.upload_reference(123,1,video().file_unique_id).get().to_dict()['upload']['message_id']==1 and original_job['status']=='assessment_unavailable'
        assert store.collection('shops').document('shop').get().to_dict()['baseline_inventory_id']=='baseline'
    try:asyncio.run(run())
    finally:
        for name in ('shops','inventories','recovery_jobs','recovery_current','recovery_private','recovery_intents','recovery_uploads'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()
