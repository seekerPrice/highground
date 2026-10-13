"""Bounded policy extraction, frozen estimate comparison and synthetic aggregates."""
from datetime import date,datetime
import re
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

MAX_POLICY_BYTES=20_000_000
MAX_POLICY_PHOTOS=5

class PolicyDTO(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)

class PolicyAssessment(PolicyDTO):
    insurer:str|None=Field(default=None,max_length=120)
    policy_type:str|None=Field(default=None,max_length=120)
    flood_covered:Literal['yes','no','unclear']
    coverage_evidence:Literal['included','excluded','unclear']
    sum_insured_rm:float|None=Field(default=None,ge=0,le=1_000_000_000)
    sum_insured_scope:Literal['stock','contents','stock_and_contents','unclear']='unclear'
    currency:Literal['MYR','unclear']='unclear'
    currency_evidence_quote:str|None=Field(default=None,max_length=120)
    sum_insured_evidence_quote:str|None=Field(default=None,max_length=200)
    excess_evidence_quote:str|None=Field(default=None,max_length=200)
    excess_rm:float|None=Field(default=None,ge=0,le=1_000_000_000)
    expiry_date:date|None=None
    evidence_quote:str|None=Field(default=None,max_length=300)

    @field_validator('insurer','policy_type','evidence_quote','currency_evidence_quote','sum_insured_evidence_quote','excess_evidence_quote')
    @classmethod
    def bounded_text(cls,value):
        if value is not None and (not value.strip() or any(ord(c)<32 for c in value) or any(c in value for c in '<>{}')):
            raise ValueError('Policy field must be bounded plain single-line text')
        return value

    @model_validator(mode='after')
    def qualified_fields(self):
        permitted={'yes':{'included'},'no':{'excluded'},'unclear':{'unclear'}}
        if self.coverage_evidence not in permitted[self.flood_covered]:raise ValueError('Contradictory policy coverage evidence')
        if self.flood_covered!='unclear' and not self.evidence_quote:raise ValueError('Explicit coverage requires an exact bounded quote')
        affirmative=r'(?i)(\b(?:flood|special[ -]perils)\b[^.;]{0,60}\b(?:included|covered|insured)\b|\b(?:includes|covers|insures)\b[^.;]{0,60}\b(?:flood|special[ -]perils)\b|\bbanjir\b[^.;]{0,60}\b(?:dilindungi|termasuk)\b)'
        if self.flood_covered=='yes':
            quote=self.evidence_quote or ''
            negative_or_conditional=r'(?i)(\b(?:unless|conditional|if|jika|tertakluk|excluded|excludes|exclusion|dikecualikan)\b|not\s+(?:covered|included|insured)|tidak\s+dilindungi|no\s+(?:flood\s+)?cover|subject\s+to)'
            if not re.search(affirmative,quote) or re.search(negative_or_conditional,quote):raise ValueError('Unrecognized or conditional inclusion must remain unclear')
        if self.flood_covered=='no':
            quote=self.evidence_quote or ''
            explicit=r'(?i)(\bflood\s+(?:(?:is|are)\s+)?(?:excluded|not\s+(?:covered|insured))\b|\bexclud(?:es|ed|ing)\b[^.;]{0,60}\bflood\b|\bno\s+flood\s+cover\b|\bdoes\s+not\s+cover\s+flood\b|\bbanjir\b[^.;]{0,60}(?:tidak\s+dilindungi|dikecualikan)|dikecualikan[^.;]{0,60}\bbanjir\b)'
            ambiguous=r'(?i)(\b(?:unless|conditional|if|jika|tertakluk)\b|except\s+when|subject\s+to|not\s+exclud|no\s+exclusion)'
            remaining=re.sub(r'(?i)\b(?:not\s+(?:covered|included|insured)|tidak\s+dilindungi)\b','',quote)
            contrary=re.search(r'(?i)\b(?:included|covered|insured|includes|covers|insures|dilindungi|termasuk)\b',remaining)
            if not re.search(explicit,quote) or re.search(ambiguous,quote) or contrary:raise ValueError('Unrecognized, contradictory or conditional exclusion must remain unclear')
        if self.sum_insured_rm is not None:
            if self.sum_insured_scope=='unclear':raise ValueError('Unclear stock/contents limit must remain unknown')
            quote=self.sum_insured_evidence_quote or ''
            if not re.search(r'(?i)\b(stock|contents|stok|kandungan)\b',quote) or re.search(r'(?i)\b(premium|building|bangunan)\b',quote):raise ValueError('Only unambiguous stock/contents insured limits may be quantified')
            if not re.search(r'(?i)(sum insured|insured amount|insured limit|jumlah.*insurans|had.*perlindungan)',quote):raise ValueError('Quote must identify the insured limit')
        if self.excess_rm is not None and not re.search(r'(?i)\b(excess|deductible|lebihan|deduktibel)\b',self.excess_evidence_quote or ''):raise ValueError('Quote must identify an explicit currency excess')
        if self.excess_rm is not None:
            fixed_excess=r'(?i)(?:excess|deductible|lebihan|deduktibel)\b\s*(?::|is\b|of\b)?\s*(?:(?:RM|MYR|ringgit)\s*\d[\d,.]*|\d[\d,.]*\s*(?:RM|MYR|ringgit))\s*[.;]?'
            if not re.fullmatch(fixed_excess,(self.excess_evidence_quote or '').strip()):raise ValueError('Unrecognized or conditional excess context must remain unknown')
        for amount,quote in ((self.sum_insured_rm,self.sum_insured_evidence_quote),(self.excess_rm,self.excess_evidence_quote)):
            if amount is None:continue
            currency=self.currency_evidence_quote or ''
            if self.currency!='MYR' or not re.search(r'(?i)(?<![A-Za-z])(RM|MYR|ringgit)(?![A-Za-z])',currency):raise ValueError('Unclear currency must leave amounts unknown')
            for excerpt in (currency,quote or ''):
                context=r'(?i)(?:\b(?:currency|currencies|mata\s+wang)\s*[:=]?\s+([A-Za-z]{2,3})\b|\b([A-Za-z]{3})\s+(?:RM|MYR)\s*(?=\d)|\b(?:RM|MYR)\s*(?:and|or|/|dan|atau)\s*([A-Za-z]{3})\b|\b([A-Za-z]{3})\s*(?:and|or|/|dan|atau)\s*(?:RM|MYR)\b)'
                if any(next(token for token in match.groups() if token).upper() not in ('RM','MYR') for match in re.finditer(context,excerpt)):raise ValueError('Mixed or contradictory quoted currency must remain unknown')
            if not quote or re.search(r'(?i)(%|(?<![A-Za-z])(?:USD|SGD|IDR|premium)(?![A-Za-z])|US\$)',quote):raise ValueError('Conditional/non-MYR amounts must remain unknown')
            amounts=[]
            for token in re.findall(r'(?<![\d.,])\d[\d,.]*',quote):
                number=token[:-1] if token.endswith('.') else token
                if re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?',number):
                    amounts.append(Decimal(number.replace(',','')))
            currency_token=r'(?<![A-Za-z])(?:RM|MYR|ringgit)(?![A-Za-z])'
            numeric_token=r'(?<![\d.,])\d[\d,.]*'
            quoted_money=re.findall(currency_token+r'\s*('+numeric_token+r')(?![A-Za-z])|('+numeric_token+r')\s*'+currency_token,quote,flags=re.IGNORECASE)
            bound=[]
            for prefix,suffix in quoted_money:
                number=prefix or suffix
                number=number[:-1] if number.endswith('.') else number
                if re.fullmatch(r'(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?',number):bound.append(Decimal(number.replace(',','')))
            if len(amounts)!=1 or len(bound)!=1 or bound[0]!=Decimal(str(amount)) or amounts[0]!=bound[0]:raise ValueError('One unambiguous quoted MYR amount must match the field')
        return self

class FrozenPolicyInventory(PolicyDTO):
    inventory_id:str|None
    total_est_value_rm:float|None=Field(ge=0,le=1_000_000_000)
    confidence:float|None=Field(ge=0,le=1)
    status:Literal['available','unavailable']
    provenance:Literal['replacement_price_estimate']='replacement_price_estimate'

    @model_validator(mode='after')
    def available_fields(self):
        if self.status=='available' and (not self.inventory_id or self.total_est_value_rm is None):raise ValueError('Inconsistent frozen inventory estimate')
        if self.status=='unavailable' and any(value is not None for value in (self.inventory_id,self.total_est_value_rm,self.confidence)):raise ValueError('Unavailable inventory fields must all be unknown')
        return self

class PolicyComparison(PolicyDTO):
    status:Literal['not_covered','unclear','expired','baseline_unavailable','limit_unavailable','estimated_shortfall','no_estimated_shortfall']
    inventory_id:str|None
    inventory_estimate_rm:float|None
    estimated_limit_gap_rm:float|None
    assessed_on:date
    expiry_status:Literal['current_date_indicated','expired','unknown']
    scope_note:str='The document stock/contents limit is compared with a frozen inventory replacement-price estimate; scope may differ. Excess is not added to cover.'
    disclaimer:str='Document extraction does not establish current coverage or a guaranteed payout. Check with your insurer.'

class PolicyOriginal(PolicyDTO):
    media_id:str=Field(pattern=r'^[0-9a-f]{64}$')
    sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    bytes:int=Field(gt=0,le=MAX_POLICY_BYTES)
    mime_type:Literal['image/jpeg','image/png','image/webp','application/pdf']
    object_generation:str=Field(pattern=r'^[1-9][0-9]{0,30}$')
    deletion_status:Literal['retained','deletion_pending','deleted']='retained'

class PolicyReply(PolicyDTO):
    text:str=Field(max_length=4096)
    reply_markup:dict|None=None
    venue:None=None
    shop_id:str|None=None
    language:str='en'
    is_demo:bool=False
    kind:Literal['policy_prompt','policy_result','policy_unavailable','danger']
    intake_id:str|None=None
    disclosure:bool=False

class PolicyAggregate(PolicyDTO):
    is_demo:Literal[True]=True
    registered_synthetic_shops:int
    assessed_known_coverage:int
    flood_cover_indicated:int
    explicit_no_flood_cover:int
    unclear_or_expired:int
    missing_policies:int
    without_cover_percent_of_known:float|None
    uninsured_stock_estimate_rm:float|None
    unknown_stock_estimates:int
    definition:str='Synthetic only. Explicit no-cover and indicated stock/contents limit gaps use frozen replacement-price estimates; missing, unclear, expired and unknown amounts are separate. No guaranteed payout or current-cover claim.'


def compare_policy(assessment:PolicyAssessment,baseline:FrozenPolicyInventory,as_of:date) -> PolicyComparison:
    fields=dict(expiry_status='unknown' if assessment.expiry_date is None else 'expired' if assessment.expiry_date<as_of else 'current_date_indicated',inventory_id=baseline.inventory_id,inventory_estimate_rm=baseline.total_est_value_rm,estimated_limit_gap_rm=None,assessed_on=as_of)
    if assessment.expiry_date is not None and assessment.expiry_date<as_of:status='expired'
    elif assessment.flood_covered=='unclear':status='unclear'
    elif assessment.flood_covered=='no':status='not_covered'
    elif baseline.status=='unavailable':status='baseline_unavailable'
    elif assessment.sum_insured_rm is None:status='limit_unavailable'
    else:
        fields['estimated_limit_gap_rm']=round(max(0,baseline.total_est_value_rm-assessment.sum_insured_rm),2)
        status='estimated_shortfall' if fields['estimated_limit_gap_rm']>0 else 'no_estimated_shortfall'
    return PolicyComparison(status=status,**fields)


def aggregate_policies(shop_ids:set[str],rows:list[dict],as_of:date) -> PolicyAggregate:
    latest={}
    for row in rows:
        if row.get('is_demo') is not True or row.get('shop_id') not in shop_ids or row.get('status')!='complete':continue
        previous=latest.get(row['shop_id'])
        if previous is None or (row['created_at'],row['policy_id'])>(previous['created_at'],previous['policy_id']):latest[row['shop_id']]=row
    yes=no=unclear=unknown=0;amounts=[]
    for row in latest.values():
        assessment=PolicyAssessment.model_validate(row['assessment'])
        baseline=FrozenPolicyInventory.model_validate(row['baseline'])
        compared=compare_policy(assessment,baseline,as_of)
        if compared.status in ('unclear','expired') or compared.expiry_status=='unknown':unclear+=1;unknown+=1;continue
        if assessment.flood_covered=='no':
            no+=1
            if baseline.total_est_value_rm is not None:amounts.append(baseline.total_est_value_rm)
            else:unknown+=1
        else:
            yes+=1
            if compared.estimated_limit_gap_rm is not None:amounts.append(compared.estimated_limit_gap_rm)
            else:unknown+=1
    known=yes+no
    return PolicyAggregate(registered_synthetic_shops=len(shop_ids),assessed_known_coverage=known,flood_cover_indicated=yes,explicit_no_flood_cover=no,unclear_or_expired=unclear,missing_policies=len(shop_ids)-len(latest),without_cover_percent_of_known=round(100*no/known,2) if known else None,uninsured_stock_estimate_rm=round(sum(amounts),2) if amounts else None,unknown_stock_estimates=unknown+len(shop_ids)-len(latest))
