import asyncio
import httpx
from api.config import Settings
from api.main import create_app

def test_protected_resume_entrypoint_rejects_missing_authorization():
    async def run():
        app=create_app(Settings())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            response=await api.post('/jobs/resume-pending',json={'limit':1})
            assert response.status_code==403
    asyncio.run(run())

import os
from uuid import uuid4
from datetime import UTC,datetime
from hashlib import sha256
import pytest
from api.tools.firestore import create_firestore_client
from api.recovery_jobs import RecoveryJobsService

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_protected_outage_recovery_one_fact_receipt_no_extra_send(monkeypatch):
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.dispatch_models import Shop,EventRequest,ActionSnapshot,LiftItem
    from api.active_risk import ActiveRiskStore
    from api.vehicle_confirmations import VehicleActionStore,VehicleConfirmationService
    from api.stock_confirmations import StockActionStore,StockConfirmationService
    from api.telegram_webhook import TelegramHandler
    from api.telegram_inbox import FirestoreInbox
    from api.media import MediaService
    from api.media_store import MediaStore
    from api.tests.test_media import Download,Storage,request as media_request,image_bytes
    monkeypatch.delenv('K_SERVICE',raising=False)
    client=create_firestore_client(Settings(gcp_project='highground-resumer-tests'));p='jobs-'+uuid4().hex+'-'
    store=FirestoreDispatchStore(client,events=p+'events',alerts=p+'alerts',shops=p+'shops')
    risk=ActiveRiskStore(client,risks=p+'risk',shops=p+'shops',deliveries=p+'deliveries',current_actions=p+'current')
    vehicles=VehicleActionStore(client,actions=p+'vehicle',current=p+'current',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops')
    stocks=StockActionStore(client,actions=p+'stock',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops',risks=p+'risk')
    class Sink:
        def __init__(self):self.fail=True;self.confirmations={};self.receipts={}
        def publish_event(self,*args):
            if self.fail:raise OSError('PRIVATE-OUTAGE')
        def insert_event(self,*args):self.publish_event()
        def insert_alert(self,*args):self.publish_event()
        def insert_confirmation(self,record):self.publish_event();self.confirmations[record['confirmation_id']]=record
        def append(self,record):self.publish_event();self.receipts[record.media_id]=record
    class Bot:
        def __init__(self):self.messages=[];self.answers=[]
        def send_message(self,*args,**kwargs):self.messages.append((args,kwargs));return 42
        def answer_callback_query(self,*args):self.answers.append(args)
    sink=Sink();bot=Bot();download=Download(image_bytes());media_store=MediaStore(client,'synthetic',p+'media')
    media=MediaService(media_store,download,Storage(),sink,lambda req:True)
    dispatch=DispatchService(store,bot,sink,hash_salt='synthetic',active_risk=risk,vehicle_actions=vehicles,stock_actions=stocks)
    confirmations=VehicleConfirmationService(vehicles,sink,hash_salt='synthetic');stock_confirmations=StockConfirmationService(stocks,sink,hash_salt='synthetic')
    jobs=RecoveryJobsService(dispatch=dispatch,confirmations=confirmations,media=media)
    inbox=FirestoreInbox(client,p+'inbox');handler=TelegramHandler(inbox,bot,confirmations=confirmations,stock_confirmations=stock_confirmations)
    settings=Settings(telegram_webhook_secret='synthetic',local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic')
    shop=Shop(shop_id='s',shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,has_vehicle=True,vehicle_type='car',baseline_inventory_id='baseline',recipients=[dict(telegram_chat_id=123,language='en',role='owner')],lift_first=[LiftItem(item_name='Synthetic stock',qty=1.,value_rm=30.,lift_effort=1)])
    client.collection(p+'shops').document('s').set(shop.model_dump())
    app=create_app(settings,handler,recovery_jobs_service=jobs)
    async def run():
        event=await dispatch.process(EventRequest(request_id='pending',level='warning',lat=3.,lng=101.,warning_structure='warning_intro_fallback'))
        assert event['status']=='pending' and len(bot.messages)==1
        alert=store.get_alert(store.get_event(event['event_id'])['alert_ids'][0]);snapshot=ActionSnapshot.model_validate(alert['snapshot'])
        receipt=await media.ingest_media(media_request(shop_id='s'),defer_ledger=True)
        # An upload without stored bytes must never become eligible for background ingestion.
        missing=media_store.ensure(media_request(shop_id='s',message_id=2,file_unique_id='not-stored'))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            for i,(kind,identity) in enumerate((('vehicle',snapshot.vehicle_action_id),('stock',snapshot.stock_action_id))):
                payload=dict(update_id=100+i,callback_query=dict(id=f'callback-{kind}',**{'from':dict(id=123)},message=dict(message_id=42,chat=dict(id=123,type='private')),data=f'{kind}:{identity}'))
                assert (await api.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'},json=payload)).status_code==200
                assert (await api.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'},json=payload)).status_code==200
            assert len(bot.answers)==2 and len(list(client.collection(p+'confirmations').stream()))==2
            auth={'Authorization':'Bearer synthetic'}
            pending=await api.post('/jobs/resume-pending',headers=auth,json={'limit':20})
            assert pending.status_code==200 and pending.json()['dispatch']['pending']==1 and pending.json()['confirmations']['pending']==2 and pending.json()['media_ledger']['pending']==1
            sink.fail=False
            recovered=await api.post('/jobs/resume-pending',headers=auth,json={'limit':20})
            assert recovered.status_code==200
            assert recovered.json()['dispatch']['completed']==1 and recovered.json()['confirmations']['completed']==2 and recovered.json()['media_ledger']['completed']==1
            again=await api.post('/jobs/resume-pending',headers=auth,json={'limit':20})
            assert all(again.json()[stage]['scanned']==0 for stage in ('dispatch','confirmations','media_ledger'))
            assert 'PRIVATE' not in recovered.text and event['event_id'] not in recovered.text and receipt.record.media_id not in recovered.text
        assert len(bot.messages)==1 and len(sink.confirmations)==2 and len(sink.receipts)==1 and download.calls==1
        assert media_store.get(receipt.record.media_id).status=='complete' and media_store.get(missing.media_id).storage_status=='pending'
        assert next(row for row in sink.confirmations.values() if row['kind']=='stock')['protected_value_rm']==30.
        await jobs.close()
    try:asyncio.run(run())
    finally:
        for name in ('events','events-plans','alerts','alerts-delivery','shops','risk','deliveries','current','vehicle','stock','confirmations','inbox','media'):
            for doc in client.collection(p+name).stream():doc.reference.delete()
        client.close()

def test_protected_auth_bounds_and_local_cloud_refusal(monkeypatch):
    from dataclasses import replace
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787');monkeypatch.delenv('K_SERVICE',raising=False)
    config=Settings(local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic')
    calls=[]
    class Jobs:
        async def resume(self,limit):
            from api.recovery_jobs import ResumeResult,StageOutcome
            calls.append(limit);return ResumeResult(dispatch=StageOutcome(),confirmations=StageOutcome(),media_ledger=StageOutcome())
    async def run(settings=config):
        app=create_app(settings,recovery_jobs_service=Jobs())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost') as api:
            for headers in ({},{'Authorization':'Bearer wrong'}):assert (await api.post('/jobs/resume-pending',headers=headers,json={})).status_code==403
            auth={'Authorization':'Bearer synthetic'}
            for body in ({'limit':0},{'limit':21},{'limit':True},{'limit':'1'},{'limit':1,'private':'x'}):assert (await api.post('/jobs/resume-pending',headers=auth,json=body)).status_code==400
            assert (await api.post('/jobs/resume-pending',headers=auth,content='x'*1001)).status_code==413
            response=await api.post('/jobs/resume-pending',headers=auth,json={'limit':1})
            return response
    assert asyncio.run(run()).status_code==200 and calls==[1]
    async def rejected(settings):
        app=create_app(settings,recovery_jobs_service=Jobs())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://localhost') as api:
            assert (await api.post('/jobs/resume-pending',headers={'Authorization':'Bearer synthetic','Host':'localhost'},json={})).status_code==403
    for settings in (replace(config,local_development=False),replace(config,demo_mode=False)):asyncio.run(rejected(settings))
    monkeypatch.setenv('K_SERVICE','hosted');asyncio.run(rejected(config));monkeypatch.delenv('K_SERVICE')
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','cloud.example:443');asyncio.run(rejected(config))
    assert calls==[1]

def test_stage_deadline_retains_work_blocks_duplicate_and_other_stages_continue():
    from types import SimpleNamespace
    entered=[];closed=[]
    class Store:
        def pending_event_ids(self,limit):assert limit==1;return ['private']
    class Empty:
        def pending_ids(self,limit):return []
    class Failed:
        def pending_ledger_ids(self,limit):raise OSError('PRIVATE')
    class Client:
        def close(self):closed.append('client')
    async def run():
        release=asyncio.Event()
        class Dispatch:
            store=Store()
            async def resume(self,identity):entered.append(identity);await release.wait();return {'status':'complete'}
            async def close(self):closed.append('dispatch')
        jobs=RecoveryJobsService(dispatch=Dispatch(),confirmations=SimpleNamespace(store=Empty()),media=SimpleNamespace(store=Failed()),settings=Settings(),client=Client(),deadline_seconds=.02)
        first=await jobs.resume(1)
        assert first.dispatch.status=='deadline_limited' and first.dispatch.inflight_unknown==1
        assert first.confirmations.status=='available' and first.media_ledger.status=='unavailable'
        second=await jobs.resume(1)
        assert second.dispatch.inflight_unknown==1 and entered==['private']
        assert not closed
        release.set();await jobs.close()
        assert closed==['dispatch','client']
    asyncio.run(run())

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_protected_resumer_suppresses_obsolete_generation_without_send(monkeypatch):
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.dispatch_models import EventRequest
    from api.active_risk import ActiveRiskStore
    from api.demo_scenario import DemoScenarioStore
    from types import SimpleNamespace
    monkeypatch.delenv('K_SERVICE',raising=False)
    client=create_firestore_client(Settings(gcp_project='highground-resumer-tests'));p='obsolete-jobs-'+uuid4().hex+'-'
    store=FirestoreDispatchStore(client,events=p+'events',shops=p+'shops',alerts=p+'alerts')
    risk=ActiveRiskStore(client,risks=p+'risk',shops=p+'shops',current_actions=p+'current',deliveries=p+'deliveries')
    client.collection(p+'demo_scenario').document('current').set({'generation':1,'state':'ready'})
    client.collection(p+'shops').document('s').set({'is_demo':True,'active_danger':False})
    event=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),datetime.now(UTC))
    DemoScenarioStore(client,risk,prefix=p).reset('boundary')
    class Poison:
        def __getattr__(self,name):raise AssertionError('Obsolete work touched transport/model/sinks')
    class Empty:
        def pending_ids(self,limit):return []
        def pending_ledger_ids(self,limit):return []
    jobs=RecoveryJobsService(dispatch=DispatchService(store,Poison(),Poison(),hash_salt='synthetic',active_risk=risk),confirmations=SimpleNamespace(store=Empty()),media=SimpleNamespace(store=Empty()))
    async def run():
        config=Settings(local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic')
        app=create_app(config,recovery_jobs_service=jobs)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            response=await api.post('/jobs/resume-pending',headers={'Authorization':'Bearer synthetic'},json={'limit':1})
            assert response.status_code==200 and response.json()['dispatch']['completed']==1
        assert store.get_event(event['event_id'])['status']=='superseded' and not risk.get('s').active_danger
        await jobs.close()
    try:asyncio.run(run())
    finally:
        for name in ('shops','events','demo_scenario','demo_resets','risk','current','deliveries'):
            for doc in client.collection(p+name).stream():doc.reference.delete()
        client.close()

def test_local_recovery_factory_refuses_missing_cloud_sinks_before_client(monkeypatch):
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787');monkeypatch.setenv('PUBSUB_EMULATOR_HOST','127.0.0.1:8797');monkeypatch.delenv('BIGQUERY_EMULATOR_HOST',raising=False);monkeypatch.delenv('K_SERVICE',raising=False)
    monkeypatch.setattr('api.tools.firestore.create_firestore_client',lambda *args:pytest.fail('Client created before loopback sink validation'))
    async def run():
        app=create_app(Settings(local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic'))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            assert (await api.post('/jobs/resume-pending',headers={'Authorization':'Bearer synthetic'},json={})).status_code==503
    asyncio.run(run())

def test_owned_client_closure_survives_another_close_failure():
    closed=[]
    class Dispatch:
        async def close(self):closed.append('dispatch');raise OSError('private')
    class Client:
        def close(self):closed.append('client')
    jobs=RecoveryJobsService(dispatch=Dispatch(),settings=Settings(),client=Client())
    with pytest.raises(OSError):asyncio.run(jobs.close())
    assert closed==['dispatch','client']
