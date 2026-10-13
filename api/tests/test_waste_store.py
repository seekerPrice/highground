"""Actual Firestore atomic waste facts and owner-only current-item actions."""
import os
from datetime import UTC,datetime
from uuid import uuid4
import pytest
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.report_store import ReportStore
from api.waste_store import WasteStore,WasteDanger
from api.agents.loss_comparison import parse_loss_comparison
from api.tests.test_waste import BASE,MEDIA,loss
from api.tests.test_waste_comparison import wire
from api.tests.test_inventory import video,item as inventory_item

pytestmark=pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')

@pytest.fixture
def setup():
    client=create_firestore_client(Settings(gcp_project='highground-waste-tests'));prefix='waste-'+uuid4().hex+'-'
    reports=ReportStore(client,'synthetic',prefix);waste=WasteStore(client,'synthetic',prefix,risks=reports.risk_store)
    reports.collection('shops').document('shop').set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='inv',recipients=[dict(telegram_chat_id=123,language='en',role='owner'),dict(telegram_chat_id=456,language='en',role='worker')]))
    reports.collection('inventories').document('inv').set(dict(BASE,items=[inventory_item(qty=2.,est_unit_value_rm=20.).model_dump()],media_id='c'*64,confidence=.8,confidence_note='Synthetic',shop_id='shop'))
    yield reports,waste
    try:
        for name in ('shops','inventories','recovery_jobs','recovery_current','recovery_private','recovery_intents','recovery_uploads','waste_assessments','waste_scopes','waste_current','waste_actions','waste_street_intents','waste_action_operations','active_risks','demo_scenario'):
            for doc in client.collection(prefix+name).stream(timeout=8,retry=None):doc.reference.delete(timeout=5,retry=None)
    finally:client.close()


def complete(reports,operation='first',*,unavailable=False):
    job=reports.start(reports.owner_shop(123),123,operation)
    reports.collection('recovery_jobs').document(job['report_id']).update({'status':'awaiting_video'})
    owner=reports.claim_job(job['report_id']);now=datetime.now(UTC)
    message_id=10 if operation=='first' else 11
    reports.bind_upload(job['report_id'],123,message_id,now,video(),now)
    reports.select_upload(job['report_id'],owner,123,message_id,video().file_unique_id,MEDIA)
    # Non-food canonical baseline permits uncertain, sealed salvage classification.
    base=job['baseline'];base['items'][0]['category']='household'
    reports.collection('recovery_jobs').document(job['report_id']).update({'baseline':base})
    candidate=wire(items=[dict(wire()['items'][0],material='sealed_metal',disposition='salvage_clean',contamination='not_observed')])
    result=parse_loss_comparison(loss().model_dump()|{'waste':candidate},base,video().duration,MEDIA)
    if unavailable:result=result.model_copy(update={'waste_status':'unavailable','waste':None})
    reports.complete_assessment(job['report_id'],owner,result)
    return reports.collection('recovery_jobs').document(job['report_id']).get().to_dict(),owner,result


def test_atomic_completion_roundtrip_owner_consent_and_baseline_refresh(setup):
    reports,waste=setup;job,owner,result=complete(reports)
    fact=waste.collection('waste_assessments').document(job['report_id']).get().to_dict()
    assert fact['assessment']['assessment_media_id']==MEDIA
    action=job['donation_actions']['inv:0']
    assert not waste.action(action,123).get('available',False)
    for sender in (456,999):
        with pytest.raises(PermissionError):waste.confirm(action,sender)
    waste.confirm(action,123)
    assert waste.action(action,123)['available'] is True
    waste.confirm(action,123,available=False)
    assert waste.action(action,123)['available'] is False
    reports.complete_assessment(job['report_id'],owner,result)
    assert len(list(waste.collection('waste_assessments').stream()))==1
    assert len(list(waste.collection('waste_actions').stream()))==1
    reports.collection('shops').document('shop').update({'baseline_inventory_id':'new'})
    with pytest.raises(ValueError):waste.confirm(action,123)
    assert waste.report_context(job,'example_bot')['donations']['inv:0']['action_url'] is None


def test_danger_arriving_after_prompt_blocks_street_and_donation(setup):
    reports,waste=setup;job,_,_=complete(reports)
    street=waste.stage_street(123,'  Jalan Example  ','street')
    action=job['donation_actions']['inv:0'];waste.action(action,123)
    reports.collection('shops').document('shop').update({'active_danger':True})
    for identity in (street['action_id'],action):
        with pytest.raises(WasteDanger):waste.confirm(identity,123)
    row=reports.collection('shops').document('shop').get().to_dict()
    assert 'owner_confirmed_street' not in row
    assert not waste.collection('waste_actions').document(action).get().to_dict().get('available',False)


def test_public_projection_missing_denominator_street_confirmation_and_private_exclusion(setup):
    reports,waste=setup
    reports.collection('shops').document('empty').set(dict(is_demo=True,lat=3.,lng=101.,recipients=[]))
    reports.collection('shops').document('private').set(dict(is_demo=False,lat=3.,lng=101.,recipients=[]))
    empty=waste.public(10.)
    assert empty.status=='empty' and empty.registered_synthetic_shops==2 and empty.missing_or_unavailable_shops==2
    job,_,_=complete(reports)
    before=waste.public(10.)
    assert before.assessed_shops==1 and before.missing_or_unavailable_shops==1
    assert before.aggregate.streets[0].street=='Unassigned'
    action=waste.stage_street(123,'Jalan Example','street')
    waste.confirm(action['action_id'],123)
    after=waste.public(20.)
    assert after.aggregate.streets[0].street=='Jalan Example'
    assert after.aggregate.streets[0].estimated_load_equivalents==.05
    public=after.model_dump_json()
    assert all(s not in public for s in ('shop_id','report_id','media_id','episode_id','telegram','sender','private'))
    assert waste.collection('waste_assessments').document(job['report_id']).get().to_dict()['owner_confirmed_street'] is None


def test_unattributed_scope_is_stable_across_new_report_same_inventory(setup):
    reports,_=setup;first=reports.start(reports.owner_shop(123),123,'first')
    reports.collection('recovery_jobs').document(first['report_id']).update({'status':'assessment_unavailable'})
    second=reports.start(reports.owner_shop(123),123,'second')
    assert first['report_id']!=second['report_id']
    assert first['waste_episode_id']==second['waste_episode_id']
    assert first['waste_episode_attribution']=='unattributed_shop_inventory_scope'


def test_old_street_confirmation_replay_cannot_revert_new_label(setup):
    reports,waste=setup
    first=waste.stage_street(123,'Jalan A','a');waste.confirm(first['action_id'],123)
    second=waste.stage_street(123,'Jalan B','b');waste.confirm(second['action_id'],123)
    before=reports.collection('shops').document('shop').get().to_dict()
    waste.confirm(first['action_id'],123)
    after=reports.collection('shops').document('shop').get().to_dict()
    assert after==before and after['owner_confirmed_street']=='Jalan B'


def test_scenario_reset_excludes_old_facts_actions_and_preserves_history(setup):
    reports,waste=setup
    scenario=reports.collection('demo_scenario').document('current');scenario.set({'generation':1,'state':'ready'})
    job,_,_=complete(reports);action=job['donation_actions']['inv:0']
    street=waste.stage_street(123,'Jalan Old','old');waste.confirm(street['action_id'],123)
    assert waste.public(10.).assessed_shops==1
    scenario.set({'generation':2,'state':'resetting'})
    assert waste.public(10.).status=='unavailable'
    with pytest.raises(ValueError):waste.confirm(action,123)
    scenario.set({'generation':2,'state':'ready'})
    public=waste.public(10.)
    assert public.status=='empty' and public.assessed_shops==0 and public.missing_or_unavailable_shops==1
    for identity in (action,street['action_id']):
        with pytest.raises(ValueError):waste.confirm(identity,123)
    assert waste.collection('waste_assessments').document(job['report_id']).get().exists


def test_new_unavailable_completion_suppresses_old_donation_and_known_waste(setup):
    reports,waste=setup;first,_,_=complete(reports)
    action=first['donation_actions']['inv:0'];waste.confirm(action,123)
    second,_,_=complete(reports,'replacement',unavailable=True)
    assert second['report_id']!=first['report_id']
    with pytest.raises(ValueError):waste.confirm(action,123)
    assert waste.report_context(first,'example_bot')['donations']['inv:0']['action_url'] is None
    summary=waste.public(10.)
    assert summary.status=='empty' and summary.assessed_shops==0 and summary.missing_or_unavailable_shops==1
    assert summary.aggregate.streets==()
    assert waste.collection('waste_assessments').document(first['report_id']).get().exists
    assert not waste.collection('waste_assessments').document(second['report_id']).get().exists
