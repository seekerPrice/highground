"""Run a fake warning through the actual ADK runner and Firestore emulator.

Usage: .venv/bin/python -m api.agents.simulate
No real Gemini invocation or Telegram dispatch. Model turns are scripted fakes.
"""
import asyncio
import json
import os
from uuid import uuid4

from google.adk.agents.run_config import RunConfig
from google.adk.models import LlmRequest, LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.adk.runners import Runner
from google.genai import types
from pydantic import PrivateAttr

from api.agents.coordinator import create_coordinator
from api.agents.sessions import create_session_service, session_user_id
from api.config import Settings, load_settings
from api.tools.firestore import create_async_firestore_client, close_async_firestore_client


class SimulatedModel(BaseLlm):
    """Scripted model double; only usable for the explicitly labelled simulation."""
    model: str = 'simulation-only-no-network'
    _turn: int = PrivateAttr(default=0)

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        turns = [
            ('transfer_to_agent', {'agent_name': 'triage_agent'}),
            ('get_official_warnings', {}),
            ('transfer_to_agent', {'agent_name': 'alert_agent'}),
            ('get_shop_profile', {'shop_id': 'simulation-shop'}),
        ]
        if self._turn < len(turns):
            name, args = turns[self._turn]
            if name not in llm_request.tools_dict:
                raise RuntimeError('Simulation tool unavailable in current ADK agent')
            part = types.Part.from_function_call(name=name, args=args)
        else:
            part = types.Part.from_text(text=json.dumps({
                'simulation': True, 'status': 'not_implemented',
                'decision': 'No risk classification or alert was performed.',
            }))
        self._turn += 1
        yield LlmResponse(content=types.Content(role='model', parts=[part]))


async def run_fake_warning(settings: Settings, *, root_collection: str = 'highground-adk-simulation') -> list[dict]:
    if not os.environ.get('FIRESTORE_EMULATOR_HOST'):
        raise ValueError('FIRESTORE_EMULATOR_HOST is required; simulation is local only')
    client = create_async_firestore_client(settings)
    service = create_session_service(settings, root_collection=root_collection, client=client)
    user_id = session_user_id(-1, settings.hash_salt)
    session_id = f'simulation-{uuid4().hex}'
    runner = Runner(app_name='highground_simulation',
                    agent=create_coordinator(settings, model=SimulatedModel()), session_service=service)
    output: list[dict] = []
    try:
        await service.create_session(app_name='highground_simulation', user_id=user_id,
                                     session_id=session_id, state={'simulation': True})
        message = types.Content(role='user', parts=[types.Part.from_text(
            text='SIMULATION: fake flood warning for simulation-shop. Inspect stub decisions only; no real alerts.')])
        async with asyncio.timeout(20):
            async for event in runner.run_async(user_id=user_id, session_id=session_id,
                                                new_message=message, run_config=RunConfig(max_llm_calls=8)):
                parts = event.content.parts if event.content else []
                for part in parts or []:
                    if part.function_call:
                        output.append({'simulation': True, 'agent': event.author,
                                       'tool': part.function_call.name})
                    if part.function_response:
                        response = part.function_response.response
                        output.append({'simulation': True, 'agent': event.author,
                                       'tool_result': part.function_response.name,
                                       'status': response.get('status', 'routing_only')})
                    if part.text:
                        output.append({'simulation': True, 'agent': event.author, 'text': part.text})
        return output
    finally:
        await service.delete_session(app_name='highground_simulation', user_id=user_id, session_id=session_id)
        await runner.close()
        await close_async_firestore_client(client)


def main() -> None:
    for decision in asyncio.run(run_fake_warning(load_settings())):
        print(json.dumps(decision))


if __name__ == '__main__':
    main()
