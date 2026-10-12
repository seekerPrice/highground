export class AccessError extends Error {
  status: number;
  constructor(status:number) {super("Request unavailable");this.status=status;}
}
export async function readJson(path:string,options:RequestInit={},signal?:AbortSignal):Promise<unknown> {
 const response=await fetch(path,{...options,signal,cache:"no-store",credentials:"omit",referrerPolicy:"no-referrer"});
 if(!response.ok)throw new AccessError(response.status);
 return response.json();
}
export function capability(fragment:string):string|null {
 const values=new URLSearchParams(fragment.replace(/^#/,""));
 if(values.size!==1 || values.getAll("key").length!==1)return null;
 const key=values.get("key");return key&&/^[A-Za-z0-9_-]{32,128}$/.test(key)?key:null;
}
export const money=(value:number)=>new Intl.NumberFormat("en-MY",{style:"currency",currency:"MYR",minimumFractionDigits:2}).format(value);
export const time=(value:string)=>new Intl.DateTimeFormat("en-MY",{timeZone:"Asia/Kuala_Lumpur",dateStyle:"medium",timeStyle:"short"}).format(new Date(value))+" MYT";
