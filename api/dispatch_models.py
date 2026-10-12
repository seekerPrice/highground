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
    reason: str = Field(default='Simulated warning', min_length=1, max_length=512)


class Recipient(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    telegram_chat_id: int
    language: Literal['en','ms','zh','ta','bn','ne','my','id']
    role: Literal['owner','worker']


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
    has_vehicle: bool = False
    vehicle_type: Literal['car','van','lorry','motorcycle'] | None = None
    lift_first: list[LiftItem] = Field(default_factory=list, max_length=8)
    baseline_inventory_id: str | None = None

    @model_validator(mode='after')
    def unique_recipients(self) -> 'Shop':
        if len({r.telegram_chat_id for r in self.recipients}) != len(self.recipients):
            raise ValueError('Duplicate recipients')
        return self


class Destination(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=100, pattern=r'^[^\n\r{}<>]+$')
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    source: str = Field(min_length=1, max_length=500)

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

    @model_validator(mode='after')
    def ordered_targets(self) -> 'ActionSnapshot':
        if self.vehicle_target_at and self.stock_target_at and self.vehicle_target_at >= self.stock_target_at:
            raise ValueError('Vehicle action target must precede stock')
        return self
