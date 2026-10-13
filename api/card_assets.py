"""Private immutable generated cards; never original uploads or evidence receipts."""
from hashlib import sha256
from google.api_core.exceptions import PreconditionFailed,Conflict

class CardAssets:
    def __init__(self,client,bucket):
        if not bucket or '/' in bucket:raise ValueError('Configured private card bucket required')
        self.client,self.bucket=client,bucket

    def write(self,identity,data):
        if len(data)>10_000_000:raise ValueError('Card PNG exceeds photo limit')
        digest=sha256(data).hexdigest();path='derived/cards/'+identity+'.png'
        blob=self.client.bucket(self.bucket).blob(path)
        blob.metadata={'derived_kind':'offline_card','card_id':identity,'sha256':digest}
        try:blob.upload_from_string(data,content_type='image/png',if_generation_match=0,timeout=8,retry=None)
        except (PreconditionFailed,Conflict):
            blob.reload(timeout=8,retry=None)
            if (blob.metadata or {}).get('card_id')!=identity or (blob.metadata or {}).get('derived_kind')!='offline_card':raise ValueError('Derived card identity conflict')
            if not isinstance(blob.size,int) or not 0<blob.size<=10_000_000:raise ValueError('Invalid existing card asset size')
            existing=blob.download_as_bytes(timeout=8,retry=None,if_generation_match=blob.generation)
            if len(existing)>10_000_000 or sha256(existing).hexdigest()!=(blob.metadata or {}).get('sha256'):raise ValueError('Derived card integrity mismatch')
            # First successful upload wins, including a crash before Firestore artifact metadata.
            digest=sha256(existing).hexdigest()
        return path,digest

    def read(self,path,digest):
        if not path.startswith('derived/cards/') or not path.endswith('.png'):raise ValueError('Unexpected derived asset path')
        blob=self.client.bucket(self.bucket).blob(path);blob.reload(timeout=8,retry=None)
        if not isinstance(blob.size,int) or not 0<blob.size<=10_000_000:raise ValueError('Invalid card asset size')
        data=blob.download_as_bytes(timeout=8,retry=None,if_generation_match=blob.generation)
        if len(data)>10_000_000 or sha256(data).hexdigest()!=digest:raise ValueError('Derived card integrity mismatch')
        return data
