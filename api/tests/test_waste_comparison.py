"""Existing loss wire result survives an independent unavailable waste block."""
from api.agents.loss_comparison import parse_loss_comparison
from api.tests.test_waste import BASE,MEDIA,loss


def wire(**changes):
    return dict(confidence=.8,items=[dict(item_id='inv:0',disposition='discard_contaminated',est_volume_m3=1.,est_weight_kg=2.,material='food',floodwater_contact='yes',contamination='present',uncertainty=None)])|changes


def test_independent_invalid_waste_preserves_original_loss_and_selected_identity():
    original=loss();payload=original.model_dump()|{'waste':wire(items=[dict(wire()['items'][0],item_id='invented')])}
    result=parse_loss_comparison(payload,BASE,10,MEDIA)
    assert result.waste_status=='unavailable' and result.waste is None
    assert result.model_dump(exclude={'waste','waste_status'})==original.model_dump(exclude={'waste','waste_status'})
    valid=parse_loss_comparison(original.model_dump()|{'waste':wire()},BASE,10,MEDIA)
    assert valid.waste_status=='available'
    assert valid.waste.inventory_id=='inv' and valid.waste.assessment_media_id==MEDIA
    assert valid.total_loss_rm==20. and valid.items==original.items


def test_unexpected_model_condition_cannot_override_or_be_silently_dropped():
    original=loss()
    candidate=wire(items=[dict(wire()['items'][0],condition='destroyed')])
    result=parse_loss_comparison(original.model_dump()|{'waste':candidate},BASE,10,MEDIA)
    assert result.waste_status=='unavailable' and result.waste is None
    assert result.items==original.items


def test_missing_loss_rows_are_only_canonical_unassessed_waste_rows():
    original=loss().model_copy(update={'items':[],'total_loss_rm':None})
    result=parse_loss_comparison(original.model_dump()|{'waste':wire(items=[])},BASE,10,MEDIA)
    assert result.items==[] and result.total_loss_rm is None
    assert result.waste.items[0].condition=='unassessed'
    assert result.waste.items[0].est_volume_m3 is None
    stored=__import__('json').loads(result.model_dump_json())
    from api.report_models import LossAssessment
    assert LossAssessment.model_validate(stored).waste==result.waste


def test_captured_pro_contaminated_bottled_water_never_relaxes_salvage_guard():
    import json
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/waste-pro-response.json').read_text())
    result=parse_loss_comparison(fixture['response'],fixture['baseline'],30,MEDIA)
    assert result.total_loss_rm==268. and len(result.items)==3
    assert result.waste_status=='unavailable' and result.waste is None


def test_captured_pro_omitted_ok_rows_are_unaffected_without_invented_waste():
    import json
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/waste-journey-response.json').read_text())
    result=parse_loss_comparison(fixture['response'],fixture['baseline'],30,MEDIA)
    assert result.waste_status=='available'
    assert len(result.items)==len(result.waste.items)==6
    assert result.total_loss_rm==fixture['response']['total_loss_rm']
    assert result.waste.assessment_media_id==MEDIA
    ok=[row for row in result.waste.items if row.condition=='ok']
    assert len(ok)==2
    for row in ok:
        assert row.disposition is None and row.est_volume_m3 is None and row.est_weight_kg is None
        assert row.material==row.floodwater_contact==row.contamination=='unknown'
