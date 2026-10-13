"""Private reader facts and an explicitly sanitized public lookup boundary."""
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,model_validator
from api.destinations import SafePoint

class CheckDTO(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True,allow_inf_nan=False)

class CheckLocation(CheckDTO):
    lat:float=Field(ge=-90,le=90)
    lng:float=Field(ge=-180,le=180)

class PrivateCheckReport(CheckDTO):
    report_id:str=Field(pattern=r'^[0-9a-f]{32}$')
    shop_id:str=Field(min_length=1,max_length=160)
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    lat:float=Field(ge=-90,le=90)
    lng:float=Field(ge=-180,le=180)
    received_at:AwareDatetime
    telegram_date:AwareDatetime
    confirmed_at:AwareDatetime|None
    location_attribution:Literal['confirmed_shop','confirmed_shared','unconfirmed_shop']
    evidence_status:Literal['positive','unverified','rejected']
    level:Literal['watch','warning','danger']|None
    is_demo:bool

class CheckObservation(CheckDTO):
    source:Literal['jps','met','shop_report']
    reported_at:AwareDatetime
    level:Literal['watch','warning','danger']|None
    rounded_distance_m:int=Field(ge=0,le=2000,multiple_of=100)
    attribution:Literal['official_observation','reporter_confirmed_location']

class DistrictCheckWarning(CheckDTO):
    source:Literal['met']
    reported_at:AwareDatetime
    level:Literal['watch','warning','danger']
    district:str=Field(min_length=1,max_length=100)
    state:str=Field(min_length=1,max_length=100)
    scope:Literal['district_only']='district_only'

class CheckSource(CheckDTO):
    source:Literal['jps','met','shop_report']
    status:Literal['current','empty','degraded','stale','unsupported','unavailable']

class CheckResult(CheckDTO):
    checked_at:AwareDatetime
    status:Literal['available','partial','unavailable']
    level:Literal['watch','warning','danger']|None
    observations:tuple[CheckObservation,...]=Field(max_length=100)
    district_warnings:tuple[DistrictCheckWarning,...]=Field(max_length=100)
    destinations:tuple[SafePoint,...]=Field(max_length=3)
    destination_status:Literal['available','unavailable']='available'
    sources:tuple[CheckSource,...]=Field(max_length=3)
    qualification:str='Only fresh mapped observations within2km are listed. Missing or unmapped observations do not establish that there is no flood. Reporter-confirmed location and Telegram/server receipt times do not authenticate a scene or capture time. Destination designation does not establish current opening, accessibility or safety.'

    @model_validator(mode='after')
    def public_places(self):
        if any(not point.verified or point.is_demo or point.opening_status=='closed' for point in self.destinations):raise ValueError('Public lookup requires eligible sourced destinations')
        return self
