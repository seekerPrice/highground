import {test} from "node:test";
import assert from "node:assert/strict";
import {allowedTarget,backendOrigin,proxy,boundedBytes,MEDIA_LIMIT} from "../lib/proxy.ts";
const id="a".repeat(32),media="b".repeat(64),secret="synthetic-private-capability";
const request=(method="GET",path="report/"+id,headers:Record<string,string>={})=>new Request("http://web.test/api/"+path,{method,headers:{Authorization:"Bearer "+secret,...headers}});

test("proxy restricts origin, method, complete report binding and query parameters",async()=>{
 for(const origin of ["http://remote.test","https://api.test/path","https://user:pass@api.test","https://api.test?redirect=evil","https://api.test#key=secret"]){assert.throws(()=>backendOrigin(origin));}
 assert.equal(backendOrigin("http://127.0.0.1:8000"),"http://127.0.0.1:8000");
 for(const path of [["https:","evil.test"],["report",id,"media",media,"../verify"],["report",id,"media","wrong"],["shops"],["demo","reset","extra"]])assert.equal(allowedTarget(path,"GET"),null);
 assert.equal(allowedTarget(["report",id],"POST"),null);
 let called=false;const fetcher:typeof fetch=async()=>{called=true;throw new Error("Forbidden");};
 assert.equal((await proxy(request("GET","report/"+id+"?key=secret"),["report",id],"https://api.test",fetcher)).status,404);
 assert.equal((await proxy(request("GET","report/"+id,{Authorization:""}),["report",id],"https://api.test",fetcher)).status,403);
 assert.equal(called,false);
});

test("private requests forward only bearer to fixed origin and return private response headers",async()=>{
 const fetcher:typeof fetch=async(url,options)=>{
  assert.equal(url,"https://api.test/api/report/"+id);const headers=new Headers(options?.headers);
  assert.equal(headers.get("Authorization"),"Bearer "+secret);assert.equal(headers.get("Cookie"),null);assert.equal(headers.get("X-Forwarded-Host"),null);
  assert.equal(options?.redirect,"error");assert.equal(options?.cache,"no-store");assert.ok(options?.signal);
  return Response.json({report_id:id});
 };
 const response=await proxy(request("GET",undefined,{Cookie:"private-cookie","X-Forwarded-Host":"evil.test"}),["report",id],"https://api.test",fetcher);
 assert.equal(response.status,200);assert.match(response.headers.get("Cache-Control")!,/no-store/);assert.equal(response.headers.get("Referrer-Policy"),"no-referrer");
 assert.deepEqual(await response.json(),{report_id:id});
});

test("public dashboard does not forward a bearer or cookies; upstream errors are sanitized",async()=>{
 const response=await proxy(request("GET","dashboard",{Cookie:"private"}),["dashboard"],"https://api.test",async(_url,options)=>{
  assert.equal(new Headers(options?.headers).get("Authorization"),null);
  return Response.json({secret}, {status:403});
 });assert.equal(response.status,403);assert.ok(!(await response.text()).includes(secret));
});

test("oversized streamed responses are canceled even when declared small",async()=>{
 let canceled=false;let calls=0;
 const stream=new ReadableStream<Uint8Array>({pull(controller){controller.enqueue(new Uint8Array(260_000));calls++;},cancel(){canceled=true;}});
 const response=await proxy(request(),["report",id],"https://api.test",async()=>new Response(stream,{headers:{"Content-Type":"application/json","Content-Length":"1"}}));
 assert.equal(response.status,502);assert.equal(canceled,true);assert.ok(calls<5);
});

test("media path stays report scoped and enforces byte/mime limits",async()=>{
 const response=await proxy(request("GET",`report/${id}/media/${media}`),["report",id,"media",media],"https://api.test",async(url)=>{
  assert.equal(url,`https://api.test/api/report/${id}/media/${media}`);return new Response("small",{headers:{"Content-Type":"text/html"}});
 });assert.equal(response.status,502);
 const tooLarge=await proxy(request(),["report",id,"media",media],"https://api.test",async()=>new Response("bytes",{headers:{"Content-Type":"video/mp4","Content-Length":String(MEDIA_LIMIT+1)}}));
 assert.equal(tooLarge.status,502);
 const controller=new AbortController();controller.abort();await assert.rejects(()=>boundedBytes(new ReadableStream(),20,controller.signal));
});

test("verification method and body use bound route without arbitrary headers",async()=>{
 const response=await proxy(request("POST",`report/${id}/media/${media}/verify`),["report",id,"media",media,"verify"],"https://api.test",async(url,options)=>{
  assert.equal(url,`https://api.test/api/report/${id}/media/${media}/verify`);assert.equal(options?.method,"POST");assert.equal(options?.body,"{}");return Response.json({status:"verified"});
 });assert.equal(response.status,200);
});

test("a stalled upstream is terminated by the actual bounded request deadline",async()=>{
 const started=Date.now();
 const response=await proxy(request(),["report",id],"https://api.test",async(_url,options)=>new Promise((_resolve,reject)=>{
  options!.signal!.addEventListener("abort",()=>reject(new Error("synthetic timeout")),{once:true});
 }));
 assert.equal(response.status,502);assert.ok(Date.now()-started<12_000);
});
