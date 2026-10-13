"""Sourced historical listings; nearest is geography, never an availability claim."""
from datetime import date
from typing import Literal
from urllib.parse import urlsplit

from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from api.dispatch_models import Destination
from api.tools.geo import distance_m


class SafePoint(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, allow_inf_nan=False)
    safe_point_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    name: str = Field(min_length=1, max_length=100, pattern=r'^[^\n\r{}<>]+$')
    type: Literal['pps', 'parking', 'high_ground']
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address_text: str = Field(min_length=1, max_length=300)
    source: str = Field(min_length=1, max_length=500)
    source_date: str
    designation_context: Literal['official_listing', 'attributed_report', 'community_listing']
    coordinate_source: str = Field(min_length=1, max_length=500)
    coordinate_provenance: str = Field(min_length=1, max_length=300)
    verified: bool  # Historical source checked, not current opening or safety.
    opening_status: Literal['unknown', 'closed'] = 'unknown'
    min_level: int | None = Field(default=None, ge=1, le=100)
    min_level_source: str | None = None
    is_demo: bool = False

    @field_validator('source', 'coordinate_source', 'min_level_source')
    @classmethod
    def source_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        url = urlsplit(value)
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Source must be an attributed HTTPS URL')
        return value

    @field_validator('source_date')
    @classmethod
    def real_source_date(cls, value: str) -> str:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError('Source date must be ISO YYYY-MM-DD')
        return value

    @model_validator(mode='after')
    def sourced_floor(self) -> 'SafePoint':
        if self.min_level is not None and (self.type != 'parking' or not self.min_level_source):
            raise ValueError('A parking floor needs its own inspected source')
        return self

    def destination(self) -> Destination:
        return Destination(name=self.name, lat=self.lat, lng=self.lng, source=self.source,
                           safe_point_id=self.safe_point_id, type=self.type, source_date=self.source_date,
                           designation_context=self.designation_context, coordinate_source=self.coordinate_source,
                           opening_status=self.opening_status, min_level=self.min_level,
                           min_level_source=self.min_level_source, coordinate_provenance=self.coordinate_provenance)


class DestinationLookup:
    def __init__(self, client: firestore.Client, *, collection: str = 'safe_points', radius_m: int = 20000) -> None:
        if type(radius_m) is not int or not 1 <= radius_m <= 100000:
            raise ValueError('Destination search radius must be 1..100000 metres')
        self.client, self.collection, self.radius_m = client, collection, radius_m

    def nearest(self, lat: float, lng: float, types: tuple[str, ...]) -> Destination | None:
        distance_m(lat, lng, lat, lng)  # Validate caller coordinates even with an empty registry.
        if not types or any(kind not in ('pps', 'parking', 'high_ground') for kind in types):
            raise ValueError('Unsupported destination type')
        candidates = []
        records=list(self.client.collection(self.collection).limit(1001).stream(timeout=8,retry=None))
        if len(records)>1000:return None # Do not claim nearest from a truncated registry.
        for record in records:
            try:
                point = SafePoint.model_validate(dict(record.to_dict(), safe_point_id=record.id))
            except (ValidationError, TypeError):
                continue
            if point.is_demo or point.type not in types or point.opening_status == 'closed':
                continue
            meters = distance_m(lat, lng, point.lat, point.lng)
            if meters <= self.radius_m:
                candidates.append((meters, point.safe_point_id, point))
        if not candidates:
            return None
        return min(candidates, key=lambda row: (row[0], row[1]))[2].destination()
