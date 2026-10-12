/** Validate the explicit public DTO boundary; private fields fail closed. */
export type Level = "none"|"watch"|"warning"|"danger";
export interface Shop {shop_id:string;shop_name:string;shop_type:string;lat:number;lng:number;level:Level;risk_score:number|null;is_demo:true}
export interface Event {event_id:string;created_at:string;level:Exclude<Level,"none">;lat:number;lng:number;radius_m:number;reason:string;confidence:number;is_demo:true}
export interface Destination {safe_point_id:string;name:string;type:"pps"|"parking"|"high_ground";lat:number;lng:number;address_text:string;source:string;source_date:string;designation_context:string;coordinate_source:string;coordinate_provenance:string;verified:boolean;opening_status:"unknown"|"closed";min_level:number|null;min_level_source:string|null;is_demo:false}
export interface Source {source:"jps"|"met";status:"fresh"|"stale"|"unavailable";checked_at:string|null;note:string}
export interface Stats {status:"available"|"unavailable";synthetic_shops:number;alerts_accepted:number|null;average_alert_acceptance_ms:number|null;vehicles_reported_moved:number|null;estimated_stock_value_reported_lifted_rm:number|null;stock_value_label:string;stock_value_definition:string;vehicle_definition:string;alert_definition:string}
export interface Dashboard {generated_at:string;status:"available"|"empty"|"unavailable";is_demo:true;scenario_started_at:string|null;shops:Shop[];events:Event[];destinations:Destination[];sources:Source[];stats:Stats}
export interface ReportItem {item_id:string;name:string;qty:number;baseline_estimate_rm:number;condition:"ok"|"damaged"|"destroyed"|"missing"|"unassessed";estimated_loss_rm:number|null;evidence_timestamp_s:number|null;uncertainty:string}
export interface Evidence {media_id:string;kind:"baseline_video"|"update_video"|"after_video"|"waterline_photo";sha256:string;bytes:number;mime_type:string;uploaded_at:string;telegram_date:string;lat:number;lng:number;location_attribution:"confirmed_shop"|"confirmed_shared"|"unconfirmed_shop";is_demo:boolean;integrity_status:"not_checked"}
export interface Report {report_id:string;created_at:string;shop_name:string;is_demo:boolean;baseline_estimate_rm:number;estimated_loss_rm:number|null;estimate_status:"available"|"unavailable";coverage:"complete"|"partial"|"none";assessed_items:number;baseline_items:number;confidence:number;confidence_note:string;summary_text:string;recovery_attribution:string;items:ReportItem[];evidence:Evidence[];disclaimer:string}
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

export function parseDashboard(input:unknown):Dashboard {
 const r=object(input,["generated_at","status","is_demo","scenario_started_at","shops","events","destinations","sources","stats"]);
 const shops=list(r.shops,50,value=>{const s=object(value,["shop_id","shop_name","shop_type","lat","lng","level","risk_score","is_demo"]);return {shop_id:string(s.shop_id,160),shop_name:string(s.shop_name,200),shop_type:string(s.shop_type,100),...position(s),level:choice(s.level,["none","watch","warning","danger"]),risk_score:nullable(s.risk_score,v=>integer(v,0,100)),is_demo:demo(s.is_demo)};});
 const events=list(r.events,100,value=>{const e=object(value,["event_id","created_at","level","lat","lng","radius_m","reason","confidence","is_demo"]);return {event_id:string(e.event_id,160),created_at:date(e.created_at),level:choice(e.level,["watch","warning","danger"]),...position(e),radius_m:integer(e.radius_m,1,10000),reason:string(e.reason,512),confidence:number(e.confidence,0,1),is_demo:demo(e.is_demo)};});
 const destinations=list(r.destinations,100,value=>{const d=object(value,["safe_point_id","name","type","lat","lng","address_text","source","source_date","designation_context","coordinate_source","coordinate_provenance","verified","opening_status","min_level","min_level_source","is_demo"]);if(d.is_demo!==false)throw new Error("Fictional destination rejected");const sourceDate=string(d.source_date,10);if(!/^\d{4}-\d{2}-\d{2}$/.test(sourceDate))throw new Error("Invalid source date");return {safe_point_id:string(d.safe_point_id,100),name:string(d.name,100),type:choice(d.type,["pps","parking","high_ground"]),...position(d),address_text:string(d.address_text,300),source:https(d.source),source_date:sourceDate,designation_context:string(d.designation_context,100),coordinate_source:https(d.coordinate_source),coordinate_provenance:string(d.coordinate_provenance,300),verified:boolean(d.verified),opening_status:choice(d.opening_status,["unknown","closed"]),min_level:nullable(d.min_level,v=>integer(v,1,100)),min_level_source:nullable(d.min_level_source,https),is_demo:false as const};});
 const sources=list(r.sources,2,value=>{const s=object(value,["source","status","checked_at","note"]);return {source:choice(s.source,["jps","met"]),status:choice(s.status,["fresh","stale","unavailable"]),checked_at:nullable(s.checked_at,date),note:string(s.note,500)};});
 const s=object(r.stats,["status","synthetic_shops","alerts_accepted","average_alert_acceptance_ms","vehicles_reported_moved","estimated_stock_value_reported_lifted_rm","stock_value_label","stock_value_definition","vehicle_definition","alert_definition"]);
 const stats:Stats={status:choice(s.status,["available","unavailable"]),synthetic_shops:integer(s.synthetic_shops,0,50),alerts_accepted:nullable(s.alerts_accepted,integer),average_alert_acceptance_ms:nullable(s.average_alert_acceptance_ms,number),vehicles_reported_moved:nullable(s.vehicles_reported_moved,integer),estimated_stock_value_reported_lifted_rm:nullable(s.estimated_stock_value_reported_lifted_rm,number),stock_value_label:string(s.stock_value_label,100),stock_value_definition:string(s.stock_value_definition,500),vehicle_definition:string(s.vehicle_definition,500),alert_definition:string(s.alert_definition,500)};
 return {generated_at:date(r.generated_at),status:choice(r.status,["available","empty","unavailable"]),is_demo:demo(r.is_demo),scenario_started_at:nullable(r.scenario_started_at,date),shops,events,destinations,sources,stats};
}

export function parseReport(input:unknown,id:string):Report {
 const r=object(input,["report_id","created_at","shop_name","is_demo","baseline_estimate_rm","estimated_loss_rm","estimate_status","coverage","assessed_items","baseline_items","confidence","confidence_note","summary_text","recovery_attribution","items","evidence","disclaimer"]);
 if(hex(r.report_id,32)!==id)throw new Error("Report identity mismatch");
 const items=list(r.items,80,value=>{const i=object(value,["item_id","condition","estimated_loss_rm","evidence_timestamp_s","uncertainty","name","qty","baseline_estimate_rm"]);const condition=choice(i.condition,["ok","damaged","destroyed","missing","unassessed"]),loss=nullable(i.estimated_loss_rm,number),baseline=number(i.baseline_estimate_rm);if((condition==="missing"||condition==="unassessed")&&loss!==null)throw new Error("Unknown item has invented loss");if(loss!==null&&loss>baseline)throw new Error("Loss exceeds baseline");return {item_id:string(i.item_id,160),condition,estimated_loss_rm:loss,evidence_timestamp_s:nullable(i.evidence_timestamp_s,v=>number(v,0,300)),uncertainty:string(i.uncertainty,300),name:string(i.name,200),qty:number(i.qty,0,1_000_000),baseline_estimate_rm:baseline};});
 const evidence=list(r.evidence,10,value=>{const e=object(value,["media_id","kind","sha256","bytes","mime_type","uploaded_at","telegram_date","lat","lng","location_attribution","is_demo","integrity_status"]);return {media_id:hex(e.media_id,64),kind:choice(e.kind,["baseline_video","update_video","after_video","waterline_photo"]),sha256:hex(e.sha256,64),bytes:integer(e.bytes,1,20_000_000),mime_type:choice(e.mime_type,["video/mp4","image/jpeg","image/png","image/webp"]),uploaded_at:date(e.uploaded_at),telegram_date:date(e.telegram_date),...position(e),location_attribution:choice(e.location_attribution,["confirmed_shop","confirmed_shared","unconfirmed_shop"]),is_demo:boolean(e.is_demo),integrity_status:choice(e.integrity_status,["not_checked"])};});
 const assessed=items.filter(i=>i.estimated_loss_rm!==null).length,total=nullable(r.estimated_loss_rm,number),coverage=choice(r.coverage,["complete","partial","none"]);
 if(integer(r.baseline_items)!==items.length||integer(r.assessed_items)!==assessed||new Set(items.map(i=>i.item_id)).size!==items.length||new Set(evidence.map(e=>e.media_id)).size!==evidence.length)throw new Error("Invalid assessment coverage");
 if(coverage!==(assessed===0?"none":assessed===items.length?"complete":"partial")||(assessed===0?total!==null:total===null||Math.abs(total-items.reduce((sum,i)=>sum+(i.estimated_loss_rm??0),0))>.005))throw new Error("Invalid assessed total");
 const isDemo=boolean(r.is_demo);if(evidence.some(e=>e.is_demo!==isDemo))throw new Error("Invalid evidence attribution");
 const status=choice(r.estimate_status,["available","unavailable"]);if((total===null)!==(status==="unavailable"))throw new Error("Invalid estimate status");
 return {report_id:id,created_at:date(r.created_at),shop_name:string(r.shop_name,200),is_demo:isDemo,baseline_estimate_rm:number(r.baseline_estimate_rm),estimated_loss_rm:total,estimate_status:status,coverage,assessed_items:assessed,baseline_items:items.length,confidence:number(r.confidence,0,1),confidence_note:string(r.confidence_note,300),summary_text:string(r.summary_text),recovery_attribution:string(r.recovery_attribution,300),items,evidence,disclaimer:string(r.disclaimer,600)};
}

export function parseIntegrity(input:unknown,receipt:Evidence):Integrity {
 const r=object(input,["media_id","status","sha256","note"]);
 if(hex(r.media_id,64)!==receipt.media_id||hex(r.sha256,64)!==receipt.sha256)throw new Error("Evidence identity mismatch");
 return {media_id:receipt.media_id,status:choice(r.status,["verified","mismatch","unavailable"]),sha256:receipt.sha256,note:string(r.note,600)};
}
