/** Validate the explicit public DTO boundary; private fields fail closed. */
export type Level = "none"|"watch"|"warning"|"danger";
export interface Shop {shop_id:string;shop_name:string;shop_type:string;lat:number;lng:number;level:Level;risk_score:number|null;is_demo:true}
export interface Event {event_id:string;created_at:string;level:Exclude<Level,"none">;lat:number;lng:number;radius_m:number;reason:string;confidence:number;is_demo:true}
export interface Destination {safe_point_id:string;name:string;type:"pps"|"parking"|"high_ground";lat:number;lng:number;address_text:string;source:string;source_date:string;designation_context:string;coordinate_source:string;coordinate_provenance:string;verified:boolean;opening_status:"unknown"|"closed";min_level:number|null;min_level_source:string|null;is_demo:false}
export interface Source {source:"jps"|"met";status:"fresh"|"stale"|"unavailable";checked_at:string|null;note:string}
export interface Stats {status:"available"|"unavailable";synthetic_shops:number;virtual_alerts_simulated:number|null;virtual_alert_definition:string;alerts_accepted:number|null;average_alert_acceptance_ms:number|null;vehicles_reported_moved:number|null;estimated_stock_value_reported_lifted_rm:number|null;stock_value_label:string;stock_value_definition:string;vehicle_definition:string;alert_definition:string}
export interface PolicyAggregate {is_demo:true;registered_synthetic_shops:number;assessed_known_coverage:number;flood_cover_indicated:number;explicit_no_flood_cover:number;unclear_or_expired:number;missing_policies:number;without_cover_percent_of_known:number|null;uninsured_stock_estimate_rm:number|null;unknown_stock_estimates:number;definition:string}
export interface Dashboard {generated_at:string;status:"available"|"empty"|"unavailable";is_demo:true;scenario_started_at:string|null;scenario_generation:number;scenario_state:"ready"|"resetting";shops:Shop[];events:Event[];destinations:Destination[];sources:Source[];stats:Stats;policy_coverage:PolicyAggregate|null;policy_note:string}
export interface ReportItem {item_id:string;name:string;qty:number;baseline_estimate_rm:number;condition:"ok"|"damaged"|"destroyed"|"missing"|"unassessed";estimated_loss_rm:number|null;evidence_timestamp_s:number|null;uncertainty:string}
export interface Evidence {media_id:string;kind:"baseline_video"|"update_video"|"after_video"|"waterline_photo";sha256:string;bytes:number;mime_type:string;uploaded_at:string;origin:"telegram"|"local_fixture";telegram_date:string|null;lat:number;lng:number;location_attribution:"confirmed_shop"|"confirmed_shared"|"unconfirmed_shop";is_demo:boolean;integrity_status:"not_checked"}
export type Disposition="discard_contaminated"|"salvage_clean"|"recycle"|"bulky_pickup";
export interface WasteItem {item_id:string;condition:ReportItem["condition"];disposition:Disposition|null;est_volume_m3:number|null;est_weight_kg:number|null;material:"food"|"drink"|"medicine"|"cosmetics"|"absorbent"|"sealed_metal"|"sealed_plastic"|"sealed_glass"|"metal"|"e_waste"|"bulky"|"unknown";floodwater_contact:"yes"|"no"|"unknown";contamination:"present"|"not_observed"|"unknown";uncertainty:string|null;donation_eligible:boolean;donation_available:boolean;donation_action_url:string|null;self_report_note:string}
export interface ReportWaste {status:"available"|"not_assessed"|"unavailable";items:WasteItem[];confidence:number|null;owner_confirmed_street:string|null;street_assignment_source:"owner_confirmed_current_shop"|"unassigned";street_confirmed_at:string|null;food_safety_line:string;safety_note:string}
export interface StreetWaste {street:string;assessment_count:number;shop_count:number;baseline_items:number;assessed_items:number;affected_items:number;unknown_items:number;quantified_volume_items:number;unknown_volume_items:number;quantified_weight_items:number;unknown_weight_items:number;est_volume_m3:number|null;est_weight_kg:number|null;estimated_load_equivalents:number|null}
export interface WasteAggregate {is_demo:true;lorry_capacity_m3:number;streets:StreetWaste[];definition:string}
export interface WasteMapLink {shop_id:string;street:string}
export interface WasteResponse {scenario_generation:number|null;map_links:WasteMapLink[];status:"available"|"empty"|"unavailable";generated_at:string;is_demo:true;registered_synthetic_shops:number|null;assessed_shops:number|null;missing_or_unavailable_shops:number|null;aggregate:WasteAggregate|null;note:string}
export interface Report {report_id:string;assessment_media_id:string;created_at:string;shop_name:string;is_demo:boolean;baseline_estimate_rm:number;estimated_loss_rm:number|null;estimate_status:"available"|"unavailable";coverage:"complete"|"partial"|"none";assessed_items:number;baseline_items:number;confidence:number;confidence_note:string;summary_text:string;recovery_attribution:string;items:ReportItem[];evidence:Evidence[];disclaimer:string;waste:ReportWaste}
export interface Integrity {media_id:string;status:"verified"|"mismatch"|"unavailable";sha256:string;note:string}

function object(value:unknown,keys:string[]):Record<string,unknown> {
  if (!value || typeof value!=="object" || Array.isArray(value)) throw new Error("Invalid response");
  const row=value as Record<string,unknown>;
  if (Object.keys(row).length!==keys.length || keys.some(key=>!(key in row))) throw new Error("Unexpected response fields");
  return row;
}
function string(value:unknown,max=1200):string {if(typeof value!=="string" || value.length>max) throw new Error("Invalid text");return value;}
function number(value:unknown,min=0,max=1_000_000_000):number {if(typeof value!=="number" || !Number.isFinite(value) || value<min || value>max)throw new Error("Invalid number");return value;}
function integer(value:unknown,min=0,max=1_000_000_000):number {const n=number(value,min,max);if(!Number.isInteger(n))throw new Error("Invalid count");return n;}
function boolean(value:unknown):boolean {if(typeof value!=="boolean")throw new Error("Invalid flag");return value;}
function nullable<T>(value:unknown,parse:(input:unknown)=>T):T|null{return value===null?null:parse(value);}
function choice<T extends string>(value:unknown,values:readonly T[]):T {if(!values.includes(value as T))throw new Error("Invalid status");return value as T;}
function list<T>(value:unknown,max:number,parse:(input:unknown)=>T):T[] {if(!Array.isArray(value)||value.length>max)throw new Error("Invalid list");return value.map(parse);}
function date(value:unknown):string {const s=string(value,50);if(!/(Z|[+-]\d\d:\d\d)$/.test(s)||!Number.isFinite(Date.parse(s)))throw new Error("Invalid time");return s;}
function hex(value:unknown,size:number):string {const s=string(value,size);if(!new RegExp(`^[a-f0-9]{${size}}$`).test(s))throw new Error("Invalid identity");return s;}
function https(value:unknown):string {const s=string(value,500),url=new URL(s);if(url.protocol!=="https:"||url.username||url.password)throw new Error("Invalid source link");return s;}
function demo(value:unknown):true {if(value!==true)throw new Error("Non-synthetic public data rejected");return true;}
function position(row:Record<string,unknown>) {return {lat:number(row.lat,-90,90),lng:number(row.lng,-180,180)};}

function parsePolicy(input:unknown):PolicyAggregate {
 const p=object(input,["is_demo","registered_synthetic_shops","assessed_known_coverage","flood_cover_indicated","explicit_no_flood_cover","unclear_or_expired","missing_policies","without_cover_percent_of_known","uninsured_stock_estimate_rm","unknown_stock_estimates","definition"]);
 const registered=integer(p.registered_synthetic_shops,0,50),known=integer(p.assessed_known_coverage,0,50),yes=integer(p.flood_cover_indicated,0,50),no=integer(p.explicit_no_flood_cover,0,50),unclear=integer(p.unclear_or_expired,0,50),missing=integer(p.missing_policies,0,50),unknown=integer(p.unknown_stock_estimates,0,50);
 const percent=nullable(p.without_cover_percent_of_known,v=>number(v,0,100)),estimate=nullable(p.uninsured_stock_estimate_rm,v=>number(v,0,250_000_000_000));
 if(known!==yes+no||registered!==known+unclear+missing||unknown<unclear+missing||unknown>registered||(known===0?percent!==null:percent===null||Math.abs(percent-100*no/known)>.011)||(unknown===registered?estimate!==null:estimate===null))throw new Error("Invalid policy aggregate");
 return {is_demo:demo(p.is_demo),registered_synthetic_shops:registered,assessed_known_coverage:known,flood_cover_indicated:yes,explicit_no_flood_cover:no,unclear_or_expired:unclear,missing_policies:missing,without_cover_percent_of_known:percent,uninsured_stock_estimate_rm:estimate,unknown_stock_estimates:unknown,definition:string(p.definition,600)};
}

export function parseDashboard(input:unknown):Dashboard {
 const optional=input&&typeof input==="object"&&!Array.isArray(input)?["policy_coverage","policy_note"].filter(key=>key in input):[];
 const r=object(input,["generated_at","status","is_demo","scenario_started_at","scenario_generation","scenario_state","shops","events","destinations","sources","stats",...optional]);
 const policy_coverage="policy_coverage" in r?nullable(r.policy_coverage,parsePolicy):null;
 const policy_note="policy_note" in r?string(r.policy_note,600):"Synthetic policy summary is unavailable.";
 const shops=list(r.shops,50,value=>{const s=object(value,["shop_id","shop_name","shop_type","lat","lng","level","risk_score","is_demo"]);return {shop_id:string(s.shop_id,160),shop_name:string(s.shop_name,200),shop_type:string(s.shop_type,100),...position(s),level:choice(s.level,["none","watch","warning","danger"]),risk_score:nullable(s.risk_score,v=>integer(v,0,100)),is_demo:demo(s.is_demo)};});
 const events=list(r.events,100,value=>{const e=object(value,["event_id","created_at","level","lat","lng","radius_m","reason","confidence","is_demo"]);return {event_id:string(e.event_id,160),created_at:date(e.created_at),level:choice(e.level,["watch","warning","danger"]),...position(e),radius_m:integer(e.radius_m,1,10000),reason:string(e.reason,512),confidence:number(e.confidence,0,1),is_demo:demo(e.is_demo)};});
 const destinations=list(r.destinations,100,value=>{const d=object(value,["safe_point_id","name","type","lat","lng","address_text","source","source_date","designation_context","coordinate_source","coordinate_provenance","verified","opening_status","min_level","min_level_source","is_demo"]);if(d.is_demo!==false)throw new Error("Fictional destination rejected");const sourceDate=string(d.source_date,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(sourceDate))throw new Error("Invalid source date");return {safe_point_id:string(d.safe_point_id,100),name:string(d.name,100),type:choice(d.type,["pps","parking","high_ground"]),...position(d),address_text:string(d.address_text,300),source:https(d.source),source_date:sourceDate,designation_context:string(d.designation_context,100),coordinate_source:https(d.coordinate_source),coordinate_provenance:string(d.coordinate_provenance,300),verified:boolean(d.verified),opening_status:choice(d.opening_status,["unknown","closed"]),min_level:nullable(d.min_level,v=>integer(v,1,100)),min_level_source:nullable(d.min_level_source,https),is_demo:false as const};});
 const sources=list(r.sources,2,value=>{const s=object(value,["source","status","checked_at","note"]);return {source:choice(s.source,["jps","met"]),status:choice(s.status,["fresh","stale","unavailable"]),checked_at:nullable(s.checked_at,date),note:string(s.note,500)};});
 const s=object(r.stats,["status","synthetic_shops","virtual_alerts_simulated","virtual_alert_definition","alerts_accepted","average_alert_acceptance_ms","vehicles_reported_moved","estimated_stock_value_reported_lifted_rm","stock_value_label","stock_value_definition","vehicle_definition","alert_definition"]);
 const stats:Stats={status:choice(s.status,["available","unavailable"]),synthetic_shops:integer(s.synthetic_shops,0,50),virtual_alerts_simulated:nullable(s.virtual_alerts_simulated,integer),virtual_alert_definition:string(s.virtual_alert_definition,500),alerts_accepted:nullable(s.alerts_accepted,integer),average_alert_acceptance_ms:nullable(s.average_alert_acceptance_ms,number),vehicles_reported_moved:nullable(s.vehicles_reported_moved,integer),estimated_stock_value_reported_lifted_rm:nullable(s.estimated_stock_value_reported_lifted_rm,number),stock_value_label:string(s.stock_value_label,100),stock_value_definition:string(s.stock_value_definition,500),vehicle_definition:string(s.vehicle_definition,500),alert_definition:string(s.alert_definition,500)};
 return {generated_at:date(r.generated_at),status:choice(r.status,["available","empty","unavailable"]),is_demo:demo(r.is_demo),scenario_started_at:nullable(r.scenario_started_at,date),scenario_generation:integer(r.scenario_generation),scenario_state:choice(r.scenario_state,["ready","resetting"]),shops,events,destinations,sources,stats,policy_coverage,policy_note};
}

export function parseReport(input:unknown,id:string):Report {
 const optional=input&&typeof input==="object"&&!Array.isArray(input)&&"waste" in input?["waste"]:[];
 const r=object(input,["report_id","assessment_media_id","created_at","shop_name","is_demo","baseline_estimate_rm","estimated_loss_rm","estimate_status","coverage","assessed_items","baseline_items","confidence","confidence_note","summary_text","recovery_attribution","items","evidence","disclaimer",...optional]);
 if(hex(r.report_id,32)!==id)throw new Error("Report identity mismatch");
 const items=list(r.items,80,value=>{const i=object(value,["item_id","condition","estimated_loss_rm","evidence_timestamp_s","uncertainty","name","qty","baseline_estimate_rm"]);const condition=choice(i.condition,["ok","damaged","destroyed","missing","unassessed"]),loss=nullable(i.estimated_loss_rm,number),baseline=number(i.baseline_estimate_rm);if((condition==="missing"||condition==="unassessed")&&loss!==null)throw new Error("Unknown item has invented loss");if(loss!==null&&loss>baseline)throw new Error("Loss exceeds baseline");return {item_id:string(i.item_id,160),condition,estimated_loss_rm:loss,evidence_timestamp_s:nullable(i.evidence_timestamp_s,v=>number(v,0,300)),uncertainty:string(i.uncertainty,300),name:string(i.name,200),qty:number(i.qty,0,1_000_000),baseline_estimate_rm:baseline};});
 const evidence=list(r.evidence,10,value=>{const e=object(value,["media_id","kind","sha256","bytes","mime_type","uploaded_at","origin","telegram_date","lat","lng","location_attribution","is_demo","integrity_status"]);const origin=choice(e.origin,["telegram","local_fixture"]),telegramDate=nullable(e.telegram_date,date);if(origin==="telegram"?telegramDate===null:telegramDate!==null||e.is_demo!==true)throw new Error("Invalid upload origin attribution");return {media_id:hex(e.media_id,64),kind:choice(e.kind,["baseline_video","update_video","after_video","waterline_photo"]),sha256:hex(e.sha256,64),bytes:integer(e.bytes,1,20_000_000),mime_type:choice(e.mime_type,["video/mp4","image/jpeg","image/png","image/webp"]),uploaded_at:date(e.uploaded_at),origin,telegram_date:telegramDate,...position(e),location_attribution:choice(e.location_attribution,["confirmed_shop","confirmed_shared","unconfirmed_shop"]),is_demo:boolean(e.is_demo),integrity_status:choice(e.integrity_status,["not_checked"])};});
 const assessmentMediaId=hex(r.assessment_media_id,64);if(!evidence.some(e=>e.media_id===assessmentMediaId&&e.kind==="after_video"))throw new Error("Assessment video is not an included after-video receipt");
 const assessed=items.filter(i=>i.estimated_loss_rm!==null).length,total=nullable(r.estimated_loss_rm,number),coverage=choice(r.coverage,["complete","partial","none"]);
 if(integer(r.baseline_items)!==items.length||integer(r.assessed_items)!==assessed||new Set(items.map(i=>i.item_id)).size!==items.length||new Set(evidence.map(e=>e.media_id)).size!==evidence.length)throw new Error("Invalid assessment coverage");
 if(coverage!==(assessed===0?"none":assessed===items.length?"complete":"partial")||(assessed===0?total!==null:total===null||Math.abs(total-items.reduce((sum,i)=>sum+(i.estimated_loss_rm??0),0))>.005))throw new Error("Invalid assessed total");
 const isDemo=boolean(r.is_demo);if(evidence.some(e=>e.is_demo!==isDemo))throw new Error("Invalid evidence attribution");
 const status=choice(r.estimate_status,["available","unavailable"]);if((total===null)!==(status==="unavailable"))throw new Error("Invalid estimate status");
 return {report_id:id,assessment_media_id:assessmentMediaId,created_at:date(r.created_at),shop_name:string(r.shop_name,200),is_demo:isDemo,baseline_estimate_rm:number(r.baseline_estimate_rm),estimated_loss_rm:total,estimate_status:status,coverage,assessed_items:assessed,baseline_items:items.length,confidence:number(r.confidence,0,1),confidence_note:string(r.confidence_note,300),summary_text:string(r.summary_text),recovery_attribution:string(r.recovery_attribution,300),items,evidence,disclaimer:string(r.disclaimer,600),waste:parseReportWaste(r.waste,items)};
}

export function parseIntegrity(input:unknown,receipt:Evidence):Integrity {
 const r=object(input,["media_id","status","sha256","note"]);
 if(hex(r.media_id,64)!==receipt.media_id||hex(r.sha256,64)!==receipt.sha256)throw new Error("Evidence identity mismatch");
 return {media_id:receipt.media_id,status:choice(r.status,["verified","mismatch","unavailable"]),sha256:receipt.sha256,note:string(r.note,600)};
}

export function evidenceTitle(receipt:Evidence,assessmentMediaId:string):string {
 if(receipt.kind==="after_video")return receipt.media_id===assessmentMediaId?"After video used for assessment":"Retained after video — not assessed";
 return {baseline_video:"Before video",update_video:"Inventory update video",waterline_photo:"Recovery water-line photo"}[receipt.kind];
}
export function assessmentTimestamp(seconds:number):string {return `Video used for assessment: ${seconds.toFixed(1)} s`;}

export function evidenceOriginCaption(receipt:Evidence):string {return receipt.origin==="local_fixture"?"Synthetic local fixture — no Telegram upload receipt":"Telegram upload receipt";}

export const FOOD_SAFETY_LINE="Throw away food, drinks and medicine that touched floodwater.";
export const WASTE_SAFETY_NOTE="Visual classifications and quantities are uncertain estimates. They do not establish that an item is safe to use, clean or donate.";
export function donationAction(value:unknown):string {
 const link=string(value,200),url=new URL(link);
 if(url.protocol!=="https:"||url.hostname!=="t.me"||url.username||url.password||url.port||url.hash||!/^\/[A-Za-z0-9_]{5,32}$/.test(url.pathname)||!/^\?start=donate_[a-f0-9]{32}$/.test(url.search)||url.href!==link)throw new Error("Invalid owner action link");
 return link;
}
function parseReportWaste(value:unknown,items:ReportItem[]):ReportWaste {
 if(value===undefined)return {status:"not_assessed",items:[],confidence:null,owner_confirmed_street:null,street_assignment_source:"unassigned",street_confirmed_at:null,food_safety_line:FOOD_SAFETY_LINE,safety_note:WASTE_SAFETY_NOTE};
 const w=object(value,["status","items","confidence","owner_confirmed_street","street_assignment_source","street_confirmed_at","food_safety_line","safety_note"]);
 const status=choice(w.status,["available","not_assessed","unavailable"]),confidence=nullable(w.confidence,v=>number(v,0,1));
 const street=nullable(w.owner_confirmed_street,v=>{const s=string(v,100);if(!s.trim()||/[\r\n{}<>]/.test(s))throw new Error("Invalid street label");return s;}),at=nullable(w.street_confirmed_at,date),assignment=choice(w.street_assignment_source,["owner_confirmed_current_shop","unassigned"]);
 if((street!==null)!==(at!==null)||(street!==null)!==(assignment==="owner_confirmed_current_shop"))throw new Error("Invalid street provenance");
 if(w.food_safety_line!==FOOD_SAFETY_LINE)throw new Error("Invalid fixed food warning");
 const rows=list(w.items,80,value=>{
  const i=object(value,["item_id","condition","disposition","est_volume_m3","est_weight_kg","material","floodwater_contact","contamination","uncertainty","donation_eligible","donation_available","donation_action_url","self_report_note"]);
  const identity=string(i.item_id,160),condition=choice(i.condition,["ok","damaged","destroyed","missing","unassessed"]),canonical=items.find(item=>item.item_id===identity);
  if(!canonical||canonical.condition!==condition)throw new Error("Waste loss identity mismatch");
  const disposition=nullable(i.disposition,v=>choice<Disposition>(v,["discard_contaminated","salvage_clean","recycle","bulky_pickup"])),volume=nullable(i.est_volume_m3,v=>number(v,0,10000)),weight=nullable(i.est_weight_kg,v=>number(v,0,1_000_000)),material=choice(i.material,["food","drink","medicine","cosmetics","absorbent","sealed_metal","sealed_plastic","sealed_glass","metal","e_waste","bulky","unknown"]),contact=choice(i.floodwater_contact,["yes","no","unknown"]),contamination=choice(i.contamination,["present","not_observed","unknown"]),uncertainty=nullable(i.uncertainty,v=>string(v,300));
  const eligible=boolean(i.donation_eligible),available=boolean(i.donation_available),action=nullable(i.donation_action_url,donationAction);
  if((["ok","missing","unassessed"].includes(condition)&&(disposition!==null||volume!==null||weight!==null))||(["food","drink","medicine","cosmetics","absorbent"].includes(material)&&contact==="yes"&&disposition!=="discard_contaminated"))throw new Error("Contradictory waste classification");
  const eligibleFacts=condition==="damaged"&&disposition==="salvage_clean"&&["sealed_metal","sealed_plastic","sealed_glass"].includes(material)&&contact!=="unknown"&&contamination==="not_observed"&&uncertainty===null;
  if((eligible&&!eligibleFacts)||(available&&!eligible)||(action!==null&&!eligible))throw new Error("Invalid donation eligibility");
  return {item_id:identity,condition,disposition,est_volume_m3:volume,est_weight_kg:weight,material,floodwater_contact:contact,contamination,uncertainty,donation_eligible:eligible,donation_available:available,donation_action_url:action,self_report_note:string(i.self_report_note,300)};
 });
 if(new Set(rows.map(item=>item.item_id)).size!==rows.length||(status==="available"?(confidence===null||rows.length!==items.length):(rows.length!==0||confidence!==null)))throw new Error("Invalid waste coverage");
 return {status,items:rows,confidence,owner_confirmed_street:street,street_assignment_source:assignment,street_confirmed_at:at,food_safety_line:FOOD_SAFETY_LINE,safety_note:string(w.safety_note,300)};
}

export function parseWaste(input:unknown):WasteResponse {
 const w=object(input,["status","generated_at","is_demo","scenario_generation","map_links","registered_synthetic_shops","assessed_shops","missing_or_unavailable_shops","aggregate","note"]),status=choice(w.status,["available","empty","unavailable"]);
 const generation=nullable(w.scenario_generation,v=>integer(v,0,Number.MAX_SAFE_INTEGER));
 const links=list(w.map_links,50,value=>{const link=object(value,["shop_id","street"]);return {shop_id:string(link.shop_id,160),street:string(link.street,100)};});
 const registered=nullable(w.registered_synthetic_shops,v=>integer(v,0,50)),assessed=nullable(w.assessed_shops,v=>integer(v,0,50)),missing=nullable(w.missing_or_unavailable_shops,v=>integer(v,0,50));
 const aggregate=nullable(w.aggregate,value=>{
  const a=object(value,["is_demo","lorry_capacity_m3","streets","definition"]),capacity=number(a.lorry_capacity_m3,Number.MIN_VALUE,Number.MAX_VALUE);
  const streets=list(a.streets,50,value=>{
   const s=object(value,["street","assessment_count","shop_count","baseline_items","assessed_items","affected_items","unknown_items","quantified_volume_items","unknown_volume_items","quantified_weight_items","unknown_weight_items","est_volume_m3","est_weight_kg","estimated_load_equivalents"]);
   const street=string(s.street,100);if(!street.trim()||/[\r\n{}<>]/.test(street))throw new Error("Invalid street label");
   const assessments=integer(s.assessment_count,1,1000),shops=integer(s.shop_count,1,50),baseline=integer(s.baseline_items,0,80000),known=integer(s.assessed_items,0,80000),affected=integer(s.affected_items,0,80000),unknown=integer(s.unknown_items,0,80000),qVolume=integer(s.quantified_volume_items,0,80000),uVolume=integer(s.unknown_volume_items,0,80000),qWeight=integer(s.quantified_weight_items,0,80000),uWeight=integer(s.unknown_weight_items,0,80000);
   const volume=nullable(s.est_volume_m3,v=>number(v,0,800_000_000)),weight=nullable(s.est_weight_kg,v=>number(v,0,80_000_000_000)),loads=nullable(s.estimated_load_equivalents,v=>number(v,0,Number.MAX_VALUE));
   if(shops>assessments||baseline!==known+unknown||affected>known||qVolume>affected||qWeight>affected||uVolume!==unknown+affected-qVolume||uWeight!==unknown+affected-qWeight||(qVolume===0)!==(volume===null)||(qWeight===0)!==(weight===null)||(volume===null?loads!==null:loads===null||Math.abs(loads-volume/capacity)>.0005001))throw new Error("Invalid waste quantities or coverage");
   return {street,assessment_count:assessments,shop_count:shops,baseline_items:baseline,assessed_items:known,affected_items:affected,unknown_items:unknown,quantified_volume_items:qVolume,unknown_volume_items:uVolume,quantified_weight_items:qWeight,unknown_weight_items:uWeight,est_volume_m3:volume,est_weight_kg:weight,estimated_load_equivalents:loads};
  });
  if(new Set(streets.map(s=>s.street)).size!==streets.length||streets.reduce((sum,s)=>sum+s.assessment_count,0)>1000||streets.reduce((sum,s)=>sum+s.baseline_items,0)>80000)throw new Error("Invalid waste aggregate scope");
  return {is_demo:demo(a.is_demo),lorry_capacity_m3:capacity,streets,definition:string(a.definition,600)};
 });
 if(status==="unavailable"?(aggregate!==null||assessed!==null||missing!==null):(registered===null||assessed===null||missing===null||aggregate===null||registered!==assessed+missing||(status==="empty")!==(assessed===0)||(assessed===0)!==(aggregate.streets.length===0)))throw new Error("Invalid waste denominator");
 if(new Set(links.map(link=>link.shop_id)).size!==links.length||links.some(link=>status!=="available"||generation===null||link.street==="Unassigned"||!aggregate?.streets.some(street=>street.street===link.street)))throw new Error("Invalid waste map scope");
 return {scenario_generation:generation,map_links:links,status,generated_at:date(w.generated_at),is_demo:demo(w.is_demo),registered_synthetic_shops:registered,assessed_shops:assessed,missing_or_unavailable_shops:missing,aggregate,note:string(w.note,600)};
}
