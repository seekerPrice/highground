import json
from google.adk.models import LlmResponse
from google.genai import types
from api.agents.policy import sanitized_policy_response
from api.tests.test_policy_models import assessment

def test_raw_ocr_and_provider_metadata_are_removed_before_persistence():
    raw='PRIVATE_FULL_OCR'*1000
    response=LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=raw)]),custom_metadata={'raw':raw},input_transcription=types.Transcription(text=raw))
    clean,result=sanitized_policy_response(response)
    assert result is None and raw not in clean.model_dump_json() and 'PRIVATE_FULL_OCR' not in clean.model_dump_json()
    assert clean.custom_metadata is None and clean.input_transcription is None

def test_valid_bounded_fields_survive_but_unrelated_response_metadata_does_not():
    response=LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=assessment().model_dump_json())]),custom_metadata={'ocr':'PRIVATE_FULL_OCR'})
    clean,result=sanitized_policy_response(response)
    assert result==assessment() and json.loads(clean.content.parts[0].text)['flood_covered']=='yes'
    assert 'PRIVATE_FULL_OCR' not in clean.model_dump_json()

import pytest
from datetime import UTC,datetime,date
from api.policy_models import PolicyAssessment,aggregate_policies
from api.tests.test_policy_models import REVIEW_AMBIGUITIES,BASE

@pytest.mark.parametrize('changes',REVIEW_AMBIGUITIES)
def test_review_wire_ambiguity_becomes_sanitized_unknown_and_never_known_aggregate(changes):
    # Wire data is external JSON, not a prevalidated domain object.
    wire=assessment().model_dump(mode='json')|changes
    clean,result=sanitized_policy_response(LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=json.dumps(wire))])))
    assert result is None
    safe=PolicyAssessment.model_validate_json(clean.content.parts[0].text)
    assert safe.flood_covered=='unclear' and safe.coverage_evidence=='unclear'
    assert safe.sum_insured_rm is None and safe.excess_rm is None and safe.evidence_quote is None
    aggregate=aggregate_policies({'synthetic'},[dict(policy_id='p',shop_id='synthetic',created_at=datetime.now(UTC),status='complete',is_demo=True,assessment=safe.model_dump(),baseline=BASE.model_dump())],date(2026,10,13))
    assert aggregate.assessed_known_coverage==0 and aggregate.unclear_or_expired==1 and aggregate.missing_policies==0
    assert aggregate.without_cover_percent_of_known is None and aggregate.uninsured_stock_estimate_rm is None and aggregate.unknown_stock_estimates==1
