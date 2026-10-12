"""Bounded visible-video inventory and immutable display facts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator
from api.photo_models import PhotoReply

class VideoMedia(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    file_id: str = Field(min_length=1,max_length=512)
    file_unique_id: str = Field(min_length=1,max_length=512)
    file_size: StrictInt | None = Field(default=None,gt=0)
    duration: StrictInt = Field(ge=1,le=300)
    width: StrictInt = Field(gt=0,le=16384)
    height: StrictInt = Field(gt=0,le=16384)
    mime_type: Literal['video/mp4'] = 'video/mp4'

class InventoryItem(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    name: str = Field(min_length=1,max_length=60,pattern=r'^[^\n\r{}<>]+$')
    category: str = Field(min_length=1,max_length=60)
    qty: float = Field(gt=0,le=1000000)
    est_unit_value_rm: float = Field(ge=0,le=1000000)
    location_in_shop: str = Field(min_length=1,max_length=100)
    height: Literal['floor','low','high']
    lift_effort: Literal[1,2,3]
    timestamp_s: float = Field(ge=0,le=300)

class InventoryAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False)
    items: list[InventoryItem] = Field(max_length=80)
    confidence: float = Field(ge=0,le=1)
    confidence_note: str = Field(min_length=1,max_length=200)

    def validate_duration(self,duration: int) -> 'InventoryAssessment':
        if any(item.timestamp_s>duration for item in self.items):
            raise ValueError('Evidence timestamp exceeds submitted video duration')
        if sum(item.qty*item.est_unit_value_rm for item in self.items)>1_000_000_000:
            raise ValueError('Inventory value exceeds bounded estimate')
        return self

class InventoryReply(BaseModel):
    model_config = ConfigDict(extra='forbid',frozen=True)
    text: str
    reply_markup: dict | None = None
    venue: dict | None = None
    shop_id: str | None = None
    language: str = 'en'
    is_demo: bool = False
    inventory_id: str | None = None
    kind: Literal['inventory','prompt','unavailable','danger']
