import asyncio
from contextlib import contextmanager,asynccontextmanager
import inspect
import re
import sys
from google.api_core.exceptions import NotFound
from api.tools.bigquery_queries import query_rows
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery, pubsub_v1
from google.adk.models import LlmResponse
from google.adk.models.base_llm import BaseLlm
from google.genai import types
from pydantic import PrivateAttr

from api.agents.warning_selector import WarningSelector
from api.config import Settings, load_settings
from api.dispatch import DispatchService
from api.dispatch_models import EventRequest
from api.dispatch_store import FirestoreDispatchStore
from api.tools.cloud_events import GoogleEventSinks, create_event_sinks
from api.tools.firestore import create_firestore_client, create_async_firestore_client, close_async_firestore_client
from api.agents.sessions import create_session_service


@contextmanager
def _cleanup_scope():
    """Exact test callbacks; independent cleanup preserves the primary failure."""
    operations=[]
    try:yield operations
    finally:
        primary=sys.exception();failures=[]
        for operation in reversed(operations):
            try:operation()
            except NotFound:pass
            except Exception as error:failures.append(type(error).__name__)
        if failures:
            note='Isolated emulator cleanup failed: '+', '.join(failures)
            if primary is not None:primary.add_note(note)
            else:raise RuntimeError(note)


@asynccontextmanager
async def _async_cleanup_scope():
    operations=[]
    try:yield operations
    finally:
        primary=sys.exception();failures=[]
        for operation in reversed(operations):
            try:
                result=operation()
                if inspect.isawaitable(result):await result
            except NotFound:pass
            except Exception as error:failures.append(type(error).__name__)
        if failures:
            note='Isolated ADK cleanup failed: '+', '.join(failures)
            if primary is not None:primary.add_note(note)
            else:raise RuntimeError(note)


async def _delete_adk_namespace(client,root):
    if not re.fullmatch(r'(warning-selector-test-|photo-adk-test-|adk-cleanup-test-)[0-9a-f]{32}',root):raise ValueError('Exact isolated ADK namespace required')
    async def delete_collection(collection):
        # list_documents includes references for missing parent documents.
        async for document in collection.list_documents(retry=None,timeout=8):
            async for nested in document.collections(retry=None,timeout=8):await delete_collection(nested)
            await document.delete(retry=None,timeout=8)
    await delete_collection(client.collection(root))


def _create_sink_resources(sinks,subscriber,project,dataset,topic_path,subscription_path,cleanup):
    cleanup.append(lambda:sinks.publisher.delete_topic(request={'topic':topic_path},timeout=10,retry=None))
    sinks.publisher.create_topic(request={'name':topic_path},timeout=10,retry=None)
    cleanup.append(lambda:subscriber.delete_subscription(request={'subscription':subscription_path},timeout=10,retry=None))
    subscriber.create_subscription(request={'name':subscription_path,'topic':topic_path},timeout=10,retry=None)
    cleanup.append(lambda:sinks.analytics.delete_dataset(f'{project}.{dataset}',delete_contents=True,not_found_ok=True,timeout=25,retry=None))
    sinks.analytics.create_dataset(bigquery.Dataset(f'{project}.{dataset}'),timeout=10,retry=None)


class Bot:
    def __init__(self):self.messages=[]
    def send_message(self,chat_id,text,reply_markup=None):self.messages.append(text);return 1


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_firestore_pipeline_restart_claim_and_crash_recovery():
    from api.tests.test_dispatch import Sinks
    client=create_firestore_client(Settings(gcp_project='highground-task7-tests'))
    prefix='dispatch-test-'+uuid4().hex
    store=FirestoreDispatchStore(client,events=prefix+'-events',alerts=prefix+'-alerts',shops=prefix+'-shops')
    shop_ref=client.collection(store.shops).document('demo-shop')
    shop_ref.set({'shop_name':'Synthetic','lat':3.,'lng':101.,'is_demo':True,
                  'recipients':[{'telegram_chat_id':123,'language':'en','role':'owner'}]})
    bot=Bot();sinks=Sinks();sinks.fail=True
    request=EventRequest(request_id='integration',level='danger',lat=3.,lng=101.)
    first=DispatchService(store,bot,sinks,hash_salt='synthetic')
    try:
        result=asyncio.run(first.process(request))
        assert result['status']=='pending' and len(bot.messages)==1
        # Reconstruct the handler/store: durable state prevents another Telegram send.
        other_store=FirestoreDispatchStore(client,events=store.events,alerts=store.alerts,shops=store.shops)
        second=DispatchService(other_store,bot,sinks,hash_salt='synthetic')
        sinks.fail=False
        assert asyncio.run(second.process(request))['status']=='complete'
        assert len(bot.messages)==1
        event_id=result['event_id']
        stored_event=client.collection(store.events).document(event_id).get().to_dict()
        assert 'targets' not in stored_event
        stored_alert=next(client.collection(store.alerts).stream()).to_dict()
        assert 'telegram_chat_id' not in stored_alert
        owner=store.claim(event_id,datetime.now(UTC))
        assert owner is not None and store.claim(event_id,datetime.now(UTC)) is None
        store.release(event_id,owner)
        alert_id=store.get_event(event_id)['alert_ids'][0]
        client.collection(store.alerts).document(alert_id).update({'status':'sending','bigquery':'pending'})
        asyncio.run(second.process(request))
        assert store.get_alert(alert_id)['status']=='uncertain' and len(bot.messages)==1
    finally:
        for collection in (store.events,store.alerts,store.shops,store.plans,store.deliveries):
            for document in client.collection(collection).stream():document.reference.delete()
        client.close()


class SelectorModel(BaseLlm):
    model:str='simulation-selector-no-network'
    _turn:int=PrivateAttr(default=0)
    async def generate_content_async(self,request,stream=False):
        part=types.Part.from_text(text='{"structure":"warning_intro_actions"}')
        self._turn+=1
        yield LlmResponse(content=types.Content(role='model',parts=[part]))


@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_adk_selection_with_completed_tool_and_persistent_trace():
    async def run():
        settings=Settings(gcp_project='highground-task7-tests')
        root='warning-selector-test-'+uuid4().hex
        async with _async_cleanup_scope() as cleanup:
            client=create_async_firestore_client(settings)
            cleanup.append(lambda:close_async_firestore_client(client))
            cleanup.append(lambda:_delete_adk_namespace(client,root))
            selector=WarningSelector(settings,model=SelectorModel(),root_collection=root)
            cleanup.append(selector.close)
            event={'event_id':'synthetic-event','level':'warning','is_demo':True}
            result=await selector(event,'en',True,False)
            assert result.structure=='warning_intro_actions'
            sessions=create_session_service(settings,client=client,root_collection=root)
            response=await sessions.list_sessions(app_name='highground_dispatch',user_id='selection-en')
            assert len(response.sessions)==1
            session=await sessions.get_session(app_name='highground_dispatch',user_id='selection-en',session_id=response.sessions[0].id)
            assert session.state['validated_warning_structure']=='warning_intro_actions'
            assert any(event.actions.transfer_to_agent=='alert_agent' for event in session.events)
            assert any(event.author=='alert_agent' and event.is_final_response() for event in session.events)
    asyncio.run(run())


@pytest.mark.skipif(not all(os.environ.get(key) for key in ('FIRESTORE_EMULATOR_HOST','PUBSUB_EMULATOR_HOST','BIGQUERY_EMULATOR_HOST')),
                    reason='Firestore/PubSub/BigQuery emulators required')
def test_official_pubsub_bigquery_event_and_alert_sinks():
    settings=load_settings();project=settings.gcp_project
    suffix=uuid4().hex
    dataset='dispatch_test_'+suffix
    topic='dispatch-test-'+suffix
    subscription='dispatch-test-'+suffix
    configured=Settings(gcp_project=project,pubsub_topic=topic,bigquery_dataset=dataset)
    with _cleanup_scope() as cleanup:
        sinks=create_event_sinks(configured);cleanup.extend([sinks.analytics.close,sinks.publisher.stop])
        subscriber=pubsub_v1.SubscriberClient(credentials=AnonymousCredentials());cleanup.append(subscriber.close)
        topic_path=sinks.publisher.topic_path(project,topic)
        subscription_path=subscriber.subscription_path(project,subscription)
        _create_sink_resources(sinks,subscriber,project,dataset,topic_path,subscription_path,cleanup)
        for table in ('events','alerts'):
            schema=json.loads((Path(__file__).parents[2]/'infra'/'schemas'/f'{table}.json').read_text())
            sinks.analytics.create_table(bigquery.Table(f'{project}.{dataset}.{table}',schema=[bigquery.SchemaField.from_api_repr(field) for field in schema]),timeout=10,retry=None)
        now=datetime.now(UTC)
        event=dict(event_id='synthetic-'+suffix,source='demo',level='danger',lat=3.,lng=101.,radius_m=1000,
                   confidence=1.,reason='Explicit synthetic emulator integration',created_at=now,is_demo=True)
        alert=dict(alert_id='synthetic-alert-'+suffix,event_id=event['event_id'],shop_id='synthetic-shop',
                   telegram_chat_id_hash='synthetic-hash',level='danger',language='en',is_demo=True,
                   sent_at=now,status='accepted',latency_ms=1)
        sinks.publish_event(event);sinks.insert_event(event);sinks.insert_alert(alert)
        response=subscriber.pull(request={'subscription':subscription_path,'max_messages':1},timeout=10,retry=None)
        assert len(response.received_messages)==1
        assert json.loads(response.received_messages[0].message.data)['event_id']==event['event_id']
        subscriber.acknowledge(request={'subscription':subscription_path,'ack_ids':[response.received_messages[0].ack_id]},timeout=10,retry=None)
        query=query_rows(sinks.analytics,f'SELECT event_id FROM `{project}.{dataset}.events`',project=project,emulator_endpoint=os.environ['BIGQUERY_EMULATOR_HOST']);assert query.cleanup=='cleaned';rows=query.rows
        assert rows[0].event_id==event['event_id']
        query=query_rows(sinks.analytics,f'SELECT alert_id FROM `{project}.{dataset}.alerts`',project=project,emulator_endpoint=os.environ['BIGQUERY_EMULATOR_HOST']);assert query.cleanup=='cleaned';rows=query.rows
        assert rows[0].alert_id==alert['alert_id']

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_adk_missing_parent_nested_records_cleanup_after_original_assertion():
    async def run():
        settings=Settings(gcp_project='highground-adk-cleanup-tests');root='adk-cleanup-test-'+uuid4().hex
        primary=AssertionError('intentional assertion seam')
        with pytest.raises(AssertionError) as caught:
            async with _async_cleanup_scope() as cleanup:
                client=create_async_firestore_client(settings)
                cleanup.append(lambda:close_async_firestore_client(client))
                cleanup.append(lambda:_delete_adk_namespace(client,root))
                parent=client.collection(root).document('missing-parent')
                child=parent.collection('sessions').document('missing-session').collection('events').document('event')
                await child.set({'synthetic':True},retry=None,timeout=8)
                assert not (await parent.get(retry=None,timeout=8)).exists
                assert (await child.get(retry=None,timeout=8)).exists
                raise primary
        assert caught.value is primary
        checker=create_async_firestore_client(settings)
        try:
            child=checker.collection(root).document('missing-parent').collection('sessions').document('missing-session').collection('events').document('event')
            assert not (await child.get(retry=None,timeout=8)).exists
        finally:await close_async_firestore_client(checker)
    asyncio.run(run())
