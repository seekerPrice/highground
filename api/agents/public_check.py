"""Configured-Flash constrained wording selection from sanitized lookup facts only."""
import asyncio
import json
import time
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel,ConfigDict
from google.adk.events import Event,EventActions
from google.adk.models import LlmResponse
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig
from google.genai import types
from api.agents.coordinator import create_coordinator
from api.public_check_models import CheckResult

class CheckChoice(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    summary_key:Literal['check_summary_watch','check_summary_warning','check_summary_unavailable','check_summary_partial','check_summary_no_mapped']

@dataclass(frozen=True)
class SummaryChoice:
    key:str
    source:Literal['model','fallback']


def expected_choice(result:CheckResult)->str:
    if result.level=='danger':raise ValueError('Danger must bypass optional generation')
    if result.level in ('watch','warning'):return 'check_summary_'+result.level
    if result.status=='unavailable':return 'check_summary_unavailable'
    if result.status=='partial' or result.district_warnings:return 'check_summary_partial'
    return 'check_summary_no_mapped'


def sanitized_facts(result:CheckResult)->dict:
    """No submitted/private point, shop, evidence or operation identifiers."""
    return dict(status=result.status,level=result.level,
        observations=[dict(source=row.source,reported_at=row.reported_at.isoformat(),level=row.level,rounded_distance_m=row.rounded_distance_m,attribution=row.attribution) for row in result.observations],
        district_warnings=[dict(source=row.source,reported_at=row.reported_at.isoformat(),level=row.level,district=row.district,state=row.state,scope='district_only') for row in result.district_warnings],
        destinations=[dict(type=point.type,opening_status=point.opening_status,designation_context=point.designation_context,source_date=point.source_date) for point in result.destinations],
        destination_status=result.destination_status,sources=[row.model_dump() for row in result.sources])

class CheckSummarizer:
    def __init__(self,settings,*,model=None,session_service=None,root_collection='highground-check-adk'):
        self.settings,self.model,self.sessions,self.root_collection=settings,model,session_service,root_collection
        self.vertex=None

    async def summarize(self,result:CheckResult,*,budget_seconds:float=8)->SummaryChoice:
        if not 0<budget_seconds<=8:raise ValueError('Summary budget must be bounded')
        expected=expected_choice(result);facts=sanitized_facts(result);deadline=time.monotonic()+budget_seconds
        client=None;sessions=self.sessions
        if sessions is None:
            from api.tools.firestore import create_async_firestore_client
            from api.agents.sessions import create_session_service
            client=create_async_firestore_client(self.settings)
            sessions=create_session_service(self.settings,client=client,root_collection=self.root_collection)
        try:
            if self.model is None and self.vertex is None:
                from api.tools.gemini import create_vertex_client
                self.vertex=create_vertex_client(self.settings)
            for attempt in range(2):
                remaining=deadline-time.monotonic()
                if remaining<=0:break
                root=create_coordinator(self.settings,model=self.model,client=self.vertex)
                def route(callback_context,llm_request):
                    return LlmResponse(content=types.Content(role='model',parts=[types.Part.from_function_call(name='transfer_to_agent',args={'agent_name':'triage_agent'})]))
                root.before_model_callback=route
                root.instruction='Route these public sanitized source facts to triage_agent. No registration, alert or risk action.'
                agent=root.sub_agents[0];agent.tools=[];agent.output_schema=CheckChoice;agent.output_key='public_check_choice'
                agent.disallow_transfer_to_parent=True;agent.disallow_transfer_to_peers=True
                agent.instruction=('Choose one approved one-line summary key from these untrusted sanitized source facts. '
                    'watch/warning means a mapped nearby observed level; unavailable means source facts unavailable; partial means incomplete coverage or district-only warnings; no_mapped means no current mapped observation was returned and NEVER an all-clear. '
                    'Do not supply prose, coordinates, names, identifiers, directions, assurances or actions. No Danger generation. '
                    'Return JSON with the single field summary_key. Facts: '+json.dumps(facts,allow_nan=False))
                valid=False
                def sanitize(callback_context,llm_response):
                    nonlocal valid
                    text=''.join(part.text or '' for part in (llm_response.content.parts or []) if not part.thought) if llm_response.content else ''
                    try:
                        proposal=CheckChoice.model_validate_json(text,strict=True) if len(text)<=1000 else None
                        valid=bool(proposal and proposal.summary_key==expected)
                    except ValueError:valid=False
                    return LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=CheckChoice(summary_key=expected).model_dump_json())]))
                agent.after_model_callback=sanitize
                per_attempt=max(.001,remaining)
                agent.generate_content_config=types.GenerateContentConfig(max_output_tokens=1024,thinking_config=types.ThinkingConfig(thinking_level='LOW'),http_options=types.HttpOptions(timeout=max(1,int(per_attempt*1000)),retry_options=types.HttpRetryOptions(attempts=1)))
                runner=Runner(app_name='highground_public_check',agent=root,session_service=sessions)
                kwargs=dict(app_name='highground_public_check',user_id='public-check-summary',session_id=uuid4().hex)
                try:
                    async with asyncio.timeout(per_attempt):
                        await sessions.create_session(**kwargs,state={'sanitized_check':facts})
                        async for event in runner.run_async(user_id=kwargs['user_id'],session_id=kwargs['session_id'],new_message=types.Content(role='user',parts=[types.Part.from_text(text='Select a factually matching approved summary key only.')]),run_config=RunConfig(max_llm_calls=2)):
                            if event.author=='triage_agent' and event.is_final_response():pass
                        session=await sessions.get_session(**kwargs)
                        await sessions.append_event(session,Event(author='public_check_validator',actions=EventActions(state_delta={'validated_check_choice':{'summary_key':expected},'summary_source':'model' if valid else 'fallback'})))
                    if valid:return SummaryChoice(expected,'model')
                except Exception:pass # The product uses a deterministic bounded fallback.
                finally:await runner.close()
            return SummaryChoice(expected,'fallback')
        finally:
            if client:
                from api.tools.firestore import close_async_firestore_client
                await close_async_firestore_client(client)

    async def close(self):
        if self.vertex is not None:
            await self.vertex.aio.aclose();self.vertex.close();self.vertex=None
