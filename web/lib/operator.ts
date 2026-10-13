export type SimulationFacts={level:"watch"|"warning"|"danger";lat:number;lng:number;radius_m?:number};
export type Intent={fingerprint:string;body:SimulationFacts&{request_id:string;reason:string}};
/** Preserve operation identity until an ambiguous result is resolved. */
export function simulationIntent(previous:Intent|null,facts:SimulationFacts):Intent {
 const fingerprint=JSON.stringify([facts.level,facts.lat,facts.lng,facts.radius_m??null]);
 if(previous?.fingerprint===fingerprint)return previous;
 return {fingerprint,body:{...facts,request_id:crypto.randomUUID(),reason:`Operator simulation: ${facts.level}`}};
}
export function operationStatus(input:unknown,reset:boolean):string {
 if(!input||typeof input!=="object"||Array.isArray(input))throw new Error("Invalid operation response");
 const row=input as Record<string,unknown>;
 if(reset)return resetResult(input).status;
 if(Object.keys(row).some(key=>!["event_id","status","alerts","reason"].includes(key))||typeof row.event_id!=="string"||!/^[a-f0-9]{64}$/.test(row.event_id)||!["complete","pending","busy","needs_review","superseded"].includes(String(row.status)))throw new Error("Invalid simulation result");
 if("reason" in row&&(row.status!=="superseded"||typeof row.reason!=="string"||!["expired","closed_episode","unattributed_source","missing_shop","simulation_mismatch","obsolete_observation","resolved_source_episode","superseded_source_watermark","obsolete_scenario"].includes(row.reason)))throw new Error("Invalid suppression reason");
 if(row.alerts!==undefined){if(!row.alerts||typeof row.alerts!=="object"||Array.isArray(row.alerts))throw new Error("Invalid alert counts");for(const [key,value] of Object.entries(row.alerts)){if(!["pending","sending","retryable","accepted","simulated","uncertain","superseded"].includes(key)||typeof value!=="number"||!Number.isInteger(value)||value<0||value>1000)throw new Error("Invalid alert count");}}
 return row.status as string;
}

export type ResetIntent={request_id:string};
export function resetIntent(previous:ResetIntent|null):ResetIntent {return previous??{request_id:crypto.randomUUID()};}
export interface ResetResult {status:"reset"|"resetting";generation:number;scenario_started_at:string|null;shops_reset:number;inflight_outcomes_unknown:number;delivery_note:string}
export function resetResult(input:unknown):ResetResult {
 if(!input||typeof input!=="object"||Array.isArray(input))throw new Error("Invalid reset result");
 const r=input as Record<string,unknown>,keys=["status","generation","scenario_started_at","shops_reset","inflight_outcomes_unknown","delivery_note"];
 if(Object.keys(r).length!==keys.length||keys.some(k=>!(k in r))||!["reset","resetting"].includes(String(r.status)))throw new Error("Invalid reset result");
 for(const key of ["generation","shops_reset","inflight_outcomes_unknown"])if(!Number.isInteger(r[key])||Number(r[key])<0||Number(r[key])>1_000_000_000)throw new Error("Invalid reset count");
 if(r.scenario_started_at!==null&&(typeof r.scenario_started_at!=="string"||!/(Z|[+-]\d\d:\d\d)$/.test(r.scenario_started_at)||!Number.isFinite(Date.parse(r.scenario_started_at))))throw new Error("Invalid reset time");
 if(r.status==="reset"&&r.scenario_started_at===null)throw new Error("Completed reset requires scenario time");
 if(typeof r.delivery_note!=="string"||r.delivery_note.length>500)throw new Error("Invalid reset note");
 return r as unknown as ResetResult;
}
