"""Synthetic dashboard projection and history-preserving operator scenario reset."""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC,datetime
import hmac
from google.cloud.firestore_v1.base_query import FieldFilter
from fastapi import APIRouter,HTTPException,Request,Response
from api.dashboard_models import Dashboard,DashboardShop,DashboardEvent,DashboardStats,SourceStatus,ResetRequest,ResetResult
from api.destinations import SafePoint
from api.active_risk import ActiveRiskStore
from api.dashboard_analytics import unavailable
from api.demo_scenario import DemoScenarioStore,FIXTURE_ORIGIN,SHOP_IDS


class DashboardStore:
    def __init__(self,client,settings,*,prefix='',analytics=None):
        self.client,self.settings,self.prefix=client,settings,prefix
        self.analytics=analytics
        self.risks=ActiveRiskStore(client,risks=prefix+'active_risks',shops=prefix+'shops',current_actions=prefix+'current_vehicle_actions',deliveries=prefix+'shop_delivery_claims',max_age=settings.official_max_age)
    def collection(self,name):return self.client.collection(self.prefix+name)
    def synthetic(self,name: str,limit: int,since: datetime|None=None,generation: int|None=None) -> tuple[list[dict],bool]:
        query=self.collection(name).where(filter=FieldFilter('is_demo','==',True))
        if name in ('events','alerts','confirmations') and generation is not None:query=query.where(filter=FieldFilter('scenario_generation','==',generation))
        time_field={'events':'created_at','alerts':'created_at','confirmations':'confirmed_at'}.get(name)
        if time_field:
            if since is not None:query=query.where(filter=FieldFilter(time_field,'>=',since))
            query=query.order_by(time_field,direction='DESCENDING')
        docs=list(query.limit(limit+1).stream())
        return [dict(d.to_dict(),**{('shop_id' if name=='shops' else 'event_id' if name=='events' else 'alert_id' if name=='alerts' else 'confirmation_id'):d.id}) for d in docs[:limit]],len(docs)<=limit
    def read(self) -> Dashboard:
        now=datetime.now(UTC);scenario=self.collection('demo_scenario').document('current').get().to_dict() or {};since=scenario.get('started_at')
        if scenario.get('fixture_shop_ids') is not None:
            scope=scenario['fixture_shop_ids']
            if len(scope)>6 or len(set(scope))!=len(scope) or not set(scope).issubset(SHOP_IDS):raise ValueError('Fixture projection exceeds bound')
            shops=[]
            for identity in scope:
                row=self.collection('shops').document(identity).get().to_dict() or {}
                if row.get('is_demo') is True and row.get('fixture_origin')==FIXTURE_ORIGIN:shops.append(dict(row,shop_id=identity))
            shop_complete=True
        else:shops,shop_complete=self.synthetic('shops',50)
        events,event_complete=self.synthetic('events',1000,since,scenario.get('generation'))
        events=[e for e in events if isinstance(e.get('created_at'),datetime) and (since is None or e['created_at']>=since) and e['created_at']<=now and e.get('status')!='superseded']
        alerts,alert_complete=self.synthetic('alerts',1000,since,scenario.get('generation'));facts,fact_complete=self.synthetic('confirmations',1000,since,scenario.get('generation'))
        public_shops=[]
        for shop in shops:
            risk=self.collection('active_risks').document(shop['shop_id']).get().to_dict() or {}
            sources=risk.get('sources',{});ranks={'none':0,'watch':1,'warning':2,'danger':3}
            level=max((s['level'] for s in sources.values() if s.get('is_demo')),key=lambda x:ranks.get(x,0),default='none')
            if shop.get('active_danger') and not sources:level='danger'
            public_shops.append(DashboardShop(shop_id=shop['shop_id'],shop_name=shop.get('shop_name','Synthetic shop'),shop_type=shop.get('shop_type','other'),lat=shop['lat'],lng=shop['lng'],risk_score=shop.get('risk_score'),level=level))
        public_events=[]
        for event in sorted(events,key=lambda e:e['created_at'],reverse=True)[:100]:
            try:public_events.append(DashboardEvent(**{k:event[k] for k in ('event_id','created_at','level','lat','lng','radius_m','reason','confidence')}))
            except (ValueError,KeyError):continue
        destinations=[]
        for doc in self.collection('safe_points').limit(100).stream():
            try:destinations.append(SafePoint.model_validate(dict(doc.to_dict(),safe_point_id=doc.id)))
            except ValueError:continue
        sources=[]
        for source in ('jps','met'):
            raw=self.collection('official_source_status').document(source).get().to_dict() or {};checked=raw.get('checked_at')
            try:checked=datetime.fromisoformat(checked.replace('Z','+00:00')) if isinstance(checked,str) else checked
            except ValueError:checked=None
            # A successful check with zero current observations still cannot establish all-clear.
            status='unavailable'
            if checked and checked.tzinfo and checked<=now and now-checked<=self.settings.official_max_age:
                if raw.get('status') in ('current','degraded'):status='fresh' if raw.get('status')=='current' else 'unavailable'
                elif raw.get('status')=='stale':status='stale'
            elif checked:status='stale'
            sources.append(SourceStatus(source=source,status=status,checked_at=checked,note='Source observation time is unknown in this summary. A recent check does not establish an all-clear.'))
        policy_coverage=None;policy_note='Synthetic policy summary is unavailable.'
        if shop_complete:
            try:
                from api.policy_store import PolicyStore
                policy_coverage=PolicyStore(self.client,self.settings.hash_salt,self.prefix).synthetic_aggregate(shops,now.date())
                policy_note='Synthetic only. Missing policies, unclear or expired wording, and unknown stock estimates are shown separately. Check with your insurer; no current-cover or payout guarantee.'
            except Exception:pass
        return Dashboard(policy_coverage=policy_coverage,policy_note=policy_note,generated_at=now,status='available' if public_shops else 'empty',scenario_started_at=since,scenario_generation=scenario.get('generation',0),scenario_state=scenario.get('state','ready'),shops=public_shops,events=public_events,destinations=destinations,sources=sources,
            stats=self.analytics.stats(shops,events,alerts,facts,complete=scenario.get('state','ready')=='ready' and all((shop_complete,event_complete,alert_complete,fact_complete))) if self.analytics else unavailable(len(shops)))
    def reset(self,request_id: str) -> dict:
        return DemoScenarioStore(self.client,self.risks,prefix=self.prefix).reset(request_id)
    def close(self):
        self.client.close()
        if self.analytics:self.analytics.close()

def create_dashboard_router(settings,store=None):
    active=store;owns=store is None
    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns and active:await asyncio.to_thread(active.close)
    router=APIRouter(lifespan=lifespan)
    def configuration():return settings() if callable(settings) else settings
    def service():
        nonlocal active
        if active is None:
            from api.tools.firestore import create_firestore_client
            from api.tools.cloud_events import create_analytics_client
            from api.dashboard_analytics import DashboardAnalytics
            config=configuration()
            active=DashboardStore(create_firestore_client(config),config,analytics=DashboardAnalytics(create_analytics_client(config),config.gcp_project,config.bigquery_dataset))
        return active
    @router.get('/api/dashboard',response_model=Dashboard)
    async def dashboard(response:Response):
        response.headers['Cache-Control']='no-store'
        try:return await asyncio.to_thread(service().read)
        except Exception:raise HTTPException(503,'Dashboard temporarily unavailable',headers={'Cache-Control':'no-store'}) from None
    @router.post('/demo/reset',response_model=ResetResult)
    async def reset(request:Request,response:Response):
        config=configuration()
        if not config.demo_mode:raise HTTPException(403,'Demo mode is disabled')
        if not config.operator_token:raise HTTPException(503,'Demo operator authentication is not configured')
        if not hmac.compare_digest(request.headers.get('Authorization','').encode(),('Bearer '+config.operator_token).encode()):raise HTTPException(403,'Invalid demo operator token')
        payload=bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload)>1000:raise HTTPException(413,'Reset request too large')
        try:body=ResetRequest.model_validate_json(bytes(payload))
        except ValueError:raise HTTPException(400,'Reset requires a valid stable request_id') from None
        response.headers['Cache-Control']='no-store'
        try:return await asyncio.to_thread(service().reset,body.request_id)
        except Exception:raise HTTPException(503,'Demo reset unavailable') from None
    return router
