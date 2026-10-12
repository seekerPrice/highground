import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {parseDashboard,parseReport,parseIntegrity} from "../lib/contracts.ts";
import {capability} from "../lib/client.ts";
const report=()=>JSON.parse(readFileSync(new URL("./fixtures/report.json",import.meta.url),"utf8"));
const dashboard=()=>JSON.parse(readFileSync(new URL("./fixtures/dashboard.json",import.meta.url),"utf8"));

test("backend fixture binds report and preserves unknown item loss/partial coverage",()=>{
 const input=report(),parsed=parseReport(input,input.report_id);
 assert.equal(parsed.coverage,"partial");assert.ok(parsed.items.some(item=>item.estimated_loss_rm===null));assert.equal(parsed.estimated_loss_rm,input.estimated_loss_rm);
 assert.throws(()=>parseReport(input,"0".repeat(32)));
 const item=input.items.find((item:{estimated_loss_rm:number|null})=>item.estimated_loss_rm===null);item.estimated_loss_rm=0;
 assert.throws(()=>parseReport(input,input.report_id));
});

test("public dashboard rejects real shops, private extra fields and fictional destinations",()=>{
 assert.equal(parseDashboard(dashboard()).is_demo,true);
 const real=dashboard();real.shops[0].is_demo=false;assert.throws(()=>parseDashboard(real));
 const privateData=dashboard();privateData.shops[0].recipients=[{telegram_chat_id:123}];assert.throws(()=>parseDashboard(privateData));
 const fake=dashboard();fake.destinations=JSON.parse(readFileSync(new URL("./fixtures/destinations.json",import.meta.url),"utf8"));fake.destinations[0].is_demo=true;assert.throws(()=>parseDashboard(fake));
 const missing=dashboard();missing.stats.status="unavailable";missing.stats.alerts_accepted=null;assert.equal(parseDashboard(missing).stats.alerts_accepted,null);
});

test("integrity badge status requires matching receipt identity/hash",()=>{
 const input=report(),receipt=parseReport(input,input.report_id).evidence[0];
 const result={media_id:receipt.media_id,status:"verified",sha256:receipt.sha256,note:"Checks file bytes only"};
 assert.equal(parseIntegrity(result,receipt).status,"verified");
 assert.equal(parseIntegrity({...result,status:"mismatch"},receipt).status,"mismatch");
 assert.throws(()=>parseIntegrity({...result,media_id:"b".repeat(64)},receipt));
 assert.throws(()=>parseIntegrity({...result,sha256:"f".repeat(64)},receipt));
});

test("capability is accepted only in exact single fragment field",()=>{
 const token="x".repeat(43);assert.equal(capability("#key="+token),token);
 for(const fragment of ["","#key=short","#key="+token+"&key=other","#key="+token+"&redirect=evil","#access="+token])assert.equal(capability(fragment),null);
});

 test("assessment receipt is explicitly bound and distinguishes retained after videos",async()=>{
 const input=report();const selected=input.evidence.find((e:{kind:string})=>e.kind==="after_video");input.assessment_media_id=selected.media_id;
 const retained={...selected,media_id:"e".repeat(64)};input.evidence.push(retained);
 const parsed=parseReport(input,input.report_id);
 assert.equal(parsed.assessment_media_id,selected.media_id);
 const labels=await import("../lib/contracts.ts");
 assert.equal(labels.evidenceTitle(selected,parsed.assessment_media_id),"After video used for assessment");
 assert.equal(labels.evidenceTitle(retained,parsed.assessment_media_id),"Retained after video — not assessed");
 assert.equal(labels.assessmentTimestamp(2),"Video used for assessment: 2.0 s");
 for(const invalid of ["f".repeat(64),input.evidence.find((e:{kind:string})=>e.kind!=="after_video").media_id,"bad"]){
  assert.throws(()=>parseReport({...input,assessment_media_id:invalid},input.report_id));
 }
 const missing={...input};delete missing.assessment_media_id;assert.throws(()=>parseReport(missing,input.report_id));
 });

test("synthetic fixture receipts cannot imply a Telegram message timestamp",async()=>{
 const input=report();const receipt=input.evidence[0];receipt.origin="local_fixture";receipt.telegram_date=null;
 const parsed=parseReport(input,input.report_id);
 assert.equal(parsed.evidence[0].telegram_date,null);
 const labels=await import("../lib/contracts.ts");assert.equal(labels.evidenceOriginCaption(parsed.evidence[0]),"Synthetic local fixture — no Telegram upload receipt");
 for(const patch of [{origin:"telegram",telegram_date:null},{origin:"local_fixture",telegram_date:"2026-10-13T00:00:00Z"},{origin:"local_fixture",is_demo:false}]){
  const bad=report();Object.assign(bad.evidence[0],patch);assert.throws(()=>parseReport(bad,bad.report_id));
 }
});

test("dashboard separates virtual simulations and durable resetting generation",()=>{
 const input=dashboard();input.scenario_generation=3;input.scenario_state="resetting";input.stats.virtual_alerts_simulated=6;input.stats.virtual_alert_definition="Virtual transport only; no Telegram API acceptance.";
 const parsed=parseDashboard(input);assert.equal(parsed.stats.virtual_alerts_simulated,6);assert.equal(parsed.scenario_state,"resetting");assert.equal(parsed.scenario_generation,3);
 assert.throws(()=>parseDashboard({...input,scenario_generation:-1}));
});
