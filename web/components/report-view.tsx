"use client";
import {useCallback,useEffect,useRef,useState} from "react";
import {parseIntegrity,parseReport,evidenceTitle,assessmentTimestamp,type Evidence,type Integrity,type Report} from "../lib/contracts";
import {AccessError,capability,money,time} from "../lib/client";
import {boundedBytes,MEDIA_LIMIT} from "../lib/proxy";

type Stage="loading"|"ready"|"missing"|"invalid"|"forbidden"|"unavailable"|"error";
const messages:Record<Exclude<Stage,"ready">,{title:string;note:string}>={
 loading:{title:"Loading your private estimate",note:"Checking access to this report."},
 missing:{title:"The private access key is missing",note:"Open the complete report link shared by HighGround. Its private access key is required."},
 invalid:{title:"This report link is invalid",note:"Ask the owner for the complete report link."},
 forbidden:{title:"Report access was rejected",note:"Ask the owner for a new report link. A report ID alone does not grant access."},
 unavailable:{title:"Report unavailable",note:"This report could not be found. Check the complete link with the owner."},
 error:{title:"The report could not be loaded",note:"The service may be temporarily unavailable. Try again."},
};
export default function ReportView({id}:{id:string}) {
 const token=useRef<string|null>(null);const [stage,setStage]=useState<Stage>("loading");const [report,setReport]=useState<Report|null>(null);const [retry,setRetry]=useState(0);
 const scoped=useCallback(async(path:string,method="GET",signal?:AbortSignal)=>{
   if(!token.current)throw new AccessError(403);
   const response=await fetch(`/api/report/${id}${path}`,{method,signal,cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer",headers:{Authorization:`Bearer ${token.current}`}});
   if(!response.ok)throw new AccessError(response.status);
   return response;
 },[id]);
 const authorized=useCallback(async(path:string,method="GET",signal?:AbortSignal)=>(await scoped(path,method,signal)).json() as Promise<unknown>,[scoped]);
 useEffect(()=>{
   const controller=new AbortController();let alive=true;
   async function load() {
    setReport(null);setStage("loading");token.current=null;
    if(!/^[a-f0-9]{32}$/.test(id)){setStage("invalid");return;}
    const fragment=window.location.hash;
    if(!fragment){setStage("missing");return;}
    token.current=capability(fragment);
    if(!token.current){setStage("invalid");return;}
    try{const value=parseReport(await authorized("","GET",controller.signal),id);if(alive){setReport(value);setStage("ready");}}
    catch(error){if(alive&&!controller.signal.aborted)setStage(error instanceof AccessError?(error.status===403?"forbidden":error.status===404?"unavailable":"error"):"error");}
   }
   void load();
   const changed=()=>{controller.abort();setRetry(value=>value+1);};window.addEventListener("hashchange",changed);
   return()=>{alive=false;controller.abort();token.current=null;window.removeEventListener("hashchange",changed);};
 },[id,retry,authorized]);
 useEffect(()=>{
   let fragment="";
   const before=()=>{fragment=window.location.hash;if(fragment)window.history.replaceState(null,"",window.location.pathname);};
   const after=()=>{if(fragment){window.history.replaceState(null,"",window.location.pathname+fragment);fragment="";}};
   window.addEventListener("beforeprint",before);window.addEventListener("afterprint",after);
   return()=>{window.removeEventListener("beforeprint",before);window.removeEventListener("afterprint",after);after();};
 },[]);
 return <main className="report-sheet">
  <header className="report-header"><div><a className="brand" href="/">HighGround</a><p>Private flood loss estimate</p></div>{stage==="ready"&&<button className="button print-control" onClick={()=>window.print()}>Save as PDF</button>}</header>
  {stage!=="ready"?<section className="report-state" role="status"><h1>{messages[stage].title}</h1><p>{messages[stage].note}</p>{stage==="error"&&<button className="button" onClick={()=>setRetry(value=>value+1)}>Try again</button>}</section>:report&&<>
   <section className="report-intro"><div>{report.is_demo&&<span className="badge simulation">Simulation</span>}<h1>{report.shop_name}</h1><p>{time(report.created_at)}</p></div><div className="report-total"><p>{report.coverage==="partial"?"Partial estimated loss":"Estimated loss"}</p><strong>{report.estimated_loss_rm===null?"Unavailable":money(report.estimated_loss_rm)}</strong><p>{report.assessed_items} of {report.baseline_items} items assessed</p></div></section>
   <section className="estimate-note"><p>{report.summary_text}</p><p><strong>Assessment confidence: {Math.round(report.confidence*100)}%.</strong> {report.confidence_note}</p><p>Baseline replacement estimate: {money(report.baseline_estimate_rm)}. {report.coverage!=="complete"&&"Unknown losses are excluded; the assessed total does not describe the full shop loss."}</p><p>Recovery attribution: {report.recovery_attribution}</p></section>
   <section aria-labelledby="comparison-title"><h2 id="comparison-title">Before and after comparison</h2><div className="table-scroll"><table className="comparison-table"><thead><tr><th scope="col">Item</th><th scope="col">Before estimate</th><th scope="col">After assessment</th><th scope="col">Estimated loss</th></tr></thead><tbody>{report.items.map(item=><tr key={item.item_id}><th scope="row">{item.name}<small>Quantity {item.qty}</small></th><td>{money(item.baseline_estimate_rm)}</td><td><strong>{item.condition==="ok"?"No visible loss":item.condition==="missing"?"Not visible in after-video":item.condition==="unassessed"?"Unassessed":item.condition==="damaged"?"Damaged":"Destroyed"}</strong><small>{item.uncertainty}</small>{item.evidence_timestamp_s!==null&&<small>{assessmentTimestamp(item.evidence_timestamp_s)}</small>}</td><td>{item.estimated_loss_rm===null?<span className="unknown">Unknown</span>:money(item.estimated_loss_rm)}</td></tr>)}</tbody></table></div></section>
   <section aria-labelledby="evidence-title" className="evidence-section"><h2 id="evidence-title">Evidence receipts</h2><p>Integrity checks compare stored bytes with the recorded hash. They do not authenticate the scene, time, location or valuation.</p>{report.evidence.map(receipt=><EvidenceCard key={receipt.media_id} id={id} receipt={receipt} assessmentMediaId={report.assessment_media_id} scoped={scoped}/>)}</section>
   <footer className="report-disclaimer"><h2>Limits of this estimate</h2><p>{report.disclaimer}</p><p>This document does not establish insurer acceptance or compensation.</p><small>Report {report.report_id}</small></footer>
  </>}
 </main>;
}
function EvidenceCard({receipt,scoped,assessmentMediaId}:{id:string;receipt:Evidence;assessmentMediaId:string;scoped:(path:string,method?:string,signal?:AbortSignal)=>Promise<Response>}) {
 const [integrity,setIntegrity]=useState<Integrity|null>(null);const [checking,setChecking]=useState(false);const [checkError,setCheckError]=useState(false);
 const [url,setUrl]=useState<string|null>(null);const [opening,setOpening]=useState(false);const [mediaError,setMediaError]=useState<string|null>(null);const controller=useRef<AbortController|null>(null);
 const objectUrl=useRef<string|null>(null);const busy=useRef(false);
 useEffect(()=>()=>{controller.current?.abort();if(objectUrl.current)URL.revokeObjectURL(objectUrl.current);},[]);
 async function verify(){
  if(busy.current)return;busy.current=true;setChecking(true);setCheckError(false);setIntegrity(null);
  const active=new AbortController();controller.current=active;
  try{setIntegrity(parseIntegrity(await (await scoped(`/media/${receipt.media_id}/verify`,"POST",active.signal)).json(),receipt));}
  catch{if(!active.signal.aborted)setCheckError(true);}finally{busy.current=false;setChecking(false);}
 }
 async function open(){
  if(url){URL.revokeObjectURL(url);objectUrl.current=null;setUrl(null);return;}
  if(busy.current)return;busy.current=true;setOpening(true);setMediaError(null);
  const active=new AbortController();controller.current=active;
  try{
   const response=await scoped(`/media/${receipt.media_id}`,"GET",active.signal);
   if(response.headers.get("Content-Type")?.split(";")[0]!==receipt.mime_type)throw new Error("Unexpected media type");
   const bytes=await boundedBytes(response.body,MEDIA_LIMIT,active.signal);
   if(bytes.byteLength!==receipt.bytes)throw new Error("Unexpected media size");
   if(active.signal.aborted)return;
   const next=URL.createObjectURL(new Blob([bytes.buffer as ArrayBuffer],{type:receipt.mime_type}));objectUrl.current=next;setUrl(next);
  }catch(error){if(!active.signal.aborted)setMediaError(error instanceof AccessError&&error.status===409?"Original failed integrity checks.":error instanceof AccessError&&error.status===404?"Original media unavailable.":"Original could not be loaded. Try again.");}
  finally{busy.current=false;setOpening(false);}
 }
 // Original bytes use the same scoped authenticated transport as verification.
 const title=evidenceTitle(receipt,assessmentMediaId);
 return <article className="evidence-receipt"><div className="receipt-heading"><h3>{title}</h3>{integrity?.status==="verified"&&!checking&&<span className="integrity verified">File integrity verified</span>}{integrity?.status==="mismatch"&&<span className="integrity mismatch">File integrity mismatch</span>}</div><dl><div><dt>Received</dt><dd>{time(receipt.uploaded_at)}</dd></div><div><dt>Telegram message time</dt><dd>{time(receipt.telegram_date)}</dd></div><div><dt>Attributed location</dt><dd>{receipt.location_attribution.replaceAll("_"," ")} ({receipt.lat.toFixed(5)}, {receipt.lng.toFixed(5)})</dd></div></dl><details><summary>SHA-256 file receipt ({receipt.sha256.slice(0,12)}…)</summary><code>{receipt.sha256}</code><p>{receipt.bytes.toLocaleString()} bytes</p></details><div className="receipt-actions print-control"><button className="button secondary" disabled={checking||opening} onClick={()=>void verify()}>{checking?"Checking file integrity…":"Verify file integrity"}</button><button className="button secondary" disabled={opening||checking} onClick={()=>void open()}>{opening?"Loading original…":url?"Close original":"View original"}</button></div>{checkError&&<p role="status">Verification unavailable. Try again.</p>}{integrity?.status==="unavailable"&&<p role="status">Stored media is unavailable for verification.</p>}{integrity?.status==="mismatch"&&<p>Stored bytes do not match the receipt. This file has not passed integrity verification.</p>}{mediaError&&<p role="status">{mediaError}</p>}{url&&<div className="original-media">{receipt.mime_type.startsWith("image/")?<img src={url} alt="Owner-provided recovery evidence"/>:<video src={url} controls preload="metadata"/>}</div>}<p className="print-only">Original media requires the private report access key.</p></article>;
}
