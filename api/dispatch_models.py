"""Private dispatch inputs and immutable displayed-action snapshots."""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from api.models import Level


class EventRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    request_id: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.:-]+$')
    source: Literal['jps', 'met', 'shop_report', 'demo'] = 'demo'
    level: Level
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=1000, ge=1, le=10_000)
    confidence: float = Field(default=1, ge=0, le=1)
    reporter_shop_id: str | None = Field(default=None, min_length=1, max_length=128)
    processing_started_at: AwareDatetime | None = None
    simulation: bool = False
    episode_id: str | None = Field(default=None, min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.:-]+$')
    warning_structure: Literal['warning_intro_fallback'] | None = None
    source_key: str | None = None
    source_episode_id: str | None = None
    source_observed_at: AwareDatetime | None = None
    source_valid_until: AwareDatetime | None = None
    reason: str = Field(default='Simulated warning', min_length=1, max_length=512)


class Recipient(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    telegram_chat_id: int
    language: Literal['en','ms','zh','ta','bn','ne','my','id']
    role: Literal['owner','worker']


class VirtualRecipient(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    key: str = Field(pattern=r'^fixture-[a-z0-9-]{1,80}$')
    language: Literal['en','ms','zh','ta','bn','ne','my','id'] = 'en'


class LiftItem(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True, allow_inf_nan=False)
    item_name: str = Field(min_length=1, max_length=100)
    qty: float = Field(gt=0, le=1_000_000)
    value_rm: float = Field(ge=0, le=1_000_000_000)
    lift_effort: Literal[1,2,3]


class Shop(BaseModel):
    model_config = ConfigDict(extra='ignore', strict=True, allow_inf_nan=False)
    shop_id: str = Field(min_length=1)
    shop_name: str = Field(min_length=1, max_length=200)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    recipients: list[Recipient] = Field(max_length=20)
    is_demo: bool = False
    virtual_recipient: VirtualRecipient | None = None
    has_vehicle: bool = False
    vehicle_type: Literal['car','van','lorry','motorcycle'] | None = None
    lift_first: list[LiftItem] = Field(default_factory=list, max_length=8)
    baseline_inventory_id: str | None = None

    @model_validator(mode='after')
    def unique_recipients(self) -> 'Shop':
        if self.virtual_recipient and (not self.is_demo or self.recipients):raise ValueError('Virtual recipients require a synthetic shop without Telegram recipients')
        if len({r.telegram_chat_id for r in self.recipients}) != len(self.recipients):
            raise ValueError('Duplicate recipients')
        return self


class Destination(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=100, pattern=r'^[^\n\r{}<>]+$')
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    source: str = Field(min_length=1, max_length=500)

    safe_point_id: str | None = None
    type: Literal['pps', 'parking', 'high_ground'] | None = None
    source_date: str | None = None
    designation_context: str | None = None
    coordinate_source: str | None = None
    opening_status: Literal['unknown', 'closed'] = 'unknown'
    min_level: int | None = Field(default=None, ge=1, le=100)
    min_level_source: str | None = None
    coordinate_provenance: str | None = None

    @property
    def route_link(self) -> str:
        return f'https://www.google.com/maps/dir/?api=1&destination={self.lat},{self.lng}'


class ActionSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    inventory_id: str | None = None
    items: tuple[LiftItem, ...] = ()
    estimated_value_rm: float = Field(default=0, ge=0)
    vehicle_type: str | None = None
    vehicle_target_at: AwareDatetime | None = None
    stock_target_at: AwareDatetime | None = None
    destination: Destination | None = None
    parking_destination: Destination | None = None
    shelter_destination: Destination | None = None
    vehicle_action_id: str | None = None
    stock_action_id: str | None = None
    episode_id: str | None = None

    @model_validator(mode='after')
    def ordered_targets(self) -> 'ActionSnapshot':
        if self.vehicle_target_at and self.stock_target_at and self.vehicle_target_at >= self.stock_target_at:
            raise ValueError('Vehicle action target must precede stock')
        return self
