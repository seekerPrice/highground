import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {parseDashboard} from "../lib/contracts.ts";
const dashboard=()=>JSON.parse(readFileSync(new URL("./fixtures/dashboard.json",import.meta.url),"utf8"));
const aggregate=()=>({is_demo:true,registered_synthetic_shops:6,assessed_known_coverage:2,flood_cover_indicated:1,explicit_no_flood_cover:1,unclear_or_expired:2,missing_policies:2,without_cover_percent_of_known:50,uninsured_stock_estimate_rm:140,unknown_stock_estimates:4,definition:"Frozen replacement-price estimates; no guaranteed payout or current-cover claim."});

test("policy aggregate accepts synthetic known denominator and keeps absent/unavailable unknown",()=>{
 const old=parseDashboard(dashboard());assert.equal(old.policy_coverage,null);
 const input={...dashboard(),policy_coverage:aggregate(),policy_note:"Synthetic extracted policy summary."};
 const parsed=parseDashboard(input);assert.equal(parsed.policy_coverage?.without_cover_percent_of_known,50);
 assert.equal(parsed.policy_coverage?.unknown_stock_estimates,4);
 assert.equal(parseDashboard({...input,policy_coverage:null}).policy_coverage,null);
 const unknown={...aggregate(),assessed_known_coverage:0,flood_cover_indicated:0,explicit_no_flood_cover:0,unclear_or_expired:4,without_cover_percent_of_known:null,uninsured_stock_estimate_rm:null,unknown_stock_estimates:6};
 assert.equal(parseDashboard({...input,policy_coverage:unknown}).policy_coverage?.uninsured_stock_estimate_rm,null);
});

test("policy boundary rejects private fields, real provenance and contradictory counts/estimates",()=>{
 const input={...dashboard(),policy_note:"Synthetic only."};
 for(const patch of [{is_demo:false},{insurer:"Private insurer"},{evidence_quote:"Private line"},{registered_synthetic_shops:-1},{explicit_no_flood_cover:2},{missing_policies:4},{without_cover_percent_of_known:100},{uninsured_stock_estimate_rm:-1},{unknown_stock_estimates:7},{unknown_stock_estimates:6,uninsured_stock_estimate_rm:0}]){
  assert.throws(()=>parseDashboard({...input,policy_coverage:{...aggregate(),...patch}}));
 }
 assert.throws(()=>parseDashboard({...input,policy_coverage:aggregate(),policy_document_url:"private"}));
});

test("policy labels expose the known denominator and partial estimate without inventing zero",async()=>{
 const {policySummary}=await import("../lib/policy-summary.ts");
 const parsed=parseDashboard({...dashboard(),policy_coverage:aggregate()});
 const labels=policySummary(parsed.policy_coverage);
 assert.equal(labels.withoutCover,"50% (1 of 2 known policies)");
 assert.equal(labels.stockEstimate,"≈RM\u00a0140.00");
 assert.equal(labels.estimateCoverage,"Quantified frozen estimates for 2 of 6 synthetic shops; 4 amounts remain unknown.");
 assert.equal(policySummary(null).withoutCover,"Unavailable");
 assert.equal(policySummary(null).stockEstimate,"Unavailable");
 const empty=parseDashboard({...dashboard(),policy_coverage:{...aggregate(),registered_synthetic_shops:0,assessed_known_coverage:0,flood_cover_indicated:0,explicit_no_flood_cover:0,unclear_or_expired:0,missing_policies:0,without_cover_percent_of_known:null,uninsured_stock_estimate_rm:null,unknown_stock_estimates:0}}).policy_coverage;
 assert.equal(policySummary(empty).withoutCover,"Unavailable — no known policy denominator");
 assert.equal(policySummary(empty).stockEstimate,"Unavailable");
 const zero=parseDashboard({...dashboard(),policy_coverage:{...aggregate(),uninsured_stock_estimate_rm:0}}).policy_coverage;
 assert.equal(policySummary(zero).stockEstimate,"≈RM\u00a00.00");
});
