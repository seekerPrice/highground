"""Official private Cloud Storage access; exact originals are create-only."""
import hashlib
import os
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import PreconditionFailed,Conflict
import google.auth
from api.tools.emulators import loopback_endpoint
from api.media_models import MediaIngestError,MAX_UPLOAD_BYTES


def create_storage_client(settings):
    if not settings.gcp_project.strip():raise ValueError('GCP_PROJECT is required')
    endpoint=os.environ.get('STORAGE_EMULATOR_HOST')
    if endpoint:
        endpoint=loopback_endpoint(endpoint,http=True)
        return storage.Client(project=settings.gcp_project,credentials=AnonymousCredentials(),
                              client_options=ClientOptions(api_endpoint=endpoint))
    credentials,_=google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'],
                                      quota_project_id=settings.gcp_project)
    return storage.Client(project=settings.gcp_project,credentials=credentials)


class OriginalStorage:
    def __init__(self,client:storage.Client,bucket:str):
        if not bucket or '/' in bucket:raise ValueError('Explicit bucket name is required')
        self.client,self.bucket=client,bucket
    def uri(self,media_id:str)->str:return f'gs://{self.bucket}/originals/{media_id}'
    def create_original(self,media_id:str,data:bytes,mime_type:str,expected_hash:str)->None:
        blob=self.client.bucket(self.bucket).blob('originals/'+media_id)
        try:
            blob.upload_from_string(data,content_type=mime_type,if_generation_match=0,timeout=8,retry=None)
        except (PreconditionFailed,Conflict):
            existing=self.read_original(media_id)
            if hashlib.sha256(existing).hexdigest()!=expected_hash:
                raise MediaIngestError('original_conflict') from None
        except Exception:
            raise MediaIngestError('storage_unavailable') from None
    def read_original(self,media_id:str)->bytes:
        try:
            data=self.client.bucket(self.bucket).blob('originals/'+media_id).download_as_bytes(start=0,end=MAX_UPLOAD_BYTES,timeout=8,retry=None)
            if len(data)>MAX_UPLOAD_BYTES:raise MediaIngestError('upload_too_large')
            return data
        except MediaIngestError:raise
        except Exception:raise MediaIngestError('storage_unavailable') from None
    def close(self):self.client.close()
