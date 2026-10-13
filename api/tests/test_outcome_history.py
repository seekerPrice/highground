"""Trusted episode starts and explicit closure share the risk transaction."""
from datetime import UTC,datetime,timedelta
from unittest.mock import patch
import pytest
from api.active_risk import ActiveRiskStore
from api.tests.test_public_check_intents import Client,Snapshot,transactional

Snapshot.exists=property(lambda self:self.value is not None)

def setup():
    client=Client()
    client.data['shops','shop']={'lat':3.1,'lng':101.6,'is_demo':False,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    now=datetime.now(UTC)
    event={'event_id':'a'*64,'source':'shop_report','level':'warning','created_at':now,'is_demo':False}
    return client,event


def test_first_reporter_episode_and_explicit_owner_closure_are_atomic_without_outbound_alert():
    client,event=setup()
    risks=ActiveRiskStore(client,episode_history='history')
    with patch('api.active_risk.firestore.transactional',transactional):
        decision=risks.apply_event_decision(event,'shop')
        rows=[v for (c,_),v in client.data.items() if c=='history']
        assert len(rows)==1
        row=rows[0]
        assert row['episode_id']==decision.episode_id and row['started_at']==event['created_at']
        assert row['first_event_id']==event['event_id'] and row['start_basis']=='receipt_time'
        assert row['closed_at'] is None and row['area'] and row['history_status']=='complete'
        assert risks.owner_declared_recovery('shop',101)
        closed=[v for (c,_),v in client.data.items() if c=='history'][0]
        assert closed['closed_at']>=row['started_at'] and closed['closure_basis']=='owner_declared'
        assert closed['started_at']==row['started_at']
        assert not any(c=='alerts' for c,_ in client.data)


def test_legacy_episode_is_not_backfilled_with_later_observation_start():
    client,event=setup()
    client.data['active_risks','shop']={'episode_id':'old-episode','sources':{},'legacy_unknown':False}
    risks=ActiveRiskStore(client,episode_history='history')
    with patch('api.active_risk.firestore.transactional',transactional):
        assert risks.apply_event_decision(event,'shop').episode_id=='old-episode'
    assert not any(c=='history' for c,_ in client.data)


def test_history_failure_rolls_back_risk_and_shop_without_partial_episode():
    client,event=setup()
    risks=ActiveRiskStore(client,episode_history='history')
    from copy import deepcopy
    original=deepcopy(client.data)
    with patch('api.active_risk.firestore.transactional',transactional),patch('api.outcome_history.geohash6',side_effect=ValueError('Invalid confirmed location')):
        with pytest.raises(ValueError):risks.apply_event_decision(event,'shop')
    assert client.data==original


@pytest.mark.parametrize('source,level',[('jps','warning'),('met','danger'),('demo','watch'),('shop_report','danger')])
def test_fixed_targeting_never_reads_optional_calibration(source,level):
    from unittest.mock import Mock
    from api.outcome_history import OutcomeHistoryAdapter
    from api.tests.test_dispatch import shop
    store=Mock();store.calibration_state.side_effect=RuntimeError('Optional learning unavailable')
    adapter=OutcomeHistoryAdapter(Mock(),store,Mock())
    plan=adapter.radius_plan(shop(),{'source':source,'level':level,'radius_m':1000,'scenario_generation':2})
    assert plan.effective_radius_m==1000 and not plan.applied
    assert not store.calibration_state.called


def test_complete_area_batch_over_hundred_defers_instead_of_sampled_shrink():
    from unittest.mock import Mock
    from api.outcome_history import OutcomeHistoryAdapter
    from api.tests.test_calibration import evidence
    client=Mock();records=[]
    for i in range(101):
        row=Mock();row.to_dict.return_value={'json':evidence(i).response.model_dump_json()};records.append(row)
    client.collection.return_value.where.return_value.limit.return_value.stream.return_value=records
    adapter=OutcomeHistoryAdapter(client,Mock(prefix=''),Mock());adapter._rows=Mock(return_value=[]);adapter._scope=Mock(return_value={'generation':2,'state':'ready'});adapter.project=Mock()
    from api.tests.test_outcomes import NOW
    batches,overflow=adapter.calibration_batches(now=NOW)
    assert batches=={} and len(overflow)==1
    assert not adapter.project.called


def test_old_fixture_generation_does_not_poison_current_refresh_or_calibration():
    from unittest.mock import Mock
    from api.outcome_history import OutcomeHistoryAdapter,history_key
    from api.tests.test_calibration import evidence
    from api.tests.test_outcomes import NOW
    from datetime import timedelta
    first=evidence(0);new=first.model_copy(update={'episode':first.episode.model_copy(update={'scenario_generation':3}),'response':first.response.model_copy(update={'scenario_generation':3})})
    old_doc=Mock(id='old');old_doc.to_dict.return_value={'is_demo':True,'scenario_generation':2,'shop_id':first.episode.shop_id,'started_at':NOW-timedelta(days=2)}
    new_doc=Mock(id=history_key(new.response.shop_id,new.response.episode_id,True,3));new_doc.to_dict.return_value={'is_demo':True,'scenario_generation':3,'shop_id':new.episode.shop_id,'started_at':NOW-timedelta(days=1)}
    old_response=Mock();old_response.to_dict.return_value={'json':first.response.model_dump_json()}
    new_response=Mock();new_response.to_dict.return_value={'json':new.response.model_dump_json()}
    client=Mock();client.collection.return_value.where.return_value.limit.return_value.stream.return_value=[old_response,new_response]
    adapter=OutcomeHistoryAdapter(client,Mock(prefix=''),Mock());adapter._scope=Mock(return_value={'state':'ready','generation':3})
    adapter._rows=Mock(return_value=[old_doc,new_doc])
    adapter.project=Mock(side_effect=lambda row,**kwargs:new.episode if row['scenario_generation']==3 else (_ for _ in ()).throw(ValueError('Obsolete fixture')))
    adapter.refresh(limit=1,now=NOW)
    batches,overflow=adapter.calibration_batches(now=NOW)
    assert not overflow and list(batches)==[(new.episode.area,True,3)]
    assert len(batches[new.episode.area,True,3])==1
    assert old_doc.reference.update.call_count==0


def test_delivery_loop_budget_stops_before_next_event_read():
    from unittest.mock import Mock,patch
    from api.outcome_history import OutcomeHistoryAdapter
    client=Mock();first=Mock(id='a'*64);second=Mock(id='b'*64)
    row={'shop_id':'shop','episode_id':'episode','history_status':'complete','is_demo':False,'scenario_generation':None}
    first.to_dict.return_value={'event_id':'event','is_demo':False,'status':'pending','created_at':datetime.now(UTC),'level':'warning'}
    second.to_dict.return_value=first.to_dict.return_value
    client.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value=[first,second]
    event_ref=client.collection.return_value.document.return_value
    event_ref.get.return_value.to_dict.return_value={'source':'shop_report'}
    adapter=OutcomeHistoryAdapter(client,Mock(),Mock())
    with patch('api.outcome_history.time.monotonic',side_effect=[0,0,2]):
        with pytest.raises(TimeoutError):adapter.project(row,deadline=1)
    assert event_ref.get.call_count==1 and not second.to_dict.called


def test_public_danger_dispatch_proceeds_with_broken_optional_learning_storage():
    from fastapi.testclient import TestClient
    from unittest.mock import Mock
    from api.main import create_app
    from api.config import Settings
    from api.outcome_history import OutcomeHistoryAdapter
    from api.tests.test_dispatch import service
    active,store,bot,sinks=service();learning=Mock();learning.calibration_state.side_effect=RuntimeError('Optional calibration unavailable')
    active.radius_planner=OutcomeHistoryAdapter(Mock(),learning,Mock())
    with TestClient(create_app(Settings(demo_mode=True,operator_token='synthetic'),dispatch_service=active)) as web:
        result=web.post('/demo/simulate-warning',headers={'Authorization':'Bearer synthetic'},json={'request_id':'danger','source':'demo','level':'danger','lat':3.,'lng':101.})
    assert result.status_code==200 and len(bot.messages)==1 and not learning.calibration_state.called
    assert next(iter(store.events.values()))['radius_m']==1000


def test_calibrated_dispatch_retry_retains_private_selection_after_learning_changes():
    import asyncio
    from unittest.mock import Mock
    from api.outcome_history import OutcomeHistoryAdapter
    from api.outcome_models import CalibrationState
    from api.tests.test_dispatch import service,request
    from api.calibration import geohash6
    active,store,bot,sinks=service();sinks.fail=True;learning=Mock()
    state=CalibrationState(area=geohash6(3.,101.),is_demo=True,scenario_generation=0,version=1,multiplier=.9)
    learning.calibration_state.return_value=state
    active.radius_planner=OutcomeHistoryAdapter(Mock(),learning,Mock())
    first=asyncio.run(active.process(request('warning')))
    frozen=next(iter(store.events.values()))['radius_plans']
    assert frozen['demo']['effective_radius_m']==900 and frozen['demo']['calibration_version']==1
    learning.calibration_state.return_value=state.model_copy(update={'version':2,'multiplier':1.5});sinks.fail=False
    second=asyncio.run(active.resume(first['event_id']))
    assert second['status']=='complete' and len(bot.messages)==1 and learning.calibration_state.call_count==1
    assert next(iter(store.events.values()))['radius_plans']==frozen
