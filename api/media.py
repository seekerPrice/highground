"""Resumable immutable Telegram uploads; all errors expose only fixed codes."""
import asyncio
from dataclasses import dataclass,field
from hashlib import sha256
from io import BytesIO
import re
import warnings
from typing import Callable, TYPE_CHECKING
from google.cloud import bigquery
if TYPE_CHECKING:
    from api.media_store import MediaStore
    from api.tools.storage import OriginalStorage

import httpx
from PIL import Image
from pydantic import BaseModel,ConfigDict,Field,StrictInt

from api.media_models import MAX_UPLOAD_BYTES,MediaRequest,MediaRecord,MediaIngestError
# Ensure token-bearing Telegram/file URLs are redacted by the shared transport filter.
from api.tools import telegram as _telegram


class TelegramFile(BaseModel):
    model_config=ConfigDict(extra='ignore',strict=True)
    file_id:str
    file_unique_id:str
    file_size:StrictInt|None=Field(default=None,gt=0)
    file_path:str=Field(min_length=1,max_length=512)


class TelegramDownloader:
    def __init__(self,token:str,client:httpx.AsyncClient):
        if not token:raise ValueError('TELEGRAM_BOT_TOKEN is required')
        self._token,self.client=token,client
    async def download(self,request:MediaRequest)->bytes:
        if request.declared_size is not None and request.declared_size>MAX_UPLOAD_BYTES:raise MediaIngestError('upload_too_large')
        try:
            response=await self.client.post(f'https://api.telegram.org/bot{self._token}/getFile',json={'file_id':request.file_id},timeout=3,follow_redirects=False)
            response.raise_for_status();body=response.json()
            if not isinstance(body,dict) or body.get('ok') is not True:raise MediaIngestError('download_unavailable')
            info=TelegramFile.model_validate(body.get('result'))
            if info.file_unique_id!=request.file_unique_id or (info.file_size is not None and info.file_size>MAX_UPLOAD_BYTES):
                raise MediaIngestError('upload_too_large' if info.file_size is not None and info.file_size>MAX_UPLOAD_BYTES else 'file_identity_mismatch')
            path=info.file_path
            if (not re.fullmatch(r'[A-Za-z0-9_./-]+',path) or path.startswith('/')
                    or any(part in ('','..','.') for part in path.split('/'))):
                raise MediaIngestError('invalid_file_path')
            chunks=bytearray()
            async with self.client.stream('GET',f'https://api.telegram.org/file/bot{self._token}/{path}',timeout=3,follow_redirects=False) as download:
                download.raise_for_status()
                if download.headers.get('content-encoding','identity')!='identity':
                    raise MediaIngestError('download_unavailable')
                declared=download.headers.get('content-length')
                if declared is not None and (not declared.isdigit() or int(declared)>MAX_UPLOAD_BYTES):
                    raise MediaIngestError('upload_too_large')
                async for chunk in download.aiter_bytes():
                    if len(chunks)+len(chunk)>MAX_UPLOAD_BYTES:raise MediaIngestError('upload_too_large')
                    chunks.extend(chunk)
            if (info.file_size is not None and len(chunks)!=info.file_size) or (request.declared_size is not None and len(chunks)!=request.declared_size):
                raise MediaIngestError('file_size_mismatch')
            return bytes(chunks)
        except MediaIngestError:raise
        except Exception:raise MediaIngestError('download_unavailable') from None


def validated_mime(data:bytes,request:MediaRequest)->str:
    if request.kind.endswith('photo'):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as image:
                    mime={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}.get(image.format)
                    if not mime or image.width*image.height>20_000_000:raise ValueError()
                    image.verify()
        except Exception:raise MediaIngestError('invalid_media') from None
    else:
        if len(data)<12 or data[4:8]!=b'ftyp':raise MediaIngestError('invalid_media')
        mime='video/mp4'
    if request.declared_mime is not None and request.declared_mime!=mime:
        raise MediaIngestError('mime_mismatch')
    return mime


@dataclass(frozen=True)
class IngestedMedia:
    record:MediaRecord
    original_bytes:bytes=field(repr=False)


class MediaService:
    def __init__(self, store: 'MediaStore', downloader: TelegramDownloader, storage: 'OriginalStorage',
                 ledger: 'EvidenceLedger', authorize: Callable[[MediaRequest], bool]):
        self.store,self.downloader,self.storage,self.ledger,self.authorize=store,downloader,storage,ledger,authorize
    async def ingest_media(self,request:MediaRequest,*,defer_ledger:bool=False)->IngestedMedia:
        if request.declared_size is not None and request.declared_size>MAX_UPLOAD_BYTES:raise MediaIngestError('upload_too_large')
        if not await asyncio.to_thread(self.authorize,request):raise MediaIngestError('unauthorized_media')
        record=await asyncio.to_thread(self.store.ensure,request)
        owner=await asyncio.to_thread(self.store.claim,record.media_id)
        try:
            if record.storage_status=='done':
                data=await asyncio.to_thread(self.storage.read_original,record.media_id)
                if len(data)!=record.bytes or sha256(data).hexdigest()!=record.sha256:
                    raise MediaIngestError('file_integrity_mismatch')
            else:
                async with asyncio.timeout(4):data=await self.downloader.download(request)
                mime=validated_mime(data,request);digest=sha256(data).hexdigest()
                await asyncio.to_thread(self.store.transition,record.media_id,owner,sha256=digest,bytes=len(data),mime_type=mime,
                                        gcs_uri=self.storage.uri(record.media_id))
                await asyncio.to_thread(self.storage.create_original,record.media_id,data,mime,digest)
                await asyncio.to_thread(self.store.transition,record.media_id,owner,storage_status='done')
            record=await asyncio.to_thread(self.store.get,record.media_id)
            if not defer_ledger and record.ledger_status!='done':
                await self._ledger(record,owner)
                record=await asyncio.to_thread(self.store.get,record.media_id)
            return IngestedMedia(record,data)
        except TimeoutError:raise MediaIngestError('download_unavailable') from None
        finally:await asyncio.to_thread(self.store.release,record.media_id,owner)
    async def _ledger(self,record:MediaRecord,owner:str)->None:
        try:await asyncio.to_thread(self.ledger.append,record)
        except Exception:raise MediaIngestError('ledger_pending') from None
        await asyncio.to_thread(self.store.transition,record.media_id,owner,ledger_status='done',status='complete')
    async def resume_ledger(self,media_id:str)->MediaRecord:
        record=await asyncio.to_thread(self.store.get,media_id)
        if record.storage_status!='done':raise MediaIngestError('storage_pending')
        if record.ledger_status=='done':return record
        owner=await asyncio.to_thread(self.store.claim,media_id)
        try:await self._ledger(record,owner);return await asyncio.to_thread(self.store.get,media_id)
        finally:await asyncio.to_thread(self.store.release,media_id,owner)
    async def verify_integrity(self,media_id:str)->bool:
        record=await asyncio.to_thread(self.store.get,media_id)
        if record.storage_status!='done' or record.ledger_status!='done':return False
        data=await asyncio.to_thread(self.storage.read_original,media_id)
        return len(data)==record.bytes and sha256(data).hexdigest()==record.sha256


class EvidenceLedger:
    def __init__(self,analytics: bigquery.Client,project:str,dataset:str='highground'):
        self.analytics,self.table=analytics,f'{project}.{dataset}.evidence_ledger'
    def append(self,record:MediaRecord)->None:
        row={key:getattr(record,key) for key in ('media_id','shop_id','kind','gcs_uri','sha256','bytes','sender_hash','lat','lng','is_demo')}
        row.update(uploaded_at=record.uploaded_at.isoformat(),telegram_date=record.telegram_date.isoformat() if record.telegram_date else None,location_source=record.location_attribution)
        errors=self.analytics.insert_rows_json(self.table,[row],row_ids=[record.media_id],timeout=8,retry=None)
        if errors:raise MediaIngestError('ledger_pending')
