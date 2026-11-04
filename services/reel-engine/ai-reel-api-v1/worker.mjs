// DeluluTech AI Reel Engine 1.0 owner-only PWA API, synthetic data only.
const ALLOWED_ORIGINS=new Set(["https://reel.delulutech.in","https://delulutech-ai-reel-engine-v1.pages.dev"]);
const CODE_PREFIX="Bearer nk-";
function j(v,status=200,h={}){return new Response(JSON.stringify(v),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff","referrer-policy":"no-referrer",...h}})}
function cors(o){return ALLOWED_ORIGINS.has(o)?{"access-control-allow-origin":o,"vary":"Origin","access-control-allow-headers":"Authorization,Content-Type","access-control-allow-methods":"POST,GET,OPTIONS","access-control-max-age":"600"}:{}}
function equal(a,b){if(!a||!b||a.length!==b.length)return false;let n=0;for(let i=0;i<a.length;i++)n|=a.charCodeAt(i)^b.charCodeAt(i);return n===0}
function hex(b){return [...b].map(v=>v.toString(16).padStart(2,"0")).join("")}
async function authorized(r,e){
  if(!e.MAD_OWNER_CODE_SHA256||!/^[a-f0-9]{64}$/.test(e.MAD_OWNER_CODE_SHA256))return false;
  const a=r.headers.get("Authorization")||"";
  if(!a.startsWith(CODE_PREFIX))return false;
  const token=a.slice(CODE_PREFIX.length);
  if(token.length<30||token.length>120||!/^[a-zA-Z0-9_-]+$/.test(token))return false;
  const hash=hex(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(token))));
  return equal(hash,e.MAD_OWNER_CODE_SHA256);
}
function validId(id){return typeof id==="string"&&/^madapp-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(id)}
function cleanPrompt(x){return typeof x==="string"&&x.length>=12&&x.length<=600&&!/[\x00-\x1f]|https?:\/\/|data:|github_pat_|ghp_|sk-[A-Za-z0-9]{12}/i.test(x)}
function completion(s,stream){
  if(!stream)return j({id:"mad-v1",object:"chat.completion",model:"mad-v5",choices:[{index:0,message:{role:"assistant",content:s},finish_reason:"stop"}],usage:{prompt_tokens:0,completion_tokens:0,total_tokens:0}});
  const first=JSON.stringify({id:"mad-v1",object:"chat.completion.chunk",model:"mad-v5",choices:[{index:0,delta:{role:"assistant",content:s},finish_reason:null}]});
  const last=JSON.stringify({id:"mad-v1",object:"chat.completion.chunk",model:"mad-v5",choices:[{index:0,delta:{},finish_reason:"stop"}]});
  return new Response("data: "+first+"\n\n"+"data: "+last+"\n\n"+"data: [DONE]\n\n",{headers:{"content-type":"text/event-stream; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
}
async function lastJob(db,id){
 const sql=id?"SELECT job_id,state,attempts,result_run,result_sha256,created_at,updated_at FROM mad_v5_jobs WHERE job_id=? AND job_id LIKE 'madapp-%' LIMIT 1":"SELECT job_id,state,attempts,result_run,result_sha256,created_at,updated_at FROM mad_v5_jobs WHERE job_id LIKE 'madapp-%' ORDER BY created_at DESC LIMIT 1";
 return id?db.prepare(sql).bind(id).first():db.prepare(sql).first();
}
async function handleChat(request,env){
 const raw=await request.text();if(raw.length>12000)return j({error:{message:"Request too large"}},413);
 let data;try{data=JSON.parse(raw)}catch{return j({error:{message:"Invalid JSON"}},400)}
 if(!Array.isArray(data.messages)||data.messages.length>40)return j({error:{message:"Invalid messages"}},400);
 const last=[...data.messages].reverse().find(m=>m?.role==="user");const prompt=last?.content;
 if(typeof prompt!=="string")return j({error:{message:"Text-only synthetic requests in V1"}},400);
 const trimmed=prompt.trim();
 if(/^(?:status|check|progress|my job|queue)(?:\s|$)/i.test(trimmed)){
   const match=trimmed.match(/madapp-[a-f0-9-]{36}/i);
   const requested=match?.[0]?.toLowerCase()||null;
   if(requested&&!validId(requested))return j({error:{message:"Invalid job ID"}},400);
   const job=await lastJob(env.DB,requested);
   if(!job)return completion("No matching AI Reel Engine job was found.",data.stream===true);
   return completion("Job "+job.job_id+": **"+job.state+"**. Attempts: "+job.attempts+". "+
    (job.result_run?"Technical run: "+job.result_run+". ":"")+
    (job.state==="queued"?"The GitHub worker checks periodically; exact start times are not yet available. ":"")+
    (job.state==="passed"?"Synthetic-only diagnostic complete; real guest media not yet enabled.":""),data.stream===true);
 }
 if(!cleanPrompt(trimmed))return j({error:{message:"Phase 1 accepts a 12–600 character text brief only. URLs, uploaded footage and secrets are not accepted."}},400);
 const now=Math.floor(Date.now()/1000),id="madapp-"+crypto.randomUUID();
 try{
  const result=await env.DB.prepare("INSERT INTO mad_v5_jobs (job_id,project_id,prompt,mode,profile,state,created_at,updated_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)")
   .bind(id,"moksha_wellness",trimmed,"live","synthetic_test","queued",now,now,now+86400).run();
  if(!result.success)return j({error:{message:"Queue write rejected"}},503);
 }catch{
   const existing=await lastJob(env.DB,null);
   if(existing&&["queued","claimed"].includes(existing.state))return completion("An AI Reel Engine job is already active: "+existing.job_id+" ("+existing.state+"). Send status to check it before submitting another.",data.stream===true);
   return j({error:{message:"Queue temporarily unavailable"}},503);
 }
 return completion("AI Reel Engine 1.0 accepted your creative brief. Job ID: "+id+". State: queued. Mode: synthetic V5 diagnostic (not real guest video editing). Send status or status followed by your job ID to check progress. Rendering is asynchronous; the existing GitHub Actions worker polls periodically. Accurate wait estimates arrive in Phase 2.",data.stream===true);
}
export default {
 async fetch(request,env){
  const url=new URL(request.url),origin=request.headers.get("origin")||"";
  if(url.pathname==="/health"&&request.method==="GET")return j({service:"AI Reel Engine 1.0 by DeluluTech",ready:Boolean(env.DB&&env.MAD_OWNER_CODE_SHA256),mode:"owner-only synthetic pilot",real_media_enabled:false,model_secrets:"GitHub Actions only"});
  const headers=cors(origin);
  if(request.method==="OPTIONS")return ALLOWED_ORIGINS.has(origin)?new Response(null,{status:204,headers}):j({error:"Forbidden origin"},403);
  if(!env.DB)return j({error:"Database unavailable"},503,headers);
  if(!ALLOWED_ORIGINS.has(origin))return j({error:"Forbidden origin"},403,headers);
  if(!await authorized(request,env))return j({error:{message:"Invalid access code"}},401,headers);
  try{
   let response;
   if(url.pathname==="/v1/chat/completions"&&request.method==="POST")response=await handleChat(request,env);
   else if(url.pathname==="/v1/models"&&request.method==="GET")response=j({object:"list",data:[{id:"mad-v5",object:"model",owned_by:"delulutech"}]});
   else response=j({error:{message:"Not found"}},404);
   for(const [k,v] of Object.entries(headers))response.headers.set(k,v);
   return response;
  }catch{return j({error:{message:"Service unavailable"}},503,headers)}
 }
};