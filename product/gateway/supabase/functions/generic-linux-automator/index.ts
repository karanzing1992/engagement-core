import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { McpServer } from "npm:@modelcontextprotocol/sdk@1.25.3/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js";
import { createClient } from "npm:@supabase/supabase-js@2.75.0";
import { z } from "npm:zod@4.1.13";

const BASE = Deno.env.get("SUPABASE_URL") || "";
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const ANON = Deno.env.get("SUPABASE_ANON_KEY") || "";
if (!BASE || !SERVICE || !ANON) throw new Error("Missing existing Supabase runtime environment");
const db = createClient(BASE,SERVICE,{auth:{persistSession:false,autoRefreshToken:false}});
const FN = "generic-linux-automator";
const ROOT = BASE + "/functions/v1/" + FN;
const MCP_URL = ROOT + "/mcp";
const HOSTS = ["dell-linux","mac-linux"] as const;
type Host = typeof HOSTS[number];
const hostInput = z.enum(HOSTS);
const LANES = ["control","operations","development"] as const;
type Lane = typeof LANES[number];
const laneInput = z.enum(LANES);
const isLane = (x:unknown):x is Lane => typeof x === "string" && (LANES as readonly string[]).includes(x);
const isHost = (x:unknown):x is Host => typeof x === "string" && (HOSTS as readonly string[]).includes(x);
const isUUID = (x:unknown):x is string =>
  typeof x === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x);
const json = (v:unknown, status=200, extra:HeadersInit={}) =>
  new Response(JSON.stringify(v),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store",...extra}});
const answer = (v:unknown) => ({structuredContent:{data:v},content:[{type:"text" as const,text:JSON.stringify(v)}]});
const toolError = (s:string) => ({isError:true,content:[{type:"text" as const,text:s}]});
const bearer = (r:Request) => (r.headers.get("authorization")||"").match(/^Bearer\s+(\S+)$/i)?.[1]||null;
async function digest(input:string) {
  const bytes=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(input)));
  return Array.from(bytes,x=>x.toString(16).padStart(2,"0")).join("");
}
type OwnerStatus = { uid: string } | { reason: "missing_token" | "invalid_token" | "auth_unavailable" };
function challenge(reason: "missing_token" | "invalid_token" = "missing_token") {
  // Only a new owner authorization can restore a missing/revoked refresh token.
  // Signal RFC 6750 invalid_token to the MCP host; NEVER fall back to worker keys or PIN.
  const base = 'Bearer resource_metadata="' + ROOT + '/.well-known/oauth-protected-resource", scope="email offline_access"';
  const header = reason === "invalid_token" ? base + ', error="invalid_token"' : base;
  return json({error: reason === "invalid_token" ? "reauthorization_required" : "authorization_required"},
    401, {"www-authenticate": header, "vary": "Authorization"});
}
async function ownerUser(req:Request):Promise<OwnerStatus> {
  const token=bearer(req);
  if(!token)return {reason:"missing_token"};
  // The MCP client owns token refresh. Server-side retries must NOT consume or replay tokens.
  let auth:Response;
  try {
    auth=await fetch(BASE+"/auth/v1/user",{
      headers:{apikey:ANON,authorization:"Bearer "+token},
      redirect:"manual",signal:AbortSignal.timeout(6000)
    });
  } catch {
    return {reason:"auth_unavailable"};
  }
  // Return a transient failure instead of making a healthy login reconnect on 429/5xx.
  if(auth.status===429||auth.status>=500)return {reason:"auth_unavailable"};
  if(!auth.ok)return {reason:"invalid_token"};
  const user=await auth.json().catch(()=>null);
  if(typeof user?.id!=="string")return {reason:"invalid_token"};
  const m=await db.from("generic_auto_members").select("user_id").eq("user_id",user.id)
    .eq("role","owner").eq("enabled",true).maybeSingle();
  if(m.error)return {reason:"auth_unavailable"};
  if(!m.data)return {reason:"invalid_token"};
  return {uid:user.id};
}
async function ownerHost(uid:string,id:Host) {
  const {data,error}=await db.from("generic_auto_hosts")
    .select("host_id,paired_at,last_seen_at,enabled,allow_shell,worker_version,control_seen_at,operations_seen_at,development_seen_at")
    .eq("host_id",id).eq("owner_id",uid).eq("enabled",true).maybeSingle();
  return error?null:data;
}
async function workerIdentity(req:Request,id:Host) {
  const t=bearer(req);
  if(!t||t.length<40||t.length>256)return null;
  const {data,error}=await db.from("generic_auto_hosts").select("host_id,owner_id")
    .eq("host_id",id).eq("worker_hash",await digest(t)).eq("enabled",true).maybeSingle();
  return error?null:data;
}
async function parse(req:Request) {
  const s=await req.text();if(s.length>100000)throw new Error("payload_too_large");
  return JSON.parse(s);
}
async function workerRoute(req:Request,path:string):Promise<Response> {
  if(req.method!=="POST")return json({error:"method_not_allowed"},405);
  let b:any;try{b=await parse(req);}catch{return json({error:"invalid_json"},400);}
  if(!isHost(b?.host_id))return json({error:"unknown_host"},400);
  const id:Host=b.host_id;
  if(path==="/worker/enroll") {
    if(typeof b.pair_code!=="string"||b.pair_code.length<40||b.pair_code.length>160
        ||typeof b.worker_hash!=="string"||!/^[a-f0-9]{64}$/.test(b.worker_hash))
        return json({error:"invalid_enrollment"},400);
    const p=await db.from("generic_auto_pairings").update({consumed_at:new Date().toISOString()})
      .eq("host_id",id).eq("code_hash",await digest(b.pair_code)).is("consumed_at",null)
      .gt("expires_at",new Date().toISOString()).select("owner_id").maybeSingle();
    if(p.error||!p.data)return json({error:"invalid_or_expired_pairing"},403);
    const h=await db.from("generic_auto_hosts")
      .update({worker_hash:b.worker_hash,paired_at:new Date().toISOString(),last_seen_at:null,worker_version:"linux-ssh-v1"})
      .eq("host_id",id).eq("owner_id",p.data.owner_id).eq("enabled",true)
      .is("paired_at",null).select("host_id").maybeSingle();
    return h.error||!h.data?json({error:"already_paired_or_unavailable"},409):
       json({ok:true,host_id:id,paired:true});
  }
  const worker=await workerIdentity(req,id);
  if(!worker)return json({error:"worker_authorization_required"},401);
  const now=new Date().toISOString();
  if(path==="/worker/poll") {
    const lane:Lane=b.lane===undefined?"operations":b.lane;
    if(!isLane(lane))return json({error:"invalid_lane"},400);
    const seenField = lane==="control"?"control_seen_at":lane==="development"?"development_seen_at":"operations_seen_at";
    const hb=await db.from("generic_auto_hosts").update({last_seen_at:now,worker_version:"linux-ssh-v1",[seenField]:now})
      .eq("host_id",id).eq("owner_id",worker.owner_id);
    if(hb.error)return json({error:"heartbeat_failed"},500);
    const pending=await db.from("generic_auto_jobs")
      .select("id,kind,command,timeout_seconds,expires_at").eq("owner_id",worker.owner_id)
      .eq("host_id",id).eq("lane",lane).eq("status","queued").gt("expires_at",now)
      .order("created_at",{ascending:true}).limit(1);
    if(pending.error)return json({error:"queue_lookup_failed"},500);
    if(!pending.data?.length)return json({ok:true,job:null});
    const job=pending.data[0],claim=crypto.randomUUID();
    const update=await db.from("generic_auto_jobs").update({status:"running",claim,started_at:now})
      .eq("id",job.id).eq("owner_id",worker.owner_id).eq("host_id",id)
      .eq("status","queued").eq("lane",lane).is("claim",null).select("id").maybeSingle();
    if(update.error)return json({error:"job_claim_failed"},500);
    return json({ok:true,job:update.data?{...job,claim}:null});
  }
  if(path==="/worker/result") {
    if(!isUUID(b?.id)||!isUUID(b?.claim)||!["completed","failed"].includes(b?.status)
       ||(b?.exit_code!==null&&!Number.isInteger(b?.exit_code)))
       return json({error:"invalid_receipt"},400);
    const out=String(b.stdout||"").replace(/\u0000/g,"\ufffd").slice(0,20000);
    const err=String(b.stderr||"").replace(/\u0000/g,"\ufffd").slice(0,20000);
    const res=await db.from("generic_auto_jobs").update({
       status:b.status,stdout:out,stderr:err,exit_code:b.exit_code,finished_at:now})
       .eq("id",b.id).eq("claim",b.claim).eq("owner_id",worker.owner_id)
       .eq("host_id",id).in("status",["running","outcome_unknown"]).select("id").maybeSingle();
    if(res.error)return json({error:"receipt_write_failed"},500);
    if(res.data)return json({ok:true});
    const prev=await db.from("generic_auto_jobs").select("claim,status").eq("id",b.id)
       .eq("host_id",id).eq("owner_id",worker.owner_id).maybeSingle();
    return prev.data?.claim===b.claim&&["completed","failed"].includes(prev.data.status)
        ?json({ok:true,already_recorded:true}):json({error:"job_not_claimed"},409);
  }
  return json({error:"not_found"},404);
}
// Backward-compatible routing for clients with the pre-v1.2.0 frozen MCP tool schema.
// Auth, per-host shell gates, fresh lane heartbeat checks and deduplication remain in enqueue.
// A literal leading comment opts into a lane without requiring an optional MCP input field.
function routeLegacyShellCommand(command:string,selectedLane?:Lane):
  {command:string,lane:Lane}|{error:string} {
  const prefix="# generic-ssh-lane:";
  if(!command.startsWith(prefix))return {command,lane:selectedLane??"operations"};
  const newline=command.indexOf("\n");
  if(newline<0)return {error:"Legacy lane selector requires a newline and a command"};
  const requested=command.slice(prefix.length,newline);
  if(!isLane(requested))return {error:"Unsupported legacy lane selector"};
  if(selectedLane&&selectedLane!==requested)return {error:"Conflicting lane selectors"};
  const stripped=command.slice(newline+1);
  if(!stripped.trim())return {error:"Legacy lane selector requires a nonempty command"};
  return {command:stripped,lane:requested};
}
async function enqueue(uid:string,id:Host,kind:"probe"|"shell",command:string,timeout:number,idempotency_key?:string,lane:Lane="operations") {
  const h=await ownerHost(uid,id),age=h?.last_seen_at?Date.now()-Date.parse(h.last_seen_at):Infinity;
  if(!h?.paired_at||!Number.isFinite(age)||age<0||age>=60000)
    return toolError("Worker offline or unpaired; no job queued");
  const heartbeatField=lane==="control"?"control_seen_at":lane==="development"?"development_seen_at":"operations_seen_at";
  const heartbeat=h[heartbeatField];
  const laneAge=heartbeat?Date.now()-Date.parse(heartbeat):Infinity;
  if(!Number.isFinite(laneAge)||laneAge<0||laneAge>=60000)
    return toolError("Requested SSH lane offline; no job queued");
  if(kind==="shell"&&!h.allow_shell)return toolError("Per-host shell execution disabled");
  // Stable caller-provided key guarantees at most one queue item for retried client requests.
  if(idempotency_key) {
    const prev=await db.from("generic_auto_jobs").select("id,status,created_at,expires_at,kind,command,timeout_seconds,lane")
      .eq("host_id",id).eq("owner_id",uid).eq("idempotency_key",idempotency_key).maybeSingle();
    if(prev.error)return toolError("Queue deduplication lookup unavailable");
    if(prev.data) {
      if(prev.data.kind!==kind||prev.data.command!==command||prev.data.timeout_seconds!==timeout||prev.data.lane!==lane)
        return toolError("Idempotency key already used for different command; request rejected");
      return answer({id:prev.data.id,status:prev.data.status,created_at:prev.data.created_at,
        expires_at:prev.data.expires_at,host_id:id,deduplicated:true,
        lane,note:"Existing job returned; do not re-execute"});
    }
  }
  const active=await db.from("generic_auto_jobs").select("id",{count:"exact",head:true})
    .eq("owner_id",uid).eq("host_id",id).eq("lane",lane).in("status",["queued","running"])
    .gt("expires_at",new Date().toISOString());
  if(active.error)return toolError("Queue admission check unavailable");
  if((active.count||0)>=12)return toolError("Host job queue busy; no new command queued");
  const row=await db.from("generic_auto_jobs").insert({
      host_id:id,owner_id:uid,kind,command,timeout_seconds:timeout,status:"queued",lane,
      idempotency_key:idempotency_key||null})
      .select("id,status,created_at,expires_at").single();
  if(row.error&&idempotency_key) {
    // A simultaneous request may have won the unique index race.
    const prev=await db.from("generic_auto_jobs").select("id,status,created_at,expires_at,kind,command,timeout_seconds,lane")
      .eq("host_id",id).eq("owner_id",uid).eq("idempotency_key",idempotency_key).maybeSingle();
    if(prev.data&&prev.data.kind===kind&&prev.data.command===command&&prev.data.timeout_seconds===timeout&&prev.data.lane===lane)
      return answer({id:prev.data.id,status:prev.data.status,created_at:prev.data.created_at,
        expires_at:prev.data.expires_at,host_id:id,deduplicated:true,
        lane,note:"Existing concurrent job returned; never resubmit"});
  }
  return row.error||!row.data?toolError("Job queue insert failed"):
      answer({...row.data,host_id:id,lane,deduplicated:false,note:"Queued only; read linux_task_status for terminal result"});
}
Deno.serve(async(req:Request)=>{
 try {
   const pathname=new URL(req.url).pathname;
   const path=pathname.replace(/^\/(?:functions\/v1\/)?generic-linux-automator/,"")||"/";
   if(req.method==="GET"&&path==="/health")
     return json({ok:true,service:FN,version:"1.2.1",worker:"independent",shell_default:"disabled"});
   if(req.method==="GET"&&["/.well-known/oauth-protected-resource",
       "/mcp/.well-known/oauth-protected-resource","/mcp/oauth-protected-resource"].includes(path))
     return json({resource:MCP_URL,authorization_servers:[BASE+"/auth/v1"],
       scopes_supported:["email","offline_access"],bearer_methods_supported:["header"]});
   if(path.startsWith("/worker/"))return await workerRoute(req,path);
   if(path!=="/mcp")return json({error:"not_found"},404);
   const owner=await ownerUser(req);
   if("reason" in owner) {
     if(owner.reason==="auth_unavailable")return json({error:"auth_temporarily_unavailable"},503,{"retry-after":"5"});
     return challenge(owner.reason);
   }
   const uid=owner.uid;
   const server=new McpServer({name:"Generic Linux SSH Automator",version:"1.2.1"});
   server.registerTool("linux_host_status",{title:"Linux worker heartbeat",
     description:"Read authenticated Dell/Mac worker heartbeat, no SSH execution",
     inputSchema:{host_id:hostInput},annotations:{readOnlyHint:true}
   },async({host_id})=>{
     const h=await ownerHost(uid,host_id);
     if(!h)return toolError("Host is not authorized");
     const age=h.last_seen_at?Math.floor((Date.now()-Date.parse(h.last_seen_at))/1000):null;
     return answer({host_id,paired:!!h.paired_at,online:typeof age==="number"&&age>=0&&age<60,
        age_seconds:age,worker_version:h.worker_version||null,allow_shell:h.allow_shell,
        checked_at:new Date().toISOString(),lanes:{control:h.control_seen_at,operations:h.operations_seen_at,development:h.development_seen_at},
        source:"dedicated-generic-linux-heartbeat"});
   });
   server.registerTool("linux_pair_host",{title:"Pair Linux worker",description:"Generate single-use 15-minute code for separately authorized Dell or Mac worker",
     inputSchema:{host_id:hostInput},annotations:{readOnlyHint:false}
   },async({host_id})=>{
     const h=await ownerHost(uid,host_id);
     if(!h)return toolError("Host not enrolled");
     if(h.paired_at)return toolError("Host already paired; no automatic re-pair");
     const entropy=crypto.getRandomValues(new Uint8Array(32));
     const code=Array.from(entropy,b=>b.toString(16).padStart(2,"0")).join("");
     const expires_at=new Date(Date.now()+900000).toISOString();
     const put=await db.from("generic_auto_pairings").insert({
       host_id,owner_id:uid,code_hash:await digest(code),expires_at});
     return put.error?toolError("Unable to issue pairing"):answer({
       host_id,pair_code:code,expires_at,one_time:true});
   });
   server.registerTool("linux_probe",{title:"Read-only Linux SSH probe",
     description:"Queue fixed local SSH identity and kernel probe; requires fresh worker",
     inputSchema:{host_id:hostInput,idempotency_key:z.string().regex(/^[A-Za-z0-9_.:-]{8,96}$/).optional()},
     annotations:{readOnlyHint:false}
   },async({host_id,idempotency_key})=>enqueue(uid,host_id,"probe","",20,idempotency_key));
   server.registerTool("linux_ssh_run",{title:"Run scoped Linux SSH command",
     description:"Owner-scoped nonroot shell command; supports lane input and legacy # generic-ssh-lane:<lane> newline prefix; both shell gates required",
     inputSchema:{host_id:hostInput,command:z.string().min(1).max(8192),
       lane:laneInput.optional(),
       timeout_seconds:z.number().int().min(5).max(120).optional(),
       idempotency_key:z.string().regex(/^[A-Za-z0-9_.:-]{8,96}$/).optional()},
     annotations:{readOnlyHint:false,destructiveHint:true,idempotentHint:false}
   },async({host_id,command,timeout_seconds,idempotency_key,lane})=>{
     const routed=routeLegacyShellCommand(command,lane);
     if("error" in routed)return toolError(routed.error);
     return enqueue(uid,host_id,"shell",routed.command,timeout_seconds??30,idempotency_key,routed.lane);
   });
   for(const [name,lane] of [["linux_control_run","control"],["linux_development_run","development"]] as const) {
     server.registerTool(name,{title:lane==="control"?"Priority control SSH lane":"Development SSH lane",
       description:`Run owner-scoped nonroot command on the ${lane} lane; both shell gates required`,
       inputSchema:{host_id:hostInput,command:z.string().min(1).max(8192),
         timeout_seconds:z.number().int().min(5).max(120).optional(),
         idempotency_key:z.string().regex(/^[A-Za-z0-9_.:-]{8,96}$/).optional()},
       annotations:{readOnlyHint:false,destructiveHint:true,idempotentHint:false}
     },async({host_id,command,timeout_seconds,idempotency_key})=>
       enqueue(uid,host_id,"shell",command,timeout_seconds??30,idempotency_key,lane));
   }
   server.registerTool("linux_task_status",{title:"Read Linux SSH task result",
     description:"Read owner-scoped host receipt: queue/running/result/exit code/output",
     inputSchema:{host_id:hostInput,id:z.string().uuid()},annotations:{readOnlyHint:true}
   },async({host_id,id})=>{
     const res=await db.from("generic_auto_jobs")
       .select("id,kind,lane,status,created_at,started_at,finished_at,expires_at,timeout_seconds,stdout,stderr,exit_code")
       .eq("host_id",host_id).eq("owner_id",uid).eq("id",id).maybeSingle();
     if(res.error||!res.data)return toolError("Job not found");
     const pastExpiry=Date.parse(res.data.expires_at)<Date.now();
     const state=res.data.status==="queued"&&pastExpiry?"expired":res.data.status;
     const stale_running=res.data.status==="running"&&pastExpiry;
     const outcome_unknown=res.data.status==="outcome_unknown";
     // Read-only projection. Never auto-requeue an uncertain remote command.
     return answer({...res.data,host_id,status:state,stale_running,outcome_unknown,
       ...((stale_running||outcome_unknown)?{recovery_hint:"Remote outcome uncertain. Do not replay this command; await a matching worker receipt or owner audit."}:{})});
   });
   const transport=new WebStandardStreamableHTTPServerTransport({
     sessionIdGenerator:undefined,enableJsonResponse:true});
   await server.connect(transport);
   try {return await transport.handleRequest(req);}
   finally {await server.close().catch(()=>undefined);}
 }catch(e) {
   console.error("generic-linux-automator error",e instanceof Error?e.stack:e);
   return json({error:"internal_error"},500);
 }
});