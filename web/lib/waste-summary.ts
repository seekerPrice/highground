import type {Dashboard,Disposition,WasteItem,WasteResponse} from "./contracts.ts";
const labels:Record<Disposition,string>={discard_contaminated:"Discard as contaminated",salvage_clean:"Salvage / cleaning classification",recycle:"Recycling classification",bulky_pickup:"Bulky pickup classification"};
export function estimatedQuantity(value:number|null,unit:string):string {return value===null?"Unknown":`≈${new Intl.NumberFormat("en-MY",{maximumFractionDigits:3}).format(value)} ${unit}`;}
export function wasteItemSummary(item:WasteItem){
 return {disposition:item.disposition===null?item.condition==="missing"||item.condition==="unassessed"?"Not assessed":"Classification unavailable":labels[item.disposition],volume:estimatedQuantity(item.est_volume_m3,"m³"),weight:estimatedQuantity(item.est_weight_kg,"kg"),uncertainty:item.uncertainty!==null?"Visual classification or quantities remain uncertain; confirm appropriate handling independently.":"No further uncertainty was recorded; this does not certify safety.",donation:item.donation_available?"Owner-reported available to donate":item.donation_eligible?"No donation availability has been confirmed by the owner":"Not eligible for donation under this assessment"};
}
export function wasteScope(value:WasteResponse|null):string {
 if(value===null||value.status==="unavailable")return "Waste assessment coverage is unavailable.";
 if(value.status==="empty")return `No completed waste assessments for ${value.registered_synthetic_shops} synthetic shops. Waste quantities are unknown.`;
 return `${value.assessed_shops} of ${value.registered_synthetic_shops} synthetic shops have a completed waste assessment; ${value.missing_or_unavailable_shops} are missing or unavailable.`;
}

/** Link shared street totals to existing public pins; never derive a street boundary. */
export function wasteMap(dashboard:Dashboard,value:WasteResponse|null){
 const current=dashboard.scenario_state==="ready"&&value?.status!=="unavailable"&&value?.scenario_generation===dashboard.scenario_generation;
 const streets=current?(value?.aggregate?.streets??[]):[];
 const pins=current?(value?.map_links??[]).flatMap(link=>{
  const shop=dashboard.shops.find(row=>row.shop_id===link.shop_id),street=streets.find(row=>row.street===link.street);
  return shop&&street?[{shop,street}]:[];
 }):[];
 return {pins,streets,note:current?wasteScope(value):"Cleanup coverage for this scenario is unavailable. No current cleanup quantities are inferred."};
}
