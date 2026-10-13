"""Protected manual work and bounded synthetic-only public outcome coverage."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC,datetime
from fastapi import APIRouter,HTTPException,Request,Response
from api.recovery_jobs import ResumeRequest
from api.outcome_models import OutcomeSummary


def create_outcome_router(settings,service=None,analytics=None):
    active=service;public=analytics;client=None
    @asynccontextmanager
    async def lifespan(app):
        yield
        if service is None and active is not None:await active.close()
        if analytics is None and public is not None:public.close()
        if client is not None:client.close()
    router=APIRouter(lifespan=lifespan)
    def config():return settings() if callable(settings) else settings
    @router.post('/jobs/ask-outcomes')
    async def ask(request:Request,response:Response):
        nonlocal active
        response.headers['Cache-Control']='no-store'
        from api.scheduler_auth import authorize_scheduler
        try:await authorize_scheduler(request.headers.get('Authorization',''),config())
        except Exception:raise HTTPException(403,'Scheduler authorization rejected') from None
        payload=bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload)>1000:raise HTTPException(413,'Outcome request too large')
        try:body=ResumeRequest.model_validate_json(bytes(payload) or b'{}')
        except ValueError:raise HTTPException(400,'Invalid bounded outcome request') from None
        try:
            if active is None:
                from api.outcome_service import create_outcome_service
                active=create_outcome_service(config())
            return await active.ask(body.limit)
        except Exception:raise HTTPException(503,'Outcome work unavailable; retry later') from None
    @router.get('/api/outcomes',response_model=OutcomeSummary)
    async def summary(response:Response):
        nonlocal public,client
        response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
        now=datetime.now(UTC)
        try:
            if public is None:
                from api.tools.firestore import create_firestore_client
                from api.tools.cloud_events import create_analytics_client
                from api.outcome_analytics import OutcomeAnalytics
                from api.outcome_store import FirestoreOutcomeStore
                configuration=config();client=create_firestore_client(configuration)
                import os
                public=OutcomeAnalytics(create_analytics_client(configuration),configuration.gcp_project,configuration.bigquery_dataset,FirestoreOutcomeStore(client,configuration.hash_salt),emulator_host=os.environ.get('BIGQUERY_EMULATOR_HOST') or None)
            from api.demo_scenario import DemoScenarioStore
            # Reuse verified fixture ownership selection; do not publish ordinary shops.
            from api.waste_store import WasteStore
            store=WasteStore(public.store.client,config().hash_salt,prefix=public.store.prefix)
            shops=await asyncio.to_thread(store.synthetic_scope)
            scenario=await asyncio.to_thread(lambda:store.collection('demo_scenario').document('current').get(timeout=5,retry=None).to_dict() or {})
            if scenario.get('state','ready')!='ready':raise ValueError('Scenario reset in progress')
            return await asyncio.to_thread(public.summary,shops,scenario.get('generation',0),now)
        except Exception:return OutcomeSummary(status='unavailable',generated_at=now,note='Synthetic owner outcomes are unavailable; missing responses remain unknown. No accuracy or independently verified water claim.')
    return router
