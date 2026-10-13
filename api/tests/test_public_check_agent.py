"""Actual ADK runner with in-memory sessions; no SDK/model acceptance claim."""
import asyncio,json
from google.adk.models import BaseLlm,LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import PrivateAttr
from api.agents.public_check import CheckSummarizer,sanitized_facts,expected_choice
from api.config import Settings
from api.tests.test_public_check import LOCATION,NOW,source,warning,report,project_check

class ChoiceModel(BaseLlm):
    model:str='synthetic-check-model'
    _calls:int=PrivateAttr(default=0)
    _first_invalid:bool=PrivateAttr(default=False)
    async def generate_content_async(self,request,stream=False):
        self._calls+=1
        payload=str(request.config.system_instruction)+str(request.contents)
        for forbidden in ('PRIVATE-SHOP','PRIVATE-STATION','PRIVATE SOURCE REASON','sha256','report_id','shop_id','latitude','longitude'):
            assert forbidden not in payload
        assert '1000' in payload and 'warning' in payload
        schema=request.config.response_schema.model_json_schema()
        assert 'check_summary_warning' in schema['properties']['summary_key']['enum']
        response='RAW-MODEL-CANARY safe to reopen now' if self._first_invalid and self._calls==1 else '{"summary_key":"check_summary_warning"}'
        yield LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=response)]))


def test_actual_adk_sanitized_choice_retry_trace_has_no_private_facts_or_bad_prose():
    async def run():
        model=ChoiceModel();model._first_invalid=True;sessions=InMemorySessionService()
        result=project_check(LOCATION,(source(warning()),),(),(),now=NOW)
        agent=CheckSummarizer(Settings(),model=model,session_service=sessions)
        summary=await agent.summarize(result)
        assert summary.key=='check_summary_warning' and summary.source=='model' and model._calls==2
        listing=await sessions.list_sessions(app_name='highground_public_check',user_id='public-check-summary')
        assert len(listing.sessions)==2
        for entry in listing.sessions:
            session=await sessions.get_session(app_name='highground_public_check',user_id='public-check-summary',session_id=entry.id)
            trace=session.model_dump_json()
            for forbidden in ('RAW-MODEL-CANARY','PRIVATE-STATION','PRIVATE SOURCE REASON','latitude','longitude','shop_id','report_id'):
                assert forbidden not in trace
            assert all(part.inline_data is None for event in session.events if event.content for part in event.content.parts or [])
            assert session.state['validated_check_choice']['summary_key']=='check_summary_warning'
        await agent.close()
    asyncio.run(run())


def test_danger_bypasses_model_and_sanitized_facts_exclude_exact_private_point():
    result=project_check(LOCATION,(),(report(),),(),now=NOW)
    data=json.dumps(sanitized_facts(result))
    assert 'PRIVATE-SHOP' not in data and 'lat' not in data and 'lng' not in data and 'sha256' not in data
    import pytest
    with pytest.raises(ValueError):expected_choice(result)
