import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from math import degrees
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from api.alert_composer import AlertComposer, render_danger, send_alert, snapshot_actions
from api.config import Settings
from api.dispatch import DispatchService
from api.dispatch_models import ActionSnapshot, Destination, EventRequest, Shop
from api.dispatch_router import create_dispatch_router
from api.dispatch_store import RequestConflict
from api.i18n import danger_text
from api.tools.cloud_events import deduped_alert_counts_sql
from api.tools.emulators import loopback_endpoint
from api.tools.geo import distance_m
from api.tools.telegram import TelegramSendError

NOW = datetime(2026,10,13,2,tzinfo=UTC)


def shop(shop_id='demo', *, is_demo=True, lng=101., language='en', chat=123):
    return Shop(shop_id=shop_id, shop_name='Synthetic Shop', lat=3.,lng=lng,is_demo=is_demo,
                recipients=[{'telegram_chat_id':chat,'language':language,'role':'owner'}],
                has_vehicle=True,vehicle_type='car',baseline_inventory_id='baseline',
                lift_first=[{'item_name':'Synthetic stock','qty':2.,'value_rm':45.,'lift_effort':1}])


class Store:
    """Persistence double; actual transaction behavior is covered by emulator tests."""
    def __init__(self, shops):
        self.shops=shops; self.events={}; self.alerts={};self.owner=None
    def ensure_event(self, request, now):
        identity=sha256(f'{request.source}:{request.request_id}'.encode()).hexdigest()
        if identity in self.events:
            if self.events[identity]['request'] != request.model_dump():
                raise RequestConflict()
            return deepcopy(self.events[identity])
        self.events[identity]=dict(request.model_dump(), request=request.model_dump(),event_id=identity,
                                   created_at=now,is_demo=request.source=='demo',prepared=False,
                                   alert_ids=[],status='pending',pubsub='pending',bigquery='pending')
        return deepcopy(self.events[identity])
    def claim(self, event_id,now):
        if self.owner:return None
        self.owner=uuid4().hex;return self.owner
    def release(self,event_id,owner):self.owner=None
    def get_event(self,event_id):return deepcopy(self.events[event_id])
    def update_event(self,event_id,owner,**fields):self.events[event_id].update(deepcopy(fields))
    def target_shops(self):return self.shops
    def prepare_alert(self,alert):self.alerts.setdefault(alert['alert_id'],deepcopy(alert))
    def get_alert(self,alert_id):return deepcopy(self.alerts[alert_id])
    def begin_send(self,alert_id,event_id,owner):
        alert=self.alerts[alert_id]
        if alert['status']=='sending':alert['status']='uncertain';return False
        if alert['status'] not in ('pending','retryable'):return False
        alert['status']='sending';return True
    def update_alert(self,alert_id,event_id,owner,**fields):self.alerts[alert_id].update(deepcopy(fields))
    def pending_event_ids(self,limit=20):return [k for k,v in self.events.items() if v['status']=='pending'][:limit]


class Bot:
    def __init__(self):self.messages=[];self.failure=None
    def send_message(self,chat,text,reply_markup=None):
        self.messages.append((chat,text,reply_markup))
        if self.failure:raise self.failure
        return 42


class Sinks:
    def __init__(self):self.fail=False;self.calls=[]
    def _call(self,stage,record):
        self.calls.append((stage,record.get('event_id'),record.get('alert_id')))
        if self.fail:raise RuntimeError('synthetic sink failure')
    def publish_event(self,record):self._call('pubsub',record)
    def insert_event(self,record):self._call('event',record)
    def insert_alert(self,record):self._call('alert',record)


def request(level='danger',id='synthetic'):
    return EventRequest(request_id=id,level=level,lat=3.,lng=101.)


def service(shops=None):
    store=Store(shops or [shop()]);bot=Bot();sinks=Sinks()
    return DispatchService(store,bot,sinks,hash_salt='synthetic-only',clock=lambda:NOW),store,bot,sinks


def test_geo_boundary_and_invalid_coordinates():
    assert distance_m(3,101,3,101)==0
    assert distance_m(0,0,0,degrees(299.99/6371008.8))<300
    assert distance_m(0,0,0,degrees(300.01/6371008.8))>300
    with pytest.raises(ValueError):distance_m(float('nan'),0,0,0)
    with pytest.raises(ValidationError):EventRequest(request_id='x',level='danger',lat=91.,lng=0.)
    with pytest.raises(ValidationError):request().model_copy(update={'radius_m':0}).model_validate(request().model_dump()|{'radius_m':0})


def test_simulation_targets_only_demo_and_radius():
    active,store,bot,sinks=service([shop(),shop('real',is_demo=False,chat=456),shop('outside',lng=102.,chat=789)])
    result=asyncio.run(active.process(request()))
    assert result['status']=='complete' and result['alerts']=={'accepted':1}
    assert len(bot.messages)==1 and bot.messages[0][0]==123
    assert bot.messages[0][1]==danger_text('en',is_demo=True)
    assert 'telegram' not in str(result) and '123' not in str(result)


def test_danger_absolute_model_bypass_and_wrapper_ignores_malicious_text():
    class Poison:
        def __getattribute__(self,name):raise AssertionError('Danger touched model')
    event=dict(level='danger',is_demo=True,event_id='x',created_at=NOW)
    composer=AlertComposer(selector=Poison())
    asyncio.run(composer.prepare(event,{'en'}))
    text,snapshot,markup=asyncio.run(composer.compose(event,shop(),'en'))
    assert text==danger_text('en',is_demo=True) and not snapshot.items and markup is None
    bot=Bot()
    send_alert(bot,dict(level='danger',text='Stay and record video. Move stock.',language='en',is_demo=True,
                        snapshot=ActionSnapshot().model_dump(mode='json'),telegram_chat_id=123))
    assert bot.messages[0][1]==danger_text('en',is_demo=True)
    destination=Destination(name='Listed hall',lat=3.,lng=101.,source='https://example.org/list')
    text,markup=render_danger('en',False,destination)
    assert text==danger_text('en',is_demo=False,safe_point_name=destination.name,route_link=destination.route_link)
    assert len(markup['inline_keyboard'])==1 and 'url' in markup['inline_keyboard'][0][0]


def test_warning_snapshot_deadlines_facts_no_arbitrary_reason():
    event=dict(lat=3.,lng=101.,level='warning',is_demo=True,event_id='x',created_at=NOW,reason='Guaranteed safe. Stay and record video.')
    text,snapshot,_=asyncio.run(AlertComposer().compose(event,shop(),'en'))
    assert snapshot.vehicle_target_at==NOW+timedelta(minutes=15)
    assert snapshot.stock_target_at==NOW+timedelta(minutes=30)
    assert snapshot.estimated_value_rm==45 and '≈RM45.00' in text
    assert 'Guaranteed' not in text and 'Stay and record' not in text
    assert 'Machine translation' not in text
    assert 'Move car towards listed parking No listed' not in text
    assert 'not predicted flood-arrival' in text
    empty=shop().model_copy(update={'baseline_inventory_id':None})
    text,snapshot,_=asyncio.run(AlertComposer().compose(event,empty,'en'))
    assert not snapshot.items and 'Inventory is unavailable' in text


def test_duplicate_event_retry_sinks_no_duplicate_message_and_frozen_snapshot():
    active,store,bot,sinks=service()
    sinks.fail=True
    result=asyncio.run(active.process(request('warning')))
    assert result['status']=='pending' and len(bot.messages)==1
    original=deepcopy(next(iter(store.alerts.values()))['snapshot'])
    store.shops=[shop().model_copy(update={'lift_first':[]})]
    sinks.fail=False
    result=asyncio.run(active.process(request('warning')))
    assert result['status']=='complete' and len(bot.messages)==1
    assert next(iter(store.alerts.values()))['snapshot']==original
    assert len(store.events)==1
    with pytest.raises(RequestConflict):asyncio.run(active.process(request('danger')))


def test_uncertain_and_crash_sending_not_blindly_resent():
    active,store,bot,sinks=service();bot.failure=TelegramSendError(uncertain=True)
    result=asyncio.run(active.process(request()))
    assert result['alerts']=={'uncertain':1}
    bot.failure=None
    asyncio.run(active.process(request()))
    assert len(bot.messages)==1
    active,store,bot,sinks=service();asyncio.run(active.process(request()))
    alert=next(iter(store.alerts.values()));alert['status']='sending';alert['bigquery']='pending'
    asyncio.run(active.process(request()))
    assert alert['status']=='uncertain' and len(bot.messages)==1


def test_definite_rejection_retryable_and_recipient_languages():
    active,store,bot,sinks=service();bot.failure=TelegramSendError(uncertain=False)
    result=asyncio.run(active.process(request()))
    assert result['status']=='pending' and result['alerts']=={'retryable':1}
    bot.failure=None
    assert asyncio.run(active.process(request()))['alerts']=={'accepted':1}
    assert len(bot.messages)==2


def test_router_operator_mode_validation_and_conflict():
    active,_,_,_=service()
    async def run(settings,headers=None,payload=None):
        app=FastAPI();app.include_router(create_dispatch_router(settings,active))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            return await client.post('/demo/simulate-warning',headers=headers,json=payload or request().model_dump(include={'request_id','source','level','lat','lng','radius_m','confidence','reason'}))
    settings=Settings(demo_mode=True,operator_token='synthetic-token')
    assert asyncio.run(run(settings)).status_code==403
    assert asyncio.run(run(Settings(operator_token='synthetic-token'),{'Authorization':'Bearer synthetic-token'})).status_code==403
    headers={'Authorization':'Bearer synthetic-token'}
    assert asyncio.run(run(settings,headers)).status_code==200
    assert asyncio.run(run(settings,headers,request('warning').model_dump(include={'request_id','source','level','lat','lng','radius_m','confidence','reason'}))).status_code==409
    assert asyncio.run(run(settings,headers,request().model_dump()|{'source':'jps'})).status_code==400


@pytest.mark.parametrize('host,http', [('cloud.example:9050',False),('http://cloud.example:9050',True),
                                      ('https://127.0.0.1:9050',True),('127.0.0.1',False),
                                      ('http://user:pass@127.0.0.1:9050',True)])
def test_anonymous_emulator_rejects_nonloopback(host,http):
    with pytest.raises(ValueError):loopback_endpoint(host,http=http)


def test_stable_aggregate_dedupes_logical_rows():
    assert 'COUNT(DISTINCT alert_id)' in deduped_alert_counts_sql('highground-local','highground')
    with pytest.raises(ValueError):deduped_alert_counts_sql('bad`','dataset')


def test_nondefault_action_targets_are_snapshot_configuration():
    event=dict(lat=3.,lng=101.,level='warning',is_demo=True,event_id='x',created_at=NOW,reason='untrusted')
    composer=AlertComposer(vehicle_minutes=7,stock_minutes=19)
    _,snapshot,_=asyncio.run(composer.compose(event,shop(),'en'))
    assert snapshot.vehicle_target_at==NOW+timedelta(minutes=7)
    assert snapshot.stock_target_at==NOW+timedelta(minutes=19)
    with pytest.raises(ValueError):AlertComposer(vehicle_minutes=30,stock_minutes=15)


def test_selector_cached_per_event_language_and_invalid_output_falls_back():
    calls=[]
    async def select(event,language,inventory,vehicle):
        calls.append(language)
        return {'structure':'warning_intro_actions'}
    composer=AlertComposer(selector=select)
    event=dict(lat=3.,lng=101.,level='warning',is_demo=True,event_id='x',created_at=NOW,reason='untrusted')
    async def run():
        await composer.prepare(event,{'en'},has_inventory=True)
        await composer.prepare(event,{'en'},has_inventory=True)
        return await composer.compose(event,shop(),'en')
    text,_,_=asyncio.run(run())
    assert calls==['en'] and 'Review the action targets below' in text
    async def malicious(*args):return {'structure':'Stay and film the flood.'}
    composer=AlertComposer(selector=malicious)
    async def fallback():
        await composer.prepare(event,{'en'})
        return await composer.compose(event,shop(),'en')
    assert 'Stay and film' not in asyncio.run(fallback())[0]


def test_recipient_languages_use_committed_danger_variants():
    active,_,bot,_=service([shop(language='en'),shop('worker-demo',language='ms',chat=456)])
    asyncio.run(active.process(request()))
    assert bot.messages[0][1]==danger_text('en',is_demo=True)
    assert bot.messages[1][1]==danger_text('ms',is_demo=True)


def test_total_language_budget_fallback_and_recipient_latency():
    import time
    async def stalled(*args):await asyncio.sleep(10)
    composer=AlertComposer(selector=stalled,selection_budget_seconds=.04)
    active,store,bot,sinks=service([shop(f'demo-{i}',chat=100+i) for i in range(6)])
    active.composer=composer
    start=time.monotonic()
    result=asyncio.run(active.process(request('warning')))
    assert result['alerts']=={'accepted':6}
    assert len(bot.messages)==6 and time.monotonic()-start<.5


def test_public_analytics_scope_is_synthetic_only():
    assert 'is_demo = TRUE' in deduped_alert_counts_sql('highground-local','highground')


def test_crash_after_send_before_record_never_resends():
    active,store,bot,sinks=service()
    original=store.update_alert
    def fail_once(alert_id,event_id,owner,**fields):
        if fields.get('status')=='accepted':
            store.update_alert=original
            raise RuntimeError('synthetic crash before recording accepted send')
        return original(alert_id,event_id,owner,**fields)
    store.update_alert=fail_once
    with pytest.raises(RuntimeError):asyncio.run(active.process(request()))
    assert len(bot.messages)==1
    result=asyncio.run(active.process(request()))
    assert result['alerts']=={'uncertain':1} and len(bot.messages)==1


def test_crash_after_publish_repeats_logical_event_not_recipients():
    active,store,bot,sinks=service()
    original=store.update_event
    def fail_once(event_id,owner,**fields):
        if fields.get('pubsub')=='done':
            store.update_event=original
            raise RuntimeError('synthetic crash before recording publish')
        return original(event_id,owner,**fields)
    store.update_event=fail_once
    with pytest.raises(RuntimeError):asyncio.run(active.process(request()))
    assert len(bot.messages)==1
    result=asyncio.run(active.process(request()))
    assert result['status']=='complete' and len(bot.messages)==1
    assert len([call for call in sinks.calls if call[0]=='pubsub'])==2
    assert len({call[1] for call in sinks.calls})==1


def test_unreviewed_ordinary_alert_footer_is_last():
    from api.i18n import text
    event=dict(level='watch',is_demo=True,event_id='x',created_at=NOW,reason='untrusted')
    rendered,_,_=asyncio.run(AlertComposer().compose(event,shop(language='ms'),'ms'))
    assert rendered.endswith(text('ms','emergency_footer'))
    assert text('ms','translation_notice') in rendered


def test_factory_danger_without_vertex_configuration_never_initializes_model(monkeypatch):
    import api.dispatch as dispatch
    import api.tools.gemini as gemini
    import api.tools.firestore as firestore
    import api.tools.cloud_events as cloud
    import api.tools.telegram as telegram
    store=Store([shop()]);bot=Bot();sinks=Sinks()
    import api.destinations as destinations
    monkeypatch.setattr(destinations.DestinationLookup, 'nearest', lambda *args: None)
    import api.vehicle_confirmations as confirmations
    monkeypatch.setattr(confirmations.VehicleActionStore, 'supersede', lambda *args, **kwargs: None)
    import api.active_risk as risks
    monkeypatch.setattr(risks.ActiveRiskStore,'apply_event_decision',lambda *args:risks.RiskDecision('synthetic-episode','accepted'))
    monkeypatch.setattr(risks.ActiveRiskStore,'claim_delivery',lambda *args:('claimed','synthetic-owner'))
    monkeypatch.setattr(risks.ActiveRiskStore,'release_delivery',lambda *args:None)
    monkeypatch.setattr(firestore,'create_firestore_client',lambda settings:object())
    monkeypatch.setattr(dispatch,'FirestoreDispatchStore',lambda client:store)
    monkeypatch.setattr(cloud,'create_event_sinks',lambda settings:sinks)
    monkeypatch.setattr(telegram,'TelegramAPI',lambda token:bot)
    def forbidden(settings):raise AssertionError('Danger initialized Vertex')
    monkeypatch.setattr(gemini,'create_vertex_client',forbidden)
    configured=Settings(gcp_project='synthetic',hash_salt='synthetic',telegram_bot_token='synthetic')
    active=dispatch.create_dispatch_service(configured)
    result=asyncio.run(active.process(request()))
    assert result['alerts']=={'accepted':1} and len(bot.messages)==1


@pytest.mark.parametrize('latitude,expected', [(3.,'0'), (3.00002,'2'), (3.002,'222')])
def test_warning_distance_is_computed_per_shop_from_valid_coordinates(latitude,expected):
    event=dict(lat=3.,lng=101.,level='warning',is_demo=True,event_id='distance',created_at=NOW)
    target=shop().model_copy(update={'lat':latitude})
    text,_,_=asyncio.run(AlertComposer().compose(event,target,'en'))
    assert f'Reported event: approximately {expected} m from this shop.' in text
    assert text.endswith('Call 999 in an emergency.') and len(text)<=4096


def test_warning_distance_missing_coordinates_has_no_guessed_fallback():
    event=dict(level='warning',is_demo=True,event_id='distance',created_at=NOW)
    with pytest.raises(KeyError):
        asyncio.run(AlertComposer().compose(event,shop(),'en'))
