import asyncio
from copy import deepcopy
from datetime import UTC,datetime
from hashlib import sha256
from io import BytesIO

import httpx
import pytest
from PIL import Image

from api.media import MediaService,TelegramDownloader,validated_mime
from api.media_models import MediaRequest,MediaRecord,MediaIngestError,MAX_UPLOAD_BYTES

NOW=datetime.now(UTC)
def image_bytes():
    output=BytesIO();Image.new('RGB',(4,4),'blue').save(output,format='PNG');return output.getvalue()
def request(data=None,**updates):
    data=data or image_bytes()
    values=dict(shop_id='synthetic-shop',kind='flood_photo',sender_chat_id=123,message_id=1,
                file_id='opaque-file',file_unique_id='opaque-unique',declared_size=len(data),telegram_date=NOW,
                received_at=NOW,lat=3.,lng=101.,is_demo=True,location_attribution='confirmed_shop')
    values.update(updates);return MediaRequest(**values)

class Store:
    def __init__(self):self.record=None;self.owner=None
    def ensure(self,req):
        if self.record is None:
            self.record=MediaRecord(media_id='synthetic-id',shop_id=req.shop_id,kind=req.kind,sender_hash='hash',
                uploaded_at=NOW,telegram_date=req.telegram_date,received_at=req.received_at,lat=req.lat,lng=req.lng,
                is_demo=req.is_demo,location_attribution=req.location_attribution)
        return self.record
    def claim(self,identity):self.owner='owner';return self.owner
    def transition(self,identity,owner,**updates):
        if owner!=self.owner:raise MediaIngestError('ingest_claim_changed')
        self.record=self.record.model_copy(update=updates)
    def get(self,identity):return self.record
    def release(self,identity,owner):self.owner=None
class Download:
    def __init__(self,data):self.data=data;self.calls=0
    async def download(self,req):self.calls+=1;return self.data
class Storage:
    def __init__(self):self.data=None;self.calls=0
    def uri(self,identity):return 'gs://synthetic/originals/'+identity
    def create_original(self,identity,data,mime,digest):
        self.calls+=1
        if self.data is not None and self.data!=data:raise MediaIngestError('original_conflict')
        self.data=data
    def read_original(self,identity):return self.data
class Ledger:
    def __init__(self):self.fail=False;self.ids=[]
    def append(self,record):
        self.ids.append(record.media_id)
        if self.fail:raise RuntimeError('synthetic')


def service():
    store=Store();download=Download(image_bytes());storage=Storage();ledger=Ledger()
    return MediaService(store,download,storage,ledger,lambda req:True),store,download,storage,ledger

def test_exact_hash_immutable_retry_and_partial_ledger_recovery():
    active,store,download,storage,ledger=service();ledger.fail=True
    with pytest.raises(MediaIngestError) as failure:asyncio.run(active.ingest_media(request()))
    assert failure.value.code=='ledger_pending' and store.record.status=='pending'
    ledger.fail=False
    result=asyncio.run(active.ingest_media(request()))
    assert result.record.status=='complete' and result.record.sha256==sha256(image_bytes()).hexdigest()
    assert download.calls==1 and storage.calls==1 and len(set(ledger.ids))==1
    assert asyncio.run(active.verify_integrity(result.record.media_id))
    storage.data=b'changed'
    assert not asyncio.run(active.verify_integrity(result.record.media_id))
    with pytest.raises(MediaIngestError):asyncio.run(active.ingest_media(request()))

def test_authorization_size_and_mime_fail_before_storage():
    active,store,download,storage,ledger=service()
    active.authorize=lambda req:False
    with pytest.raises(MediaIngestError):asyncio.run(active.ingest_media(request()))
    assert download.calls==0 and storage.calls==0
    with pytest.raises(MediaIngestError):asyncio.run(active.ingest_media(request(declared_size=MAX_UPLOAD_BYTES+1)))
    with pytest.raises(MediaIngestError):validated_mime(image_bytes(),request(declared_mime='image/jpeg'))
    with pytest.raises(MediaIngestError):validated_mime(b'not image',request())

class Chunks(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'a'*(MAX_UPLOAD_BYTES//2)
        yield b'b'*(MAX_UPLOAD_BYTES//2+1)

@pytest.mark.parametrize('mode',['stream_limit','declared_limit','bad_path','redirect'])
def test_download_bounded_fixed_origin_and_safe_errors(mode):
    urls=[]
    async def handle(req):
        urls.append(str(req.url))
        if req.url.path.endswith('getFile'):
            if mode=='redirect':return httpx.Response(302,headers={'location':'https://attacker.example/file'})
            return httpx.Response(200,json={'ok':True,'result':{'file_id':'opaque-file','file_unique_id':'opaque-unique',
                'file_size':MAX_UPLOAD_BYTES+1 if mode=='declared_limit' else MAX_UPLOAD_BYTES,
                'file_path':'../secret' if mode=='bad_path' else 'photos/valid.png'}})
        return httpx.Response(200,stream=Chunks())
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle),follow_redirects=True) as client:
            return await TelegramDownloader('private-token',client).download(request(declared_size=MAX_UPLOAD_BYTES))
    with pytest.raises(MediaIngestError) as failure:asyncio.run(run())
    assert 'private-token' not in str(failure.value)
    assert all('api.telegram.org' in url for url in urls)
    if mode in ('bad_path','redirect','declared_limit'):assert len(urls)==1


def test_download_exact_bytes_with_omitted_declared_size():
    data=image_bytes()
    async def handle(req):
        if req.url.path.endswith('getFile'):
            return httpx.Response(200,json={'ok':True,'result':{'file_id':'opaque-file','file_unique_id':'opaque-unique',
                'file_path':'photos/valid.png','file_size':len(data)}})
        return httpx.Response(200,content=data)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await TelegramDownloader('private-token',client).download(request(declared_size=None))
    assert asyncio.run(run())==data
