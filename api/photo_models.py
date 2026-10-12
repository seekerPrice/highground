"""Uncertain photo depiction and confirmed report-location contracts."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,StrictInt,model_validator

class PhotoMedia(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    file_id:str=Field(min_length=1,max_length=512)
    file_unique_id:str=Field(min_length=1,max_length=512)
    file_size:StrictInt|None=Field(default=None,gt=0)

class PhotoAssessment(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    scene:Literal['flooding','unrelated','staged','screenshot','old','unreadable']
    assessment_status:Literal['assessed','uncertain']
    is_flooding:bool
    water_location:Literal['street','entrance','inside_premises','none']
    confidence:float=Field(ge=0,le=1)
    est_depth_cm:StrictInt|None=Field(default=None,ge=0)
    reason:str=Field(min_length=1,max_length=200)
    @model_validator(mode='after')
    def consistency(self):
        if self.scene in ('unrelated','staged','screenshot','old') and (self.assessment_status!='assessed' or self.is_flooding is not False or self.water_location!='none'):
            raise ValueError('Rejected scene cannot supply flood evidence')
        if self.is_flooding and self.water_location=='none':raise ValueError('Positive depiction must locate water')
        if self.assessment_status=='uncertain' and self.confidence>=.7:raise ValueError('Uncertain depiction cannot be high confidence')
        if self.scene=='flooding' and self.is_flooding is not True:raise ValueError('Flood depiction must be positive')
        if self.is_flooding is False and self.water_location!='none':raise ValueError('Negative depiction cannot locate water')
        if self.water_location=='inside_premises' and self.is_flooding is not True:raise ValueError('Inside water requires positive depiction')
        if len(self.reason.split())>20:raise ValueError('Reason exceeds20words')
        if not self.is_flooding and self.est_depth_cm is not None:raise ValueError('Negative depiction cannot estimate depth')
        return self

class PhotoReply(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    text:str=''
    reply_markup:dict|None=None
    venue:dict|None=None
    code:Literal['registration_required','confirm_at_shop','share_location','confirm_shared_location',
                 'rate_limited','invalid_photo','upload_too_large','source_unavailable','location_invalid',
                 'report_recorded','report_rejected','report_stale','danger']
    language:str='en'
    report_id:str|None=None
    lat:float|None=None
    lng:float|None=None
    is_demo:bool=False
    confidence:float|None=None
    level:Literal['watch','warning','danger']|None=None
    event_id:str|None=None
