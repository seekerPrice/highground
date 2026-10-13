"""Actual protected HTTP entry points, with no SDK or external transport."""
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.config import Settings
from api.main import create_app
from api.telegram_webhook import TelegramHandler
from api.tests.test_policy_callback_guards import Inbox
from api.tests.test_policy_webhook import API,message,post
from api.tests.test_outcome_service import service,local_transactions
from api.tests.test_outcomes import NOW
from api.outcome_models import OwnerOutcome


def test_public_callback_owner_binding_ack_and_immutable_response(local_transactions):
    svc,data,key=service(local_transactions)
    asyncio.run(svc._prompt(key));row=data.rows['outcome_prompts',key]
    inbox=Inbox();api=API()
    payload={'update_id':1,'callback_query':{'id':'one','from':{'id':101},'message':{'message_id':91,'chat':{'id':101,'type':'private'}},'data':'outcome:'+row['callback_token']+':street'}}
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,outcomes=svc))) as client:
        assert post(client,payload).status_code==200
        assert len(api.acks)==1 and inbox.state=='done'
        assert OwnerOutcome.model_validate_json(data.rows['outcome_responses',key]['json']).answer=='street_only'
        assert post(client,payload).status_code==200 and len(api.acks)==1


def test_inside_command_optional_depth_is_explicit_bounded_and_first_response_retained(local_transactions):
    svc,data,key=service(local_transactions);api=API();inbox=Inbox()
    from unittest.mock import Mock
    svc.outcomes.episodes=Mock(return_value=(svc.outcomes.episode(key),))
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,outcomes=svc))) as client:
        payload=message(1,'/outcome inside '+NOW.isoformat()+' 1001');payload['message']['chat']['id']=101
        assert post(client,payload).status_code==200 and ('outcome_responses',key) not in data.rows
        inbox.state=None;payload=message(2,'/outcome inside '+NOW.isoformat()+' 42');payload['message']['chat']['id']=101
        assert post(client,payload).status_code==200
        response=OwnerOutcome.model_validate_json(data.rows['outcome_responses',key]['json'])
        assert response.depth_cm==42 and response.reference_basis=='owner_declared'
        inbox.state=None;payload=message(3,'/outcome inside '+NOW.isoformat()+' 99');payload['message']['chat']['id']=101
        assert post(client,payload).status_code==200
        assert OwnerOutcome.model_validate_json(data.rows['outcome_responses',key]['json'])==response


def test_protected_manual_job_auth_bounds_and_retry_contract(monkeypatch):
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787');monkeypatch.delenv('K_SERVICE',raising=False)
    class Service:
        calls=[]
        async def ask(self,limit):
            self.calls.append(limit)
            if len(self.calls)==1:raise RuntimeError('Sink unavailable')
            return {'status':'available','outcomes_completed':1}
    svc=Service();settings=Settings(local_development=True,demo_mode=True,scheduler_local_auth=True,operator_token='synthetic')
    with TestClient(create_app(settings,outcome_service=svc)) as client:
        assert client.post('/jobs/ask-outcomes').status_code==403 and not svc.calls
        headers={'Authorization':'Bearer synthetic'}
        assert client.post('/jobs/ask-outcomes',json={'limit':21},headers=headers).status_code==400 and not svc.calls
        assert client.post('/jobs/ask-outcomes',json={'limit':1},headers=headers).status_code==503
        result=client.post('/jobs/ask-outcomes',json={'limit':1},headers=headers)
        assert result.status_code==200 and result.json()['outcomes_completed']==1 and result.headers['cache-control']=='no-store'
        monkeypatch.setenv('K_SERVICE','cloud')
        assert client.post('/jobs/ask-outcomes',headers=headers).status_code==403
