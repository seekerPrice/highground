"""Actual Firestore + existing ingestion; synthetic in-process GCS/ledger only."""
import asyncio
from io import BytesIO
from uuid import uuid4
from datetime import UTC,datetime
import os
import pytest
from PIL import Image
from api.config import Settings
from api.policy import PolicyService,PolicyDocument
from api.policy_models import PolicyOriginal
from api.policy_store import PolicyStore
from api.policy_media import PolicyStorage,PolicyMediaStore,PolicyMediaGateway
from api.media import MediaService
from api.tools.firestore import create_firestore_client
from api.tests.test_policy_storage import Bucket,Client
from api.tests.test_policy_service import Model,start,upload

class Download:
    def __init__(self):self.calls=0;image=Image.new('RGB',(8,8),'blue');buffer=BytesIO();image.save(buffer,format='JPEG');self.data=buffer.getvalue()
    async def download(self,request,*,max_bytes):
        self.calls+=1
        assert len(self.data)<=max_bytes
        return self.data
class Ledger:
    def __init__(self):self.unavailable=False;self.ids=set()
    def append(self,record):
        if self.unavailable:raise RuntimeError('Synthetic ledger outage')
        self.ids.add(record.media_id)

@pytest.fixture
def gateway():
    if not os.environ.get('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore emulator required')
    client=create_firestore_client(Settings(gcp_project='highground-policy-gateway-tests'));prefix='policy-gateway-'+uuid4().hex+'-'
    store=PolicyStore(client,'synthetic',prefix)
    store.collection('shops').document('shop').set(dict(lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=123,role='owner',language='en')]))
    bucket=Bucket(True);storage=PolicyStorage(Client(bucket),'private',store.original_binding)
    media_store=PolicyMediaStore(client,'synthetic',prefix+'media',prefix+'policy_media_retirements')
    download=Download();ledger=Ledger();media=MediaService(media_store,download,storage,ledger,lambda request:False)
    bridge=PolicyMediaGateway(media,store);media.authorize=bridge.authorize_media
    active=PolicyService(store,bridge,Model())
    try:yield active,store,bridge,download,ledger,bucket
    finally:
        for name in ('shops','policy_current','policy_jobs','policy_intents','policy_uploads','policy_originals','policies','media','policy_media_retirements','active_risks'):
            for doc in store.collection(name).stream(timeout=5,retry=None):doc.reference.delete(timeout=5,retry=None)
        client.close()

async def image_upload(active):
    return await active.handle_photo(123,1,1,int(datetime.now(UTC).timestamp()),PolicyDocument(file_id='image',file_unique_id='image',mime_type='image/jpeg'))

def test_shared_ingestion_receipt_generation_default_delete_and_no_resurrection(gateway):
    active,store,bridge,download,ledger,bucket=gateway
    async def run():
        identity=await start(active);await image_upload(active)
        receipt=store.get(identity)['originals'][0]
        assert receipt['object_generation']=='1' and receipt['media_id'] in ledger.ids
        result=await active.done(123,identity)
        assert result.kind=='policy_result' and 'stored policy copy deleted' in result.text
        assert bucket.versions[bucket.current]['data']==b''
        await image_upload(active);assert download.calls==1
        with pytest.raises(Exception):await bridge.read(PolicyOriginal.model_validate(receipt))
    asyncio.run(run())

def test_never_put_marker_ledger_failure_resumes_without_file_download(gateway):
    active,store,bridge,download,ledger,bucket=gateway
    async def run():
        identity=await start(active);ledger.unavailable=True
        create=bridge.media.storage.create_original
        def unavailable(*args,**kwargs):raise RuntimeError('PUT did not start')
        bridge.media.storage.create_original=unavailable
        await image_upload(active)
        job=store.get(identity)
        assert job['status']=='failed' and job['deletion_pending'] and not job['originals']
        assert bucket.versions[bucket.current]['data']==b''
        bridge.media.storage.create_original=create;ledger.unavailable=False
        result=await active.resume_deletions()
        assert result=={'scanned':1,'completed':1,'pending':0}
        assert store.get(identity)['uploads'][0]['absence_verified']
        assert download.calls==1 and len(ledger.ids)==1
        assert await active.resume_deletions()=={'scanned':0,'completed':0,'pending':0}
    asyncio.run(run())
