"""Deterministic geohash6 and conservative non-official Warning radius plans."""
import math
from datetime import datetime,timedelta
from hashlib import sha256
from api.outcome_models import CalibrationState,CalibrationEvidence,CalibrationDecision,RadiusPlan,OwnerOutcome
from api.outcomes import first_outcomes


def geohash6(latitude:float,longitude:float)->str:
    for value,limit in ((latitude,90),(longitude,180)):
        if type(value) not in (int,float) or not math.isfinite(value) or not -limit<=value<=limit:raise ValueError('Invalid confirmed coordinates')
    bounds=[[-180.,180.],[-90.,90.]];coordinates=[longitude,latitude];bits=0
    for index in range(30):
        axis=index%2;low,high=bounds[axis];middle=(low+high)/2
        upper=coordinates[axis]>=middle
        bits=(bits<<1)|int(upper)
        bounds[axis]=[middle,high] if upper else [low,middle]
    alphabet='0123456789bcdefghjkmnpqrstuvwxyz'
    return ''.join(alphabet[(bits>>shift)&31] for shift in range(25,-1,-5))


def outcome_key(response:OwnerOutcome)->str:
    return sha256(f'{response.is_demo}:{response.scenario_generation}:{response.shop_id}:{response.episode_id}'.encode()).hexdigest()


def _alert_coverage(row:CalibrationEvidence)->bool:
    response=row.response
    if response.entrypoint!='alert_response':return False
    return any(delivery.level in ('warning','danger') and delivery.status=='accepted' and delivery.provenance=='telegram_api' and delivery.accepted_at<=response.answered_at for delivery in row.episode.deliveries) or (response.is_demo and response.origin=='synthetic_fixture' and any(delivery.level in ('warning','danger') and delivery.status=='simulated' and delivery.provenance=='synthetic_fixture' and delivery.simulated_at is not None and delivery.simulated_at<=response.answered_at for delivery in row.episode.deliveries))


def _missed_inside(row:CalibrationEvidence)->bool:
    response=row.response
    if response.entrypoint!='owner_report' or response.reference_basis!='owner_declared' or response.answer!='inside' or row.episode.history_status!='complete':return False
    for delivery in row.episode.deliveries:
        if delivery.status=='accepted':
            if delivery.accepted_at<=response.observed_at:return False
            continue # A proven later acceptance cannot erase an earlier inside report.
        at=delivery.request_started_at or delivery.created_at
        if at<=response.observed_at and (delivery.provenance!='telegram_api' or delivery.status in ('pending','sending','retryable','uncertain')):return False
    return True


def decide_calibration(state:CalibrationState,evidence:tuple[CalibrationEvidence,...],*,now:datetime,consumed_keys:frozenset[str]=frozenset())->CalibrationDecision:
    from api.outcomes import response_matches_episode
    if now.tzinfo is None or now.utcoffset() is None:raise ValueError('Calibration clock must be aware')
    if len(evidence)>1000 or len(consumed_keys)>1000:raise ValueError('Calibration evidence exceeds bound')
    start=now-timedelta(days=30);first=first_outcomes(tuple(row.response for row in evidence));eligible=[]
    identities={}
    for row in evidence:
        response=row.response;key=outcome_key(response)
        if response.response_id in identities and identities[response.response_id]!=key:raise ValueError('Conflicting response identity')
        identities[response.response_id]=key
        scope=(response.is_demo,response.scenario_generation,response.shop_id,response.episode_id)
        if first[scope]!=response or key in consumed_keys:continue
        if not response_matches_episode(response,row.episode) or (response.area,response.is_demo,response.scenario_generation)!=(state.area,state.is_demo,state.scenario_generation):continue
        if not start<=response.answered_at<=now or not start<=response.observed_at<=now:continue
        if any(outcome_key(existing.response)==key for existing in eligible):continue
        eligible.append(row)
    covered=[row for row in eligible if _alert_coverage(row)]
    growth=[row for row in eligible if _missed_inside(row)]
    water=sum(row.response.answer!='no' for row in covered)
    consumed=[];new=state.multiplier
    if growth:
        reason='grow';new=min(1.5,round(state.multiplier*1.1,10));consumed=growth+(covered if len(covered)>=5 else [])
    elif len(covered)>=5:
        reason='shrink' if water/len(covered)<.3 else 'no_change'
        new=max(.5,round(state.multiplier*.9,10)) if reason=='shrink' else state.multiplier
        consumed=covered
    else:reason='insufficient_responses' if eligible else 'no_fresh_evidence'
    return CalibrationDecision(reason=reason,old_multiplier=state.multiplier,new_multiplier=new,expected_version=state.version,new_version=state.version+int(bool(consumed)),consumed_response_ids=tuple(row.response.response_id for row in consumed),consumed_outcome_keys=tuple(outcome_key(row.response) for row in consumed),fixture_response_count=sum(row.response.origin=='synthetic_fixture' for row in consumed),response_count=len(covered),water_response_count=water,window_start=start,window_end=now)


def freeze_radius(base_radius_m:float,*,level:str,source:str,area:str,is_demo:bool,scenario_generation:int|None,state:CalibrationState|None,purpose:str='dispatch',existing:RadiusPlan|None=None)->RadiusPlan:
    if type(base_radius_m) not in (int,float) or not math.isfinite(base_radius_m) or not 1<=base_radius_m<=10000:raise ValueError('Invalid base radius')
    if level not in ('watch','warning','danger') or source not in ('jps','met','shop_report','demo') or purpose not in ('dispatch','corroboration','public_check'):raise ValueError('Invalid targeting scope')
    if type(is_demo) is not bool or is_demo!=(scenario_generation is not None):raise ValueError('Invalid targeting realm')
    if existing is not None:
        if (existing.base_radius_m,existing.level,existing.source,existing.area,existing.is_demo,existing.scenario_generation,existing.purpose)!=(base_radius_m,level,source,area,is_demo,scenario_generation,purpose):raise ValueError('Frozen targeting scope mismatch')
        return existing # Same immutable target scope retains its original calibration.

    applies=purpose=='dispatch' and level=='warning' and source in ('shop_report','demo') and state is not None and (state.area,state.is_demo,state.scenario_generation)==(area,is_demo,scenario_generation)
    multiplier=state.multiplier if applies else 1.
    return RadiusPlan(area=area,is_demo=is_demo,scenario_generation=scenario_generation,source=source,level=level,purpose=purpose,base_radius_m=float(base_radius_m),effective_radius_m=base_radius_m*multiplier,multiplier=multiplier,calibration_version=state.version if applies else None,applied=applies)
