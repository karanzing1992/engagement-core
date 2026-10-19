// Candidate only. Reuses Pine's owned OAuth-MCP/outbound-worker approach,
// but uses separate credentials, tables, host IDs and execution authorizations.
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { McpServer } from "npm:@modelcontextprotocol/sdk@1.25.3/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js";
import { createClient } from "npm:@supabase/supabase-js@2.75.0";
import { z } from "npm:zod@4.1.13";

const PROJECT = Deno.env.get("SUPABASE_URL") || "";
const SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const ANON = Deno.env.get("SUPABASE_ANON_KEY") || "";
if (!PROJECT || !SERVICE || !ANON) throw new Error("missing_server_environment");
const db = createClient(PROJECT,SERVICE,{auth:{persistSession:false,autoRefreshToken:false}});
const NAME = "generic-linux-automator", ROOT = PROJECT+"/functions/v1/"+NAME;
const HOSTS = ["dell-linux","mac-linux"] as const;
type Host = typeof HOSTS[number];
const hostSchema = z.enum(HOSTS);
const knownHost = (x:unknown):x is Host => typeof x==="string" && (HOSTS as readonly string[]).includes(x);
const uuid = (x:unknown):x is string => typeof x==="string" &&
 /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(x);
const json=(v:unknown,status=200,extra:HeadersInit={})=>new Response(JSON.stringify(v),{
 status,headers:{"content-type":"application/json","cache-control":"no-store",...extra}});
const ok=(v:unknown)=>({structuredContent:{data:v},content:[{type:"text" as const,text:JSON.stringify(v)}]});
const fail=(s:string)=>({isError:true,content:[{type:"text" as const,text:s}]});
const bearer=(r:Request)=>(r.headers.get("authorization")||"").match(/^Bearer\s+(\S+)$/i)?.[1]||null;
async function sha(s:string){ const hash=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s)));
 return Array.from(hash,b=>b.toString(16).padStart(2,"0")).join(""); }
async function ownerUser(r:Request){
 const t=bearer(r);if(!t)return null;
 const v=await fetch(PROJECT+"/auth/v1/user",{
  headers:{apikey:ANON,authorization:"Bearer "+t},redirect:"manual"});
 if(!v.ok)return null;
 const data=await v.json().catch(()=>null);
 if(typeof data?.id!=="string")return null;
 const m=await db.from("generic_auto_members").select("user_id").eq("user_id",data.id)
  .eq("role","owner").eq("enabled",true).maybeSingle();
 return m.error||!m.data?null:data.id as string;
}
async function host(uid:string,id:Host){
 const {data,error}=await db.from("generic_auto_hosts")
  .select("host_id,owner_id,paired_at,last_seen_at,worker_version,enabled,allow_shell")
  .eq("host_id",id).eq("owner_id",uid).eq("enabled",true).maybeSingle();
 return error?null:data;
}
async function worker(r:Request,id:Host){
 const t=bearer(r);if(!t||t.length<40||t.length>256)return null;
 const {data,error}=await db.from("generic_auto_hosts").select("owner_id,host_id")
  .eq("host_id",id).eq("worker_hash",await sha(t)).eq("enabled",true).maybeSingle();
 return error?null:data;
}
async function body(r:Request){
 const txt=await r.text();if(txt.length>100000)throw new Error("request_too_large");
 return JSON.parse(txt);
}
async function workerRequest(req:Request,path:string){
 if(req.method!=="POST")return json({error:"method_not_allowed"},405);
 let b:any;try{b=await body(req);}catch{return json({error:"bad_json"},400);}
 if(!knownHost(b?.host_id))return json({error:"bad_host"},400);
 const id:Host=b.host_id;
 if(path==="/worker/enroll"){
   if(typeof b.pair_code!=="string"||b.pair_code.length<40||b.pair_code.length>160||
     typeof b.worker_hash!=="string"||!/^[a-f0-9]{64}$/.test(b.worker_hash))
     return json({error:"bad_enrollment"},400);
   const pair=await db.from("generic_auto_pairings")
    .update({consumed_at:new Date().toISOString()}).eq("host_id",id)
    .eq("code_hash",await sha(b.pair_code)).is("consumed_at",null)
    .gt("expires_at",new Date().toISOString()).select("owner_id").maybeSingle();
   if(pair.error||!pair.data)return json({error:"expired_or_invalid_pairing"},403);
   const enrolled=await db.from("generic_auto_hosts")
    .update({worker_hash:b.worker_hash,paired_at:new Date().toISOString(),
       last_seen_at:null,worker_version:"linux-ssh-worker-v1"})
    .eq("host_id",id).eq("owner_id",pair.data.owner_id).eq("enabled",true)
    .is("paired_at",null).select("host_id").maybeSingle();
   if(enrolled.error||!enrolled.data)return json({error:"pair_failed_or_already_paired"},409);
   return json({ok:true,host_id:id,paired:true});
 }
 const w=await worker(req,id);if(!w)return json({error:"worker_unauthorized"},401);
 const now=new Date().toISOString();
 if(path==="/worker/poll"){
   const heartbeat=await db.from("generic_auto_hosts")
    .update({last_seen_at:now,worker_version:"linux-ssh-worker-v1"})
    .eq("host_id",id).eq("owner_id",w.owner_id);
   if(heartbeat.error)return json({error:"heartbeat_failed"},500);
   const queue=await db.from("generic_auto_jobs")
    .select("id,kind,command,timeout_seconds,expires_at")
    .eq("owner_id",w.owner_id).eq("host_id",id).eq("status","queued")
    .gt("expires_at",now).order("created_at",{ascending:true}).limit(1);
   if(queue.error)return json({error:"queue_failed"},500);
   if(!queue.data?.length)return json({ok:true,job:null});
   const job=queue.data[0],claim=crypto.randomUUID();
   const started=await db.from("generic_auto_jobs")
    .update({status:"running",claim,started_at:now})
    .eq("id",job.id).eq("owner_id",w.owner_id).eq("host_id",id)
    .eq("status","queued").is("claim",null).select("id").maybeSingle();
   if(started.error)return json({error:"claim_failed"},500);
   return json({ok:true,job:started.data?{...job,claim}:null});
 }
 if(path==="/worker/result"){
   if(!uuid(b.id)||!uuid(b.claim)||!["completed","failed"].includes(b.status)||
      (b.exit_code!==null&&!Number.isInteger(b.exit_code)))
       return json({error:"bad_result"},400);
   const out=String(b.stdout||"").replace(/\u0000/g,"\ufffd").slice(0,20000);
   const err=String(b.stderr||"").replace(/\u0000/g,"\ufffd").slice(0,20000);
   const sent=await db.from("generic_auto_jobs")
    .update({status:b.status,exit_code:b.exit_code,stdout:out,stderr:err,finished_at:now})
    .eq("id",b.id).eq("claim",b.claim).eq("host_id",id).eq("owner_id",w.owner_id)
    .eq("status","running").select("id").maybeSingle();
   if(sent.error)return json({error:"result_write_failed"},500);
   if(sent.data)return json({ok:true});
   const old=await db.from("generic_auto_jobs").select("claim,status").eq("id",b.id)
    .eq("host_id",id).eq("owner_id",w.owner_id).maybeSingle();
   return old.data?.claim===b.claim&&["completed","failed"].includes(old.data.status)
    ?json({ok:true,already_recorded:true}):json({error:"invalid_job_claim"},409);
 }
 return json({error:"not_found"},404);
}
async function enqueue(uid:string,id:Host,kind:"probe"|"shell",command:string,timeout:number){
 const h=await host(uid,id),age=h?.last_seen_at?Date.now()-Date.parse(h.last_seen_at):Infinity;
 if(!h?.paired_at||!Number.isFinite(age)||age<0||age>=60000)
   return fail("Host offline or not paired; nothing queued");
 if(kind==="shell"&&!h.allow_shell)return fail("Shell execution has not been enabled");
 const newjob=await db.from("generic_auto_jobs")
  .insert({owner_id:uid,host_id:id,kind,command,timeout_seconds:timeout,status:"queued"})
  .select("id,status,created_at,expires_at").single();
 return newjob.error||!newjob.data?fail("Could not queue job"):
  ok({...newjob.data,host_id:id,note:"Queued only; read terminal receipt"});
}
Deno.serve(async(req:Request)=>{
 try{
  const path=new URL(req.url).pathname.replace(/^\/(?:functions\/v1\/)?generic-linux-automator/,"")||"/";
  if(req.method==="GET"&&path==="/health")
    return json({ok:true,service:NAME,version:"candidate-1",mode:"separate"});
  if(req.method==="GET"&&["/.well-known/oauth-protected-resource",
     "/mcp/.well-known/oauth-protected-resource"].includes(path))
    return json({resource:ROOT+"/mcp",authorization_servers:[PROJECT+"/auth/v1"],
      scopes_supported:["email","offline_access"],bearer_methods_supported:["header"]});
  if(path.startsWith("/worker/"))return await workerRequest(req,path);
  if(path!=="/mcp")return json({error:"not_found"},404);
  const uid=await ownerUser(req);
  if(!uid)return json({error:"auth_required"},401,{"www-authenticate":
    'Bearer resource_metadata="'+ROOT+'/.well-known/oauth-protected-resource", scope="email offline_access"'});
  const server=new McpServer({name:"Generic Linux Automator",version:"0.1.0"});
  server.registerTool("linux_host_status",{
    title:"Linux host heartbeat",description:"Check enrollment and fresh worker heartbeat; does not execute SSH.",
    inputSchema:{host_id:hostSchema},annotations:{readOnlyHint:true}
  },async({host_id})=>{
    const h=await host(uid,host_id);
    if(!h)return fail("Host not registered");
    const age=h.last_seen_at?Math.floor((Date.now()-Date.parse(h.last_seen_at))/1000):null;
    return ok({host_id,paired:!!h.paired_at,online:typeof age==="number"&&age>=0&&age<60,
      age_seconds:age,checked_at:new Date().toISOString(),worker_version:h.worker_version||null,
      allow_shell:h.allow_shell,source:"dedicated-generic-worker-heartbeat"});
  });
  server.registerTool("linux_pair_host",{
    title:"Pair one Linux worker",description:"Owner-only, one-time 15-minute enrollment code; never enter on another host.",
    inputSchema:{host_id:hostSchema},annotations:{readOnlyHint:false}
  },async({host_id})=>{
    const h=await host(uid,host_id);
    if(!h||h.paired_at)return fail("Host missing, disabled or already paired");
    const random=crypto.getRandomValues(new Uint8Array(32));
    const code=Array.from(random,b=>b.toString(16).padStart(2,"0")).join("");
    const expires_at=new Date(Date.now()+900000).toISOString();
    const p=await db.from("generic_auto_pairings")
      .insert({host_id,owner_id:uid,code_hash:await sha(code),expires_at});
    return p.error?fail("Unable to pair"):ok({host_id,pair_code:code,expires_at,one_time:true});
  });
  server.registerTool("linux_probe",{
    title:"Read-only SSH identity probe",description:"Queue fixed identity, kernel and hostname probe.",
    inputSchema:{host_id:hostSchema},annotations:{readOnlyHint:false}
  },async({host_id})=>enqueue(uid,host_id,"probe","",20));
  server.registerTool("linux_ssh_run",{
    title:"Run scoped Linux SSH command",description:"Disabled until both gateway and local-host authorization are enabled.",
    inputSchema:{host_id:hostSchema,command:z.string().min(1).max(8192),
      timeout_seconds:z.number().int().min(5).max(120).optional()},
    annotations:{readOnlyHint:false,destructiveHint:true,idempotentHint:false}
  },async({host_id,command,timeout_seconds})=>
    enqueue(uid,host_id,"shell",command,timeout_seconds??30));
  server.registerTool("linux_task_status",{
    title:"Read SSH result",description:"Return queue state, terminal status, exit code and sanitized output.",
    inputSchema:{host_id:hostSchema,id:z.string().uuid()},annotations:{readOnlyHint:true}
  },async({host_id,id})=>{
    const j=await db.from("generic_auto_jobs")
      .select("id,kind,status,created_at,started_at,finished_at,expires_at,stdout,stderr,exit_code")
      .eq("id",id).eq("host_id",host_id).eq("owner_id",uid).maybeSingle();
    if(j.error||!j.data)return fail("Job not found for this owner and host");
    return ok({...j.data,host_id,status:j.data.status==="queued"&&
      Date.parse(j.data.expires_at)<Date.now()?"expired":j.data.status});
  });
  const transport=new WebStandardStreamableHTTPServerTransport({
     sessionIdGenerator:undefined,enableJsonResponse:true});
  await server.connect(transport);
  try{return await transport.handleRequest(req);}
  finally{await server.close().catch(()=>undefined);}
 }catch(e){
   console.error("AUTOMATOR_GATEWAY_ERROR",e instanceof Error?e.name:"unknown");
   return json({error:"internal_error"},500);
 }
});
