import {test} from "node:test";
import assert from "node:assert/strict";
import {simulationIntent,operationStatus} from "../lib/operator.ts";
test("ambiguous simulation retry reuses identity while changed facts start a new operation",()=>{
 const facts={level:"warning" as const,lat:3.,lng:101.};const first=simulationIntent(null,facts);
 assert.equal(simulationIntent(first,facts).body.request_id,first.body.request_id);
 assert.notEqual(simulationIntent(first,{...facts,level:"danger"}).body.request_id,first.body.request_id);
});
test("operator result validates known status/counts instead of reflecting arbitrary text",()=>{
 assert.equal(operationStatus({event_id:"a".repeat(64),status:"complete",alerts:{accepted:1}},false),"complete");
 assert.throws(()=>operationStatus({event_id:"a".repeat(64),status:"private arbitrary content"},false));
 assert.throws(()=>operationStatus({event_id:"a".repeat(64),status:"complete",alerts:{chat_id:123}},false));
 assert.equal(operationStatus({status:"reset",generation:1,scenario_started_at:"2026-10-13T01:00:00Z",shops_reset:6,inflight_outcomes_unknown:0,delivery_note:"Earlier sends cannot be unsent."},true),"reset");
});

test("reset retry preserves identity and exposes incomplete durable generation",async()=>{
 const operations=await import("../lib/operator.ts");const first=operations.resetIntent(null);assert.equal(operations.resetIntent(first).request_id,first.request_id);
 const result={status:"resetting",generation:4,scenario_started_at:null,shops_reset:2,inflight_outcomes_unknown:1,delivery_note:"An earlier external outcome is unknown."};
 assert.equal(operationStatus(result,true),"resetting");
 assert.equal(operationStatus({...result,status:"reset",scenario_started_at:"2026-10-13T00:00:00Z"},true),"reset");
 assert.throws(()=>operationStatus({...result,generation:-1},true));
});

test("successful virtual simulation is confirmed without counting Telegram acceptance",()=>{
 assert.equal(operationStatus({event_id:"a".repeat(64),status:"complete",alerts:{simulated:6}},false),"complete");
 assert.throws(()=>operationStatus({event_id:"a".repeat(64),status:"complete",alerts:{simulated:-1}},false));
});

test("superseded scenario response releases retry identity without reflecting arbitrary reason",()=>{
 const facts={level:"warning" as const,lat:3,lng:101};let intent:ReturnType<typeof simulationIntent>|null=simulationIntent(null,facts);const previous=intent.body.request_id;
 const status=operationStatus({event_id:"a".repeat(64),status:"superseded",reason:"obsolete_scenario"},false);
 if(["complete","superseded","reset"].includes(status))intent=null;
 assert.equal(status,"superseded");assert.notEqual(simulationIntent(intent,facts).body.request_id,previous);
 assert.throws(()=>operationStatus({event_id:"a".repeat(64),status:"superseded",reason:"private arbitrary content"},false));
 assert.throws(()=>operationStatus({event_id:"a".repeat(64),status:"complete",reason:"obsolete_scenario"},false));
});
