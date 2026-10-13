"""Immutable derived-card facts; the model cannot supply property/place amounts."""
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import AwareDatetime,BaseModel,ConfigDict,Field,model_validator,field_validator
from api.dispatch_models import LiftItem
from api.destinations import SafePoint
from api.i18n import text,catalog

LANGUAGES=Literal['en','ms','zh','ta','bn','ne','my','id']

class CardContext(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,strict=True,allow_inf_nan=False)
    card_id: str = Field(pattern=r'^[0-9a-f]{64}$')
    shop_id: str = Field(min_length=1,max_length=128)
    shop_name: str = Field(min_length=1,max_length=200)
    language: LANGUAGES
    lat: float = Field(ge=-90,le=90)
    lng: float = Field(ge=-180,le=180)
    inventory_id: str | None = None
    items: tuple[LiftItem,...] = Field(default=(),max_length=5)
    displayed_value_rm: float = Field(default=0,ge=0,le=5_000_000_000)
    parking: SafePoint | None = None
    shelter: SafePoint | None = None
    prepared_at: AwareDatetime
    is_demo: bool
    episode_id: str | None = None
    event_id: str | None = None
    scenario_generation: int | None = Field(default=None,ge=0)

    @field_validator('shop_name')
    @classmethod
    def plain_name(cls,value):
        import unicodedata
        if any(unicodedata.category(c).startswith('C') and c not in ('\u200c','\u200d') for c in value):raise ValueError('Shop name contains unsupported control characters')
        return value

    @model_validator(mode='after')
    def canonical_facts(self):
        if self.items and not self.inventory_id:raise ValueError('Displayed items require an inventory identity')
        if abs(self.displayed_value_rm-sum(item.value_rm for item in self.items))>.005:raise ValueError('Card total must equal displayed immutable items only')
        for point,kind in ((self.parking,'parking'),(self.shelter,'pps')):
            if point and (point.type!=kind or point.is_demo or point.opening_status=='closed'):raise ValueError('Card destinations require eligible sourced listings')
        return self

class CardChoice(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    title: Literal['card_title','card_title_actions'] = 'card_title'
    footer: Literal['card_footer'] = 'card_footer'

class CardText(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    title: str
    lift_lines: tuple[str,...]
    parking_line: str
    shelter_line: str
    emergency_line: str
    footer: str


def card_text(context:CardContext,choice:CardChoice=CardChoice())->CardText:
    language=context.language
    def t(key,**facts):return text(language,key,**facts)
    def place(point,missing):
        if point is None:return t(missing)
        return t('card_place',name=point.name,address=point.address_text)+'\n'+t('card_opening_unknown')
    lines=tuple(t('card_item',item_name=item.item_name,qty=f'{item.qty:g}',value_rm=f'{item.value_rm:.2f}') for item in context.items)
    lines=lines+(t('card_total',value_rm=f'{context.displayed_value_rm:.2f}'),) if lines else (t('card_inventory_missing'),)
    footer=t(choice.footer)
    if not catalog(language)['_reviewed']:footer+='\n'+t('translation_notice')
    return CardText(title=t(choice.title),lift_lines=lines,parking_line=place(context.parking,'card_no_parking'),shelter_line=place(context.shelter,'card_no_shelter'),emergency_line=t('card_emergency'),footer=footer)


def card_time(context:CardContext)->str:
    return context.prepared_at.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%Y-%m-%d %H:%M')


def card_from_storage(value:dict)->CardContext:
    """Firestore arrays decode as lists; normalize only this owned tuple field."""
    stored=dict(value)
    if isinstance(stored.get('items'),list):stored['items']=tuple(stored['items'])
    return CardContext.model_validate(stored)
