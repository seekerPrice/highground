"""Sanitized report facts and public unknown denominators."""
from datetime import UTC,datetime
import pytest
from api.waste_models import WasteResponse
from api.tests.test_waste import BASE,MEDIA,loss,record
from api.agents.loss_comparison import parse_loss_comparison
from api.tests.test_waste_comparison import wire


def test_report_uncertainty_is_canonical_and_no_model_safety_assurance():
    from api.waste import report_waste
    result=parse_loss_comparison(loss().model_dump()|{'waste':wire(items=[dict(wire()['items'][0],uncertainty='safe to donate; collection guaranteed')])},BASE,10,MEDIA)
    projected=report_waste(result)
    assert projected.status=='available' and projected.items[0].uncertainty=='Visual classification or quantities remain uncertain; confirm appropriate handling independently.'
    assert 'collection guaranteed' not in projected.model_dump_json()
    assert 'safe to donate' not in projected.model_dump_json()
    assert not projected.items[0].donation_available
    assert projected.owner_confirmed_street is None and projected.street_assignment_source=='unassigned'
    assert report_waste(loss()).status=='not_assessed'


def test_empty_waste_denominator_is_missing_assessments_not_known_zero():
    from api.waste import aggregate_waste
    base=dict(status='empty',generated_at=datetime.now(UTC),registered_synthetic_shops=6,assessed_shops=0,missing_or_unavailable_shops=6,aggregate=aggregate_waste([],synthetic_shop_ids={'shop'}),note='No completed assessment; quantities unavailable.')
    result=WasteResponse(**base)
    assert result.assessed_shops==0 and result.missing_or_unavailable_shops==6
    for changes in ({'missing_or_unavailable_shops':0},{'aggregate':None},{'status':'available'}):
        with pytest.raises(ValueError):WasteResponse(**(base|changes))
    unknown=WasteResponse(**(base|dict(status='unavailable',assessed_shops=None,missing_or_unavailable_shops=None,aggregate=None)))
    assert unknown.aggregate is None
    with pytest.raises(ValueError):WasteResponse(**(base|dict(status='unavailable',aggregate=None)))


def report_reader(assessment):
    from hashlib import sha256
    from api.tests.test_reports import ReaderStore,Records
    from api.report_api import ReportReader
    from api.media_models import MediaRecord
    now=datetime(2026,10,13,tzinfo=UTC);identity='b'*32
    store=ReaderStore()
    store.jobs[identity]=dict(report_id=identity,shop_id='shop',shop_name='Synthetic waste fixture',is_demo=True,created_at=now,media_id=MEDIA,baseline=dict(BASE,media_id='c'*64),assessment=assessment.model_dump(mode='json'),upload={'duration':10},recovery_attribution='Synthetic owner-declared recovery, not proof of clearance.',evidence_media_ids=['c'*64,MEDIA])
    record=dict(shop_id='shop',sender_hash='PRIVATE',sha256=sha256(b'synthetic').hexdigest(),bytes=9,mime_type='video/mp4',uploaded_at=now,received_at=now,telegram_date=now,lat=3.,lng=101.,location_attribution='confirmed_shop',is_demo=True,storage_status='done',ledger_status='done')
    records=Records({MEDIA:MediaRecord(media_id=MEDIA,kind='after_video',**record),'c'*64:MediaRecord(media_id='c'*64,kind='baseline_video',**record)})
    return ReportReader(store,records,None),identity


def test_actual_report_reader_loss_receipts_unchanged_and_waste_no_untrusted_prose():
    original=loss()
    assessed=parse_loss_comparison(original.model_dump()|{'waste':wire(items=[dict(wire()['items'][0],uncertainty='safe to donate')])},BASE,10,MEDIA)
    reader,identity=report_reader(assessed)
    result=reader.report(identity,'Bearer '+identity+'-token')
    old_reader,_=report_reader(original);old=old_reader.report(identity,'Bearer '+identity+'-token')
    assert result.model_dump(exclude={'waste'})==old.model_dump(exclude={'waste'})
    assert result.waste.status=='available' and old.waste.status=='not_assessed'
    assert result.waste.items[0].item_id==result.items[0].item_id
    assert result.assessment_media_id==MEDIA and 'safe to donate' not in result.model_dump_json()
    with pytest.raises(PermissionError):reader.report(identity,'Bearer wrong')


def test_omitted_loss_row_keeps_frozen_display_name_for_waste_join():
    original=loss().model_copy(update={'items':[],'total_loss_rm':None})
    assessed=parse_loss_comparison(original.model_dump()|{'waste':wire(items=[])},BASE,10,MEDIA)
    reader,identity=report_reader(assessed)
    report=reader.report(identity,'Bearer '+identity+'-token')
    names={item.item_id:item.name for item in report.items}
    assert report.waste.items[0].item_id in names
    assert names[report.waste.items[0].item_id]=='Rice'
    assert report.items[0].condition=='unassessed' and report.items[0].estimated_loss_rm is None


def test_captured_pro_loss_prose_never_becomes_cleaning_advice_in_report():
    import json
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/waste-pro-response.json').read_text())
    result=parse_loss_comparison(fixture['response'],fixture['baseline'],30,MEDIA)
    reader,identity=report_reader(result)
    reader.store.jobs[identity]['baseline']=fixture['baseline']
    reader.store.jobs[identity]['upload']['duration']=30
    report=reader.report(identity,'Bearer '+identity+'-token')
    assert report.estimated_loss_rm==268. and report.waste.status=='unavailable'
    assert 'thorough cleaning' not in report.model_dump_json() and 'seal integrity' not in report.model_dump_json()
    assert len(report.items)==3


def test_report_read_uses_normalized_category_precedence_for_stored_waste():
    from api.tests.test_waste import assessment,item
    stored=loss().model_copy(update={'waste_status':'available','waste':assessment(items=(item(),))})
    reader,identity=report_reader(stored)
    reader.store.jobs[identity]['baseline']['items'][0]['category']='Food Staples'
    report=reader.report(identity,'Bearer '+identity+'-token')
    assert report.waste.items[0].disposition=='discard_contaminated'
    assert report.waste.items[0].contamination=='present'
    assert not report.waste.items[0].donation_eligible


def test_lorry_capacity_configuration_is_positive_finite_and_env_loaded(monkeypatch):
    from api.config import Settings,load_settings
    assert Settings().lorry_capacity_m3==10.
    for value in (0.,-1.,float('nan'),float('inf'),True):
        with pytest.raises(ValueError):Settings(lorry_capacity_m3=value)
    monkeypatch.setenv('LORRY_CAPACITY_M3','12.5')
    assert load_settings().lorry_capacity_m3==12.5


def test_public_waste_router_is_synthetic_only_and_never_uses_capability():
    import json
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.waste_api import create_waste_router
    from api.config import Settings
    response=WasteResponse.model_validate_json((Path(__file__).parent/'fixtures/waste-response.json').read_text())
    class Store:
        def public(self,capacity):assert capacity==10.;return response
    app=FastAPI();app.include_router(create_waste_router(Settings(),Store()))
    with TestClient(app) as client:
        result=client.get('/api/waste',headers={'Authorization':'Bearer PRIVATE-CAPABILITY','Cookie':'PRIVATE-SESSION'})
        assert result.status_code==200 and result.headers['cache-control']=='no-store'
        assert result.json()['is_demo'] is True
        assert 'PRIVATE' not in result.text and 'media_id' not in result.text and 'shop_id' not in result.text
