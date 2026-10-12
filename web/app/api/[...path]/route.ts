import { proxy } from "../../../lib/proxy";
export const dynamic = "force-dynamic";
async function handle(request: Request, context: {params: Promise<{path:string[]}>}) {
  const {path} = await context.params;
  return proxy(request,path,process.env.HIGHGROUND_API_ORIGIN);
}
export const GET = handle;
export const POST = handle;
