import asyncio
from datetime import UTC,datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from google.cloud import bigquery
from google.adk.models.base_llm import BaseLlm
from google.adk.models import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from api.config import Settings,load_settings
from api.media import MediaService,EvidenceLedger,IngestedMedia
from api.media_store import MediaStore
from api.media_models import MediaRequest,MediaRecord,MediaIngestError,MAX_UPLOAD_BYTES
from api.tools.storage import OriginalStorage,create_storage_client
from api.tools.firestore import create_firestore_client,create_async_firestore_client,close_async_firestore_client
from api.tools.cloud_events import create_event_sinks
from api.agents.photo_triage import PhotoAssessor
from api.agents.sessions import create_session_service
from api.tests.test_media import image_bytes,Download


@pytest.mark.skipif(not all(os.environ.get(name) for name in ('STORAGE_EMULATOR_HOST','BIGQUERY_EMULATOR_HOST','FIRESTORE_EMULATOR_HOST','PUBSUB_EMULATOR_HOST')),reason='local emulators required')
def test_official_immutable_storage_hash_ledger_and_bounded_read():
    settings=load_settings();suffix=uuid4().hex;dataset='media_test_'+suffix;bucket='highground-media-test-'+suffix
    storage_client=create_storage_client(settings);storage_client.create_bucket(bucket,timeout=8,retry=None)
    storage=OriginalStorage(storage_client,bucket)
    configured=Settings(gcp_project=settings.gcp_project,bigquery_dataset=dataset)
    sinks=create_event_sinks(configured)
    sinks.analytics.create_dataset(bigquery.Dataset(f'{settings.gcp_project}.{dataset}'),timeout=8,retry=None)
    schema=json.loads((Path(__file__).parents[2]/'infra/schemas/evidence_ledger.json').read_text())
    sinks.analytics.create_table(bigquery.Table(f'{settings.gcp_project}.{dataset}.evidence_ledger',
        schema=[bigquery.SchemaField.from_api_repr(field) for field in schema]),timeout=8,retry=None)
    client=create_firestore_client(settings);collection='media-test-'+suffix;store=MediaStore(client,'synthetic',collection)
    ledger=EvidenceLedger(sinks.analytics,settings.gcp_project,dataset);data=image_bytes();now=datetime.now(UTC)
    request=MediaRequest(shop_id='synthetic',kind='flood_photo',sender_chat_id=123,message_id=1,file_id='opaque',
        file_unique_id='opaque-unique',declared_size=len(data),telegram_date=now,received_at=now,lat=3.,lng=101.,
        is_demo=True,location_attribution='unconfirmed_shop')
    active=MediaService(store,Download(data),storage,ledger,lambda req:True)
    try:
        receipt=asyncio.run(active.ingest_media(request));identity=receipt.record.media_id
        again=asyncio.run(active.ingest_media(request))
        assert again.record.media_id==identity and storage.read_original(identity)==data
        assert receipt.record.sha256==sha256(data).hexdigest() and asyncio.run(active.verify_integrity(identity))
        with pytest.raises(MediaIngestError):storage.create_original(identity,b'changed','image/png',sha256(b'changed').hexdigest())
        rows=list(sinks.analytics.query(f'SELECT media_id,location_source FROM `{settings.gcp_project}.{dataset}.evidence_ledger`',
            retry=None,job_retry=None,timeout=8).result(timeout=8,retry=None,job_retry=None))
        assert len(rows)==1 and rows[0].media_id==identity and rows[0].location_source=='unconfirmed_shop'
        blob=storage_client.bucket(bucket).blob('originals/oversized')
        blob.upload_from_string(b'x'*(MAX_UPLOAD_BYTES+2),timeout=8,retry=None)
        with pytest.raises(MediaIngestError) as failure:storage.read_original('oversized')
        assert failure.value.code=='upload_too_large'
    finally:
        for blob in storage_client.list_blobs(bucket):blob.delete(timeout=8,retry=None)
        storage_client.bucket(bucket).delete(timeout=8,retry=None)
        for doc in client.collection(collection).stream():doc.reference.delete()
        sinks.analytics.delete_dataset(f'{settings.gcp_project}.{dataset}',delete_contents=True,not_found_ok=True,timeout=8,retry=None)
        storage.close();client.close();sinks.close()


class PhotoModel(BaseLlm):
    model:str='synthetic-photo-model'
    _seen:bool=PrivateAttr(default=False)
    _expected:bytes=PrivateAttr(default=b'')
    async def generate_content_async(self,request,stream=False):
        self._seen=any(part.inline_data and part.inline_data.data for content in request.contents for part in content.parts or [])
        assert self._seen
        assert any(part.inline_data and part.inline_data.data==self._expected for content in request.contents for part in content.parts or [])
        yield LlmResponse(content=types.Content(role='model',parts=[types.Part.from_text(text=json.dumps(dict(
            scene='flooding',assessment_status='assessed',is_flooding=True,water_location='street',est_depth_cm=None,
            confidence=.8,reason='Fictional water is depicted.')))]))

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_adk_photo_payload_is_not_persisted_in_session_events():
    async def run():
        settings=Settings(gcp_project='highground-task9-tests');namespace='photo-adk-test-'+uuid4().hex
        data=(Path(__file__).parents[2]/'demo/media/synthetic-after.png').read_bytes();now=datetime.now(UTC)
        record=MediaRecord(media_id='synthetic-large',shop_id='synthetic',kind='flood_photo',sender_hash='opaque',
            sha256=sha256(data).hexdigest(),bytes=len(data),mime_type='image/png',uploaded_at=now,received_at=now,
            telegram_date=now,lat=3.,lng=101.,is_demo=True,location_attribution='unconfirmed_shop')
        model=PhotoModel();model._expected=data
        assessor=PhotoAssessor(settings,model=model,root_collection=namespace)
        result=await assessor.assess(IngestedMedia(record,data),'synthetic-report',True)
        assert result.confidence==.8
        client=create_async_firestore_client(settings);sessions=create_session_service(settings,client=client,root_collection=namespace)
        try:
            listing=await sessions.list_sessions(app_name='highground_photo',user_id='photo-assessment')
            session=await sessions.get_session(app_name='highground_photo',user_id='photo-assessment',session_id=listing.sessions[0].id)
            encoded=''.join(event.model_dump_json() for event in session.events)
            assert len(encoded)<100_000
            assert all(part.inline_data is None for event in session.events if event.content for part in event.content.parts or [])
            assert session.state['validated_assessment']['confidence']==.8
            await sessions.delete_session(app_name='highground_photo',user_id='photo-assessment',session_id=session.id)
        finally:await close_async_firestore_client(client)
    asyncio.run(run())
