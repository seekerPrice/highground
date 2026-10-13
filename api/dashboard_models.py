"""Bounded synthetic-only public dashboard contracts."""
from typing import Literal
from pydantic import AwareDatetime, Field
from api.report_models import DTO
from api.destinations import SafePoint

class DashboardShop(DTO):
    shop_id: str
    shop_name: str
    shop_type: str
    lat: float
    lng: float
    level: Literal['none','watch','warning','danger']
    risk_score: int | None
    is_demo: Literal[True] = True

class DashboardEvent(DTO):
    event_id: str
    created_at: AwareDatetime
    level: Literal['watch','warning','danger']
    lat: float
    lng: float
    radius_m: int = Field(ge=1,le=10000)
    reason: str
    confidence: float = Field(ge=0,le=1)
    is_demo: Literal[True] = True

class SourceStatus(DTO):
    source: Literal['jps','met']
    status: Literal['fresh','stale','unavailable']
    checked_at: AwareDatetime | None
    note: str

class DashboardStats(DTO):
    status: Literal['available','unavailable']
    synthetic_shops: int
    virtual_alerts_simulated: int | None = None
    virtual_alert_definition: str = 'Local virtual delivery simulation; no Telegram API call, delivery/read receipt or real self-report.'
    alerts_accepted: int | None
    average_alert_acceptance_ms: float | None
    vehicles_reported_moved: int | None
    estimated_stock_value_reported_lifted_rm: float | None
    stock_value_label: str = 'Estimated stock value reported lifted'
    stock_value_definition: str = 'Maximum actually displayed confirmed stock estimate per shop and episode, summed across shops and episodes; self-reported.'
    vehicle_definition: str = 'One self-reported vehicle completion per shop and episode.'
    alert_definition: str = 'Telegram API acceptance; does not establish delivery or reading. Latency is measured from event receipt to API acceptance.'

class Dashboard(DTO):
    generated_at: AwareDatetime
    status: Literal['available','empty','unavailable']
    is_demo: Literal[True] = True
    scenario_started_at: AwareDatetime | None
    scenario_generation: int = Field(default=0,ge=0)
    scenario_state: Literal['ready','resetting'] = 'ready'
    shops: list[DashboardShop] = Field(max_length=50)
    events: list[DashboardEvent] = Field(max_length=100)
    destinations: list[SafePoint] = Field(max_length=100)
    sources: list[SourceStatus] = Field(max_length=2)
    stats: DashboardStats

class ResetRequest(DTO):
    request_id: str = Field(min_length=1,max_length=128,pattern=r'^[A-Za-z0-9_.:-]+$')

class ResetResult(DTO):
    status: Literal['reset','resetting']
    generation: int
    scenario_started_at: str | None
    shops_reset: int
    inflight_outcomes_unknown: int
    delivery_note: str
