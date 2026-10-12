"""Real dispatch/action stores across Danger and queued official recovery."""
import asyncio
from datetime import UTC,datetime,timedelta
import pytest
from api.tests.test_active_risk import domain
from api.tests.test_dispatch import Sinks
from api.dispatch import DispatchService
from api.dispatch_store import FirestoreDispatchStore
from api.dispatch_models import EventRequest,ActionSnapshot
from api.models import Warning,Geography,SourceResult
from api.vehicle_confirmations import VehicleActionStore
from api.stock_confirmations import StockActionStore
from api.agents.sessions import session_user_id


@pytest.fixture
def pipeline(domain):
    client,risk,poll=domain;prefix=risk.risks
    dispatch=FirestoreDispatchStore(client,events=prefix+'events',alerts=prefix+'alerts',shops=risk.shops)
    vehicles=VehicleActionStore(client,actions=prefix+'vehicles',current=risk.current_actions,confirmations=prefix+'confirmations',alerts=dispatch.alerts,shops=risk.shops)
    stocks=StockActionStore(client,actions=prefix+'stocks',confirmations=vehicles.confirmations,alerts=dispatch.alerts,shops=risk.shops,risks=risk.risks)
    client.collection(risk.shops).document('shop').update({'has_vehicle':True,'vehicle_type':'car','baseline_inventory_id':'baseline',
        'lift_first':[{'item_name':'Rice','qty':2.,'value_rm':20.,'lift_effort':1}]})
    class Sender:
        def __init__(self):self.messages=[]
        def send_message(self,chat,text,reply_markup=None):self.messages.append((chat,text,reply_markup));return len(self.messages)
    bot=Sender();service=DispatchService(dispatch,bot,Sinks(),hash_salt='salt',active_risk=risk,vehicle_actions=vehicles,stock_actions=stocks)
    now=datetime.now(UTC)-timedelta(seconds=10)
    def emit(station,level,offset):
        at=now+timedelta(seconds=offset)
        warning=Warning(source='jps',source_id=station,level=level,observed_at=at,geography=Geography(latitude=3.,longitude=101.),reason='Official indicator')
        poll.observe(SourceResult(source='jps',status='current',checked_at=at,warnings=(warning,)))
        request=next(EventRequest.model_validate_json(value['request_json']) for _,value in poll.pending()
                     if value['kind']=='event' and EventRequest.model_validate_json(value['request_json']).source_observed_at==at)
        result=asyncio.run(service.process(request))
        alert=dispatch.get_alert(dispatch.get_event(result['event_id'])['alert_ids'][0])
        return request,alert
    def normal(offset):
        at=now+timedelta(seconds=offset)
        poll.observe(SourceResult(source='jps',status='current',checked_at=at,resolved={'jps:A':at}))
        return at
    def confirm(store,alert,kind):
        snapshot=ActionSnapshot.model_validate(alert['snapshot'])
        identity=getattr(snapshot,kind+'_action_id')
        return store.record(identity,sender_chat_id=1,message_chat_id=1,message_id=alert['message_id'],sender_hash=session_user_id(1,'salt'),now=datetime.now(UTC))[0]
    try:yield client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm
    finally:
        for collection in (dispatch.events,dispatch.plans,dispatch.alerts,dispatch.deliveries,vehicles.actions,vehicles.confirmations,stocks.actions):
            for document in client.collection(collection).stream():document.reference.delete()


@pytest.mark.parametrize('other_source',[False,True])
def test_queued_recovery_releases_new_vehicle_action_and_never_releases_old_button(pipeline,other_source):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    old_request,old=emit('A','warning',0)
    if other_source:emit('B','watch',1)
    danger,_=emit('A','danger',2)
    assert confirm(vehicles,old,'vehicle')=='superseded'
    at=normal(3)
    new_request,new=emit('A','warning',4)
    assert not risk.get('shop').active_danger
    assert risk.recover_official('jps:A',danger.source_episode_id,at)==0
    new_snapshot=ActionSnapshot.model_validate(new['snapshot'])
    buttons=[button for row in new['reply_markup']['inline_keyboard'] for button in row]
    assert any(button.get('callback_data')=='vehicle:'+new_snapshot.vehicle_action_id for button in buttons)
    assert confirm(vehicles,new,'vehicle')=='recorded'
    assert confirm(vehicles,old,'vehicle')=='superseded'
    assert confirm(stocks,new,'stock')=='recorded'


@pytest.mark.parametrize('queued',[False,True])
def test_old_stock_action_cannot_revive_in_continuing_episode_and_new_action_works(pipeline,queued):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    _,old=emit('A','warning',0)
    original_episode=risk.get('shop').episode_id
    emit('B','watch',1)
    danger,_=emit('A','danger',2)
    assert confirm(stocks,old,'stock')=='superseded'
    at=normal(3)
    if not queued:assert risk.recover_official('jps:A',danger.source_episode_id,at)==1
    _,new=emit('A','warning',4)
    assert risk.get('shop').episode_id==original_episode and not risk.get('shop').active_danger
    assert risk.recover_official('jps:A',danger.source_episode_id,at)==0
    assert confirm(stocks,old,'stock')=='superseded'
    assert confirm(stocks,new,'stock')=='recorded'


def test_reconciliation_keeps_vehicle_blocked_while_another_danger_remains(pipeline):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    _,old=emit('A','warning',0)
    emit('A','danger',1)
    emit('B','danger',2)
    normal(3)
    _,new=emit('A','warning',4)
    assert risk.get('shop').active_danger
    current=client.collection(risk.current_actions).document('shop').get().to_dict()
    assert current['blocked'] is True
    assert new['status']=='superseded'
    assert confirm(vehicles,old,'vehicle')=='superseded'
    assert confirm(stocks,old,'stock')=='superseded'


@pytest.mark.parametrize('queued',[False,True])
def test_legacy_active_danger_without_generation_keeps_old_stock_invalid_after_recovery(pipeline,queued):
    from google.cloud import firestore
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    _,old=emit('A','warning',0)
    original=risk.get('shop').episode_id
    emit('B','watch',1)
    danger,_=emit('A','danger',2)
    # Model the candidate's legacy records before the generation field existed.
    client.collection(risk.risks).document('shop').update({'danger_generation':firestore.DELETE_FIELD})
    old_snapshot=ActionSnapshot.model_validate(old['snapshot'])
    client.collection(stocks.actions).document(old_snapshot.stock_action_id).update({'danger_generation':firestore.DELETE_FIELD})
    # A pre-fix crash could leave this old pointer unblocked even though risk
    # already contained Danger. Recovery must invalidate it before new prepare.
    client.collection(risk.current_actions).document('shop').set({'blocked':False,'action_id':old_snapshot.vehicle_action_id,
        'event_id':old['event_id'],'episode_id':original,'created_at':old['created_at']})
    at=normal(3)
    if not queued:
        assert risk.recover_official('jps:A',danger.source_episode_id,at)==1
    else:
        emit('C','watch',4)  # Receipt reconciliation without a new vehicle action.
    assert client.collection(risk.current_actions).document('shop').get().to_dict()['action_id'] is None
    assert confirm(vehicles,old,'vehicle')=='superseded'
    _,new=emit('A','warning',5)
    assert risk.get('shop').episode_id==original and not risk.get('shop').active_danger
    assert client.collection(risk.risks).document('shop').get().to_dict()['danger_generation']==1
    assert confirm(stocks,old,'stock')=='superseded'
    assert confirm(stocks,new,'stock')=='recorded'
    assert confirm(vehicles,new,'vehicle')=='recorded'


def test_unrelated_watch_recovery_retains_unblocked_current_vehicle_action(pipeline):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    emit('A','warning',0)
    other,_=emit('B','watch',1)
    emit('A','danger',2)
    normal(3)
    _,new=emit('A','warning',4)
    episode=risk.get('shop').episode_id
    at=other.source_observed_at+timedelta(seconds=5)
    poll.observe(SourceResult(source='jps',status='current',checked_at=at,resolved={'jps:B':at}))
    assert risk.recover_official('jps:B',other.source_episode_id,at)==1
    assert risk.get('shop').episode_id==episode and not risk.get('shop').active_danger
    assert confirm(vehicles,new,'vehicle')=='recorded'


def test_committed_danger_crash_before_dispatch_invalidation_cannot_revive_old_vehicle(pipeline,monkeypatch):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    original_request,old=emit('A','warning',0)
    emit('B','watch',1)
    apply=risk.apply_event_decision
    def crash_after_commit(event,shop_id):
        result=apply(event,shop_id)
        if event['level']=='danger':raise RuntimeError('simulated crash after canonical risk commit')
        return result
    monkeypatch.setattr(risk,'apply_event_decision',crash_after_commit)
    with pytest.raises(RuntimeError,match='simulated crash'):emit('A','danger',2)
    assert risk.get('shop').active_danger
    monkeypatch.setattr(risk,'apply_event_decision',apply)
    at=normal(3)
    assert risk.recover_official('jps:A',original_request.source_episode_id,at)==1
    assert not risk.get('shop').active_danger
    assert confirm(vehicles,old,'vehicle')=='superseded'
    assert confirm(stocks,old,'stock')=='superseded'
    _,new=emit('A','warning',4)
    assert confirm(vehicles,new,'vehicle')=='recorded'


def test_canonical_risk_is_sole_vehicle_pointer_writer_for_danger(pipeline,monkeypatch):
    client,risk,poll,dispatch,vehicles,stocks,emit,normal,confirm=pipeline
    _,old=emit('A','warning',0)
    def forbidden(*args,**kwargs):raise AssertionError('Danger used a separate delayed pointer writer')
    monkeypatch.setattr(vehicles,'supersede',forbidden)
    emit('A','danger',1)
    assert client.collection(risk.current_actions).document('shop').get().to_dict()['blocked'] is True
    assert confirm(vehicles,old,'vehicle')=='superseded'
