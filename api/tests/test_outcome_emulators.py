"""Real Firestore transaction/HTTP proofs; transport and analytics are boundary doubles."""
import asyncio,os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC,datetime
from uuid import uuid4
from unittest.mock import Mock
import pytest
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
from fastapi.testclient import TestClient
from api.active_risk import ActiveRiskStore
from api.outcome_store import FirestoreOutcomeStore
from api.outcome_history import OutcomeHistoryAdapter
from api.outcome_service import OutcomeService
from api.photo_store import PhotoStore
from api.config import Settings
from api.main import create_app
from api.telegram_webhook import TelegramHandler
from api.telegram_inbox import FirestoreInbox
from api.tests.test_policy_webhook import API,post

@pytest.fixture
def real():
    if not os.getenv('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore emulator required')
    if os.environ['FIRESTORE_EMULATOR_HOST']!='127.0.0.1:8787':pytest.fail('Dedicated loopback Firestore required')
    client=firestore.Client(project='highground-outcome-tests',credentials=AnonymousCredentials());prefix='outcome_'+uuid4().hex+'_'
    risks=ActiveRiskStore(client,risks=prefix+'active_risks',shops=prefix+'shops',deliveries=prefix+'shop_delivery_claims',current_actions=prefix+'current_vehicle_actions',episode_history=prefix+'history')
    store=FirestoreOutcomeStore(client,'isolated-salt',prefix=prefix,shops=prefix+'shops',risks=prefix+'active_risks')
    history=OutcomeHistoryAdapter(client,store,risks,events=prefix+'events',alerts=prefix+'alerts',ledger=prefix+'history')
    event={'event_id':'a'*64,'created_at':datetime.now(UTC),'source':'shop_report','level':'warning','is_demo':False}
    try:
        client.collection(prefix+'shops').document('shop').set({'lat':3.,'lng':101.,'is_demo':False,'recipients':[{'role':'owner','telegram_chat_id':101,'language':'en'}]})
        yield client,prefix,risks,store,history,event
    finally:
        try:
            names=('shops','active_risks','shop_delivery_claims','current_vehicle_actions','history','events','alerts','inbox')+tuple('outcome_'+k for k in ('episodes','responses','facts','calibration','consumed','calibration_facts','prompts','tokens'))
            for name in names:
                for row in client.collection(prefix+name).stream(timeout=5,retry=None):row.reference.delete(timeout=5,retry=None)
        finally:client.close()


def test_actual_atomic_reporter_history_and_explicit_closure_roundtrip(real):
    client,prefix,risks,store,history,event=real
    decision=risks.apply_event_decision(event,'shop')
    keys=history.refresh(limit=1,now=datetime.now(UTC));episode=store.episode(keys[0])
    assert episode.episode_id==decision.episode_id and episode.started_at==event['created_at'] and not episode.deliveries
    assert risks.owner_declared_recovery('shop',101)
    history.refresh(limit=1,now=datetime.now(UTC));closed=store.episode(keys[0])
    assert closed.started_at==episode.started_at and closed.closed_at is not None
    assert not list(client.collection(prefix+'alerts').stream(timeout=5,retry=None))


def test_actual_alert_outcome_shared_lease_has_single_winner(real):
    client,prefix,risks,store,history,event=real
    episode_id=risks.apply_event(event,'shop');key=history.refresh(limit=1,now=datetime.now(UTC))[0];episode=store.episode(key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(risks.claim_outcome_delivery,episode,101),pool.submit(risks.claim_delivery,'shop',dict(event,episode_id=episode_id))]
        results=[future.result() for future in tasks]
    assert sorted(status for status,_ in results)==['busy','claimed']
    owner=next(owner for status,owner in results if status=='claimed')
    risks.release_delivery('shop',owner)
    assert risks.claim_outcome_delivery(episode,101)[0]=='claimed'


def test_actual_protected_job_callback_and_sink_outage_resume_one_logical_fact(real,monkeypatch):
    client,prefix,risks,store,history,event=real
    risks.apply_event(event,'shop');risks.owner_declared_recovery('shop',101)
    api=API();sinks=Mock();sinks.insert_outcome.side_effect=[RuntimeError('Temporary analytics outage'),None]
    service=OutcomeService(store,history,api,sinks,risk_store=risks,shop_store=PhotoStore(client,'isolated-salt',prefix,risks))
    settings=Settings(telegram_webhook_secret='synthetic-secret',local_development=True,demo_mode=True,scheduler_local_auth=True,operator_token='synthetic')
    monkeypatch.delenv('K_SERVICE',raising=False)
    handler=TelegramHandler(FirestoreInbox(client,prefix+'inbox'),api,outcomes=service)
    with TestClient(create_app(settings,handler,outcome_service=service)) as web:
        headers={'Authorization':'Bearer synthetic'}
        first=web.post('/jobs/ask-outcomes',json={'limit':1},headers=headers)
        assert first.status_code==200 and first.json()['prompts_accepted']==1 and len(api.sent)==1
        keys=history.refresh(limit=1,now=datetime.now(UTC));key=keys[0];row=store._read(store._ref('prompts',key))
        payload={'update_id':1,'callback_query':{'id':'synthetic','from':{'id':101},'message':{'message_id':row['message_id'],'chat':{'id':101,'type':'private'}},'data':'outcome:'+row['callback_token']+':inside'}}
        assert post(web,payload).status_code==200 and post(web,payload).status_code==200
        count=len(api.sent)
        failed=web.post('/jobs/ask-outcomes',json={'limit':1},headers=headers)
        assert failed.status_code==200 and failed.json()['failed']==1 and store._read(store._ref('facts',key))['bigquery']=='pending'
        recovered=web.post('/jobs/ask-outcomes',json={'limit':1},headers=headers)
        assert recovered.status_code==200 and recovered.json()['outcomes_completed']==1 and recovered.json()['prompts_accepted']==0
        assert len(api.sent)==count and len(list(client.collection(prefix+'outcome_responses').stream(timeout=5,retry=None)))==1
        assert store._read(store._ref('facts',key))['bigquery']=='done'
    asyncio.run(service.close())
