"""Bounded waste estimates; classifications do not certify safety or collection."""
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

class WasteDTO(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True,allow_inf_nan=False)

class WasteItem(WasteDTO):
    item_id:str=Field(min_length=1,max_length=160)
    condition:Literal['ok','damaged','destroyed','missing','unassessed']
    disposition:Literal['discard_contaminated','salvage_clean','recycle','bulky_pickup']|None
    est_volume_m3:float|None=Field(ge=0,le=10000)
    est_weight_kg:float|None=Field(ge=0,le=1000000)
    material:Literal['food','drink','medicine','cosmetics','absorbent','sealed_metal','sealed_plastic','sealed_glass','metal','e_waste','bulky','unknown']
    floodwater_contact:Literal['yes','no','unknown']
    contamination:Literal['present','not_observed','unknown']
    uncertainty:str|None=Field(min_length=1,max_length=300)

class WasteAssessment(WasteDTO):
    version:Literal[1]=1
    inventory_id:str=Field(min_length=1,max_length=160)
    assessment_media_id:str=Field(pattern=r'^[0-9a-f]{64}$')
    items:tuple[WasteItem,...]=Field(max_length=80)
    confidence:float=Field(ge=0,le=1)

    @field_validator('items',mode='before')
    @classmethod
    def transport_items(cls,value):
        return tuple(value) if isinstance(value,list) else value

class WasteRecord(WasteDTO):
    assessment_id:str=Field(min_length=1,max_length=160)
    shop_id:str=Field(min_length=1,max_length=160)
    episode_id:str=Field(min_length=1,max_length=160)
    completed_at:AwareDatetime
    status:Literal['complete','pending','failed']
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    owner_confirmed_street:str|None=Field(min_length=1,max_length=100,pattern=r'^[^\n\r{}<>]+$')
    @field_validator('owner_confirmed_street',mode='before')
    @classmethod
    def normalized_street(cls,value):
        return value.strip() or None if isinstance(value,str) else value

    baseline_items:int=Field(ge=0,le=80)
    assessment:WasteAssessment

class StreetWaste(WasteDTO):
    street:str
    assessment_count:int
    shop_count:int
    baseline_items:int
    assessed_items:int
    affected_items:int
    unknown_items:int
    quantified_volume_items:int
    unknown_volume_items:int
    quantified_weight_items:int
    unknown_weight_items:int
    est_volume_m3:float|None
    est_weight_kg:float|None
    estimated_load_equivalents:float|None

class WasteAggregate(WasteDTO):
    is_demo:Literal[True]=True
    lorry_capacity_m3:float
    streets:tuple[StreetWaste,...]
    definition:str='Synthetic estimates from the latest completed assessment per shop, episode and inventory. Missing/unassessed items and unknown quantities remain unknown. Estimated load-equivalents are not required trucks or a collection promise.'

class WasteReportItem(WasteItem):
    donation_eligible:bool
    donation_available:bool
    donation_action_url:str|None=Field(max_length=200)
    self_report_note:str='Donation availability is an owner self-report; eligibility is not a safety certification or collection promise.'

class ReportWaste(WasteDTO):
    status:Literal['not_assessed','available','unavailable']='not_assessed'
    items:list[WasteReportItem]=Field(default_factory=list,max_length=80)
    confidence:float|None=Field(default=None,ge=0,le=1)
    owner_confirmed_street:str|None=Field(default=None,max_length=100)
    street_assignment_source:Literal['owner_confirmed_current_shop','unassigned']='unassigned'
    street_confirmed_at:AwareDatetime|None=None
    food_safety_line:Literal['Throw away food, drinks and medicine that touched floodwater.']='Throw away food, drinks and medicine that touched floodwater.'
    safety_note:str='Visual classifications and quantities are uncertain estimates. They do not establish that an item is safe to use, clean or donate.'

    @model_validator(mode='after')
    def consistent(self):
        if self.status!='available' and (self.items or self.confidence is not None):raise ValueError('Unavailable waste cannot contain assessed facts')
        if self.status=='available' and self.confidence is None:raise ValueError('Available waste requires confidence')
        confirmed=self.owner_confirmed_street is not None
        if confirmed!=(self.street_assignment_source=='owner_confirmed_current_shop') or confirmed!=(self.street_confirmed_at is not None):raise ValueError('Street requires confirmation provenance')
        return self

class WasteResponse(WasteDTO):
    status:Literal['available','empty','unavailable']
    generated_at:AwareDatetime
    is_demo:Literal[True]=True
    registered_synthetic_shops:int|None=Field(ge=0,le=50)
    assessed_shops:int|None=Field(ge=0,le=50)
    missing_or_unavailable_shops:int|None=Field(ge=0,le=50)
    aggregate:WasteAggregate|None
    note:str=Field(min_length=1,max_length=600)

    @model_validator(mode='after')
    def denominator(self):
        if self.status=='unavailable':
            if self.aggregate is not None or self.assessed_shops is not None or self.missing_or_unavailable_shops is not None:raise ValueError('Unavailable aggregate cannot claim known counts')
        else:
            if self.registered_synthetic_shops is None or self.assessed_shops is None or self.missing_or_unavailable_shops is None or self.aggregate is None:raise ValueError('Available scope requires explicit denominators')
            if self.registered_synthetic_shops!=self.assessed_shops+self.missing_or_unavailable_shops:raise ValueError('Inconsistent synthetic denominator')
            if (self.status=='empty')!=(self.assessed_shops==0):raise ValueError('Empty means no completed assessment, not zero waste')
        return self
