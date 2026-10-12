"""Validated official observations; source availability is independent of risk."""
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Source = Literal['jps', 'met']
Level = Literal['watch', 'warning', 'danger']


class Geography(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    district: str | None = Field(default=None, min_length=1)
    state: str | None = Field(default=None, min_length=1)

    @model_validator(mode='after')
    def applicable_place(self) -> 'Geography':
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('coordinates must be paired')
        if self.latitude is None and not (self.district and self.state):
            raise ValueError('coordinates or attributed district and state required')
        return self


class Warning(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    source: Source
    source_id: str = Field(min_length=1)
    level: Level
    observed_at: AwareDatetime
    geography: Geography
    reason: str = Field(min_length=1)
    source_indicator: str | None = None
    valid_until: AwareDatetime | None = None


class SourceResult(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    source: Source
    status: Literal['current', 'empty', 'degraded', 'stale', 'unsupported', 'unavailable']
    checked_at: AwareDatetime
    warnings: tuple[Warning, ...] = ()
    records_received: int = Field(default=0, ge=0)
    records_current: int = Field(default=0, ge=0)
    resolved: dict[str, AwareDatetime] = Field(default_factory=dict)
    rejected: dict[str, int] = Field(default_factory=dict)
    detail: str | None = None
