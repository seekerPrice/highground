"""Protected manual policy stage reports pending honestly; no SDK/model calls."""
import asyncio
from types import SimpleNamespace
import httpx
from api.main import create_app
from api.config import Settings
from api.recovery_jobs import RecoveryJobsService

def test_protected_policy_deletion_stage_outage_retry_idempotency_and_auth(monkeypatch):
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST','127.0.0.1:8787');monkeypatch.delenv('K_SERVICE',raising=False)
    job={'deletion_pending':True,'receipt':'immutable'}
    class Policy:
        def __init__(self):self.unavailable=True;self.calls=0;self.store=SimpleNamespace(get=lambda identity:dict(job))
        def _service(self):return self
        async def _delete(self,record):
            self.calls+=1
            if not self.unavailable:job['deletion_pending']=False
        async def close(self):pass
    policy=Policy();jobs=RecoveryJobsService();jobs.policy=policy
    jobs._dispatch_ids=lambda limit:[];jobs._confirmation_ids=lambda limit:[];jobs._media_ids=lambda limit:[];jobs._card_ids=lambda limit:[]
    jobs._policy_ids=lambda limit:['reserved-policy'] if job['deletion_pending'] else []
    settings=Settings(local_development=True,scheduler_local_auth=True,demo_mode=True,operator_token='synthetic')
    async def run():
        app=create_app(settings,recovery_jobs_service=jobs)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            assert (await api.post('/jobs/resume-pending',json={'limit':1})).status_code==403 and policy.calls==0
            headers={'Authorization':'Bearer synthetic'}
            assert (await api.post('/jobs/resume-pending',headers=headers,json={'limit':21})).status_code==400 and policy.calls==0
            result=(await api.post('/jobs/resume-pending',headers=headers,json={'limit':1})).json()['policy_deletions']
            assert result['scanned']==1 and result['pending']==1 and result['completed']==0
            policy.unavailable=False
            result=(await api.post('/jobs/resume-pending',headers=headers,json={'limit':1})).json()['policy_deletions']
            assert result['completed']==1 and result['pending']==0 and job['receipt']=='immutable'
            result=(await api.post('/jobs/resume-pending',headers=headers,json={'limit':1})).json()['policy_deletions']
            assert result['scanned']==0 and policy.calls==2
            monkeypatch.setenv('K_SERVICE','synthetic-cloud')
            assert (await api.post('/jobs/resume-pending',headers=headers,json={'limit':1})).status_code==403 and policy.calls==2
        await jobs.close()
    asyncio.run(run())
