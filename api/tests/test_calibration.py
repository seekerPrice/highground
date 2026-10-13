from datetime import timedelta
import pytest
from api.outcome_models import CalibrationState,CalibrationEvidence,OutcomeDelivery
from api.calibration import geohash6
from api.tests.test_outcomes import NOW,episode,respond


def test_geohash_primary_vectors_order_and_coordinate_edges():
    assert geohash6(48.,-126.)=='c0w3hf' # PostGIS ST_Point longitude,latitude.
    assert geohash6(52.205,.119)=='u120fx' # Author's published encode vector.
    assert geohash6(0.,0.)=='s00000'
    assert geohash6(90.,180.)=='zzzzzz'
    assert geohash6(-90.,-180.)=='000000'
    assert geohash6(0.,180.)=='xbpbpb' and geohash6(0.,-180.)=='800000'
    for coords in ((float('nan'),0.),(0.,float('inf')),(91.,0.),(0.,181.),(True,0.)):
        with pytest.raises(ValueError):geohash6(*coords)


def state(**changes):return CalibrationState(**(dict(area='w2833s',is_demo=True,scenario_generation=2)|changes))
def evidence(index,answer='no',**changes):
    ep=episode(shop_id=f'shop-{index}',**changes)
    response=respond(ep,actor_shop_id=ep.shop_id,answer=answer)
    return CalibrationEvidence(episode=ep,response=response)


def test_shrink_requires_five_disjoint_first_responses_strictly_below_point_three():
    from api.calibration import decide_calibration
    five=tuple(evidence(i) for i in range(5))
    assert decide_calibration(state(),five[:4],now=NOW).reason=='insufficient_responses'
    shrink=decide_calibration(state(),five,now=NOW)
    assert shrink.new_multiplier==.9 and len(shrink.consumed_outcome_keys)==5
    replay=decide_calibration(state(version=shrink.new_version,multiplier=shrink.new_multiplier),five,now=NOW,consumed_keys=frozenset(shrink.consumed_outcome_keys))
    assert replay.reason=='no_fresh_evidence' and replay.new_multiplier==.9
    edge=tuple(evidence(i,'street_only' if i<3 else 'no') for i in range(10))
    assert decide_calibration(state(),edge,now=NOW).reason=='no_change'
    below=tuple(evidence(i,'entrance' if i==0 else 'no') for i in range(5))
    assert decide_calibration(state(),below,now=NOW).reason=='shrink'


def test_growth_requires_inside_owner_report_and_complete_no_prior_acceptance_or_ambiguity():
    from api.calibration import decide_calibration
    ep=episode(deliveries=());inside=respond(ep,answer='inside',entrypoint='owner_report')
    candidate=CalibrationEvidence(episode=ep,response=inside)
    assert decide_calibration(state(),(candidate,),now=NOW).new_multiplier==1.1
    assert decide_calibration(state(multiplier=1.49),(candidate,),now=NOW).new_multiplier==1.5
    assert decide_calibration(state(),(evidence(1,'inside'),),now=NOW).reason!='grow' # Alert-only answer cannot establish missed evidence.
    for history in ('incomplete','overflowed'):
        assert decide_calibration(state(),(candidate.model_copy(update={'episode':ep.model_copy(update={'history_status':history})}),),now=NOW).reason!='grow'
    for status in ('sending','uncertain','pending','retryable'):
        delivery=OutcomeDelivery(alert_id='f'*64,created_at=NOW-timedelta(hours=6),request_started_at=NOW-timedelta(hours=6),level='warning',source='demo',provenance='telegram_api',status=status)
        possible=candidate.model_copy(update={'episode':ep.model_copy(update={'deliveries':(delivery,)})})
        assert decide_calibration(state(),(possible,),now=NOW).reason!='grow'
    prior=OutcomeDelivery(alert_id='f'*64,created_at=NOW-timedelta(hours=6),accepted_at=NOW-timedelta(hours=6),level='warning',source='demo',provenance='telegram_api',status='accepted')
    assert decide_calibration(state(),(candidate.model_copy(update={'episode':ep.model_copy(update={'deliveries':(prior,)})}),),now=NOW).reason!='grow'
    later=prior.model_copy(update={'accepted_at':NOW-timedelta(hours=4)})
    assert decide_calibration(state(),(candidate.model_copy(update={'episode':ep.model_copy(update={'deliveries':(later,)})}),),now=NOW).reason=='grow'
    virtual=prior.model_copy(update={'status':'simulated','provenance':'local_virtual','accepted_at':None})
    assert decide_calibration(state(),(candidate.model_copy(update={'episode':ep.model_copy(update={'deliveries':(virtual,)})}),),now=NOW).reason!='grow'


def test_duplicate_first_scope_consumption_real_demo_reset_and_window_boundaries():
    from api.calibration import decide_calibration,outcome_key
    five=tuple(evidence(i) for i in range(5));first=five[0]
    duplicate=first.model_copy(update={'response':first.response.model_copy(update={'response_id':'e'*64,'answered_at':NOW+timedelta(microseconds=1),'answer':'inside'})})
    result=decide_calibration(state(),five+(duplicate,),now=NOW)
    assert result.response_count==5 and result.water_response_count==0
    changed=first.model_copy(update={'response':first.response.model_copy(update={'response_id':'e'*64})})
    assert decide_calibration(state(),(changed,),now=NOW,consumed_keys=frozenset({outcome_key(first.response)})).reason=='no_fresh_evidence'
    assert decide_calibration(state(is_demo=False,scenario_generation=None),five,now=NOW).reason=='no_fresh_evidence'
    assert decide_calibration(state(scenario_generation=3),five,now=NOW).reason=='no_fresh_evidence'
    older=first.model_copy(update={'response':first.response.model_copy(update={'observed_at':NOW-timedelta(days=31),'answered_at':NOW-timedelta(days=31)})})
    assert decide_calibration(state(),(older,),now=NOW).reason=='no_fresh_evidence'
    edge_ep=episode(shop_id='edge',started_at=NOW-timedelta(days=31),deliveries=(OutcomeDelivery(alert_id='f'*64,created_at=NOW-timedelta(days=31),accepted_at=NOW-timedelta(days=30,hours=1),level='warning',source='demo',provenance='telegram_api',status='accepted'),))
    edge=respond(edge_ep,actor_shop_id='edge',observed_at=NOW-timedelta(days=30),answered_at=NOW-timedelta(days=30))
    assert decide_calibration(state(),(CalibrationEvidence(episode=edge_ep,response=edge),),now=NOW).reason=='insufficient_responses'
    clamped=decide_calibration(state(multiplier=.51),five,now=NOW);assert clamped.new_multiplier==.5


def test_radius_plan_is_per_shop_frozen_and_never_changes_official_danger_or_fixed_queries():
    from api.calibration import freeze_radius
    common=dict(area='w2833s',is_demo=True,scenario_generation=2,state=state(multiplier=1.5,version=7))
    plan=freeze_radius(10000.,level='warning',source='demo',**common)
    assert plan.base_radius_m==10000 and plan.effective_radius_m==15000 and plan.calibration_version==7
    assert freeze_radius(10000.,level='warning',source='demo',existing=plan,**(common|{'state':state(multiplier=.5,version=8)}))==plan
    for level,source,purpose,radius in (('danger','shop_report','dispatch',300.),('warning','jps','dispatch',1000.),('warning','met','dispatch',1000.),('watch','demo','dispatch',1000.),('warning','shop_report','corroboration',500.),('warning','demo','public_check',2000.)):
        unchanged=freeze_radius(radius,level=level,source=source,purpose=purpose,**common)
        assert unchanged.effective_radius_m==radius and not unchanged.applied
    assert not freeze_radius(1000.,level='warning',source='demo',**(common|{'area':'u120fx'})).applied


def test_one_growth_step_wins_simultaneous_shrink_and_consumes_both_evidence_scopes():
    from api.calibration import decide_calibration
    covered=tuple(evidence(i) for i in range(5));ep=episode(shop_id='missed',deliveries=())
    inside=CalibrationEvidence(episode=ep,response=respond(ep,actor_shop_id='missed',answer='inside',entrypoint='owner_report'))
    result=decide_calibration(state(),covered+(inside,),now=NOW)
    assert result.reason=='grow' and result.new_multiplier==1.1
    assert len(result.consumed_outcome_keys)==6 and result.response_count==5
    assert decide_calibration(state(multiplier=1.1,version=1),covered+(inside,),now=NOW,consumed_keys=frozenset(result.consumed_outcome_keys)).reason=='no_fresh_evidence'


def test_synthetic_fixture_history_is_explicit_never_telegram_acceptance_or_real_learning():
    from api.calibration import decide_calibration
    rows=[]
    for i in range(5):
        delivery=OutcomeDelivery(alert_id=f'{i:064x}',created_at=NOW-timedelta(hours=7),simulated_at=NOW-timedelta(hours=6),level='warning',source='demo',provenance='synthetic_fixture',status='simulated')
        ep=episode(shop_id=f'fixture-{i}',deliveries=(delivery,))
        response=respond(ep,actor_shop_id=ep.shop_id,origin='synthetic_fixture')
        rows.append(CalibrationEvidence(episode=ep,response=response))
    result=decide_calibration(state(),tuple(rows),now=NOW)
    assert result.reason=='shrink' and result.fixture_response_count==5
    assert decide_calibration(state(is_demo=False,scenario_generation=None),tuple(rows),now=NOW).reason=='no_fresh_evidence'
    from api.outcomes import prompt_due
    assert not prompt_due(rows[0].episode,NOW,current_owner_hash=rows[0].response.owner_hash,current_generation=2).due


def test_existing_target_plan_rejects_danger_official_fixed_query_or_scope_mismatch():
    from api.calibration import freeze_radius
    common=dict(level='warning',source='demo',area='w2833s',is_demo=True,scenario_generation=2,state=state(multiplier=.5,version=1))
    plan=freeze_radius(1000.,**common)
    for changed in ({'level':'danger'},{'source':'jps'},{'source':'met'},{'purpose':'public_check'},{'purpose':'corroboration'},{'area':'u120fx'},{'scenario_generation':3}):
        with pytest.raises(ValueError):freeze_radius(1000.,existing=plan,**(common|changed))
    with pytest.raises(ValueError):freeze_radius(500.,existing=plan,**common)


def test_persisted_radius_plan_cannot_decode_inconsistent_or_authoritative_calibration():
    from api.calibration import freeze_radius
    from api.outcome_models import RadiusPlan
    plan=freeze_radius(1000.,level='warning',source='demo',area='w2833s',is_demo=True,scenario_generation=2,state=state(multiplier=.5,version=1))
    assert RadiusPlan.model_validate_json(plan.model_dump_json())==plan
    for change in ({'effective_radius_m':999.},{'source':'jps'},{'level':'danger'},{'purpose':'public_check'},{'applied':False},{'calibration_version':None},{'scenario_generation':None}):
        with pytest.raises(ValueError):RadiusPlan.model_validate(plan.model_dump()|change)


def test_accepted_watch_history_blocks_missed_growth_but_is_not_due_or_shrink_evidence():
    from api.outcomes import prompt_due
    from api.calibration import decide_calibration
    watch=OutcomeDelivery.model_validate(episode().deliveries[0].model_dump()|{'level':'watch'})
    ep=episode(deliveries=(watch,))
    assert not prompt_due(ep,NOW,current_owner_hash='a'*64,current_generation=2).due
    inside=respond(ep,answer='inside',entrypoint='owner_report')
    assert decide_calibration(state(),(CalibrationEvidence(episode=ep,response=inside),),now=NOW).reason!='grow'
    five=tuple(evidence(i,deliveries=(watch,)) for i in range(5))
    decision=decide_calibration(state(),five,now=NOW)
    assert decision.reason=='insufficient_responses' and decision.new_multiplier==1. and decision.response_count==0
