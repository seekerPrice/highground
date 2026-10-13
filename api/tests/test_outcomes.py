from datetime import UTC,datetime,timedelta
import pytest
from api.outcome_models import OutcomeEpisode,OutcomeDelivery
from api.outcomes import first_owner_response
NOW=datetime(2026,10,14,0,tzinfo=UTC);OWNER='a'*64

def episode(**changes):return OutcomeEpisode(**(dict(shop_id='private-shop',episode_id='confirmed-episode',area='w2833s',started_at=NOW-timedelta(hours=7),owner_hash=OWNER,is_demo=True,scenario_generation=2,deliveries=(OutcomeDelivery(alert_id='b'*64,created_at=NOW-timedelta(hours=7),accepted_at=NOW-timedelta(hours=6),level='warning',source='demo',provenance='telegram_api',status='accepted'),))|changes))
def respond(ep=None,previous=None,**changes):return first_owner_response(previous,ep or episode(),**(dict(actor_hash=OWNER,actor_shop_id='private-shop',actor_role='owner',current_owner_hash=OWNER,answer='no',observed_at=NOW-timedelta(hours=5),answered_at=NOW)|changes))


def test_current_owner_first_response_is_immutable_and_worker_other_shop_or_episode_denied():
    first=respond();assert respond(previous=first,answer='inside')==first
    for changes in ({'actor_role':'worker'},{'actor_hash':'c'*64},{'actor_shop_id':'other'},{'observed_at':NOW-timedelta(hours=8)}):
        with pytest.raises(ValueError):respond(**changes)
    with pytest.raises(ValueError):respond(episode(episode_id='other'),previous=first)
    assert first.depth_cm is None


def test_six_hour_or_explicit_closure_due_boundary_defers_danger_and_obsolete_demo():
    from api.outcomes import prompt_due
    assert prompt_due(episode(),NOW,current_owner_hash=OWNER,current_generation=2).due
    assert not prompt_due(episode(),NOW-timedelta(microseconds=1),current_owner_hash=OWNER,current_generation=2).due
    assert prompt_due(episode(deliveries=(),closed_at=NOW),NOW,current_owner_hash=OWNER,current_generation=2).due
    assert not prompt_due(episode(),NOW,current_owner_hash=OWNER,current_generation=2,active_danger=True).due
    assert prompt_due(episode(),NOW,current_owner_hash=OWNER,current_generation=3).reason=='obsolete_scenario'
    assert prompt_due(episode(),NOW,current_owner_hash=None,current_generation=2).reason=='no_owner'
    virtual=episode(deliveries=(OutcomeDelivery(alert_id='b'*64,created_at=NOW-timedelta(hours=7),level='warning',source='demo',provenance='local_virtual',status='simulated'),))
    assert prompt_due(virtual,NOW,current_owner_hash=OWNER,current_generation=2).reason=='no_accepted_alert_or_closure'


def test_synthetic_coverage_counts_first_shop_episode_response_and_missing_not_no():
    from api.outcomes import outcome_coverage
    from api.outcome_models import OutcomePrompt
    one=episode();two=episode(episode_id='two');real=episode(is_demo=False,scenario_generation=None,deliveries=(one.deliveries[0].model_copy(update={'source':'shop_report'}),))
    first=respond();duplicate=first.model_copy(update={'response_id':'d'*64,'answer':'inside','answered_at':NOW+timedelta(seconds=1)})
    prompts=(OutcomePrompt(is_demo=True,scenario_generation=2,shop_id=one.shop_id,episode_id=one.episode_id,status='accepted',provenance='telegram_api'),OutcomePrompt(is_demo=True,scenario_generation=2,shop_id=one.shop_id,episode_id=one.episode_id,status='accepted',provenance='telegram_api'),OutcomePrompt(is_demo=True,scenario_generation=2,shop_id=two.shop_id,episode_id=two.episode_id,status='simulated',provenance='local_virtual'))
    coverage=outcome_coverage((one,two,real),(first,duplicate),prompts,synthetic_shop_ids={'private-shop'},generation=2)
    assert coverage.eligible_shop_episodes==2 and coverage.accepted_prompts==1 and coverage.virtual_prompts==1
    assert coverage.responses==1 and coverage.no==1 and coverage.inside==0 and coverage.missing_unknown==1
    assert 'private-shop' not in coverage.model_dump_json() and 'owner_hash' not in coverage.model_dump_json()


def test_coverage_rejects_old_generation_prompts_and_out_of_episode_observation():
    from api.outcomes import outcome_coverage
    from api.outcome_models import OutcomePrompt
    stale=OutcomePrompt(is_demo=True,scenario_generation=2,shop_id='private-shop',episode_id='confirmed-episode',status='accepted',provenance='telegram_api').model_copy(update={'scenario_generation':1})
    outside=respond().model_copy(update={'observed_at':NOW-timedelta(hours=8)})
    result=outcome_coverage((episode(),),(outside,),(stale,),synthetic_shop_ids={'private-shop'},generation=2)
    assert result.accepted_prompts==0 and result.responses==0 and result.missing_unknown==1


def test_public_summary_unknown_scope_and_history_denominator_are_explicit():
    from api.outcome_models import OutcomeSummary,CalibrationHistoryPoint
    unavailable=OutcomeSummary(status='unavailable',generated_at=NOW,note='Synthetic outcome summary unavailable.')
    assert unavailable.scenario_generation is None and unavailable.coverage is None
    with pytest.raises(ValueError):OutcomeSummary(status='unavailable',generated_at=NOW,scenario_generation=0,note='Unknown')
    with pytest.raises(ValueError):CalibrationHistoryPoint(evaluated_at=NOW,old_multiplier=1.,new_multiplier=.9,reason='shrink',response_count=5,water_response_count=6,fixture_response_count=0)
    with pytest.raises(ValueError):OutcomeSummary.model_validate_json(unavailable.model_dump_json().replace('"note":','"owner_hash":"private","note":'))


def test_reference_time_is_explicit_and_missed_inside_cannot_use_episode_reference():
    from api.outcome_models import OwnerOutcome
    from api.tests.test_outcomes import episode
    ep=episode()
    response=first_owner_response(None,ep,actor_hash='a'*64,actor_shop_id=ep.shop_id,actor_role='owner',current_owner_hash='a'*64,answer='inside',observed_at=ep.started_at,answered_at=ep.started_at,entrypoint='alert_response')
    assert response.reference_basis=='episode_reference'
    with pytest.raises(ValueError):OwnerOutcome.model_validate(response.model_dump()|{'entrypoint':'owner_report','reference_basis':'episode_reference'})
    declared=first_owner_response(None,ep,actor_hash='a'*64,actor_shop_id=ep.shop_id,actor_role='owner',current_owner_hash='a'*64,answer='inside',observed_at=ep.started_at,answered_at=ep.started_at,entrypoint='owner_report')
    assert declared.reference_basis=='owner_declared'
