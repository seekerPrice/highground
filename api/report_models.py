"""Strict loss-domain validation and capability-scoped public report contracts."""
from typing import Literal
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from api.inventory_models import InventoryAssessment

class DTO(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class LossItem(DTO):
    item_id: str = Field(min_length=1, max_length=160)
    condition: Literal['ok','damaged','destroyed','missing','unassessed']
    estimated_loss_rm: float | None = Field(ge=0, le=1_000_000_000)
    evidence_timestamp_s: float | None = Field(ge=0, le=300)
    uncertainty: str = Field(min_length=1, max_length=300)

class LossAssessment(DTO):
    items: list[LossItem] = Field(max_length=80)
    total_loss_rm: float | None = Field(ge=0, le=1_000_000_000)
    summary_text: str = Field(min_length=1, max_length=1200)
    confidence: float = Field(ge=0, le=1)
    confidence_note: str = Field(min_length=1, max_length=300)

    def validate_baseline(self, baseline: dict, duration: int) -> 'LossAssessment':
        expected = {f"{baseline['inventory_id']}:{i}": row for i,row in enumerate(baseline['items'])}
        seen=set(); assessed=[]
        for item in self.items:
            if item.item_id in seen or item.item_id not in expected: raise ValueError('Unknown or duplicate item identity')
            seen.add(item.item_id)
            row=expected[item.item_id]; maximum=round(row['qty']*row['est_unit_value_rm'],2)
            if item.evidence_timestamp_s is not None and item.evidence_timestamp_s>duration: raise ValueError('Timestamp exceeds after-video')
            if item.condition in ('missing','unassessed'):
                if item.estimated_loss_rm is not None: raise ValueError('Uncertain absence has unknown loss')
            else:
                if item.estimated_loss_rm is None or item.evidence_timestamp_s is None: raise ValueError('Assessed loss requires visible evidence')
                if item.estimated_loss_rm>maximum or (item.condition=='ok' and item.estimated_loss_rm!=0): raise ValueError('Loss exceeds baseline or contradicts condition')
                if abs(item.estimated_loss_rm-round(item.estimated_loss_rm,2))>0.000001: raise ValueError('Loss must use cents')
                assessed.append(item.estimated_loss_rm)
        total=round(sum(assessed),2) if assessed else None
        if self.total_loss_rm!=total or (total is not None and total>baseline['total_est_value_rm']): raise ValueError('Invalid assessed aggregate')
        return self

class ReportItem(LossItem):
    name: str
    qty: float
    baseline_estimate_rm: float

class EvidenceReceipt(DTO):
    media_id: str
    kind: Literal['baseline_video','update_video','after_video','waterline_photo']
    sha256: str
    bytes: int
    mime_type: str
    uploaded_at: AwareDatetime
    telegram_date: AwareDatetime
    lat: float
    lng: float
    location_attribution: Literal['confirmed_shop','confirmed_shared','unconfirmed_shop']
    is_demo: bool
    integrity_status: Literal['not_checked'] = 'not_checked'

class Report(DTO):
    report_id: str
    created_at: AwareDatetime
    shop_name: str
    is_demo: bool
    baseline_estimate_rm: float
    estimated_loss_rm: float | None
    estimate_status: Literal['available','unavailable']
    coverage: Literal['complete','partial','none']
    assessed_items: int
    baseline_items: int
    confidence: float
    confidence_note: str
    summary_text: str
    recovery_attribution: str
    items: list[ReportItem] = Field(max_length=80)
    evidence: list[EvidenceReceipt] = Field(max_length=10)
    disclaimer: str = 'Replacement-price and loss estimates only. Unknown items are excluded from the assessed total. File integrity does not authenticate the scene, time, location or valuation.'

class IntegrityResult(DTO):
    media_id: str
    status: Literal['verified','mismatch','unavailable']
    sha256: str
    note: str = 'Checks stored file bytes only; does not authenticate the scene, time, location or valuation.'


def freeze_baseline(record: dict) -> dict:
    validated=InventoryAssessment(items=record['items'],confidence=record['confidence'],confidence_note=record['confidence_note'])
    total=round(sum(item.qty*item.est_unit_value_rm for item in validated.items),2)
    if not validated.items or total!=record['total_est_value_rm']: raise ValueError('Unavailable or invalid baseline')
    return dict(inventory_id=record['inventory_id'],media_id=record['media_id'],items=[item.model_dump() for item in validated.items],total_est_value_rm=total,confidence=validated.confidence,confidence_note=validated.confidence_note)
