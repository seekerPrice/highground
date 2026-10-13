from datetime import UTC,datetime,timedelta
import pytest
from pydantic import ValidationError
from api.report_models import LossAssessment
from api.waste_models import WasteAssessment,WasteItem,WasteRecord
from api.waste import validate_waste,donation_eligible,FOOD_SAFETY_LINE

BASE={'inventory_id':'inv','items':[{'name':'Rice','category':'food','qty':2.,'est_unit_value_rm':20.}], 'total_est_value_rm':40.}
MEDIA='a'*64

def item(**changes):
    return WasteItem(**(dict(item_id='inv:0',condition='damaged',disposition='salvage_clean',est_volume_m3=1.,est_weight_kg=2.,material='sealed_metal',floodwater_contact='yes',contamination='not_observed',uncertainty=None)|changes))

def assessment(**changes):return WasteAssessment(**(dict(inventory_id='inv',assessment_media_id=MEDIA,items=(item(),),confidence=.8)|changes))
def loss(condition='damaged'):
    unknown=condition in ('missing','unassessed')
    return LossAssessment(items=[dict(item_id='inv:0',condition=condition,estimated_loss_rm=None if unknown else 0. if condition=='ok' else 20.,evidence_timestamp_s=None if unknown else 1.,uncertainty='Condition visible; replacement-price estimate.')],total_loss_rm=None if unknown else 0. if condition=='ok' else 20.,summary_text='Estimated loss',confidence=.8,confidence_note='Estimate only.')

def test_selected_clip_inventory_and_item_binding_rejects_reinterpretation():
    for candidate in (assessment(inventory_id='other'),assessment(assessment_media_id='b'*64),assessment(items=(item(item_id='other'),)),assessment(items=(item(),item())),assessment(items=(item(condition='destroyed'),))):
        with pytest.raises(ValueError):validate_waste(candidate,BASE,loss(),MEDIA,10)
    with pytest.raises(ValueError):validate_waste(assessment(items=(item(condition='missing'),)),BASE,loss('missing'),MEDIA,10)


def test_contaminated_food_is_discarded_and_missing_is_never_quantified():
    food=assessment(items=(item(material='food',floodwater_contact='yes'),))
    corrected=validate_waste(food,BASE,loss(),MEDIA,10)
    assert corrected.items[0].disposition=='discard_contaminated'
    assert FOOD_SAFETY_LINE=='Throw away food, drinks and medicine that touched floodwater.'
    missing=assessment(items=(item(condition='missing',disposition=None,est_volume_m3=None,est_weight_kg=None,material='unknown',floodwater_contact='unknown',contamination='unknown',uncertainty='Not visible'),))
    assert validate_waste(missing,BASE,loss('missing'),MEDIA,10).items[0].est_volume_m3 is None


def test_donation_requires_owner_opt_in_and_no_assessed_uncertainty_or_contamination():
    assert donation_eligible(item(),owner_opt_in=True) # Sealed material can require cleaning; no safety certification.
    assert not donation_eligible(item(),owner_opt_in=False)
    for change in ({'contamination':'present'},{'contamination':'unknown'},{'uncertainty':'Condition unclear'},{'material':'food'},{'condition':'missing'}):
        assert not donation_eligible(item(**change),owner_opt_in=True)
    with pytest.raises(ValueError):donation_eligible(item(),owner_opt_in='yes')


def test_estimate_bounds_reject_negative_nan_unknown_fields():
    for changes in ({'est_volume_m3':-1.},{'est_weight_kg':float('nan')},{'est_weight_kg':float('inf')},{'disposition':'safe_to_use'}):
        with pytest.raises(ValidationError):item(**changes)


def record(identity='r1',**changes):
    values=dict(assessment_id=identity,shop_id='shop',episode_id='episode',completed_at=datetime(2026,10,13,tzinfo=UTC),status='complete',is_demo=True,owner_confirmed_street='Owner-confirmed street',baseline_items=1,assessment=assessment())
    return WasteRecord(**(values|changes))


def test_latest_completed_dedupes_same_inventory_keeps_episodes_and_unknown_coverage():
    from api.waste import aggregate_waste
    early=record(assessment=assessment(items=(item(est_volume_m3=9.),)))
    latest=record('r2',completed_at=early.completed_at+timedelta(seconds=1),assessment=assessment(items=(item(est_volume_m3=2.,est_weight_kg=None),)))
    pending=record('r3',completed_at=early.completed_at+timedelta(seconds=2),status='pending',assessment=assessment(items=(item(est_volume_m3=99.),)))
    second_episode=record('r4',episode_id='next-episode',assessment=assessment(items=(item(est_volume_m3=3.),)))
    missing=record('r5',shop_id='unknown-shop',owner_confirmed_street=None,assessment=assessment(items=(item(condition='missing',disposition=None,est_volume_m3=None,est_weight_kg=None,material='unknown',floodwater_contact='unknown',contamination='unknown',uncertainty='Not visible'),)))
    result=aggregate_waste([early,latest,pending,second_episode,missing,record('private',is_demo=False),record('not-owned',shop_id='not-owned')],synthetic_shop_ids={'shop','unknown-shop'},lorry_capacity_m3=10.)
    street=next(s for s in result.streets if s.street=='Owner-confirmed street')
    assert street.est_volume_m3==5. and street.estimated_load_equivalents==.5
    assert street.assessment_count==2 and street.shop_count==1
    assert street.unknown_weight_items==1 and street.quantified_weight_items==1
    unassigned=next(s for s in result.streets if s.street=='Unassigned')
    assert unassigned.est_volume_m3 is None and unassigned.estimated_load_equivalents is None
    assert unassigned.unknown_items==1 and unassigned.unknown_volume_items==1
    public=result.model_dump_json()
    assert 'shop_id' not in public and 'episode_id' not in public and 'not-owned' not in public and 'media_id' not in public
    assert 'not required trucks' in result.definition


def test_unknown_and_omitted_baseline_items_are_never_summed_as_zero_and_capacity_is_positive():
    from api.waste import aggregate_waste
    partial=record(baseline_items=2,assessment=assessment(items=(item(est_volume_m3=None,est_weight_kg=None,uncertainty='Size unavailable'),)))
    result=aggregate_waste([partial],synthetic_shop_ids={'shop'})
    assert result.streets[0].est_volume_m3 is None and result.streets[0].unknown_items==1
    assert result.streets[0].unknown_volume_items==2
    for capacity in (0.,-1.,float('nan'),float('inf'),True):
        with pytest.raises(ValueError):aggregate_waste([partial],synthetic_shop_ids={'shop'},lorry_capacity_m3=capacity)
    with pytest.raises(ValueError):aggregate_waste([record(baseline_items=0)],synthetic_shop_ids={'shop'})


def test_canonical_hazardous_categories_override_incorrect_salvage_material_without_mutating_loss():
    original=loss();before=original.model_dump()
    result=validate_waste(assessment(),BASE,original,MEDIA,10)
    assert result.items[0].disposition=='discard_contaminated'
    assert not donation_eligible(result.items[0],owner_opt_in=True)
    assert original.model_dump()==before
    for material in ('food','drink','medicine','cosmetics','absorbent'):
        result=validate_waste(assessment(items=(item(material=material),)),BASE,original,MEDIA,10)
        assert result.items[0].disposition=='discard_contaminated'
    with pytest.raises(ValueError):validate_waste(assessment(items=()),BASE,original,MEDIA,10)


def test_quantified_zero_differs_from_unavailable_and_street_labels_are_not_guessed():
    from api.waste import aggregate_waste
    zero=record(owner_confirmed_street=None,assessment=assessment(items=(item(est_volume_m3=0.,est_weight_kg=0.),)))
    street=aggregate_waste([zero],synthetic_shop_ids={'shop'}).streets[0]
    assert street.street=='Unassigned' and street.est_volume_m3==0. and street.estimated_load_equivalents==0.
    assert street.unknown_volume_items==0
    unknown=record(assessment=assessment(items=(item(est_volume_m3=None,est_weight_kg=None),)))
    assert aggregate_waste([unknown],synthetic_shop_ids={'shop'}).streets[0].est_volume_m3 is None

@pytest.mark.parametrize('changes',[{'condition':'destroyed'},{'floodwater_contact':'unknown'}],ids=['destroyed-not-salvageable','unknown-contact'])
def test_donation_never_certifies_destroyed_or_unknown_contact_items(changes):
    assert not donation_eligible(item(**changes),owner_opt_in=True)

def test_confirmed_street_is_normalized_and_blank_is_unassigned():
    from api.waste import aggregate_waste
    normalized=record(owner_confirmed_street='  Jalan Example  ')
    blank=record('blank',owner_confirmed_street='   ')
    assert normalized.owner_confirmed_street=='Jalan Example'
    assert blank.owner_confirmed_street is None
    assert aggregate_waste([blank],synthetic_shop_ids={'shop'}).streets[0].street=='Unassigned'


def test_explicit_contamination_prohibits_salvage_even_with_known_food_override():
    with pytest.raises(ValueError):validate_waste(assessment(items=(item(contamination='present'),)),BASE,loss(),MEDIA,10)

@pytest.mark.parametrize('category',['Food Staples','foodstaples','Beverages'])
def test_exact_known_hazardous_categories_precede_sealed_packaging(category):
    baseline=dict(BASE,items=[dict(BASE['items'][0],category=category)])
    assert validate_waste(assessment(),baseline,loss(),MEDIA,10).items[0].disposition=='discard_contaminated'
