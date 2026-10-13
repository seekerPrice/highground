/** Fixed-origin backend boundary. No cookies, redirects or arbitrary targets. */
const REPORT = /^[a-f0-9]{32}$/;
const MEDIA = /^[a-f0-9]{64}$/;
export const MEDIA_LIMIT = 20_000_000;
const JSON_LIMIT = 512_000;
const HEADERS = {"Cache-Control":"private, no-store, max-age=0", "Referrer-Policy":"no-referrer", "X-Content-Type-Options":"nosniff"};

function failure(status: number): Response {
  return Response.json({error: status === 403 ? "Access rejected" : status === 404 ? "Unavailable" : "Request unavailable"}, {status, headers: HEADERS});
}

export function backendOrigin(value: string | undefined): string {
  if (!value) throw new Error("Backend is not configured");
  const url = new URL(value);
  const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if ((url.protocol !== "https:" && !(url.protocol === "http:" && local)) || url.username || url.password || url.search || url.hash || url.pathname !== "/") throw new Error("Invalid backend origin");
  return url.origin;
}

export function allowedTarget(path: string[], method: string): {path: string; private: boolean; media: boolean} | null {
  if (path.length === 1 && path[0] === "dashboard" && method === "GET") return {path:"/api/dashboard", private:false, media:false};
  if (path.length === 1 && path[0] === "outcomes" && method === "GET") return {path:"/api/outcomes", private:false, media:false};
  if (path.length === 1 && path[0] === "waste" && method === "GET") return {path:"/api/waste", private:false, media:false};
  if (path[0] === "report" && REPORT.test(path[1] ?? "")) {
    if (path.length === 2 && method === "GET") return {path:`/api/report/${path[1]}`, private:true, media:false};
    if (path[2] === "media" && MEDIA.test(path[3] ?? "")) {
      if (path.length === 4 && method === "GET") return {path:`/api/report/${path[1]}/media/${path[3]}`, private:true, media:true};
      if (path.length === 5 && path[4] === "verify" && method === "POST") return {path:`/api/report/${path[1]}/media/${path[3]}/verify`, private:true, media:false};
    }
  }
  if (path.length === 2 && path[0] === "demo" && ["simulate-warning", "reset"].includes(path[1]) && method === "POST") return {path:`/demo/${path[1]}`, private:true, media:false};
  return null;
}

export async function boundedBytes(body: ReadableStream<Uint8Array> | null, limit: number, signal?: AbortSignal): Promise<Uint8Array> {
  if (!body) return new Uint8Array();
  const reader = body.getReader();
  const chunks: Uint8Array[] = []; let size = 0;
  const cancel = () => { void reader.cancel(); };
  signal?.addEventListener("abort", cancel, {once:true});
  try {
    while (true) {
      if (signal?.aborted) throw new Error("Request timed out");
      const {done, value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error("Response too large");
      chunks.push(value);
    }
    if (signal?.aborted) throw new Error("Request timed out");
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.byteLength; }
    return bytes;
  } finally { signal?.removeEventListener("abort",cancel); await reader.cancel().catch(() => {}); reader.releaseLock(); }
}

async function rejectUpstream(response:Response,status:number):Promise<Response>{
  await response.body?.cancel().catch(()=>{});return failure(status);
}

export async function proxy(request: Request, path: string[], origin: string | undefined, fetcher: typeof fetch = fetch): Promise<Response> {
  const target = allowedTarget(path,request.method);
  if (!target || new URL(request.url).search) return failure(404);
  let base: string;
  try { base = backendOrigin(origin); } catch { return failure(503); }
  const authorization = request.headers.get("Authorization") ?? "";
  if (target.private && !/^Bearer [A-Za-z0-9._~+/-]{1,512}$/.test(authorization)) return failure(403);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), target.media ? 15_000 : 10_000);
  try {
    const headers: Record<string,string> = {Accept:target.media ? "video/mp4, image/jpeg, image/png, image/webp" : "application/json"};
    if (target.private) headers.Authorization = authorization;
    let body: string | undefined;
    if (request.method === "POST") {
      const bytes = await boundedBytes(request.body,16_000,controller.signal);
      body = bytes.byteLength ? new TextDecoder().decode(bytes) : "{}";
      const parsed: unknown = JSON.parse(body);
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return failure(400);
      headers["Content-Type"] = "application/json";
    }
    const response = await fetcher(base + target.path, {method:request.method,headers,body,redirect:"error",cache:"no-store",signal:controller.signal});
    if (!response.ok) return rejectUpstream(response,[400,403,404,409,413,429].includes(response.status) ? response.status : 502);
    const limit = target.media ? MEDIA_LIMIT : JSON_LIMIT;
    const declared = response.headers.get("Content-Length");
    if (declared && (!/^\d+$/.test(declared) || Number(declared) > limit)) return rejectUpstream(response,502);
    const type = response.headers.get("Content-Type")?.split(";")[0].trim() ?? "";
    if (target.media ? !["video/mp4","image/jpeg","image/png","image/webp"].includes(type) : type !== "application/json") return rejectUpstream(response,502);
    const bytes = await boundedBytes(response.body,limit,controller.signal);
    return new Response(bytes.buffer as ArrayBuffer,{status:200,headers:{...HEADERS,"Content-Type":type}});
  } catch { return failure(502); } finally { clearTimeout(timer); }
}
