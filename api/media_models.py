"""Private validated upload metadata. These times/locations do not authenticate a scene."""
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,StrictInt,model_validator

MAX_UPLOAD_BYTES=20_000_000
MediaKind=Literal['baseline_video','update_video','after_video','flood_photo','waterline_photo']

class MediaRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False)
    shop_id:str=Field(min_length=1,max_length=128)
    kind:MediaKind
    sender_chat_id:StrictInt
    message_id:StrictInt=Field(ge=0)
    file_id:str=Field(min_length=1,max_length=512)
    file_unique_id:str=Field(min_length=1,max_length=512)
    declared_size:StrictInt|None=Field(default=None,gt=0)
    declared_mime:str|None=None
    telegram_date:AwareDatetime
    received_at:AwareDatetime
    lat:float=Field(ge=-90,le=90)
    lng:float=Field(ge=-180,le=180)
    location_attribution:Literal['unconfirmed_shop','confirmed_shop','confirmed_shared']
    is_demo:bool=False

class MediaRecord(BaseModel):
    model_config=ConfigDict(extra='ignore',frozen=True,allow_inf_nan=False)
    media_id:str
    shop_id:str
    kind:MediaKind
    sender_hash:str
    sha256:str|None=None
    bytes:int|None=None
    mime_type:str|None=None
    gcs_uri:str|None=None
    uploaded_at:AwareDatetime
    origin:Literal['telegram','local_fixture']='telegram'
    telegram_date:AwareDatetime|None
    received_at:AwareDatetime
    lat:float
    lng:float
    location_attribution:Literal['unconfirmed_shop','confirmed_shop','confirmed_shared']
    is_demo:bool
    storage_status:Literal['pending','done']='pending'
    ledger_status:Literal['pending','done']='pending'
    status:Literal['pending','complete']='pending'

    @model_validator(mode='after')
    def origin_timestamp(self):
        if self.origin=='telegram' and self.telegram_date is None:raise ValueError('Telegram original requires its receipt date')
        if self.origin=='local_fixture' and (not self.is_demo or self.telegram_date is not None):raise ValueError('Local fixture must be synthetic without a Telegram date')
        return self

class MediaIngestError(RuntimeError):
    def __init__(self,code:str):
        self.code=code
        super().__init__(code)
