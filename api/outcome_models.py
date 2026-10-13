"""Owner-reported outcomes and frozen episode/delivery facts, not accuracy claims."""
from typing import Literal
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,model_validator

class OutcomeDTO(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,frozen=True,allow_inf_nan=False)

class OutcomeDelivery(OutcomeDTO):
    alert_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    created_at:AwareDatetime
    request_started_at:AwareDatetime|None=None
    accepted_at:AwareDatetime|None=None
    simulated_at:AwareDatetime|None=None
    level:Literal['watch','warning','danger']
    source:Literal['jps','met','shop_report','demo']
    provenance:Literal['telegram_api','local_virtual','synthetic_fixture']
    status:Literal['accepted','simulated','pending','sending','retryable','uncertain','failed','superseded']
    @model_validator(mode='after')
    def delivery_facts(self):
        if (self.status=='accepted')!=(self.accepted_at is not None):raise ValueError('Accepted time requires actual accepted status')
        if self.status=='accepted' and self.provenance!='telegram_api':raise ValueError('Virtual delivery cannot claim Telegram acceptance')
        if self.status=='simulated' and self.provenance not in ('local_virtual','synthetic_fixture'):raise ValueError('Simulation requires virtual provenance')
        if self.request_started_at is not None and self.request_started_at<self.created_at:raise ValueError('Invalid send ordering')
        if self.accepted_at is not None and self.accepted_at<self.created_at:raise ValueError('Invalid acceptance ordering')
        return self

class OutcomeEpisode(OutcomeDTO):
    shop_id:str=Field(min_length=1,max_length=160)
    episode_id:str=Field(min_length=1,max_length=160)
    area:str=Field(pattern=r'^[0123456789bcdefghjkmnpqrstuvwxyz]{6}$')
    started_at:AwareDatetime
    closed_at:AwareDatetime|None=None
    owner_hash:str|None=Field(default=None,pattern=r'^[a-f0-9]{64}$')
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    deliveries:tuple[OutcomeDelivery,...]=Field(default=(),max_length=1000)
    history_status:Literal['complete','incomplete','overflowed']='complete'
    @model_validator(mode='after')
    def episode_facts(self):
        if self.is_demo!=(self.scenario_generation is not None):raise ValueError('Demo generation must be explicit and real state separate')
        if self.closed_at is not None and self.closed_at<self.started_at:raise ValueError('Invalid explicit closure')
        if any(row.created_at<self.started_at for row in self.deliveries):raise ValueError('Delivery predates confirmed episode')
        if not self.is_demo and any(row.source=='demo' or row.provenance!='telegram_api' for row in self.deliveries):raise ValueError('Synthetic delivery cannot enter real episode')
        return self

class OwnerOutcome(OutcomeDTO):
    response_id:str=Field(pattern=r'^[a-f0-9]{64}$')
    shop_id:str=Field(min_length=1,max_length=160)
    episode_id:str=Field(min_length=1,max_length=160)
    area:str=Field(pattern=r'^[0123456789bcdefghjkmnpqrstuvwxyz]{6}$')
    owner_hash:str=Field(pattern=r'^[a-f0-9]{64}$')
    answer:Literal['no','street_only','entrance','inside']
    depth_cm:int|None=Field(default=None,ge=0,le=1000)
    observed_at:AwareDatetime
    answered_at:AwareDatetime
    entrypoint:Literal['alert_response','owner_report']
    reference_basis:Literal['owner_declared','episode_reference']|None=None
    origin:Literal['telegram_owner','synthetic_fixture']='telegram_owner'
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    @model_validator(mode='after')
    def outcome_facts(self):
        expected='owner_declared' if self.entrypoint=='owner_report' else 'episode_reference'
        if self.reference_basis is None:object.__setattr__(self,'reference_basis',expected)
        elif self.reference_basis!=expected:raise ValueError('Reference time attribution must match the explicit entrypoint')
        if self.observed_at>self.answered_at:raise ValueError('Observation cannot follow response')
        if self.answer=='no' and self.depth_cm is not None:raise ValueError('No water cannot have inferred depth')
        if self.entrypoint=='owner_report' and self.answer!='inside':raise ValueError('Explicit unprompted flow records inside only')
        if self.is_demo!=(self.scenario_generation is not None) or (self.origin=='synthetic_fixture' and not self.is_demo):raise ValueError('Synthetic evidence cannot enter real state')
        return self

class PromptDecision(OutcomeDTO):
    due:bool
    reason:Literal['due','waiting','active_danger','no_owner','no_accepted_alert_or_closure','obsolete_scenario']
    due_at:AwareDatetime|None

class OutcomePrompt(OutcomeDTO):
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    shop_id:str
    episode_id:str
    status:Literal['accepted','simulated','pending','sending','retryable','uncertain','failed','superseded']
    provenance:Literal['telegram_api','local_virtual','synthetic_fixture']

class OutcomeCoverage(OutcomeDTO):
    is_demo:Literal[True]=True
    eligible_shop_episodes:int=Field(ge=0,le=1000)
    accepted_prompts:int=Field(ge=0,le=1000)
    virtual_prompts:int=Field(ge=0,le=1000)
    uncertain_or_sending_prompts:int=Field(ge=0,le=1000)
    responses:int=Field(ge=0,le=1000)
    fixture_responses:int=Field(ge=0,le=1000)
    no:int=Field(ge=0,le=1000)
    street_only:int=Field(ge=0,le=1000)
    entrance:int=Field(ge=0,le=1000)
    inside:int=Field(ge=0,le=1000)
    missing_unknown:int=Field(ge=0,le=1000)
    fixture_prompts:int=Field(ge=0,le=1000)
    definition:str='Synthetic owner reports and response coverage, not accuracy or independent water verification. Missing responses remain unknown; virtual delivery is not Telegram acceptance.'

class CalibrationState(OutcomeDTO):
    area:str=Field(pattern=r'^[0123456789bcdefghjkmnpqrstuvwxyz]{6}$')
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    version:int=Field(default=0,ge=0)
    multiplier:float=Field(default=1.,ge=.5,le=1.5)
    @model_validator(mode='after')
    def realm(self):
        if self.is_demo!=(self.scenario_generation is not None):raise ValueError('Calibration realms must remain separate')
        return self

class CalibrationEvidence(OutcomeDTO):
    episode:OutcomeEpisode
    response:OwnerOutcome

class CalibrationDecision(OutcomeDTO):
    reason:Literal['shrink','grow','no_change','insufficient_responses','no_fresh_evidence']
    old_multiplier:float
    new_multiplier:float
    expected_version:int
    new_version:int
    consumed_response_ids:tuple[str,...]
    consumed_outcome_keys:tuple[str,...]
    fixture_response_count:int
    response_count:int
    water_response_count:int
    window_start:AwareDatetime
    window_end:AwareDatetime

class RadiusPlan(OutcomeDTO):
    area:str=Field(pattern=r'^[0123456789bcdefghjkmnpqrstuvwxyz]{6}$')
    is_demo:bool
    scenario_generation:int|None=Field(default=None,ge=0)
    source:Literal['jps','met','shop_report','demo']
    level:Literal['watch','warning','danger']
    purpose:Literal['dispatch','corroboration','public_check']
    base_radius_m:float=Field(ge=1,le=10000)
    effective_radius_m:float=Field(ge=.5,le=15000)
    multiplier:float=Field(ge=.5,le=1.5)
    calibration_version:int|None=Field(default=None,ge=0)
    applied:bool
    @model_validator(mode='after')
    def consistent_target(self):
        if self.is_demo!=(self.scenario_generation is not None):raise ValueError('Targeting realm mismatch')
        if abs(self.effective_radius_m-self.base_radius_m*self.multiplier)>1e-8:raise ValueError('Inconsistent effective radius')
        if self.applied:
            if self.source not in ('demo','shop_report') or self.level!='warning' or self.purpose!='dispatch' or self.calibration_version is None:raise ValueError('Calibration cannot change authoritative or fixed targeting')
        elif self.multiplier!=1. or self.calibration_version is not None:raise ValueError('Unapplied targeting cannot carry calibration')
        return self

class CalibrationHistoryPoint(OutcomeDTO):
    evaluated_at:AwareDatetime
    old_multiplier:float=Field(ge=.5,le=1.5)
    new_multiplier:float=Field(ge=.5,le=1.5)
    reason:Literal['shrink','grow','no_change']
    response_count:int=Field(ge=0,le=100)
    water_response_count:int=Field(ge=0,le=100)
    fixture_response_count:int=Field(ge=0,le=100)
    @model_validator(mode='after')
    def denominator(self):
        if self.water_response_count>self.response_count:raise ValueError('Invalid response denominator')
        return self

class CalibrationAreaSummary(OutcomeDTO):
    area:str=Field(pattern=r'^[0123456789bcdefghjkmnpqrstuvwxyz]{6}$')
    multiplier:float=Field(ge=.5,le=1.5)
    version:int=Field(ge=0)
    evaluated_at:AwareDatetime|None
    history:tuple[CalibrationHistoryPoint,...]=Field(default=(),max_length=50)

class OutcomeSummary(OutcomeDTO):
    status:Literal['available','empty','unavailable']
    generated_at:AwareDatetime
    is_demo:Literal[True]=True
    scenario_generation:int|None=Field(default=None,ge=0)
    registered_synthetic_shops:int|None=Field(default=None,ge=0,le=50)
    coverage:OutcomeCoverage|None=None
    calibration_areas:tuple[CalibrationAreaSummary,...]=Field(default=(),max_length=50)
    history_truncated:bool=False
    note:str=Field(min_length=1,max_length=1024)
    @model_validator(mode='after')
    def public_scope(self):
        if sum(len(area.history) for area in self.calibration_areas)>50:raise ValueError('Public calibration history exceeds bound')
        if len({area.area for area in self.calibration_areas})!=len(self.calibration_areas):raise ValueError('Duplicate public area')
        if self.status=='unavailable':
            if self.scenario_generation is not None or self.registered_synthetic_shops is not None or self.coverage is not None or self.calibration_areas:raise ValueError('Unavailable outcome scope cannot invent data')
        elif self.scenario_generation is None or self.registered_synthetic_shops is None or self.coverage is None:raise ValueError('Known outcome scope requires coverage')
        if self.status=='empty' and (self.coverage.eligible_shop_episodes or self.calibration_areas):raise ValueError('Empty outcome scope cannot contain history')
        return self
