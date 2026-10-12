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
