from datetime import UTC,datetime,timedelta
from uuid import uuid4
import asyncio
import os
import pytest
from api.dashboard import DashboardStore,create_dashboard_router
from api.dashboard_models import DashboardStats
from api.config import Settings
from api.tools.firestore import create_firestore_client
from fastapi import FastAPI
import httpx

def dashboard_metrics(shops,events,alerts,confirmations,*,complete=True):
    event_ids={e['event_id'] for e in events};shop_ids={s['shop_id'] for s in shops}
    accepted=[a for a in alerts if a.get('is_demo') is True and a.get('event_id') in event_ids and a.get('shop_id') in shop_ids and a.get('status')=='accepted']
    times=[a['latency_ms'] for a in accepted if type(a.get('latency_ms')) in (int,float) and 0<=a['latency_ms']<=86400000]
    accepted_by_id={a.get('alert_id'):a for a in accepted}
    vehicles=set();stock={}
    for fact in confirmations:
        if fact.get('is_demo') is not True or fact.get('self_reported') is not True or fact.get('event_id') not in event_ids or fact.get('shop_id') not in shop_ids or not fact.get('episode_id'):continue
        alert=accepted_by_id.get(fact.get('alert_id'))
        if not alert or alert.get('snapshot')!=fact.get('snapshot') or alert.get('shop_id')!=fact['shop_id'] or alert.get('event_id')!=fact['event_id']:continue
        key=(fact['shop_id'],fact['episode_id'])
        if fact.get('kind')=='vehicle':vehicles.add(key)
        if fact.get('kind')=='stock':
            snapshot=fact.get('snapshot') or {};value=fact.get('protected_value_rm')
            displayed=round(sum(i.get('value_rm',0) for i in snapshot.get('items',[])),2)
            if type(value) not in (int,float) or not 0<=value<=1e9 or value!=displayed or snapshot.get('estimated_value_rm')!=value:continue
            stock[key]=max(stock.get(key,0),value)
    return DashboardStats(status='available' if complete else 'unavailable',synthetic_shops=len(shops),alerts_accepted=len(accepted) if complete else None,
        average_alert_acceptance_ms=round(sum(times)/len(times),2) if complete and times and len(times)==len(accepted) else None,
        vehicles_reported_moved=len(vehicles) if complete else None,estimated_stock_value_reported_lifted_rm=round(sum(stock.values()),2) if complete else None)

def snapshot(value):return {'estimated_value_rm':value,'items':[{'value_rm':value}]}
def test_episode_metrics_use_accepted_snapshot_max_and_distinct_vehicle():
    now=datetime.now(UTC)
    shops=[{'shop_id':'s'}];events=[{'event_id':'e'},{'event_id':'e2'}]
    alerts=[dict(alert_id=f'a{i}',shop_id='s',event_id=event,is_demo=True,status='accepted',latency_ms=20.,snapshot=snapshot(value)) for i,(value,event) in enumerate([(10.,'e'),(30.,'e2'),(8.,'e2')])]
    facts=[dict(confirmed_at=now,shop_id='s',episode_id='episode',event_id=a['event_id'],alert_id=a['alert_id'],is_demo=True,self_reported=True,kind='stock',protected_value_rm=a['snapshot']['estimated_value_rm'],snapshot=a['snapshot']) for a in alerts]
    facts+=[dict(facts[0],kind='vehicle'),dict(facts[1],kind='vehicle')]
    facts+=[dict(facts[1],protected_value_rm=999.,snapshot=snapshot(999.)),dict(facts[1],is_demo=False),dict(facts[1],event_id='historical')]
    stats=dashboard_metrics(shops,events,alerts,facts)
    assert stats.estimated_stock_value_reported_lifted_rm==30. and stats.vehicles_reported_moved==1
    assert stats.alerts_accepted==3 and stats.average_alert_acceptance_ms==20.
    assert dashboard_metrics(shops,events,alerts,facts,complete=False).alerts_accepted is None
    assert dashboard_metrics(shops,events,[],[]).average_alert_acceptance_ms is None

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore required')
def test_public_dashboard_reset_filters_private_history_and_late_facts():
    client=create_firestore_client(Settings(gcp_project='highground-dashboard-tests'));prefix='dashboard-'+uuid4().hex+'-';settings=Settings(demo_mode=True,operator_token='synthetic',official_max_age_minutes=7)
    class Analytics:
        def stats(self,*args,**kwargs):return dashboard_metrics(*args,**kwargs)
    store=DashboardStore(client,settings,prefix=prefix,analytics=Analytics());now=datetime.now(UTC)
    shop=dict(shop_name='Synthetic',shop_type='grocery',lat=3.,lng=101.,is_demo=True,risk_score=60,recipients=[{'telegram_chat_id':123,'role':'owner','language':'en'}],owner_name='PRIVATE-OWNER')
    store.collection('shops').document('s').set(shop);store.collection('shops').document('real').set(dict(shop,is_demo=False))
    event=dict(created_at=now,level='warning',lat=3.,lng=101.,radius_m=1000,reason='Synthetic event',confidence=1.,is_demo=True,status='complete',raw={'PRIVATE':'SECRET'})
    store.collection('events').document('e').set(event)
    store.collection('alerts').document('a').set(dict(created_at=now,shop_id='s',event_id='e',is_demo=True,status='accepted',latency_ms=45.,snapshot=snapshot(10.),telegram_chat_id_hash='PRIVATE-HASH'))
    store.collection('confirmations').document('c').set(dict(confirmed_at=now,shop_id='s',episode_id='episode',event_id='e',alert_id='a',is_demo=True,self_reported=True,kind='stock',protected_value_rm=10.,snapshot=snapshot(10.)))
    store.collection('official_source_status').document('jps').set({'status':'current','checked_at':(now-timedelta(minutes=8)).isoformat()})
    app=FastAPI();app.include_router(create_dashboard_router(settings,store))
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as api:
            result=await api.get('/api/dashboard');assert result.status_code==200
            assert 'PRIVATE' not in result.text and '123' not in result.text and len(result.json()['shops'])==1
            assert result.json()['sources'][0]['status']=='stale' and result.json()['stats']['estimated_stock_value_reported_lifted_rm']==10.
            assert (await api.post('/demo/reset',json={})).status_code==403
            assert (await api.post('/demo/reset',headers={'Authorization':'Bearer synthetic'},json={'request_id':'reset-test'})).status_code==200
            assert store.collection('events').document('e').get().exists and store.collection('confirmations').document('c').get().exists
            # Late confirmation of an older event must not repopulate the current display.
            store.collection('confirmations').document('late').set(dict(confirmed_at=now,shop_id='s',episode_id='episode',event_id='e',alert_id='a',is_demo=True,self_reported=True,kind='stock',protected_value_rm=10.,snapshot=snapshot(10.)))
            reset=await api.get('/api/dashboard');assert reset.json()['events']==[] and reset.json()['stats']['estimated_stock_value_reported_lifted_rm']==0.
    try:asyncio.run(run())
    finally:
        for name in ('shops','events','alerts','confirmations','official_source_status','demo_scenario','active_risks','current_vehicle_actions'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()


def test_bigquery_stats_bounded_identity_query_and_unavailable(monkeypatch):
    monkeypatch.delenv('BIGQUERY_EMULATOR_HOST',raising=False)
    from api.dashboard_analytics import DashboardAnalytics
    class Job:
        def result(self,**kwargs):
            assert kwargs==dict(timeout=4,retry=None,job_retry=None,max_results=1)
            return [dict(virtual_count=0,alert_count=1,latency_count=1,latency_ms=25.,confirmation_count=1,vehicles=0,stock_value=10.)]
    class Client:
        project='synthetic-project'
        def query(self,sql,**kwargs):
            assert kwargs['retry'] is None and kwargs['job_retry'] is None and kwargs['timeout']==4
            assert 'MAX(value_rm)' in sql and 'GROUP BY alert_id' in sql and 'IN UNNEST(@confirmations)' in sql
            self.parameters=kwargs['job_config'].query_parameters
            return Job()
    client=Client();analytics=DashboardAnalytics(client,'synthetic-project','synthetic')
    alerts=[dict(alert_id='a',shop_id='s',event_id='e',is_demo=True,status='accepted',snapshot=snapshot(10.))]
    facts=[dict(confirmation_id='c',alert_id='a',shop_id='s',event_id='e',episode_id='ep',is_demo=True,self_reported=True,kind='stock',snapshot=snapshot(10.),protected_value_rm=10.)]
    result=analytics.stats([{'shop_id':'s'}],[{'event_id':'e'}],alerts,facts,complete=True)
    assert result.status=='available' and result.estimated_stock_value_reported_lifted_rm==10.
    assert {p.name:p.values for p in client.parameters}=={'shops':['s'],'events':['e'],'alerts':['a'],'confirmations':['c'],'virtual_alerts':[]}
    assert analytics.stats([{'shop_id':'s'}],[],alerts,facts,complete=True).status=='unavailable'
    assert analytics.stats([],[],[],[],complete=False).alerts_accepted is None

def test_materialized_dashboard_survives_cleanup_failure_without_private_logs(monkeypatch,caplog):
    from types import SimpleNamespace
    from api.dashboard_analytics import DashboardAnalytics
    monkeypatch.setenv('BIGQUERY_EMULATOR_HOST','http://127.0.0.1:9050')
    class Job:
        job_id='exact_job';destination=SimpleNamespace(project='synthetic-project',dataset_id='exact_job',table_id='exact_job')
        def result(self,**kwargs):return [dict(virtual_count=0,alert_count=0,latency_count=0,latency_ms=None,confirmation_count=0,vehicles=0,stock_value=0.)]
    class Client:
        project='synthetic-project';_connection=SimpleNamespace(API_BASE_URL='http://127.0.0.1:9050')
        def query(self,*args,**kwargs):return Job()
        def delete_dataset(self,*args,**kwargs):raise RuntimeError('PRIVATE-SDK-BODY')
    analytics=DashboardAnalytics(Client(),'synthetic-project','synthetic')
    result=analytics.stats([],[],[],[],complete=True)
    assert result.status=='available' and result.alerts_accepted==0 and analytics.last_cleanup_status=='failed'
    assert 'Dashboard local query cleanup: failed (RuntimeError)' in caplog.text and 'PRIVATE' not in caplog.text

@pytest.mark.parametrize('endpoint',[None,''])
def test_optional_empty_emulator_host_matches_unset_no_cleanup(endpoint,monkeypatch):
    from api.dashboard_analytics import DashboardAnalytics
    if endpoint is None:monkeypatch.delenv('BIGQUERY_EMULATOR_HOST',raising=False)
    else:monkeypatch.setenv('BIGQUERY_EMULATOR_HOST',endpoint)
    class Job:
        def result(self,**kwargs):return [dict(virtual_count=0,alert_count=0,latency_count=0,latency_ms=None,confirmation_count=0,vehicles=0,stock_value=0.)]
    class Client:
        project='synthetic-project'
        def query(self,*args,**kwargs):return Job()
        def delete_dataset(self,*args,**kwargs):pytest.fail('Disabled emulator cleanup deleted production result')
    analytics=DashboardAnalytics(Client(),'synthetic-project','synthetic')
    assert analytics.stats([],[],[],[],complete=True).status=='available'
    assert analytics.last_cleanup_status=='not_required'
