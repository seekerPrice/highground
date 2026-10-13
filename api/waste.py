"""Pure waste validation and synthetic aggregation; no owner authorization here."""
import math
from typing import Any,Mapping
from api.waste_models import WasteAssessment, WasteItem,WasteRecord,StreetWaste,WasteAggregate
from api.report_models import LossAssessment

FOOD_SAFETY_LINE='Throw away food, drinks and medicine that touched floodwater.'
HAZARDOUS_MATERIALS={'food','drink','medicine','cosmetics','absorbent'}
SEALED_MATERIALS={'sealed_metal','sealed_plastic','sealed_glass'}

def canonical_material_category(category:str)->str:
    normalized=category.strip().casefold()
    return {'food staples':'food','foodstaples':'food','beverages':'drink'}.get(normalized,normalized if normalized in HAZARDOUS_MATERIALS else 'unknown')


def validate_waste(assessment:WasteAssessment,baseline:Mapping[str,Any],loss:LossAssessment,selected_media_id:str,duration:int)->WasteAssessment:
    if type(duration) is not int or not 1<=duration<=300:raise ValueError('Selected clip duration must be1..300 seconds')
    if assessment.inventory_id!=baseline['inventory_id'] or assessment.assessment_media_id!=selected_media_id:raise ValueError('Waste inventory or selected clip mismatch')
    loss.validate_baseline(baseline,duration)
    found={row.item_id:row for row in loss.items}
    expected={f"{baseline['inventory_id']}:{index}":found.get(f"{baseline['inventory_id']}:{index}") for index in range(len(baseline['items']))}
    seen=set();validated=[]
    categories={f"{baseline['inventory_id']}:{i}":canonical_material_category(row['category']) for i,row in enumerate(baseline['items'])}
    for item in assessment.items:
        if item.item_id in seen or item.item_id not in expected:raise ValueError('Unknown or duplicate waste identity')
        seen.add(item.item_id)
        if item.condition!=(expected[item.item_id].condition if expected[item.item_id] else 'unassessed'):raise ValueError('Waste cannot reinterpret assessed condition')
        if item.condition in ('missing','unassessed','ok'):
            if item.disposition is not None or item.est_volume_m3 is not None or item.est_weight_kg is not None:raise ValueError('Unassessed or unaffected item cannot acquire waste quantities')
            if item.condition in ('missing','unassessed') and (item.floodwater_contact!='unknown' or item.contamination!='unknown'):raise ValueError('Unseen item contact remains unknown')
            validated.append(item);continue
        hazardous=item.material in HAZARDOUS_MATERIALS or categories[item.item_id] in HAZARDOUS_MATERIALS
        if item.disposition=='salvage_clean' and item.contamination=='present':raise ValueError('Observed contamination prohibits salvage classification')
        if hazardous and item.floodwater_contact=='yes':
            item=item.model_copy(update={'disposition':'discard_contaminated','contamination':'present'})
        if item.disposition is None:
            if item.est_volume_m3 is not None or item.est_weight_kg is not None or item.uncertainty is None:raise ValueError('Unclassified affected item requires unknown quantities and uncertainty')
        elif item.disposition=='salvage_clean' and (hazardous or item.material not in SEALED_MATERIALS or item.contamination=='present'):
            raise ValueError('Contradictory salvage classification')
        elif item.disposition=='recycle' and item.material not in ('metal','e_waste','sealed_metal'):
            raise ValueError('Recycling classification requires metal or electronic material')
        elif item.disposition=='bulky_pickup' and item.material!='bulky':raise ValueError('Bulky classification requires bulky material')
        validated.append(item)
    if seen!=set(expected):raise ValueError('Waste must preserve every assessed/unknown loss item')
    return assessment.model_copy(update={'items':tuple(validated)})


def donation_eligible(item:WasteItem,*,owner_opt_in:bool)->bool:
    if type(owner_opt_in) is not bool:raise ValueError('Donation requires explicit owner opt-in')
    return owner_opt_in and item.condition=='damaged' and item.floodwater_contact in ('yes','no') and item.disposition=='salvage_clean' and item.material in SEALED_MATERIALS and item.contamination=='not_observed' and item.uncertainty is None


def aggregate_waste(records:list[WasteRecord],*,synthetic_shop_ids:set[str],lorry_capacity_m3:float=10.)->WasteAggregate:
    """Readers supply verified synthetic scope and already-bound completed facts."""
    if type(lorry_capacity_m3) not in (int,float) or not math.isfinite(lorry_capacity_m3) or lorry_capacity_m3<=0:raise ValueError('Lorry capacity must be finite and positive')
    if len(records)>1000 or len(synthetic_shop_ids)>50:raise ValueError('Waste aggregate exceeds bounded scope')
    latest={}
    for row in records:
        if row.status!='complete' or not row.is_demo or row.shop_id not in synthetic_shop_ids:continue
        ids=[item.item_id for item in row.assessment.items]
        if len(set(ids))!=len(ids) or len(ids)>row.baseline_items:raise ValueError('Invalid assessment coverage')
        if any(not identity.startswith(row.assessment.inventory_id+':') for identity in ids):raise ValueError('Invalid inventory item binding')
        key=(row.shop_id,row.episode_id,row.assessment.inventory_id)
        previous=latest.get(key)
        if previous is None or (row.completed_at,row.assessment_id)>(previous.completed_at,previous.assessment_id):latest[key]=row
    streets={}
    for row in latest.values():streets.setdefault(row.owner_confirmed_street or 'Unassigned',[]).append(row)
    output=[]
    for street,rows in sorted(streets.items()):
        items=[item for row in rows for item in row.assessment.items]
        affected=[item for item in items if item.condition in ('damaged','destroyed')]
        omitted=sum(row.baseline_items-len(row.assessment.items) for row in rows)
        unknown=omitted+sum(item.condition in ('missing','unassessed') for item in items)
        volumes=[item.est_volume_m3 for item in affected if item.est_volume_m3 is not None]
        weights=[item.est_weight_kg for item in affected if item.est_weight_kg is not None]
        volume=round(sum(volumes),3) if volumes else None
        weight=round(sum(weights),2) if weights else None
        loads=round(volume/lorry_capacity_m3,3) if volume is not None else None
        output.append(StreetWaste(street=street,assessment_count=len(rows),shop_count=len({row.shop_id for row in rows}),baseline_items=sum(row.baseline_items for row in rows),assessed_items=len(items)-sum(item.condition in ('missing','unassessed') for item in items),affected_items=len(affected),unknown_items=unknown,quantified_volume_items=len(volumes),unknown_volume_items=unknown+len(affected)-len(volumes),quantified_weight_items=len(weights),unknown_weight_items=unknown+len(affected)-len(weights),est_volume_m3=volume,est_weight_kg=weight,estimated_load_equivalents=loads))
    return WasteAggregate(lorry_capacity_m3=float(lorry_capacity_m3),streets=tuple(output))


def report_waste(loss:LossAssessment,*,street:str|None=None,street_confirmed_at=None,donations:Mapping[str,Mapping[str,Any]]|None=None):
    """Render canonical descriptions; model prose cannot become an assurance."""
    from api.waste_models import ReportWaste,WasteReportItem
    values=dict(owner_confirmed_street=street,street_confirmed_at=street_confirmed_at,
        street_assignment_source='owner_confirmed_current_shop' if street is not None else 'unassigned')
    if loss.waste is None:return ReportWaste(status=loss.waste_status,**values)
    rows=[]
    for item in loss.waste.items:
        donation=(donations or {}).get(item.item_id,{})
        eligible=donation_eligible(item,owner_opt_in=True)
        uncertainty=('Not assessed in the selected after-video; quantities remain unknown.' if item.condition in ('missing','unassessed') else
            'Visual classification or quantities remain uncertain; confirm appropriate handling independently.' if item.uncertainty is not None or 'unknown' in (item.material,item.floodwater_contact,item.contamination) else None)
        rows.append(WasteReportItem(**(item.model_dump()|{'uncertainty':uncertainty}),donation_eligible=eligible,
            donation_available=eligible and donation.get('available') is True,
            donation_action_url=donation.get('action_url') if eligible else None))
    return ReportWaste(status='available',items=rows,confidence=loss.waste.confidence,**values)
