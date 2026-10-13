import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {exampleCalculations, type PublicExample} from "../lib/example-calculation.ts";
const read = (path:string) => readFileSync(new URL(path,import.meta.url));
const example:PublicExample = JSON.parse(read("../lib/example-data.json").toString());
const captured = JSON.parse(read("../../api/tests/fixtures/waste-journey-response.json").toString());

test("public example is an exact narrow allowlist of the captured estimates",()=>{
 assert.deepEqual(Object.keys(example).sort(),["title","provenance","input_kind","baseline_confidence","assessment_confidence","baseline_uncertainty","assessment_uncertainty","items","assets","review_discrepancies","review_note"].sort());
 assert.equal(example.items.length,6);
 assert.deepEqual(example.items,captured.baseline.items.map((item:Record<string,unknown>,index:number)=>{
  const loss=captured.response.items[index];
  return {name:item.name,qty:item.qty,est_unit_value_rm:item.est_unit_value_rm,height:item.height,lift_effort:item.lift_effort,condition:loss.condition,estimated_loss_rm:loss.estimated_loss_rm,uncertainty:loss.uncertainty};
 }));
 assert.equal(example.baseline_confidence,captured.baseline.confidence);
 assert.equal(example.assessment_confidence,captured.response.confidence);
 assert.equal(example.baseline_uncertainty,captured.baseline.confidence_note);
 assert.equal(example.assessment_uncertainty,captured.response.confidence_note);
 assert.deepEqual(example.review_discrepancies.map(row=>[row.generation_brief_qty,row.model_estimated_qty]),[[4,6],[6,8]]);
 for(const row of example.review_discrepancies){assert.equal(row.model_estimated_qty,example.items.find(item=>item.name===row.item)?.qty);}
 for(const asset of example.assets)assert.deepEqual(Object.keys(asset).sort(),["phase","path","sha256","bytes"].sort());
 for(const row of example.review_discrepancies)assert.deepEqual(Object.keys(row).sort(),["item","generation_brief_qty","model_estimated_qty"].sort());
 assert.doesNotMatch(JSON.stringify(example),/media_id|inventory_id|report_id|telegram|gcs|gs:\/\/|#key=|donation_action|journey-fixture|location_in_shop|timestamp_s/);
});
test("worked priorities and recovery independently calculate exact captured totals",()=>{
 const result=exampleCalculations(example.items);
 assert.deepEqual(result.ranked.map(item=>[item.name,item.score]),[["Rice Cookers",360],["10kg Rice Cartons",105],["Bulk Dry Goods (Lower Bins)",80],["Packaged Water (24-bottle wraps)",60]]);
 assert.equal(result.priorityValue,850);assert.equal(result.baseline,1700);assert.equal(result.loss,850);assert.equal(result.assessed,6);
 assert.equal(result.baseline,captured.baseline.total_est_value_rm);assert.equal(result.loss,captured.response.total_loss_rm);
 const high={...example.items[0],height:"high",est_unit_value_rm:100000};
 assert.deepEqual(exampleCalculations([high]).ranked,[]);
});
test("public PNG checksums match exact original bytes without private ledger claims",()=>{
 assert.equal(example.assets.length,2);
 for(const asset of example.assets){
  assert.equal(asset.path,`/example/synthetic-${asset.phase}.png`);
  const original=read(`../../demo/media/synthetic-${asset.phase}.png`),published=read(`../public${asset.path}`);
  assert.deepEqual(published,original);assert.equal(published.length,asset.bytes);
  assert.equal(createHash("sha256").update(published).digest("hex"),asset.sha256);
 }
});
