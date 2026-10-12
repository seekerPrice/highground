import asyncio
import os
from uuid import uuid4

import pytest
from google.adk.errors import StaleSessionError
from google.adk.events import Event, EventActions
from google.genai import types

from api.agents.coordinator import create_coordinator
from api.agents.sessions import create_session_service, session_user_id
from api.agents.simulate import SimulatedModel, run_fake_warning
from api.agents.stubs import send_telegram
from api.config import Settings
from api.tools.firestore import create_async_firestore_client, create_firestore_client, close_async_firestore_client


def test_adk_structure_and_stubs_do_not_dispatch():
    root = create_coordinator(Settings(), model=SimulatedModel())
    assert root.name == 'highground_coordinator'
    assert [agent.name for agent in root.sub_agents] == ['triage_agent', 'alert_agent', 'loss_agent']
    assert all(agent.parent_agent is root for agent in root.sub_agents)
    assert send_telegram('private-chat', 'private-message')['status'] == 'not_implemented'
    assert 'private' not in str(send_telegram('private-chat', 'private-message'))
    with pytest.raises(ValueError):
        create_coordinator(Settings())


def test_hashed_session_identity_and_explicit_project(monkeypatch):
    assert session_user_id(123, 'test-salt') == session_user_id(123, 'test-salt')
    assert session_user_id(123, 'test-salt') != session_user_id(123, 'other-salt')
    assert len(session_user_id(123, 'test-salt')) == 64
    with pytest.raises(ValueError):
        session_user_id(123, '')
    with pytest.raises(ValueError):
        session_user_id(True, 'test-salt')
    with pytest.raises(ValueError):
        create_firestore_client(Settings())
    monkeypatch.setenv('FIRESTORE_EMULATOR_HOST', '127.0.0.1:8787')
    client = create_firestore_client(Settings(gcp_project='highground-task6-tests'))
    assert client.project == 'highground-task6-tests'
    client.close()


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'), reason='local emulator required')
def test_real_firestore_adk_session_reconstruction_and_stale_write():
    async def run():
        settings = Settings(gcp_project='highground-task6-tests')
        namespace = 'task6-'+uuid4().hex
        client = create_async_firestore_client(settings)
        other_client = create_async_firestore_client(settings)
        service = create_session_service(settings, root_collection=namespace, client=client)
        other = create_session_service(settings, root_collection=namespace, client=other_client)
        kwargs = dict(app_name='session_test', user_id='hashed-test-user', session_id='test-session')
        try:
            session = await service.create_session(**kwargs, state={'stage': 'start'})
            stale = await other.get_session(**kwargs)
            event = Event(author='highground_coordinator', invocation_id='test',
                          content=types.Content(role='model', parts=[types.Part.from_text(text='synthetic')]),
                          actions=EventActions(state_delta={'stage': 'next'}))
            await service.append_event(session, event)
            restored = await other.get_session(**kwargs)
            assert restored.state['stage'] == 'next'
            assert restored.events[0].id == event.id
            with pytest.raises(StaleSessionError):
                await other.append_event(stale, Event(author='highground_coordinator',
                                                     actions=EventActions(state_delta={'stage': 'wrong'})))
            partial = Event(author='highground_coordinator', partial=True,
                            actions=EventActions(state_delta={'stage': 'partial'}))
            await other.append_event(restored, partial)
            assert (await service.get_session(**kwargs)).state['stage'] == 'next'
        finally:
            await service.delete_session(**kwargs)
            await close_async_firestore_client(client)
            await close_async_firestore_client(other_client)
    asyncio.run(run())


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'), reason='local emulator required')
def test_actual_adk_runner_fake_warning_no_real_decisions():
    settings = Settings(gcp_project='highground-task6-tests', hash_salt='synthetic-only')
    output = asyncio.run(run_fake_warning(settings, root_collection='task6-'+uuid4().hex))
    assert all(row['simulation'] is True for row in output)
    assert {row['agent'] for row in output} == {'highground_coordinator', 'triage_agent', 'alert_agent'}
    tool_results = [row for row in output if row.get('tool_result') in ('get_official_warnings', 'get_shop_profile')]
    assert len(tool_results) == 2 and all(row['status'] == 'not_implemented' for row in tool_results)
    assert 'No risk classification or alert' in output[-1]['text']
