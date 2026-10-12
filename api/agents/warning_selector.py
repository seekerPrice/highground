"""Useful actual ADK Warning selection; no action/risk authority in model output."""
from typing import Literal, TYPE_CHECKING
from uuid import uuid4
import json

from google.adk.agents.run_config import RunConfig
from google.adk.events import Event, EventActions
from google.adk.models.base_llm import BaseLlm
from google.adk.models import LlmResponse
from google.adk.runners import Runner
from google.genai import types
from pydantic import BaseModel, ConfigDict

from api.agents.coordinator import create_coordinator
from api.agents.sessions import create_session_service
from api.tools.firestore import create_async_firestore_client, close_async_firestore_client
from api.tools.gemini import create_vertex_client

if TYPE_CHECKING:
    from api.config import Settings


class WarningStructure(BaseModel):
    model_config = ConfigDict(extra='forbid')
    structure: Literal['warning_intro_fallback', 'warning_intro_actions']


class WarningSelector:
    def __init__(self, settings: 'Settings', *, model: BaseLlm | None = None,
                 root_collection: str = 'highground-dispatch-adk') -> None:
        self.settings, self.model, self.root_collection = settings, model, root_collection
        self._vertex = None

    async def __call__(self, event: dict, language: str, has_inventory: bool, has_vehicle: bool) -> WarningStructure:
        # This object is cheap; all clients/credentials are initialized only here.
        if event['level'] != 'warning':
            raise ValueError('ADK selector accepts Warning context only')
        if self.model is None:
            if not self.settings.gemini_fast_model.strip() or not self.settings.gemini_pro_model.strip():
                raise ValueError('Configured ADK models are unavailable')
            if self._vertex is None:
                self._vertex = create_vertex_client(self.settings)
        vertex = self._vertex
        client = create_async_firestore_client(self.settings)
        sessions = create_session_service(self.settings, client=client, root_collection=self.root_collection)
        context = dict(level='warning', language=language, is_demo=event['is_demo'],
                       inventory_available=has_inventory, vehicle_present=has_vehicle,
                       allowed_structures=['warning_intro_fallback', 'warning_intro_actions'])

        def get_warning_context() -> dict:
            """Read-only approved context. No recipients, amounts, instructions or destinations."""
            return dict(context)

        root = create_coordinator(self.settings, model=self.model, client=vertex)
        root.instruction = (
            'You are highground_coordinator. This is an approved Warning message-structure selection, '
            'not risk triage or dispatch. Transfer immediately to alert_agent. '
            'No messages or protective actions can be performed by this selector.'
        )
        def route_warning(callback_context, llm_request):
            # The deterministic input type already identifies the completed alert seam.
            # This is ADK's supported callback, not a simulated model response.
            return LlmResponse(content=types.Content(role='model', parts=[types.Part.from_function_call(
                name='transfer_to_agent', args={'agent_name':'alert_agent'})]))
        root.before_model_callback = route_warning
        alert = root.sub_agents[1]
        alert.tools = []
        alert.instruction = (
            'You are alert_agent selecting a committed localized Warning introduction. '
            'The validated context is supplied below; no context-tool roundtrip is required. '
            'Choose warning_intro_actions when inventory or vehicle facts benefit from an action-summary introduction, '
            'otherwise warning_intro_fallback. Return only JSON {"structure":"<approved key>"}. Do not write advice, amounts, times or destinations. '
            'This selection cannot authorize or perform dispatch. Validated context: '+json.dumps(get_warning_context())
        )
        alert.disallow_transfer_to_parent = True
        alert.disallow_transfer_to_peers = True
        # External output still receives strict Pydantic validation below.
        alert.output_schema = WarningStructure
        alert.output_key = 'warning_structure'
        for agent in [root, *root.sub_agents]:
            agent.generate_content_config = types.GenerateContentConfig(
                max_output_tokens=1024, thinking_config=types.ThinkingConfig(thinking_level='LOW'),
                http_options=types.HttpOptions(timeout=15000, retry_options=types.HttpRetryOptions(attempts=1)),
            )
        session_id = f"{event['event_id']}-{language}-{uuid4().hex}"
        kwargs = dict(app_name='highground_dispatch', user_id=f'selection-{language}', session_id=session_id)
        runner = Runner(app_name='highground_dispatch', agent=root, session_service=sessions)
        try:
            await sessions.create_session(**kwargs, state={'event_id':event['event_id'], 'simulation':event['is_demo']})
            message = types.Content(role='user', parts=[types.Part.from_text(
                text='Select the approved localized Warning structure using the supplied validated context. No tools or actions.')])
            result = None
            async for decision in runner.run_async(user_id=kwargs['user_id'], session_id=session_id,
                                                   new_message=message, run_config=RunConfig(max_llm_calls=4)):
                if decision.author == 'alert_agent' and decision.is_final_response() and decision.content:
                    text = ''.join(part.text or '' for part in decision.content.parts or [])
                    if len(text) > 1000:
                        raise ValueError('Selector output exceeds schema limit')
                    result = WarningStructure.model_validate_json(text, strict=True)
            if result is None:
                raise ValueError('Alert agent did not return an approved structure')
            session = await sessions.get_session(**kwargs)
            await sessions.append_event(session, Event(author='dispatch_validator',
                                                       actions=EventActions(state_delta={'validated_warning_structure':result.structure})))
            return result
        finally:
            await runner.close()
            await close_async_firestore_client(client)

    async def close(self) -> None:
        if self._vertex is not None:
            await self._vertex.aio.aclose()
            self._vertex.close()
            self._vertex = None
