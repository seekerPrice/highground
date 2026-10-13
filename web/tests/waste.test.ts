import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {parseReport} from "../lib/contracts.ts";
const fixture=(name:string)=>JSON.parse(readFileSync(new URL(`./fixtures/${name}.json`,import.meta.url),"utf8"));

test("versioned report waste joins canonical loss rows and old reports remain not assessed",()=>{
 const input=fixture("waste-report"),parsed=parseReport(input,input.report_id);
 assert.equal(parsed.waste.status,"available");assert.equal(parsed.waste.items[0].disposition,"discard_contaminated");
 assert.equal(parsed.evidence.length,2);assert.equal(parsed.estimated_loss_rm,20);
 const old=fixture("report");assert.equal(parseReport(old,old.report_id).waste.status,"not_assessed");
 for(const change of [{item_id:"other"},{condition:"destroyed"},{estimated_loss_rm:999},{donation_eligible:true},{donation_action_url:"https://evil.test"}]){
  const bad=fixture("waste-report");Object.assign(bad.waste.items[0],change);assert.throws(()=>parseReport(bad,bad.report_id));
 }
 const duplicate=fixture("waste-report");duplicate.waste.items.push({...duplicate.waste.items[0]});assert.throws(()=>parseReport(duplicate,duplicate.report_id));
 const missing=fixture("waste-report");missing.waste.items=[];assert.throws(()=>parseReport(missing,missing.report_id));
 const warning=fixture("waste-report");warning.waste.food_safety_line="Food is safe";assert.throws(()=>parseReport(warning,warning.report_id));
});

test("public waste has explicit assessment coverage and unknown quantities without private fields",async()=>{
 const {parseWaste}=await import("../lib/contracts.ts");
 const input=fixture("waste-response"),parsed=parseWaste(input);
 assert.equal(parsed.assessed_shops,1);assert.equal(parsed.missing_or_unavailable_shops,5);
 assert.equal(parsed.aggregate?.streets[0].estimated_load_equivalents,.1);
 const partial=fixture("waste-response"),street=partial.aggregate.streets[0];street.baseline_items=2;street.unknown_items=1;street.unknown_volume_items=1;street.unknown_weight_items=1;
 assert.equal(parseWaste(partial).aggregate?.streets[0].unknown_items,1);
 const missing=fixture("waste-response");missing.status="unavailable";missing.assessed_shops=null;missing.missing_or_unavailable_shops=null;missing.aggregate=null;
 assert.equal(parseWaste(missing).aggregate,null);
 for(const patch of [{is_demo:false},{media_id:"private"},{assessed_shops:2},{status:"empty"}])assert.throws(()=>parseWaste({...input,...patch}));
 for(const patch of [{estimated_load_equivalents:1},{shop_id:"private"},{est_volume_m3:-1},{unknown_items:2},{quantified_weight_items:0}]){
  const bad=fixture("waste-response");Object.assign(bad.aggregate.streets[0],patch);assert.throws(()=>parseWaste(bad));
 }
});

test("donation links are exact owner-bound Telegram actions without capability forwarding",async()=>{
 const {donationAction}=await import("../lib/contracts.ts");const action="donate_"+"a".repeat(32),safe="https://t.me/HighGroundBot?start="+action;
 assert.equal(donationAction(safe),safe);
 for(const bad of ["https://evil.test/HighGroundBot?start="+action,"https://t.me@evil.test/HighGroundBot?start="+action,"https://user:pass@t.me/HighGroundBot?start="+action,safe+"#key=private",safe+"&key=private",safe+"&start="+action,"http://t.me/HighGroundBot?start="+action,"https://t.me:444/HighGroundBot?start="+action,"https://t.me/HighGroundBot?start=donate_notopaque"]){assert.throws(()=>donationAction(bad));}
 const input=fixture("waste-report");Object.assign(input.waste.items[0],{material:"sealed_metal",floodwater_contact:"yes",contamination:"not_observed",disposition:"salvage_clean",donation_eligible:true,donation_action_url:safe});
 assert.equal(parseReport(input,input.report_id).waste.items[0].donation_action_url,safe);
});

test("waste labels keep unknown quantities and empty assessment coverage distinct from zero",async()=>{
 const {wasteItemSummary,wasteScope}=await import("../lib/waste-summary.ts");const {parseWaste}=await import("../lib/contracts.ts");
 const input=fixture("waste-report"),item=parseReport(input,input.report_id).waste.items[0];
 assert.equal(wasteItemSummary(item).disposition,"Discard as contaminated");assert.equal(wasteItemSummary(item).volume,"≈1 m³");
 assert.equal(wasteItemSummary({...item,est_volume_m3:null}).volume,"Unknown");
 assert.equal(wasteItemSummary({...item,est_volume_m3:0}).volume,"≈0 m³");
 assert.equal(wasteScope(parseWaste(fixture("waste-response"))),"1 of 6 synthetic shops have a completed waste assessment; 5 are missing or unavailable.");
 const empty=fixture("waste-response");empty.status="empty";empty.assessed_shops=0;empty.missing_or_unavailable_shops=6;empty.aggregate.streets=[];
 assert.equal(wasteScope(parseWaste(empty)),"No completed waste assessments for 6 synthetic shops. Waste quantities are unknown.");
});

test("public waste proxy permits only GET and strips report/operator credentials",async()=>{
 const {proxy,allowedTarget}=await import("../lib/proxy.ts");
 assert.equal(allowedTarget(["waste"],"POST"),null);assert.equal(allowedTarget(["waste","private"],"GET"),null);
 let called=false;
 const response=await proxy(new Request("http://web.test/api/waste",{headers:{Authorization:"Bearer private-capability",Cookie:"private-cookie"}}),["waste"],"https://api.test",async(url,options)=>{
  called=true;assert.equal(url,"https://api.test/api/waste");const headers=new Headers(options?.headers);assert.equal(headers.get("Authorization"),null);assert.equal(headers.get("Cookie"),null);return Response.json(fixture("waste-response"));
 });assert.equal(response.status,200);assert.equal(called,true);assert.match(response.headers.get("Cache-Control")!,/no-store/);
});

test("missing loss items cannot acquire waste quantities or donation availability",()=>{
 const input=fixture("waste-report");Object.assign(input.items[0],{condition:"missing",estimated_loss_rm:null,evidence_timestamp_s:null});Object.assign(input,{estimated_loss_rm:null,estimate_status:"unavailable",coverage:"none",assessed_items:0});
 Object.assign(input.waste.items[0],{condition:"missing",disposition:null,est_volume_m3:null,est_weight_kg:null,material:"unknown",floodwater_contact:"unknown",contamination:"unknown",uncertainty:"Not assessed"});
 assert.equal(parseReport(input,input.report_id).waste.items[0].est_volume_m3,null);
 for(const patch of [{est_volume_m3:0},{donation_available:true},{donation_action_url:"https://t.me/HighGroundBot?start=donate_"+"a".repeat(32)}]){
  const bad=structuredClone(input);Object.assign(bad.waste.items[0],patch);assert.throws(()=>parseReport(bad,bad.report_id));
 }
});

test("cleanup pins join only same-generation public shops without duplicating street totals",async()=>{
 const {wasteMap}=await import("../lib/waste-summary.ts");const {parseWaste,parseDashboard}=await import("../lib/contracts.ts");
 const input=fixture("waste-response"),dashboard=fixture("dashboard");
 input.scenario_generation=dashboard.scenario_generation;input.map_links=[{shop_id:dashboard.shops[0].shop_id,street:input.aggregate.streets[0].street}];
 const value=parseWaste(input),data=parseDashboard(dashboard),layer=wasteMap(data,value);
 assert.equal(layer.pins.length,1);assert.equal(layer.streets.length,1);assert.equal(layer.streets[0].est_volume_m3,1);
 const two={...data,shops:[...data.shops,{...data.shops[0],shop_id:"other-public"}]};
 const joined=wasteMap(two,{...value,map_links:[...value.map_links,{shop_id:"other-public",street:input.aggregate.streets[0].street}]});assert.equal(joined.pins.length,2);assert.equal(joined.streets.length,1);assert.equal(joined.streets[0].est_volume_m3,1);
 assert.equal(wasteMap({...data,scenario_generation:data.scenario_generation+1},value).pins.length,0);
 assert.equal(wasteMap({...data,scenario_state:"resetting"},value).pins.length,0);
 assert.equal(wasteMap({...data,shops:[]},value).pins.length,0);
 assert.equal(wasteMap(data,{...value,map_links:[{shop_id:"private-or-absent",street:input.aggregate.streets[0].street}]}).pins.length,0);
 const unknown=structuredClone(input);unknown.aggregate.streets[0].est_volume_m3=null;unknown.aggregate.streets[0].estimated_load_equivalents=null;unknown.aggregate.streets[0].quantified_volume_items=0;unknown.aggregate.streets[0].unknown_volume_items=1;
 assert.equal(wasteMap(data,parseWaste(unknown)).streets[0].est_volume_m3,null);
 const duplicate=structuredClone(input);duplicate.map_links.push(duplicate.map_links[0]);assert.throws(()=>parseWaste(duplicate));
 const unassigned=structuredClone(input);unassigned.map_links[0].street="Unassigned";assert.throws(()=>parseWaste(unassigned));
});
