import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC,datetime,timedelta
from uuid import uuid4
import os
import pytest
from api.active_risk import ActiveRiskStore
from api.config import Settings
from api.models import Warning,Geography,SourceResult
from api.polling import PollStore,source_episode
from api.dispatch_models import EventRequest
from api.tools.firestore import create_firestore_client


@pytest.fixture
def domain():
    if not os.getenv('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore emulator required')
    client=create_firestore_client(Settings(gcp_project='highground-task10-tests'));prefix='risk-'+uuid4().hex
    risk=ActiveRiskStore(client,risks=prefix+'r',shops=prefix+'s',deliveries=prefix+'d',current_actions=prefix+'a')
    poll=PollStore(client,states=prefix+'sources',intents=prefix+'intents',status=prefix+'status')
    risk.source_states=poll.states
    client.collection(risk.shops).document('shop').set({'shop_name':'Synthetic','lat':3.,'lng':101.,'is_demo':False,'recipients':[{'telegram_chat_id':1,'language':'en','role':'owner'}]})
    try:yield client,risk,poll
    finally:
        for collection in (risk.risks,risk.shops,risk.deliveries,risk.current_actions,poll.states,poll.intents,poll.status):
            for document in client.collection(collection).stream():document.reference.delete()
        client.close()


def event(level='warning',source='jps',key='jps:station',episode='official-one',at=None):
    now=at or datetime.now(UTC)
    return dict(event_id=uuid4().hex,source=source,source_key=key,source_episode_id=episode,source_observed_at=now,
                level=level,is_demo=False,created_at=now,processing_started_at=now)


def test_atomic_poll_concurrency_restart_and_recovery(domain):
    client,risk,poll=domain;now=datetime.now(UTC)
    warning=Warning(source='jps',source_id='station',level='warning',observed_at=now,geography=Geography(latitude=3.,longitude=101.),reason='Official indicator')
    result=SourceResult(source='jps',status='current',checked_at=now,warnings=(warning,),records_current=1)
    with ThreadPoolExecutor(max_workers=3) as executor:list(executor.map(lambda _:poll.observe(result),range(3)))
    assert len(poll.pending())==1
    restarted=PollStore(client,states=poll.states,intents=poll.intents,status=poll.status)
    restarted.observe(result);assert len(restarted.pending())==1
    identity,intent=poll.pending()[0];request=EventRequest.model_validate_json(intent['request_json'])
    assert request.source_key=='jps:station' and request.source_valid_until==now+timedelta(minutes=90)
    risk.apply_event(event(at=now,episode=request.source_episode_id),'shop')
    assert risk.get('shop').episode_id
    poll.observe(SourceResult(source='jps',status='stale',checked_at=now,rejected={'stale':1}))
    assert len(poll.pending())==1
    poll.observe(SourceResult(source='jps',status='current',checked_at=now,resolved={'jps:station':now+timedelta(seconds=1)}))
    assert len(poll.pending())==2 and any(value['kind']=='recovery' for _,value in poll.pending())


def test_multiple_sources_same_episode_recovery_exact_source_and_freshness(domain):
    _,risk,_=domain;now=datetime.now(UTC)-timedelta(seconds=2)
    first=event('danger',at=now);episode=risk.apply_event(first,'shop')
    assert risk.apply_event(event(key='jps:other',episode='other',at=now),'shop')==episode
    assert risk.get('shop').official_danger
    assert risk.recover_official('jps:other','other',datetime.now(UTC))==1
    assert risk.get('shop').active_danger
    assert risk.recover_official('jps:station','wrong',datetime.now(UTC))==0
    assert risk.recover_official('jps:station','official-one',now-timedelta(hours=2))==0
    assert risk.owner_declared_recovery('shop',1) is False
    assert risk.recover_official('jps:station','official-one',datetime.now(UTC))==1
    assert not risk.get('shop').active_danger and risk.get('shop').episode_id is None
    assert risk.apply_event(first,'shop') is None
    fresh=risk.apply_event(event(at=datetime.now(UTC)),'shop')
    assert fresh and fresh!=episode


def test_legacy_photo_owner_and_demo_reset_do_not_resurrect(domain):
    client,risk,_=domain
    photo=event('danger','shop_report',key=None,episode=None)
    assert risk.apply_event(photo,'shop')
    assert not risk.owner_declared_recovery('shop',2)
    assert risk.owner_declared_recovery('shop',1)
    assert not risk.get('shop').active_danger and risk.apply_event(photo,'shop') is None
    ref=client.collection(risk.shops).document('legacy');ref.set({'active_danger':True,'is_demo':False,'recipients':[{'telegram_chat_id':1,'role':'owner'}]})
    assert risk.get('legacy').legacy_unknown and not risk.owner_declared_recovery('legacy',1)
    client.collection(risk.shops).document('demo').set({'is_demo':True,'active_danger':True})
    assert risk.reset_demo('demo')
    simulated={**event('danger','shop_report',key=None),'is_demo':True}
    assert risk.apply_event(simulated,'demo')
    assert risk.reset_demo('demo') and risk.apply_event(simulated,'demo') is None


def test_older_observation_suppressed_and_final_freshness_without_expiry(domain):
    client,risk,_=domain;now=datetime.now(UTC)
    risk.apply_event(event('watch',at=now),'shop')
    late=event('danger',at=now-timedelta(seconds=1))
    assert risk.apply_event_decision(late,'shop').reason=='obsolete_observation'
    assert not risk.get('shop').active_danger
    expired=event('danger',at=now-timedelta(minutes=91))
    assert risk.apply_event_decision(expired,'shop').reason=='expired'
    assert risk.claim_delivery('shop',expired)[0]=='superseded'
    client.collection(risk.shops).document('demo').set({'is_demo':True})
    demo={**event('danger'),'is_demo':True,'source_key':None,'source_episode_id':None,'source_observed_at':None}
    assert risk.apply_event(demo,'demo') and risk.get('demo').active_danger and not risk.get('demo').official_danger


def test_delayed_warning_composition_cannot_follow_danger(domain):
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.alert_composer import AlertComposer
    from api.tests.test_dispatch import Sinks
    client,risk,_=domain
    store=FirestoreDispatchStore(client,events=risk.risks+'events',alerts=risk.risks+'alerts',shops=risk.shops)
    class Bot:
        def __init__(self):self.messages=[]
        def send_message(self,chat,text,reply_markup=None):self.messages.append(text);return len(self.messages)
    async def run():
        paused=asyncio.Event();release=asyncio.Event()
        class Delayed(AlertComposer):
            async def compose(self,event,shop,language,**kwargs):
                if event['level']=='warning':paused.set();await release.wait()
                return await super().compose(event,shop,language,**kwargs)
        bot=Bot();service=DispatchService(store,bot,Sinks(),hash_salt='synthetic',composer=Delayed(),active_risk=risk)
        now=datetime.now(UTC)
        def request(level,identity):return EventRequest(request_id=identity,source='jps',level=level,lat=3.,lng=101.,source_key='jps:station',source_episode_id='one',source_observed_at=now)
        pending=asyncio.create_task(service.process(request('warning','warning')))
        await asyncio.wait_for(paused.wait(),3)
        danger=await service.process(request('danger','danger'))
        assert danger['status']=='complete' and len(bot.messages)==1 and 'DANGER' in bot.messages[0]
        release.set();warning=await pending
        assert warning['alerts']=={'superseded':1} and len(bot.messages)==1
    try:asyncio.run(run())
    finally:
        for collection in (store.events,store.plans,store.alerts,store.deliveries):
            for document in client.collection(collection).stream():document.reference.delete()


def test_delivery_lease_serializes_in_flight_external_requests(domain):
    _,risk,_=domain
    warning=event();episode=risk.apply_event(warning,'shop');warning['episode_id']=episode
    disposition,owner=risk.claim_delivery('shop',warning)
    assert disposition=='claimed'
    danger=event('danger');danger['episode_id']=risk.apply_event(danger,'shop')
    assert risk.claim_delivery('shop',danger)==('busy',None)
    risk.release_delivery('shop',owner)
    assert risk.claim_delivery('shop',warning)==('superseded',None)
    disposition,owner=risk.claim_delivery('shop',danger)
    assert disposition=='claimed';risk.release_delivery('shop',owner)


def test_repeated_normal_can_retry_fresh_recovery_and_done_intent_stays_done(domain):
    _,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=4)
    warning=Warning(source='jps',source_id='station',level='danger',observed_at=now,geography=Geography(latitude=3.,longitude=101.),reason='Official Danger')
    poll.observe(SourceResult(source='jps',status='current',checked_at=now,warnings=(warning,)))
    event_id,intent=poll.pending()[0];poll.done(event_id)
    first=now+timedelta(seconds=1)
    recovery=SourceResult(source='jps',status='current',checked_at=first,resolved={'jps:station':first})
    poll.observe(recovery)
    identity,intent=poll.pending()[0];original=intent['source_episode_id'];poll.done(identity)
    poll.observe(recovery)
    assert poll.pending()==[]
    # A delayed expired recovery did not clear risk: next fresh NORMAL retains
    # the original source episode, rather than leaving Danger stuck forever.
    next_time=now+timedelta(seconds=2)
    poll.observe(SourceResult(source='jps',status='current',checked_at=next_time,resolved={'jps:station':next_time}))
    assert len(poll.pending())==1 and poll.pending()[0][1]['source_episode_id']==original


def test_official_recovery_never_clears_simulated_source(domain):
    client,risk,_=domain
    client.collection(risk.shops).document('demo').set({'is_demo':True,'recipients':[{'telegram_chat_id':1,'role':'owner'}]})
    simulated={**event('danger'),'is_demo':True}
    assert risk.apply_event(simulated,'demo')
    assert risk.recover_official(simulated['source_key'],simulated['source_episode_id'],datetime.now(UTC))==0
    assert risk.get('demo').active_danger and not risk.get('demo').official_danger
    assert not risk.owner_declared_recovery('demo',1)
    assert risk.reset_demo('demo') and not risk.get('demo').active_danger


def test_recovered_watermark_suppresses_old_pending_intent_and_prepared_delivery(domain):
    from api.polling import PollService
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.tests.test_dispatch import Bot,Sinks
    client,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=3)
    warning=Warning(source='jps',source_id='station',level='danger',observed_at=now,geography=Geography(latitude=3.,longitude=101.),reason='Official Danger')
    poll.observe(SourceResult(source='jps',status='current',checked_at=now,warnings=(warning,)))
    request=EventRequest.model_validate_json(poll.pending()[0][1]['request_json'])
    # Model a crash after preparation, before external send; source progress
    # must also guard that already-prepared outbox on restart.
    prepared={**request.model_dump(), 'event_id':'prepared','is_demo':False,'created_at':now,'processing_started_at':now}
    prepared['episode_id']=risk.apply_event(prepared,'shop')
    normal_at=now+timedelta(seconds=1)
    poll.observe(SourceResult(source='jps',status='current',checked_at=normal_at,resolved={'jps:station':normal_at}))
    assert risk.claim_delivery('shop',prepared)==('superseded',None)
    assert risk.apply_event_decision(prepared,'shop').reason=='resolved_source_episode'
    # Also cover crash-before-any-shop-risk-persistence: recovery first cannot
    # rely on an existing shop risk document to prevent the old intent.
    client.collection(risk.risks).document('shop').delete()
    client.collection(risk.shops).document('shop').update({'active_danger':False})
    store=FirestoreDispatchStore(client,events=risk.risks+'events',alerts=risk.risks+'alerts',shops=risk.shops)
    bot=Bot();dispatch=DispatchService(store,bot,Sinks(),hash_salt='synthetic',active_risk=risk)
    async def fetcher(**kwargs):return (SourceResult(source='jps',status='empty',checked_at=datetime.now(UTC)),SourceResult(source='met',status='unsupported',checked_at=datetime.now(UTC)))
    async def run():
        # Exercise both arbitrary intent orders.
        original=poll.pending
        for reverse in (False,True):
            for document in client.collection(poll.intents).stream():document.reference.update({'status':'pending'})
            poll.pending=lambda:sorted(original(),key=lambda row:row[1]['kind'],reverse=reverse)
            await PollService(poll,dispatch,risk,fetcher=fetcher).poll()
            assert bot.messages==[]
        later=warning.model_copy(update={'level':'warning','observed_at':now+timedelta(seconds=2)})
        poll.observe(SourceResult(source='jps',status='current',checked_at=later.observed_at,warnings=(later,)))
        pending=original();assert len(pending)==1
        fresh=EventRequest.model_validate_json(pending[0][1]['request_json'])
        assert fresh.source_episode_id!=request.source_episode_id
        await PollService(poll,dispatch,risk,fetcher=fetcher).poll()
        assert len(bot.messages)==1
    try:asyncio.run(run())
    finally:
        for collection in (store.events,store.plans,store.alerts,store.deliveries):
            for document in client.collection(collection).stream():document.reference.delete()


@pytest.mark.parametrize('reverse',[False,True])
def test_pending_source_escalation_only_delivers_highest_watermark(domain,reverse):
    from api.polling import PollService
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.tests.test_dispatch import Bot,Sinks
    client,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=2)
    warning=Warning(source='jps',source_id='station',level='warning',observed_at=now,geography=Geography(latitude=3.,longitude=101.),reason='Official Warning')
    poll.observe(SourceResult(source='jps',status='current',checked_at=now,warnings=(warning,)))
    first=EventRequest.model_validate_json(poll.pending()[0][1]['request_json'])
    danger=warning.model_copy(update={'level':'danger','observed_at':now+timedelta(seconds=1)})
    poll.observe(SourceResult(source='jps',status='current',checked_at=danger.observed_at,warnings=(danger,)))
    assert len(poll.pending())==2 and not client.collection(risk.risks).document('shop').get().exists
    old_event={**first.model_dump(),'event_id':'old-warning','is_demo':False,'created_at':now}
    assert risk.apply_event_decision(old_event,'shop').reason=='superseded_source_watermark'
    assert risk.claim_delivery('shop',old_event)==('superseded',None)
    original=poll.pending
    poll.pending=lambda:sorted(original(),key=lambda row:EventRequest.model_validate_json(row[1]['request_json']).level,reverse=reverse)
    store=FirestoreDispatchStore(client,events=risk.risks+'events',alerts=risk.risks+'alerts',shops=risk.shops)
    bot=Bot();dispatch=DispatchService(store,bot,Sinks(),hash_salt='synthetic',active_risk=risk)
    async def fetcher(**kwargs):return (SourceResult(source='jps',status='empty',checked_at=datetime.now(UTC)),SourceResult(source='met',status='unsupported',checked_at=datetime.now(UTC)))
    try:
        asyncio.run(PollService(poll,dispatch,risk,fetcher=fetcher).poll())
        assert len(bot.messages)==1 and 'DANGER' in bot.messages[0][1]
        assert poll.pending()==[]
    finally:
        for collection in (store.events,store.plans,store.alerts,store.deliveries):
            for document in client.collection(collection).stream():document.reference.delete()
