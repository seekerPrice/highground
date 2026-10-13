import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseOutcomes,outcomeCoverageLabel,calibrationEvidenceLabel} from '../lib/outcome-summary.ts';
import {proxy,allowedTarget} from '../lib/proxy.ts';
const fixture=()=>({status:'available',generated_at:'2026-10-14T00:00:00Z',is_demo:true,scenario_generation:2,registered_synthetic_shops:6,coverage:{is_demo:true,eligible_shop_episodes:6,accepted_prompts:4,virtual_prompts:1,uncertain_or_sending_prompts:1,responses:5,fixture_responses:0,no:4,street_only:1,entrance:0,inside:0,missing_unknown:1,fixture_prompts:0,definition:'Synthetic owner reports and response coverage, not accuracy or independent water verification.'},calibration_areas:[{area:'w2833s',multiplier:.9,version:1,evaluated_at:'2026-10-13T23:00:00Z',history:[{evaluated_at:'2026-10-13T23:00:00Z',old_multiplier:1,new_multiplier:.9,reason:'shrink',response_count:5,water_response_count:1,fixture_response_count:0}]}],history_truncated:false,note:'Synthetic self-reported feedback.'});
test('feedback contract preserves missing unknown and explicit synthetic trend',()=>{
 const parsed=parseOutcomes(fixture());assert.equal(parsed.coverage!.missing_unknown,1);assert.equal(parsed.calibration_areas[0].history[0].new_multiplier,.9);
 assert.equal(outcomeCoverageLabel(parsed),'5 of 6 shop episodes have an owner response; 1 remain unknown.');
 const unknown={...fixture(),status:'unavailable',scenario_generation:null,registered_synthetic_shops:null,coverage:null,calibration_areas:[]};
 assert.equal(outcomeCoverageLabel(parseOutcomes(unknown)),'Owner-response coverage is unavailable. Missing data does not mean no water.');
});
test('public feedback rejects private fields, real provenance and invented denominator',()=>{
 for(const patch of [{owner_hash:'private'},{is_demo:false},{coverage:{...fixture().coverage,missing_unknown:0}},{coverage:{...fixture().coverage,inside:5}},{calibration_areas:[{...fixture().calibration_areas[0],shop_id:'private'}]}])assert.throws(()=>parseOutcomes({...fixture(),...patch}));
 const unknown={...fixture(),status:'unavailable',coverage:null,calibration_areas:[],registered_synthetic_shops:null};assert.throws(()=>parseOutcomes(unknown));
});
test('public feedback proxy accepts only exact GET and strips all credentials',async()=>{
 assert.equal(allowedTarget(['outcomes'],'POST'),null);assert.equal(allowedTarget(['outcomes','private'],'GET'),null);
 const result=await proxy(new Request('http://web.test/api/outcomes',{headers:{Authorization:'Bearer private',Cookie:'secret'}}),['outcomes'],'https://api.test',async(url,options)=>{
  assert.equal(url,'https://api.test/api/outcomes');const headers=new Headers(options?.headers);assert.equal(headers.get('Authorization'),null);assert.equal(headers.get('Cookie'),null);return Response.json(fixture());
 });assert.equal(result.status,200);assert.match(result.headers.get('Cache-Control')!,/no-store/);
});

test('disposable preview fixtures keep seeded history and empty versus unavailable distinct',async()=>{
 const {readFileSync}=await import('node:fs');const read=(name:string)=>parseOutcomes(JSON.parse(readFileSync(new URL(`./fixtures/outcomes-${name}.json`,import.meta.url),'utf8')));
 const available=read('available');assert.equal(available.coverage!.accepted_prompts,0);assert.equal(available.coverage!.fixture_responses,5);assert.equal(available.calibration_areas[0].history[0].fixture_response_count,5);assert.match(available.note,/UI fixture only/);
 const empty=read('empty'),unknown=read('unavailable');assert.equal(empty.coverage!.eligible_shop_episodes,0);assert.match(outcomeCoverageLabel(empty),/remain unknown/);assert.equal(unknown.coverage,null);assert.equal(unknown.scenario_generation,null);
});

test('seeded calibration evidence never masquerades as accepted alerts',()=>{
 const history={evaluated_at:'2026-10-14T00:00:00Z',old_multiplier:1,new_multiplier:.9,reason:'shrink' as const,response_count:5,water_response_count:1,fixture_response_count:5};
 const label=calibrationEvidenceLabel(history);assert.match(label,/1 water responses among 5 eligible responses/);assert.match(label,/5 explicitly seeded records/);assert.match(label,/do not establish Telegram acceptance/);assert.doesNotMatch(label,/accepted-alert responses/);
});
