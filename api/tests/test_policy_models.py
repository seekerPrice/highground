from datetime import date,datetime,UTC
import pytest
from pydantic import ValidationError
from api.policy_models import PolicyAssessment,FrozenPolicyInventory,compare_policy,aggregate_policies

BASE=FrozenPolicyInventory(inventory_id='frozen',total_est_value_rm=100.,confidence=.7,status='available')
def assessment(**changes):return PolicyAssessment(**(dict(flood_covered='yes',coverage_evidence='included',sum_insured_rm=60.,sum_insured_scope='stock_and_contents',currency='MYR',currency_evidence_quote='Currency MYR',sum_insured_evidence_quote='Stock and contents sum insured MYR 60',excess_evidence_quote='Excess MYR 10',excess_rm=10.,expiry_date=date(2027,1,1),evidence_quote='Flood is included.')|changes))

@pytest.mark.parametrize('changes',[{'sum_insured_rm':float('nan')},{'excess_rm':-1.},{'flood_covered':'no'},{'evidence_quote':None},{'sum_insured_scope':'unclear'},{'evidence_quote':'Full OCR\nsecond line'}])
def test_policy_rejects_unbounded_or_contradictory_extraction(changes):
    with pytest.raises(ValidationError):assessment(**changes)

def test_unknown_expiry_frozen_estimate_and_excess_never_invent_cover():
    assert compare_policy(assessment(),BASE,date(2026,10,13)).estimated_limit_gap_rm==40.
    assert compare_policy(assessment(excess_rm=500.,excess_evidence_quote='Excess MYR 500'),BASE,date(2026,10,13)).estimated_limit_gap_rm==40.
    assert compare_policy(assessment(expiry_date=date(2020,1,1)),BASE,date(2026,10,13)).status=='expired'
    assert compare_policy(assessment(sum_insured_rm=None),BASE,date(2026,10,13)).status=='limit_unavailable'
    assert compare_policy(assessment(flood_covered='unclear',coverage_evidence='unclear',evidence_quote=None),BASE,date(2026,10,13)).estimated_limit_gap_rm is None
    absent=FrozenPolicyInventory(inventory_id=None,total_est_value_rm=None,confidence=None,status='unavailable')
    assert compare_policy(assessment(),absent,date(2026,10,13)).status=='baseline_unavailable'

def test_synthetic_aggregate_separates_missing_unknown_expired_and_denominator():
    now=datetime.now(UTC)
    def row(shop,policy,**changes):return dict(shop_id=shop,policy_id=shop,created_at=now,is_demo=True,status='complete',assessment=policy.model_dump(),baseline=BASE.model_dump(),**changes)
    rows=[row('yes',assessment()),row('no',assessment(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is excluded.')),row('unknown',assessment(flood_covered='unclear',coverage_evidence='unclear',evidence_quote=None)),row('expired',assessment(expiry_date=date(2020,1,1)))]
    rows.append(dict(rows[0],shop_id='private',is_demo=False))
    result=aggregate_policies({'yes','no','unknown','expired','missing'},rows,date(2026,10,13))
    assert result.assessed_known_coverage==2 and result.without_cover_percent_of_known==50.
    assert result.uninsured_stock_estimate_rm==140. and result.unclear_or_expired==2 and result.missing_policies==1 and result.unknown_stock_estimates==3

def test_incomplete_fire_perils_cannot_assert_explicit_no_cover():
    with pytest.raises(ValidationError):assessment(flood_covered='no',coverage_evidence='fire_listed_perils',evidence_quote='Fire, lightning and explosion.')

def test_unavailable_frozen_estimate_cannot_retain_a_partial_stale_amount():
    with pytest.raises(ValidationError):FrozenPolicyInventory(inventory_id=None,total_est_value_rm=100.,confidence=None,status='unavailable')

@pytest.mark.parametrize('changes',[{'currency':'unclear','currency_evidence_quote':None},{'sum_insured_evidence_quote':'Building sum insured MYR60'},{'sum_insured_evidence_quote':'Annual premium MYR60'},{'sum_insured_evidence_quote':'Stock sum insured USD60'},{'excess_evidence_quote':'Excess 10% of loss'}])
def test_unrelated_currency_premium_building_or_conditional_excess_stays_unquantified(changes):
    with pytest.raises(ValidationError):assessment(**changes)

def test_unknown_expiry_remains_qualified_and_outside_current_coverage_denominator():
    unknown=assessment(expiry_date=None)
    assert compare_policy(unknown,BASE,date(2026,10,13)).expiry_status=='unknown'
    result=aggregate_policies({'s'},[dict(policy_id='p',shop_id='s',created_at=datetime.now(UTC),status='complete',is_demo=True,assessment=unknown.model_dump(),baseline=BASE.model_dump())],date(2026,10,13))
    assert result.assessed_known_coverage==0 and result.without_cover_percent_of_known is None and result.uninsured_stock_estimate_rm is None

def test_currency_evidence_accepts_adjacent_rm_amount_without_embedded_token():
    valid=assessment(sum_insured_rm=10000.,currency_evidence_quote='RM10,000.00',sum_insured_evidence_quote='Stock and contents sum insured RM10,000.00')
    assert valid.sum_insured_rm==10000.
    with pytest.raises(ValidationError):assessment(currency_evidence_quote='WORM60')

def test_sentence_final_period_preserves_exact_quoted_currency_amounts():
    value=assessment(sum_insured_rm=60000.,sum_insured_evidence_quote='Stock and contents sum insured MYR60,000.',excess_rm=1000.,excess_evidence_quote='Excess MYR1,000.')
    assert value.sum_insured_rm==60000. and value.excess_rm==1000.

@pytest.mark.parametrize('quote',['Stock sum insured MYR60,00.','Stock sum insured MYR60.000.','Stock sum insured MYR60..'])
def test_malformed_or_ambiguous_numeric_quotes_are_not_partially_accepted(quote):
    with pytest.raises(ValidationError):assessment(sum_insured_rm=60.,sum_insured_evidence_quote=quote)

def test_fire_only_quote_cannot_be_misclassified_as_explicit_flood_exclusion():
    with pytest.raises(ValidationError):assessment(flood_covered='no',coverage_evidence='excluded',evidence_quote='Fire, lightning and explosion are insured.')

@pytest.mark.parametrize('quote',['Flood is not excluded.','Flood excluded unless separately endorsed.','No flood exclusion applies.'])
def test_negated_or_conditional_exclusion_never_becomes_explicit_no(quote):
    with pytest.raises(ValidationError):assessment(flood_covered='no',coverage_evidence='excluded',evidence_quote=quote)

def test_recognizable_malay_exclusion_is_bounded_evidence_only():
    assert assessment(flood_covered='no',coverage_evidence='excluded',evidence_quote='Banjir dikecualikan.').flood_covered=='no'

def test_unrelated_quoted_limit_does_not_establish_a_currency_excess():
    with pytest.raises(ValidationError):assessment(excess_rm=60.,excess_evidence_quote='Stock sum insured MYR60')

@pytest.mark.parametrize('quote',['Fire cover only.','Flood is excluded.','Flood is not covered.','Flood included only if separately endorsed.'])
def test_yes_requires_recognizable_unconditional_affirmative_flood_wording(quote):
    with pytest.raises(ValidationError):assessment(evidence_quote=quote)

REVIEW_AMBIGUITIES=[
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is excluded. Flood is included.'),id='conflicting-flood-clauses'),
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is excluded in the base policy; endorsement includes flood.'),id='endorsement-base-conflict'),
    pytest.param(dict(sum_insured_scope='stock',sum_insured_evidence_quote='Stock sum insured EUR60'),id='amount-quote-non-MYR'),
    pytest.param(dict(sum_insured_scope='stock',sum_insured_evidence_quote='Stock sum insured 60'),id='amount-quote-no-currency'),
    pytest.param(dict(excess_rm=1000.,excess_evidence_quote='Excess RM1,000 if alarm fitted, otherwise RM2,000'),id='alternative-conditional-excess'),
    pytest.param(dict(excess_rm=1000.,excess_evidence_quote='Excess RM1,000 if alarm fitted'),id='single-conditional-excess'),
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is excluded. Flood is explicitly included.'),id='qualified-positive-conflict'),
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is excluded. Special perils are included.'),id='special-perils-conflict'),
    pytest.param(dict(sum_insured_evidence_quote='Stock sum insured EUR RM60'),id='mixed-amount-currency'),
    pytest.param(dict(currency_evidence_quote='Currency EUR and MYR'),id='mixed-currency-evidence'),
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is not covered under the base policy but is covered by endorsement.'),id='endorsement-without-repeated-flood'),
    pytest.param(dict(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is not covered but flood is included.'),id='negated-base-positive-endorsement'),
    pytest.param(dict(flood_covered='unclear',coverage_evidence='unclear',evidence_quote=None,sum_insured_rm=None,sum_insured_scope='unclear',excess_rm=1000.,excess_evidence_quote='Excess RM1,000 when unoccupied.'),id='when-conditional-excess'),
    pytest.param(dict(excess_rm=1000.,excess_evidence_quote='Excess RM1,000 during closure.'),id='unrecognized-excess-context'),
]

@pytest.mark.parametrize('changes',REVIEW_AMBIGUITIES)
def test_review_ambiguous_policy_fields_fail_closed(changes):
    with pytest.raises(ValidationError):assessment(**changes)

@pytest.mark.parametrize('quote',['Stock sum insured RM10,000.','Stock sum insured RM 10,000.','Stock sum insured MYR10,000.'])
def test_currency_is_attached_to_exact_valid_quoted_amount(quote):
    assert assessment(sum_insured_rm=10000.,sum_insured_evidence_quote=quote).sum_insured_rm==10000.

def test_real_pro_affirmative_fields_and_canonical_negative_remain_valid():
    value=assessment(insurer='Synthetic insurer',policy_type='Synthetic business policy',sum_insured_rm=60000.,sum_insured_evidence_quote='Stock and contents sum insured MYR60,000.',excess_rm=1000.,excess_evidence_quote='Excess MYR1,000.',expiry_date=date(2027,6,30),evidence_quote='Flood is included.')
    assert value.sum_insured_rm==60000. and value.excess_rm==1000.
    assert assessment(flood_covered='no',coverage_evidence='excluded',evidence_quote='Flood is not covered.').flood_covered=='no'

@pytest.mark.parametrize('quote',['Excess: MYR1,000.','Deductible is RM 1,000.','Lebihan of 1,000 MYR.'])
def test_canonical_fixed_excess_quote_shapes_remain_known(quote):
    assert assessment(excess_rm=1000.,excess_evidence_quote=quote).excess_rm==1000.
