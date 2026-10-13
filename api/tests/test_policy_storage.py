"""Deterministic generation interleavings; real GCS acceptance is separate."""
from copy import deepcopy
from hashlib import sha256
import pytest
from google.api_core.exceptions import NotFound,PreconditionFailed
from api.policy_media import PolicyStorage
from api.policy_models import PolicyOriginal
from api.media_models import MediaIngestError

MEDIA='b'*64;DATA=b'synthetic sensitive policy original'
BINDING={'media_id':MEDIA,'intake_id':'i'*32,'upload_key':'u'*64}

class Bucket:
    def __init__(self,versioned):self.versions={};self.current=None;self.next=1;self.versioned=versioned;self.deleted=[];self.hook=None
    def blob(self,name,generation=None):return Blob(self,generation)
class Client:
    def __init__(self,bucket):self._bucket=bucket
    def bucket(self,name):return self._bucket
class Blob:
    @property
    def metadata(self):return deepcopy(self._metadata)
    @metadata.setter
    def metadata(self,value):self._metadata=deepcopy(value)
    def __init__(self,bucket,generation):self.bucket=bucket;self.generation=generation;self.metadata=None
    def _row(self):
        target=self.generation if self.generation is not None else self.bucket.current
        if target not in self.bucket.versions:raise NotFound('Missing exact generation')
        return target,self.bucket.versions[target]
    def reload(self,**kwargs):
        target,row=self._row();self.generation=target;self.metadata=deepcopy(row['metadata']);self.size=len(row['data'])
    def upload_from_string(self,data,*,if_generation_match,**kwargs):
        if self.bucket.hook:
            hook=self.bucket.hook;self.bucket.hook=None;hook()
        current=self.bucket.current
        if (if_generation_match==0 and current is not None) or (if_generation_match!=0 and current!=if_generation_match):raise PreconditionFailed('Generation fence')
        if current is not None and not self.bucket.versioned:self.bucket.versions.pop(current,None)
        self.generation=self.bucket.next;self.bucket.next+=1
        self.bucket.current=self.generation
        self.bucket.versions[self.generation]={'data':data,'metadata':deepcopy(self.metadata or {})}
    def download_as_bytes(self,**kwargs):return self._row()[1]['data']
    def delete(self,*,if_generation_match,**kwargs):
        target,_=self._row()
        if target!=if_generation_match:raise PreconditionFailed('Wrong generation')
        self.bucket.versions.pop(target);self.bucket.deleted.append(target)
        if self.bucket.current==target:self.bucket.current=None

@pytest.fixture(params=[False,True],ids=['unversioned','versioned'])
def storage(request):
    bucket=Bucket(request.param);store=PolicyStorage(Client(bucket),'private',lambda media:BINDING if media==MEDIA else None)
    return store,bucket

def original(storage):
    generation=storage.create_original(MEDIA,DATA,'application/pdf',sha256(DATA).hexdigest())
    return PolicyOriginal(media_id=MEDIA,sha256=sha256(DATA).hexdigest(),bytes=len(DATA),mime_type='application/pdf',object_generation=generation)

def test_exact_original_deleted_and_empty_fence_blocks_delayed_create_and_reads(storage):
    store,bucket=storage;receipt=original(store)
    assert store.fence_and_delete(MEDIA,receipt)
    assert all(row['data']!=DATA for row in bucket.versions.values())
    assert bucket.versions[bucket.current]['data']==b''
    assert store.fence_and_delete(MEDIA,receipt) # idempotent exact-generation absence
    with pytest.raises(MediaIngestError,match='policy_copy_deleted'):store.create_original(MEDIA,DATA,'application/pdf',receipt.sha256)
    with pytest.raises(MediaIngestError,match='policy_copy_deleted'):store.read_original(MEDIA)

def test_unrelated_replacement_generation_is_never_overwritten_or_deleted(storage):
    store,bucket=storage;receipt=original(store)
    replacement=bucket.blob('originals/'+MEDIA);replacement.metadata={'different_owner':'true'}
    replacement.upload_from_string(b'unrelated replacement',if_generation_match=int(receipt.object_generation))
    before=deepcopy(bucket.versions)
    with pytest.raises(MediaIngestError,match='original_conflict'):store.fence_and_delete(MEDIA,receipt)
    assert bucket.versions==before and bucket.deleted==[]

def test_owned_hash_receipt_recovers_put_generation_without_re_download(storage):
    store,bucket=storage;receipt=original(store)
    assert store.recover_generation(MEDIA,receipt.sha256,receipt.bytes)==receipt.object_generation
    assert store.fence_and_delete(MEDIA,receipt)
    assert store.recover_generation(MEDIA,receipt.sha256,receipt.bytes)==receipt.object_generation
    with pytest.raises(MediaIngestError,match='original_conflict'):store.recover_generation(MEDIA,'a'*64,receipt.bytes)

def test_never_put_reservation_is_permanently_fenced_without_invented_generation(storage):
    store,bucket=storage
    assert store.fence_and_delete(MEDIA,None)
    assert 'policy_deleted_generation' not in bucket.versions[bucket.current]['metadata']
    with pytest.raises(MediaIngestError):store.create_original(MEDIA,DATA,'application/pdf',sha256(DATA).hexdigest())

def test_ifgenzero_collision_with_delayed_put_stays_pending_until_receipt_recovered(storage):
    store,bucket=storage
    bucket.hook=lambda:store.create_original(MEDIA,DATA,'application/pdf',sha256(DATA).hexdigest())
    with pytest.raises(MediaIngestError,match='original_conflict'):store.fence_and_delete(MEDIA,None)
    generation=store.recover_generation(MEDIA,sha256(DATA).hexdigest(),len(DATA))
    receipt=PolicyOriginal(media_id=MEDIA,sha256=sha256(DATA).hexdigest(),bytes=len(DATA),mime_type='application/pdf',object_generation=generation)
    assert store.fence_and_delete(MEDIA,receipt)

def test_never_put_fence_survives_known_hash_ledger_outage_before_absent_receipt(storage):
    store,bucket=storage
    # Download/hash were recorded, PUT never happened. A failed ledger append
    # leaves the policy job unresolved even though the empty fence now exists.
    assert store.fence_and_delete(MEDIA,None)
    assert store.recover_generation(MEDIA,sha256(DATA).hexdigest(),len(DATA)) is None
    assert store.fence_and_delete(MEDIA,None)

def test_nonempty_object_with_marker_metadata_never_counts_as_deleted(storage):
    store,bucket=storage;receipt=original(store)
    current=bucket.versions[bucket.current]
    current['metadata'].update(policy_deleted='true',policy_deleted_generation=receipt.object_generation)
    before=deepcopy(bucket.versions)
    with pytest.raises(MediaIngestError,match='original_conflict'):store.fence_and_delete(MEDIA,receipt)
    with pytest.raises(MediaIngestError,match='original_conflict'):store.recover_generation(MEDIA,receipt.sha256,receipt.bytes)
    assert bucket.versions==before and bucket.deleted==[]

def test_official_blob_metadata_copy_contract():
    from google.cloud.storage import Blob as OfficialBlob,Bucket as OfficialBucket
    blob=OfficialBlob('original',OfficialBucket(None,'synthetic'))
    blob.metadata={'owner':'synthetic'}
    detached=blob.metadata;detached['sha256']='b'*64
    assert blob.metadata=={'owner':'synthetic'}
