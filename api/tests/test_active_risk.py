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
    risk.source_recoveries=poll.recoveries
    client.collection(risk.shops).document('shop').set({'shop_name':'Synthetic','lat':3.,'lng':101.,'is_demo':False,'recipients':[{'telegram_chat_id':1,'language':'en','role':'owner'}]})
    try:yield client,risk,poll
    finally:
        for collection in (risk.risks,risk.shops,risk.deliveries,risk.current_actions,poll.states,poll.intents,poll.status,poll.recoveries):
            for document in client.collection(collection).stream():document.reference.delete()
        client.close()


def event(level='warning',source='jps',key='jps:station',episode='official-one',at=None):
    now=at or datetime.now(UTC)
    return dict(event_id=uuid4().hex,source=source,source_key=key,source_episode_id=episode,source_observed_at=now,
                level=level,is_demo=False,created_at=now,processing_started_at=now)


def test_atomic_poll_concurrency_restart_and_recovery(domain):
    client,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=2)
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
    poll.observe(SourceResult(source='jps',status='current',checked_at=now+timedelta(seconds=1),resolved={'jps:station':now+timedelta(seconds=1)}))
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


@pytest.mark.parametrize('new_first',[False,True,'concurrent'])
@pytest.mark.parametrize('other_source',[False,True])
def test_explicit_source_recovery_between_dangers_preserves_new_attribution_and_shop_scope(domain,new_first,other_source):
    client,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=5)
    source='jps:station'
    def observe(level,at):
        warning=Warning(source='jps',source_id='station',level=level,observed_at=at,geography=Geography(latitude=3.,longitude=101.),reason='Official indicator')
        poll.observe(SourceResult(source='jps',status='current',checked_at=at,warnings=(warning,)))
        intent=next(value for _,value in poll.pending() if value['kind']=='event' and EventRequest.model_validate_json(value['request_json']).source_observed_at==at)
        request=EventRequest.model_validate_json(intent['request_json'])
        return {**request.model_dump(),'event_id':request.request_id,'is_demo':False,'created_at':at}
    old=observe('danger',now)
    original_shop_episode=risk.apply_event(old,'shop')
    if other_source:risk.apply_event(event('warning',key='jps:other',episode='other',at=now),'shop')
    normal_at=now+timedelta(seconds=1)
    poll.observe(SourceResult(source='jps',status='current',checked_at=normal_at,resolved={source:normal_at}))
    new=observe('danger',now+timedelta(seconds=2))
    assert new['source_episode_id']!=old['source_episode_id']
    if new_first=='concurrent':
        with ThreadPoolExecutor(max_workers=2) as executor:
            applied=executor.submit(risk.apply_event,new,'shop')
            recovered=executor.submit(risk.recover_official,source,old['source_episode_id'],normal_at)
            new_shop_episode=applied.result();recovered.result()
    elif new_first:
        new_shop_episode=risk.apply_event(new,'shop')
        risk.recover_official(source,old['source_episode_id'],normal_at)
    else:
        risk.recover_official(source,old['source_episode_id'],normal_at)
        new_shop_episode=risk.apply_event(new,'shop')
    assert risk.get('shop').active_danger
    record=client.collection(risk.risks).document('shop').get().to_dict()
    assert record['sources'][source]['source_episode_id']==new['source_episode_id']
    assert (new_shop_episode==original_shop_episode) is other_source
    final_normal=now+timedelta(seconds=3)
    poll.observe(SourceResult(source='jps',status='current',checked_at=final_normal,resolved={source:final_normal}))
    assert risk.recover_official(source,new['source_episode_id'],final_normal)==1
    assert not risk.get('shop').active_danger
    assert bool(risk.get('shop').episode_id) is other_source


def test_no_recovery_receipt_from_stale_or_missing_observation(domain):
    client,risk,poll=domain;now=datetime.now(UTC)
    active=event('danger',at=now-timedelta(seconds=1))
    original=risk.apply_event(active,'shop')
    poll.observe(SourceResult(source='jps',status='stale',checked_at=now,resolved={'jps:station':now}))
    poll.observe(SourceResult(source='jps',status='empty',checked_at=now))
    assert list(client.collection(poll.recoveries).stream())==[]
    later=event('warning',episode='unproven-new-gap',at=now)
    assert risk.apply_event(later,'shop')==original and risk.get('shop').active_danger
    record=client.collection(risk.risks).document('shop').get().to_dict()
    assert record['sources']['jps:station']['source_episode_id']=='official-one'


@pytest.mark.parametrize('incoming_source',['shop_report','jps'])
def test_aged_recovery_receipt_cannot_clear_official_danger_on_unrelated_event(domain,incoming_source):
    from hashlib import sha256
    client,risk,poll=domain;now=datetime.now(UTC)
    original=risk.apply_event(event('danger',at=now-timedelta(seconds=1)),'shop')
    reference=client.collection(risk.risks).document('shop')
    record=reference.get().to_dict();old_time=now-timedelta(days=1,seconds=2)
    record['sources']['jps:station']['observed_at']=old_time;reference.set(record)
    receipt_id=sha256(b'jps:station:official-one').hexdigest()
    client.collection(poll.recoveries).document(receipt_id).set({'source_key':'jps:station','source_episode_id':'official-one',
        'observed_at':old_time+timedelta(seconds=1),'checked_at':old_time+timedelta(seconds=1)})
    incoming=event('warning',incoming_source,key=None if incoming_source=='shop_report' else 'jps:other',episode='other',at=now)
    assert risk.apply_event(incoming,'shop')==original
    state=risk.get('shop')
    assert state.active_danger and state.official_danger


def test_aged_recovery_preserves_latch_but_attributes_new_same_source_danger(domain):
    from hashlib import sha256
    client,risk,poll=domain;now=datetime.now(UTC)-timedelta(seconds=2)
    original=risk.apply_event(event('danger',at=now),'shop')
    ref=client.collection(risk.risks).document('shop');record=ref.get().to_dict();yesterday=now-timedelta(days=1)
    record['sources']['jps:station']['observed_at']=yesterday;ref.set(record)
    receipt_id=sha256(b'jps:station:official-one').hexdigest()
    client.collection(poll.recoveries).document(receipt_id).set({'source_key':'jps:station','source_episode_id':'official-one',
        'observed_at':yesterday+timedelta(seconds=1),'checked_at':yesterday+timedelta(seconds=1)})
    incoming=event('danger',episode='new-current',at=now+timedelta(seconds=1))
    assert risk.apply_event(incoming,'shop')==original
    state=risk.get('shop');assert state.active_danger and state.official_danger
    rebound=ref.get().to_dict()['sources']['jps:station']
    assert rebound['source_episode_id']=='new-current' and rebound['carried_danger_from']=='official-one'
    assert risk.recover_official('jps:station','new-current',datetime.now(UTC))==1
    assert not risk.get('shop').active_danger


def test_nondefault_official_cutoff_propagates_parser_poll_and_risk_factory(domain,monkeypatch):
    from api.polling import create_poll_service
    from api.tools.datagov import parse_flood,DEFAULT_MAX_AGE
    import api.tools.firestore as factory
    import api.dispatch as dispatch_module
    client,risk,poll=domain;now=datetime.now(UTC)
    calls=[]
    class Dispatch:
        async def process(self,request):calls.append(request);return {'status':'complete','event_id':'synthetic'}
    monkeypatch.setattr(factory,'create_firestore_client',lambda settings:client)
    monkeypatch.setattr(dispatch_module,'create_dispatch_service',lambda settings:Dispatch())
    service=create_poll_service(Settings(gcp_project='highground-task10-tests',official_max_age_minutes=5))
    assert service.store.max_age==service.risk.max_age==timedelta(minutes=5)
    service.store.states=poll.states;service.store.intents=poll.intents;service.store.status=poll.status;service.store.recoveries=poll.recoveries
    service.risk.risks=risk.risks;service.risk.shops=risk.shops;service.risk.source_states=poll.states;service.risk.source_recoveries=poll.recoveries
    observed=now-timedelta(minutes=6)
    row={'station_id':'station','latitude':3.,'longitude':101.,'district':'Test','state':'Test','water_level_current':1.,
         'water_level_indicator':'DANGER','water_level_update_datetime':observed.isoformat(),'station_status':'ON','water_level_status':'ON'}
    async def fetcher(*,client,max_age=DEFAULT_MAX_AGE):
        return (parse_flood([row],now=now,max_age=max_age),SourceResult(source='met',status='unsupported',checked_at=now))
    service.fetcher=fetcher
    result=asyncio.run(service.poll())
    assert calls==[] and result['processed_intents']==0
    assert service.risk.apply_event_decision(event('danger',at=observed),'shop').reason=='expired'
    assert service.risk.claim_delivery('shop',event('danger',at=observed))==('superseded',None)
    fresh=event('danger',at=now-timedelta(minutes=7))
    # Existing persisted Danger outlives freshness; stale recovery never clears it.
    risk.apply_event(fresh,'shop')
    assert service.risk.recover_official('jps:station','official-one',now-timedelta(minutes=6))==0
    assert service.risk.get('shop').active_danger


def test_tightened_cutoff_preserves_historical_acceptance_without_clearing_danger(domain):
    from hashlib import sha256
    client,risk,poll=domain;now=datetime.now(UTC)
    original=risk.apply_event(event('danger',at=now-timedelta(minutes=60)),'shop')
    receipt_id=sha256(b'jps:station:official-one').hexdigest()
    client.collection(poll.recoveries).document(receipt_id).set({'source_key':'jps:station','source_episode_id':'official-one',
        'observed_at':now-timedelta(minutes=40),'checked_at':now-timedelta(minutes=5),'accepted_max_age_seconds':5400})
    tightened=ActiveRiskStore(client,risks=risk.risks,shops=risk.shops,source_states=poll.states,
                              source_recoveries=poll.recoveries,max_age=Settings(official_max_age_minutes=30).official_max_age)
    new=event('danger',episode='new-current',at=now-timedelta(minutes=1))
    assert tightened.apply_event(new,'shop')==original
    assert tightened.get('shop').active_danger
    bound=client.collection(risk.risks).document('shop').get().to_dict()['sources']['jps:station']
    assert bound['source_episode_id']=='new-current' and bound['carried_danger_from']=='official-one'
    assert tightened.recover_official('jps:station','new-current',datetime.now(UTC))==1
    assert not tightened.get('shop').active_danger


def test_official_cutoff_bounds_and_environment(monkeypatch):
    from api.config import load_settings
    for value in (0,91,True,1.5):
        with pytest.raises(ValueError):Settings(official_max_age_minutes=value)
    monkeypatch.setenv('OFFICIAL_MAX_AGE_MINUTES','30')
    assert load_settings().official_max_age==timedelta(minutes=30)
    monkeypatch.setenv('OFFICIAL_MAX_AGE_MINUTES','unbounded')
    with pytest.raises(ValueError):load_settings()


def test_dispatch_mutating_risk_factory_uses_configured_cutoff(domain,monkeypatch):
    import api.tools.firestore as factory
    import api.tools.cloud_events as cloud
    import api.tools.telegram as telegram
    from api.dispatch import create_dispatch_service
    from api.tests.test_dispatch import Sinks,Bot
    client,*_=domain
    monkeypatch.setattr(factory,'create_firestore_client',lambda settings:client)
    monkeypatch.setattr(cloud,'create_event_sinks',lambda settings:Sinks())
    monkeypatch.setattr(telegram,'TelegramAPI',lambda token:Bot())
    service=create_dispatch_service(Settings(gcp_project='highground-task10-tests',hash_salt='synthetic',telegram_bot_token='synthetic',official_max_age_minutes=5))
    assert service.active_risk.max_age==timedelta(minutes=5)
