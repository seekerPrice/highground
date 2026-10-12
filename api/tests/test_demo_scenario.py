"""Actual transaction seams for the server-owned synthetic generation boundary."""
from datetime import UTC, datetime
from uuid import uuid4
import os
import pytest
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.dispatch_models import EventRequest
from api.dispatch_store import FirestoreDispatchStore
from api.active_risk import ActiveRiskStore

pytestmark=pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore required')

@pytest.fixture
def scope():
    client=create_firestore_client(Settings(gcp_project='highground-scenario-tests'))
    prefix='scenario-'+uuid4().hex+'-'
    yield client,prefix
    for name in ('shops','events','events-plans','alerts','alerts-delivery','demo_scenario','demo_resets','active_risks','current_vehicle_actions','shop_delivery_claims','media','inventories','vehicle_actions','stock_actions','confirmations','safe_points','inbox'):
        for doc in client.collection(prefix+name).stream():doc.reference.delete()
    client.close()

def services(scope):
    client,p=scope
    store=FirestoreDispatchStore(client,events=p+'events',alerts=p+'alerts',shops=p+'shops')
    risk=ActiveRiskStore(client,risks=p+'active_risks',shops=p+'shops',deliveries=p+'shop_delivery_claims',current_actions=p+'current_vehicle_actions')
    return store,risk

def scenario(scope,**values):
    client,p=scope
    client.collection(p+'demo_scenario').document('current').set(dict(generation=1,state='ready',**values))

def test_creation_is_server_assigned_and_blocked_during_reset(scope):
    store,_=services(scope);scenario(scope)
    req=EventRequest(request_id='first',level='warning',lat=3.,lng=101.)
    event=store.ensure_event(req,datetime.now(UTC))
    assert event['scenario_generation']==1
    client,p=scope;client.collection(p+'demo_scenario').document('current').update({'state':'resetting'})
    with pytest.raises(ValueError,match='reset'):store.ensure_event(req.model_copy(update={'request_id':'new'}),datetime.now(UTC))
    assert store.ensure_event(req,datetime.now(UTC))['scenario_generation']==1

def test_delayed_old_event_cannot_apply_risk(scope):
    store,risk=services(scope);scenario(scope)
    client,p=scope;client.collection(p+'shops').document('s').set({'is_demo':True,'active_danger':False})
    event=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),datetime.now(UTC))
    client.collection(p+'demo_scenario').document('current').update({'generation':2})
    assert risk.apply_event_decision(event,'s').reason=='obsolete_scenario'
    assert not risk.get('s').active_danger

def test_reset_final_send_fence(scope):
    store,_=services(scope);scenario(scope)
    now=datetime.now(UTC);event=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),now)
    owner=store.claim(event['event_id'],now)
    store.prepare_alert(dict(alert_id='a',event_id=event['event_id'],shop_id='s',telegram_chat_id=123,status='pending'))
    client,p=scope;client.collection(p+'demo_scenario').document('current').update({'state':'resetting'})
    assert not store.begin_send('a',event['event_id'],owner)
    assert store.get_alert('a')['status']=='superseded'

def test_reset_drains_lease_then_preserves_immutable_history_and_duplicate(scope):
    from api.demo_scenario import DemoScenarioStore
    store,risk=services(scope);scenario(scope)
    client,p=scope
    client.collection(p+'shops').document('s').set({'is_demo':True,'active_danger':False})
    client.collection(p+'shops').document('real').set({'is_demo':False,'active_danger':True})
    event=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),datetime.now(UTC))
    episode=risk.apply_event(event,'s');event['episode_id']=episode
    disposition,owner=risk.claim_delivery('s',event);assert disposition=='claimed'
    resets=DemoScenarioStore(client,risk,prefix=p)
    assert resets.reset('reset-one')['status']=='resetting'
    assert risk.claim_delivery('s',event)[0]=='superseded'
    risk.release_delivery('s',owner)
    first=resets.reset('reset-one');assert first['generation']==2 and first['status']=='reset'
    fresh=store.ensure_event(EventRequest(request_id='fresh',level='warning',lat=3.,lng=101.),datetime.now(UTC))
    assert risk.apply_event_decision(fresh,'s').reason=='accepted'
    assert resets.reset('reset-one')==first
    assert risk.get('s').episode_id is not None
    assert risk.get('real').active_danger
    assert client.collection(p+'events').document(event['event_id']).get().exists

def test_duplicate_reset_paused_before_mutation_cannot_clear_new_risk(scope,monkeypatch):
    from api.demo_scenario import DemoScenarioStore
    store,risk=services(scope);scenario(scope)
    client,p=scope;client.collection(p+'shops').document('s').set({'is_demo':True,'active_danger':False})
    old=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),datetime.now(UTC));risk.apply_event(old,'s')
    resets=DemoScenarioStore(client,risk,prefix=p);original=risk.reset_demo;entered=False
    def interleave(shop_id,**kwargs):
        nonlocal entered
        if not entered:
            entered=True
            resets.reset('same-request')
            fresh=store.ensure_event(EventRequest(request_id='fresh',level='warning',lat=3.,lng=101.),datetime.now(UTC))
            assert risk.apply_event_decision(fresh,'s').reason=='accepted'
        return original(shop_id,**kwargs)
    monkeypatch.setattr(risk,'reset_demo',interleave)
    assert resets.reset('same-request')['generation']==2
    assert risk.get('s').episode_id is not None
    record=client.collection(p+'active_risks').document('s').get().to_dict()
    assert next(iter(record['sources'].values()))['level']=='warning'

def test_partial_reset_restart_and_different_request_blocked(scope,monkeypatch):
    from api.demo_scenario import DemoScenarioStore,ScenarioResetBusy
    store,risk=services(scope);scenario(scope)
    client,p=scope
    for identity in ('a','b'):client.collection(p+'shops').document(identity).set({'is_demo':True,'active_danger':False})
    original=risk.reset_demo
    def fail(identity,**kwargs):
        if identity=='b':raise RuntimeError('interrupted reset')
        return original(identity,**kwargs)
    monkeypatch.setattr(risk,'reset_demo',fail)
    with pytest.raises(RuntimeError):DemoScenarioStore(client,risk,prefix=p).reset('partial')
    state=client.collection(p+'demo_scenario').document('current').get().to_dict()
    assert state['state']=='resetting' and state['done']==['a']
    with pytest.raises(ScenarioResetBusy):DemoScenarioStore(client,risk,prefix=p).reset('different')
    monkeypatch.setattr(risk,'reset_demo',original)
    assert DemoScenarioStore(client,risk,prefix=p).reset('partial')['generation']==2

def test_virtual_seed_real_receipt_repeatability_sentinel_and_binding(scope):
    from pathlib import Path
    from hashlib import sha256
    from api.demo_seed import FixtureSeeder,SHOP_IDS
    from api.media_models import MediaRecord
    client,p=scope
    sentinel={'is_demo':False,'shop_name':'real sentinel','recipients':[dict(telegram_chat_id=123,language='en',role='owner')]}
    client.collection(p+'shops').document('real').set(sentinel)
    class Storage:
        def __init__(self):self.data={}
        def uri(self,identity):return 'gs://synthetic-test/originals/'+identity
        def create_original(self,identity,data,mime,digest):
            assert sha256(data).hexdigest()==digest
            if identity in self.data:assert self.data[identity]==data
            self.data[identity]=data
    class Ledger:
        def __init__(self):self.records=[]
        def append(self,record):self.records.append(record)
    storage=Storage();ledger=Ledger();seed=FixtureSeeder(client,storage,ledger,prefix=p)
    data=(Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes()
    assert seed.seed(data)['vehicles']==3
    originals={doc.id:doc.to_dict() for doc in client.collection(p+'media').stream()}
    assert len(originals)==6 and len(ledger.records)==6
    seed.seed(data);assert len(ledger.records)==6
    assert {doc.id:doc.to_dict() for doc in client.collection(p+'media').stream()}==originals
    shops=[client.collection(p+'shops').document(identity).get().to_dict() for identity in SHOP_IDS]
    assert sum(s['has_vehicle'] for s in shops)==3 and all(not s['recipients'] and s['virtual_recipient'] for s in shops)
    for identity,row in originals.items():
        receipt=MediaRecord.model_validate(row)
        assert receipt.origin=='local_fixture' and receipt.telegram_date is None and receipt.sha256==sha256(data).hexdigest()
        assert storage.data[identity]==data
    assert client.collection(p+'shops').document('real').get().to_dict()==sentinel
    seed.bind_registered(1,'real');seed.seed(data)
    assert client.collection(p+'shops').document(SHOP_IDS[0]).get().to_dict()['recipients']==sentinel['recipients']
    assert client.collection(p+'shops').document(SHOP_IDS[0]).get().to_dict()['virtual_recipient'] is None

def test_actual_factory_local_virtual_refuses_cloud_and_non_demo(monkeypatch):
    from api.dispatch import create_dispatch_service
    config=Settings(gcp_project='synthetic-tests',hash_salt='synthetic',local_development=True,demo_mode=True,demo_virtual_delivery=True)
    for key,value in [('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787'),('PUBSUB_EMULATOR_HOST','127.0.0.1:8797'),('BIGQUERY_EMULATOR_HOST','http://127.0.0.1:9050')]:monkeypatch.setenv(key,value)
    with pytest.raises(ValueError):create_dispatch_service(Settings(demo_mode=False,demo_virtual_delivery=True))
    monkeypatch.setenv('BIGQUERY_EMULATOR_HOST','https://cloud.example:443')
    with pytest.raises(ValueError):create_dispatch_service(config)
    monkeypatch.setenv('BIGQUERY_EMULATOR_HOST','http://127.0.0.1:9050')
    monkeypatch.setattr('api.agents.warning_selector.WarningSelector',lambda settings:object())
    monkeypatch.setattr('api.tools.cloud_events.create_event_sinks',lambda settings:object())
    monkeypatch.setattr('api.tools.telegram.TelegramAPI',lambda *args:pytest.fail('Virtual factory constructed Telegram'))
    active=create_dispatch_service(config)
    assert active.telegram is None and active.virtual_delivery is not None
    active.store.client.close()


def test_virtual_actual_dispatch_never_calls_telegram_and_reset_during_prepare(scope):
    import asyncio
    from api.demo_scenario import DemoScenarioStore
    from api.dispatch import DispatchService
    from api.dispatch_models import ActionSnapshot
    from api.alert_composer import AlertComposer
    from api.demo_transport import LocalVirtualDelivery
    store,risk=services(scope);scenario(scope)
    client,p=scope
    client.collection(p+'shops').document('s').set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,recipients=[],virtual_recipient=dict(key='fixture-test',language='en')))
    class Poison:
        def send_message(self,*args,**kwargs):pytest.fail('Virtual dispatch called Telegram')
    class Sinks:
        def publish_event(self,event):pass
        def insert_event(self,event):pass
        def insert_alert(self,alert):assert alert['status']=='simulated' and alert['message_id'] is None
    active=DispatchService(store,Poison(),Sinks(),hash_salt='synthetic',active_risk=risk,virtual_delivery=LocalVirtualDelivery())
    result=asyncio.run(active.process(EventRequest(request_id='virtual',level='danger',lat=3.,lng=101.)))
    assert result['alerts']=={'simulated':1}
    alert=store.get_alert(store.get_event(result['event_id'])['alert_ids'][0])
    assert alert['delivery_provenance']=='local_virtual' and 'telegram_chat_id' not in alert and alert['reply_markup'] is None
    DemoScenarioStore(client,risk,prefix=p).reset('initial')
    class ResetComposer(AlertComposer):
        async def prepare(self,*args,**kwargs):DemoScenarioStore(client,risk,prefix=p).reset('during-model')
        async def action_snapshot(self,*args,**kwargs):pytest.fail('Old event prepared an action after reset')
    active.composer=ResetComposer()
    result=asyncio.run(active.process(EventRequest(request_id='model-race',level='warning',lat=3.,lng=101.)))
    assert result['status']=='superseded' and not risk.get('s').active_danger

@pytest.mark.parametrize('missing',['FIRESTORE_EMULATOR_HOST','STORAGE_EMULATOR_HOST','PUBSUB_EMULATOR_HOST','BIGQUERY_EMULATOR_HOST'])
def test_seed_entrypoint_requires_all_loopback_endpoints_before_client(missing,monkeypatch):
    import sys
    from api.demo_seed import main
    for name,value in [('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787'),('STORAGE_EMULATOR_HOST','http://127.0.0.1:4443'),('PUBSUB_EMULATOR_HOST','127.0.0.1:8797'),('BIGQUERY_EMULATOR_HOST','http://127.0.0.1:9050')]:monkeypatch.setenv(name,value)
    monkeypatch.delenv(missing)
    monkeypatch.setattr(sys,'argv',['seed'])
    monkeypatch.setattr('api.config.load_settings',lambda:Settings(local_development=True,demo_mode=True,demo_virtual_delivery=True))
    for factory in ('api.tools.firestore.create_firestore_client','api.tools.storage.create_storage_client','api.tools.cloud_events.create_analytics_client'):
        monkeypatch.setattr(factory,lambda *args,**kwargs:pytest.fail('Client constructed before endpoint validation'))
    with pytest.raises(ValueError):main()

def test_callbacks_blocked_during_partial_reset_then_fresh_snapshots_record(scope):
    from hashlib import sha256
    from api.vehicle_confirmations import VehicleActionStore,vehicle_action_id
    from api.stock_confirmations import StockActionStore
    from api.dispatch_models import Shop,ActionSnapshot,LiftItem
    from api.agents.sessions import session_user_id
    from api.demo_scenario import DemoScenarioStore
    from datetime import timedelta
    store,risk=services(scope);scenario(scope)
    client,p=scope;now=datetime.now(UTC);salt='synthetic';sender=123;sender_hash=session_user_id(sender,salt)
    shop=Shop(shop_id='s',shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=sender,language='en',role='owner')],has_vehicle=True,vehicle_type='car',baseline_inventory_id='baseline')
    client.collection(p+'shops').document('s').set(shop.model_dump())
    vehicle=VehicleActionStore(client,actions=p+'vehicle_actions',current=p+'current_vehicle_actions',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops')
    stock=StockActionStore(client,actions=p+'stock_actions',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops',risks=p+'active_risks')
    def prepared(identity):
        event=store.ensure_event(EventRequest(request_id=identity,level='warning',lat=3.,lng=101.),datetime.now(UTC));event['episode_id']=risk.apply_event(event,'s')
        snapshot=ActionSnapshot(inventory_id='baseline',items=(LiftItem(item_name='Synthetic',qty=1.,value_rm=30.,lift_effort=1),),estimated_value_rm=30.,vehicle_type='car',vehicle_target_at=now+timedelta(minutes=15),stock_target_at=now+timedelta(minutes=30),episode_id=event['episode_id'],vehicle_action_id=vehicle_action_id(event['event_id'],'s'),stock_action_id=sha256(f"{event['event_id']}:s:stock".encode()).hexdigest()[:32])
        va=vehicle.prepare(event,shop,snapshot,salt);sa=stock.prepare(event,shop,snapshot,salt)
        alert_id=sha256(f"{event['event_id']}:s:{sender_hash}".encode()).hexdigest()
        client.collection(p+'alerts').document(alert_id).set(dict(status='accepted',message_id=42,level='warning',snapshot=snapshot.model_dump(mode='json')))
        return va['action_id'],sa['action_id']
    old=prepared('old')
    client.collection(p+'demo_scenario').document('current').update({'state':'resetting','reset_request_id':'partial','next_generation':2,'done':[],'shop_ids':['s']})
    for actions,identity in zip((vehicle,stock),old):
        assert actions.record(identity,sender_chat_id=sender,message_chat_id=sender,message_id=42,sender_hash=sender_hash,now=now)[0]=='superseded'
    DemoScenarioStore(client,risk,prefix=p).reset('partial')
    fresh=prepared('fresh')
    for actions,identity in zip((vehicle,stock),fresh):
        assert actions.record(identity,sender_chat_id=sender,message_chat_id=sender,message_id=42,sender_hash=sender_hash,now=now)[0]=='recorded'
        fact=client.collection(p+'confirmations').document(identity).get().to_dict()
        assert fact['scenario_generation']==2 and fact['snapshot']['estimated_value_rm']==30.

def test_seed_creation_at_reset_scope_boundary_cannot_leave_old_risk(scope,monkeypatch):
    from pathlib import Path
    from api.demo_seed import FixtureSeeder,SHOP_IDS
    from api.demo_scenario import DemoScenarioStore,ScenarioResetBusy
    store,risk=services(scope);scenario(scope)
    client,p=scope
    class Storage:
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):pass
    class Ledger:
        def append(self,*args):pass
    seed=FixtureSeeder(client,Storage(),Ledger(),prefix=p)
    data=(Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes()
    resets=DemoScenarioStore(client,risk,prefix=p);original=resets._shop_ids;entered=False
    def interleave():
        nonlocal entered
        captured=original()
        if not entered:
            entered=True
            try:
                seed.seed(data)
                old=store.ensure_event(EventRequest(request_id='old',level='danger',lat=3.,lng=101.),datetime.now(UTC))
                assert risk.apply_event_decision(old,SHOP_IDS[0]).reason=='accepted'
            except ScenarioResetBusy:pass
        return captured
    monkeypatch.setattr(resets,'_shop_ids',interleave)
    assert resets.reset('scope-race')['generation']==2
    assert not risk.get(SHOP_IDS[0]).active_danger

@pytest.mark.parametrize('endpoint',['','https://cloud.invalid:443','http://127.0.0.1:9050/path'])
def test_seed_entrypoint_rejects_malformed_bq_before_client(endpoint,monkeypatch):
    import sys
    from api.demo_seed import main
    for name,value in [('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787'),('STORAGE_EMULATOR_HOST','http://127.0.0.1:4443'),('PUBSUB_EMULATOR_HOST','127.0.0.1:8797'),('BIGQUERY_EMULATOR_HOST',endpoint)]:monkeypatch.setenv(name,value)
    monkeypatch.setattr(sys,'argv',['seed'])
    monkeypatch.setattr('api.config.load_settings',lambda:Settings(local_development=True,demo_mode=True,demo_virtual_delivery=True))
    monkeypatch.setattr('api.tools.firestore.create_firestore_client',lambda *args,**kwargs:pytest.fail('Client constructed before validation'))
    with pytest.raises(ValueError):main()

def test_receipt_origin_validation_is_not_telegram_selectable():
    from pydantic import ValidationError
    from api.media_models import MediaRecord,MediaRequest
    from api.report_models import EvidenceReceipt
    now=datetime.now(UTC)
    fields=dict(media_id='a'*64,shop_id='s',kind='baseline_video',sender_hash='synthetic',sha256='b'*64,bytes=12,mime_type='video/mp4',uploaded_at=now,received_at=now,lat=3.,lng=101.,location_attribution='unconfirmed_shop',is_demo=True,origin='local_fixture',telegram_date=None)
    record=MediaRecord(**fields)
    receipt=EvidenceReceipt(**{name:getattr(record,name) for name in EvidenceReceipt.model_fields if name!='integrity_status'})
    assert receipt.origin=='local_fixture' and receipt.telegram_date is None
    for changes in ({'origin':'telegram'},{'telegram_date':now},{'is_demo':False}):
        with pytest.raises(ValidationError):MediaRecord(**(fields|changes))
        with pytest.raises(ValidationError):EvidenceReceipt(**({name:getattr(record,name) for name in EvidenceReceipt.model_fields if name!='integrity_status'}|changes))
    with pytest.raises(ValidationError):MediaRequest(shop_id='s',kind='baseline_video',sender_chat_id=123,message_id=1,file_id='f',file_unique_id='u',telegram_date=now,received_at=now,lat=3.,lng=101.,location_attribution='confirmed_shop',origin='local_fixture')

def test_inflight_real_transport_finishes_before_ready_and_late_old_rows_excluded(scope):
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from api.dispatch import DispatchService
    from api.demo_scenario import DemoScenarioStore
    from api.dashboard import DashboardStore
    from api.dashboard_analytics import unavailable
    store,risk=services(scope);scenario(scope)
    client,p=scope
    client.collection(p+'shops').document('s').set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    entered=Event();release=Event()
    class Bot:
        def send_message(self,*args,**kwargs):
            entered.set();assert release.wait(3);return 42
    class Sinks:
        def publish_event(self,*args):pass
        def insert_event(self,*args):pass
        def insert_alert(self,*args):pass
    active=DispatchService(store,Bot(),Sinks(),hash_salt='synthetic',active_risk=risk)
    resets=DemoScenarioStore(client,risk,prefix=p)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(asyncio.run,active.process(EventRequest(request_id='inflight',level='danger',lat=3.,lng=101.)))
        try:
            assert entered.wait(3)
            assert resets.reset('inflight-reset')['status']=='resetting'
        finally:release.set()
        result=future.result(timeout=5)
    assert result['alerts']=={'accepted':1}
    assert resets.reset('inflight-reset')['status']=='reset'
    old=store.get_event(result['event_id']);old['created_at']=datetime.now(UTC)
    # A late sink/receipt timestamp is never a current-generation entitlement.
    client.collection(p+'events').document(result['event_id']).update({'created_at':old['created_at'],'bigquery':'done'})
    class Analytics:
        def stats(self,shops,events,alerts,facts,**kwargs):
            assert events==[] and alerts==[] and facts==[]
            return unavailable(len(shops))
    dashboard=DashboardStore(client,Settings(),prefix=p,analytics=Analytics()).read()
    assert dashboard.scenario_generation==2 and dashboard.events==[] and dashboard.shops[0].level=='none'

def test_public_reset_validates_auth_identity_payload_and_idempotency(scope):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from api.dashboard import DashboardStore,create_dashboard_router
    client,p=scope;settings=Settings(demo_mode=True,operator_token='synthetic')
    store=DashboardStore(client,settings,prefix=p);app=FastAPI();app.include_router(create_dashboard_router(settings,store))
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            for headers in ({},{'Authorization':'Bearer wrong'}):assert (await api.post('/demo/reset',headers=headers,json={'request_id':'stable'})).status_code==403
            auth={'Authorization':'Bearer synthetic'}
            for body in ({},{'request_id':'a/b'},{'request_id':'stable','generation':999}):assert (await api.post('/demo/reset',headers=auth,json=body)).status_code==400
            assert (await api.post('/demo/reset',headers=auth,content='x'*1001)).status_code==413
            first=await api.post('/demo/reset',headers=auth,json={'request_id':'stable'})
            second=await api.post('/demo/reset',headers=auth,json={'request_id':'stable'})
            assert first.status_code==200 and first.json()==second.json() and first.json()['generation']==1
            assert first.headers['Cache-Control']=='no-store'
    asyncio.run(run())

def test_partial_seed_reset_does_not_deadlock_on_absent_fixtures(scope):
    from pathlib import Path
    from api.demo_seed import FixtureSeeder,SHOP_IDS
    from api.demo_scenario import DemoScenarioStore
    client,p=scope;_,risk=services(scope)
    class Storage:
        def __init__(self):self.calls=0
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):
            self.calls+=1
            if self.calls==2:raise RuntimeError('Interrupted partial seed')
    class Ledger:
        def append(self,*args):pass
    storage=Storage();seed=FixtureSeeder(client,storage,Ledger(),prefix=p)
    data=(Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes()
    with pytest.raises(RuntimeError):seed.seed(data)
    assert client.collection(p+'shops').document(SHOP_IDS[0]).get().exists
    assert not client.collection(p+'shops').document(SHOP_IDS[1]).get().exists
    assert DemoScenarioStore(client,risk,prefix=p).reset('partial-seed')['status']=='reset'
    assert seed.seed(data)['synthetic_shops']==6

def test_seeded_scope_excludes_unrelated_demo_projection_delivery_and_reset(scope):
    from pathlib import Path
    from api.demo_seed import FixtureSeeder
    from api.demo_scenario import DemoScenarioStore
    from api.dashboard import DashboardStore
    client,p=scope;store,risk=services(scope)
    outside=dict(shop_name='Other synthetic fixture',lat=3.,lng=101.,is_demo=True,active_danger=True,recipients=[])
    client.collection(p+'shops').document('other-demo').set(outside)
    class Storage:
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):pass
    class Ledger:
        def append(self,*args):pass
    FixtureSeeder(client,Storage(),Ledger(),prefix=p).seed((Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes())
    dashboard=DashboardStore(client,Settings(),prefix=p).read()
    assert len(dashboard.shops)==6 and 'other-demo' not in {shop.shop_id for shop in dashboard.shops}
    assert 'other-demo' not in {shop.shop_id for shop in store.target_shops()}
    assert DemoScenarioStore(client,risk,prefix=p).reset('owned-scope')['shops_reset']==6
    assert client.collection(p+'shops').document('other-demo').get().to_dict()==outside

def test_bound_alert_recipient_preserves_ordinary_media_report_lookup_and_ambiguity(scope):
    from pathlib import Path
    from api.demo_seed import FixtureSeeder,SHOP_IDS
    from api.photo_store import PhotoStore
    from api.inventory_store import InventoryStore
    from api.report_store import ReportStore
    from api.tests.test_media import request as media_request
    client,p=scope
    ordinary=dict(shop_name='Ordinary',lat=3.,lng=101.,is_demo=False,recipients=[dict(telegram_chat_id=123,language='en',role='owner')])
    client.collection(p+'shops').document('ordinary').set(ordinary)
    class Storage:
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):pass
    class Ledger:
        def append(self,*args):pass
    seed=FixtureSeeder(client,Storage(),Ledger(),prefix=p)
    seed.seed((Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes())
    stores=[PhotoStore(client,'synthetic',p),InventoryStore(client,'synthetic',p),ReportStore(client,'synthetic',p)]
    assert all(store.shop_for_sender(123)['shop_id']=='ordinary' for store in stores)
    seed.bind_registered(1,'ordinary');seed.seed((Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes())
    assert all(store.shop_for_sender(123)['shop_id']=='ordinary' for store in stores)
    assert stores[2].owner_shop(123)['shop_id']=='ordinary'
    assert all(store.authorize_media(media_request(shop_id='ordinary',is_demo=False)) for store in stores)
    assert not any(store.authorize_media(media_request(shop_id=SHOP_IDS[0],is_demo=True)) for store in stores)
    assert client.collection(p+'shops').document('ordinary').get().to_dict()==ordinary
    # The prior committed binding shape has provenance but no explicit scope.
    from google.cloud import firestore
    client.collection(p+'shops').document(SHOP_IDS[0]).update({'recipient_scope':firestore.DELETE_FIELD})
    assert all(store.shop_for_sender(123)['shop_id']=='ordinary' for store in stores)
    assert not any(store.authorize_media(media_request(shop_id=SHOP_IDS[0],is_demo=True)) for store in stores)
    # Ordinary test registrations may themselves be synthetic; don't exclude them.
    client.collection(p+'shops').document('ordinary').update({'is_demo':True})
    assert stores[0].shop_for_sender(123)['shop_id']=='ordinary'
    client.collection(p+'shops').document('second-ordinary').set(ordinary)
    assert all(store.shop_for_sender(123) is None for store in stores)


def test_bound_fixture_cannot_bypass_preexisting_ordinary_danger_prompt_guard(scope):
    from pathlib import Path
    from api.demo_seed import FixtureSeeder
    from api.inventory import InventoryService
    from api.inventory_store import InventoryStore
    from api.inventory_models import InventoryReply
    from api.i18n import danger_text
    import asyncio
    client,p=scope
    ordinary=dict(shop_name='Ordinary',lat=3.,lng=101.,is_demo=False,active_danger=True,recipients=[dict(telegram_chat_id=123,language='en',role='owner')])
    client.collection(p+'shops').document('ordinary').set(ordinary)
    class Storage:
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):pass
    class Ledger:
        def append(self,*args):pass
    seed=FixtureSeeder(client,Storage(),Ledger(),prefix=p)
    seed.seed((Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes());seed.bind_registered(1,'ordinary')
    active=InventoryService(InventoryStore(client,'synthetic',p),None,None)
    reply=asyncio.run(active.recheck_reply(123,InventoryReply(text='Send a baseline video',kind='prompt')))
    assert reply.kind=='danger' and reply.text==danger_text('en',is_demo=False)

def test_scoped_binding_retains_dispatch_and_vehicle_stock_callback_authorization(scope):
    from pathlib import Path
    import asyncio,httpx
    from api.demo_seed import FixtureSeeder,SHOP_IDS
    from api.dispatch import DispatchService
    from api.dispatch_models import ActionSnapshot
    from api.vehicle_confirmations import VehicleActionStore,VehicleConfirmationService
    from api.stock_confirmations import StockActionStore,StockConfirmationService
    from api.telegram_webhook import TelegramHandler
    from api.telegram_inbox import FirestoreInbox
    from api.main import create_app
    client,p=scope;store,risk=services(scope)
    ordinary=dict(shop_name='Ordinary',lat=3.,lng=101.,is_demo=False,recipients=[dict(telegram_chat_id=123,language='en',role='owner')])
    client.collection(p+'shops').document('ordinary').set(ordinary)
    class Storage:
        def uri(self,identity):return 'gs://synthetic/originals/'+identity
        def create_original(self,*args):pass
    class Ledger:
        def append(self,*args):pass
    seed=FixtureSeeder(client,Storage(),Ledger(),prefix=p);seed.seed((Path(__file__).resolve().parents[2]/'demo/media/synthetic-before-still.mp4').read_bytes());seed.bind_registered(1,'ordinary')
    class Bot:
        def __init__(self):self.messages=[];self.answers=[]
        def send_message(self,*args,**kwargs):self.messages.append(args);return 77
        def answer_callback_query(self,*args):self.answers.append(args)
    class Sinks:
        def publish_event(self,*args):pass
        def insert_event(self,*args):pass
        def insert_alert(self,*args):pass
        def insert_confirmation(self,*args):pass
    bot=Bot();sinks=Sinks()
    vehicles=VehicleActionStore(client,actions=p+'vehicle_actions',current=p+'current_vehicle_actions',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops')
    stocks=StockActionStore(client,actions=p+'stock_actions',confirmations=p+'confirmations',alerts=p+'alerts',shops=p+'shops',risks=p+'active_risks')
    dispatch=DispatchService(store,bot,sinks,hash_salt='synthetic',active_risk=risk,vehicle_actions=vehicles,stock_actions=stocks)
    handler=TelegramHandler(FirestoreInbox(client,p+'inbox'),bot,confirmations=VehicleConfirmationService(vehicles,sinks,hash_salt='synthetic'),stock_confirmations=StockConfirmationService(stocks,sinks,hash_salt='synthetic'))
    app=create_app(Settings(telegram_webhook_secret='synthetic'),handler)
    async def run():
        event=await dispatch.process(EventRequest(request_id='bound',level='warning',lat=3.0315,lng=101.5356,warning_structure='warning_intro_fallback'))
        assert event['alerts']=={'accepted':1} and len(bot.messages)==1
        alert=store.get_alert(store.get_event(event['event_id'])['alert_ids'][0])
        assert alert['shop_id']==SHOP_IDS[0]
        snapshot=ActionSnapshot.model_validate(alert['snapshot'])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            for i,(kind,identity) in enumerate((('vehicle',snapshot.vehicle_action_id),('stock',snapshot.stock_action_id))):
                body=dict(update_id=100+i,callback_query=dict(id=f'bound-{kind}',**{'from':dict(id=123)},message=dict(message_id=77,chat=dict(id=123,type='private')),data=f'{kind}:{identity}'))
                assert (await api.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'},json=body)).status_code==200
        facts=[doc.to_dict() for doc in client.collection(p+'confirmations').stream()]
        assert {row['kind'] for row in facts}=={'vehicle','stock'} and len(facts)==2
        assert all(row['shop_id']==SHOP_IDS[0] and row['snapshot']==alert['snapshot'] for row in facts)
        assert len(bot.answers)==2 and client.collection(p+'shops').document('ordinary').get().to_dict()==ordinary
    asyncio.run(run())
    for doc in client.collection(p+'inbox').stream():doc.reference.delete()
