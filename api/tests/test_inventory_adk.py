import asyncio,json,os
from datetime import UTC,datetime
from hashlib import sha256
from uuid import uuid4
import pytest
from pydantic import PrivateAttr
from google.adk.models import BaseLlm,LlmResponse
from google.genai import types
from api.agents.inventory_loss import InventoryAssessor
from api.agents.sessions import create_session_service
from api.tools.firestore import create_async_firestore_client,close_async_firestore_client
from api.config import Settings
from api.media import IngestedMedia
from api.media_models import MediaRecord
from api.tests.test_inventory import VIDEO,assessment

class InventoryModel(BaseLlm):
    model:str='synthetic-inventory-model'
    async def generate_content_async(self,request,stream=False):
        assert any(p.inline_data and p.inline_data.data==VIDEO and p.inline_data.mime_type=='video/mp4' for c in request.contents for p in c.parts or [])
        yield LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=assessment().model_dump_json())]))

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_loss_agent_receives_exact_video_without_persisted_inline_bytes():
    async def run():
        settings=Settings(gcp_project='highground-task11-tests');namespace='inventory-adk-'+uuid4().hex;now=datetime.now(UTC)
        record=MediaRecord(media_id='synthetic-before',shop_id='shop',kind='baseline_video',sender_hash='opaque',sha256=sha256(VIDEO).hexdigest(),
            bytes=len(VIDEO),mime_type='video/mp4',uploaded_at=now,received_at=now,telegram_date=now,lat=3.,lng=101.,is_demo=True,location_attribution='confirmed_shop')
        assessor=InventoryAssessor(settings,model=InventoryModel(),root_collection=namespace)
        result=await assessor.assess(IngestedMedia(record,VIDEO),'inventory',True,30)
        assert result.items[0].name=='Rice'
        client=create_async_firestore_client(settings);sessions=create_session_service(settings,client=client,root_collection=namespace)
        try:
            listing=await sessions.list_sessions(app_name='highground_inventory',user_id='inventory-assessment')
            session=await sessions.get_session(app_name='highground_inventory',user_id='inventory-assessment',session_id=listing.sessions[0].id)
            assert all(p.inline_data is None for e in session.events if e.content for p in e.content.parts or [])
            assert session.state['validated_inventory']['items'][0]['name']=='Rice'
            assert any(e.author=='loss_agent' for e in session.events)
            assert sum(len(e.model_dump_json()) for e in session.events)<100000
            await sessions.delete_session(app_name='highground_inventory',user_id='inventory-assessment',session_id=session.id)
        finally:await close_async_firestore_client(client)
    asyncio.run(run())


class LossModel(BaseLlm):
    model: str='synthetic-loss-model'
    async def generate_content_async(self,request,stream=False):
        from api.tests.test_reports import loss
        inline=[p for c in request.contents for p in c.parts or [] if p.inline_data]
        assert len(inline)==1 and inline[0].inline_data.data==VIDEO
        assert 'baseline:0' in str(request.config.system_instruction)
        schema=request.config.response_schema.model_json_schema()
        assert schema['$defs']['_WireLossItem']['properties']['condition']['enum']==['ok','damaged','destroyed','missing','unassessed']
        prompt=str(request.config.system_instruction)
        assert 'Choose exactly one condition: ok, damaged, destroyed, missing, or unassessed.' in prompt
        assert 'For missing OR unassessed, estimated_loss_rm and evidence_timestamp_s must both be null.' in prompt
        assert 'missing/unassessed' not in prompt
        yield LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=loss().model_dump_json())]))

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_loss_comparison_frozen_json_one_video_no_persisted_bytes():
    from api.agents.loss_comparison import LossAssessor
    from api.tests.test_reports import BASE
    async def run():
        settings=Settings(gcp_project='highground-recovery-tests');namespace='loss-adk-'+uuid4().hex;now=datetime.now(UTC)
        record=MediaRecord(media_id='a'*64,shop_id='shop',kind='after_video',sender_hash='opaque',sha256=sha256(VIDEO).hexdigest(),bytes=len(VIDEO),mime_type='video/mp4',uploaded_at=now,received_at=now,telegram_date=now,lat=3.,lng=101.,is_demo=True,location_attribution='confirmed_shop')
        assessor=LossAssessor(settings,model=LossModel(),root_collection=namespace)
        result=await assessor.assess(IngestedMedia(record,VIDEO),'report',True,30,BASE)
        assert result.total_loss_rm==10.
        client=create_async_firestore_client(settings);sessions=create_session_service(settings,client=client,root_collection=namespace)
        try:
            listing=await sessions.list_sessions(app_name='highground_loss',user_id='loss-assessment')
            session=await sessions.get_session(app_name='highground_loss',user_id='loss-assessment',session_id=listing.sessions[0].id)
            assert all(p.inline_data is None for event in session.events if event.content for p in event.content.parts or [])
            assert session.state['validated_loss']['total_loss_rm']==10.
            await sessions.delete_session(app_name='highground_loss',user_id='loss-assessment',session_id=session.id)
        finally:await close_async_firestore_client(client)
    asyncio.run(run())
