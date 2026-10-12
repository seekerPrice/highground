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
 assert.equal(operationStatus({status:"reset",scenario_started_at:"2026-10-13T01:00:00Z",shops_reset:6},true),"reset");
});
