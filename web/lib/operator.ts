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
 if(reset){
  if(Object.keys(row).length!==3||row.status!=="reset"||typeof row.scenario_started_at!=="string"||!Number.isFinite(Date.parse(row.scenario_started_at))||!Number.isInteger(row.shops_reset)||Number(row.shops_reset)<0||Number(row.shops_reset)>50)throw new Error("Invalid reset result");
  return "reset";
 }
 if(Object.keys(row).some(key=>!["event_id","status","alerts"].includes(key))||typeof row.event_id!=="string"||!/^[a-f0-9]{64}$/.test(row.event_id)||!["complete","pending","busy","needs_review","superseded"].includes(String(row.status)))throw new Error("Invalid simulation result");
 if(row.alerts!==undefined){if(!row.alerts||typeof row.alerts!=="object"||Array.isArray(row.alerts))throw new Error("Invalid alert counts");for(const [key,value] of Object.entries(row.alerts)){if(!["pending","sending","retryable","accepted","uncertain","superseded"].includes(key)||typeof value!=="number"||!Number.isInteger(value)||value<0||value>1000)throw new Error("Invalid alert count");}}
 return row.status as string;
}
