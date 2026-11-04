// DeluluTech AI Reel Engine 1.0 owner-only PWA API, synthetic data only.
const ALLOWED_ORIGINS=new Set(["https://reel.delulutech.in","https://delulutech-ai-reel-engine-v1.pages.dev"]);
const CODE_PREFIX="Bearer nk-";
function j(v,status=200,h={}){return new Response(JSON.stringify(v),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff","referrer-policy":"no-referrer",...h}})}
function cors(o){return ALLOWED_ORIGINS.has(o)?{"access-control-allow-origin":o,"vary":"Origin","access-control-allow-headers":"Authorization,Content-Type,X-Chunk-SHA256","access-control-allow-methods":"POST,GET,PUT,OPTIONS","access-control-max-age":"600"}:{}}
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

/* Private real-media draft MVP: all endpoints run behind the existing owner
 * credential and exact Origin allowlist. 4 MiB KV chunks; 80 MiB source cap.
 * No public object addresses, no raw source in GitHub, no public distribution.
 */
const MAD_CHUNK=4*1024*1024, MAD_MAX=80*1024*1024, MAD_TTL=172800;
const MAD_ID=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const MAD_UPLOAD=/^upload-([a-f0-9-]{36})$/, MAD_JOB=/^madmedia-([a-f0-9-]{36})$/;
const MEDIA_MIMES=new Set(["video/mp4","video/quicktime","video/webm"]);
function validMediaId(str,kind){return typeof str==="string"&&str.startsWith(kind)&&MAD_ID.test(str.slice(kind.length))}
function digestHex(b){return hex(new Uint8Array(b))}
async function hashBytes(b){return digestHex(await crypto.subtle.digest("SHA-256",b))}
function privateKey(part,id,index){return "private/mad-v1/"+part+"/"+id+"/"+index}
function mediaError(message,status=400){return j({error:{message}},status)}
async function doMedia(request,env,url){
 const p=url.pathname.split("/").filter(Boolean);
 if(p[0]!=="v1"||p[1]!=="media")return mediaError("Route not found",404);
 if(!env.MEDIA_KV)return mediaError("Private media storage unavailable",503);
 const now=Math.floor(Date.now()/1000);
 if(p[2]==="uploads"&&p.length===3&&request.method==="POST"){
   let m;try{m=await request.json()}catch{return mediaError("Invalid upload metadata")}
   if(!m||typeof m!=="object"||typeof m.name!=="string"||!MEDIA_MIMES.has(m.mime)||!Number.isInteger(m.size)||m.size<1024||m.size>MAD_MAX||!(/^[a-f0-9]{64}$/.test(m.sha256||"")))return mediaError("Invalid video metadata, format or size (maximum 80 MiB)");
   const ext=(m.name.split(".").pop()||"").toLowerCase(),exts={"video/mp4":["mp4"],"video/quicktime":["mov"],"video/webm":["webm"]};
   if(!exts[m.mime].includes(ext)||m.name.length>120||/[/\\\x00-\x1f]/.test(m.name))return mediaError("Unsupported file name or format");
   const active=await env.DB.prepare("SELECT COUNT(*) AS n FROM mad_v1_uploads WHERE state='uploading' AND expires_at>?").bind(now).first();
   if(active.n>=2)return mediaError("Two uploads are already in progress",429);
   const id="upload-"+crypto.randomUUID(),count=Math.ceil(m.size/MAD_CHUNK);
   await env.DB.prepare("INSERT INTO mad_v1_uploads(id,owner,file_name,mime,bytes,sha256,chunk_count,created_at,expires_at) VALUES (?,'owner',?,?,?,?,?,?,?)").bind(id,m.name,m.mime,m.size,m.sha256,count,now,now+MAD_TTL).run();
   return j({upload_id:id,chunk_bytes:MAD_CHUNK,chunks:count,max_bytes:MAD_MAX,expires_after_hours:48},201);
 }
 const upload=p[3];
 if(p[2]==="uploads"&&validMediaId(upload,"upload-")){
   const rec=await env.DB.prepare("SELECT * FROM mad_v1_uploads WHERE id=? AND expires_at>?").bind(upload,now).first();
   if(!rec)return mediaError("Upload not found or expired",404);
   if(p.length===4&&request.method==="GET"){
     const row=await env.DB.prepare("SELECT COUNT(*) AS n FROM mad_v1_source_chunks WHERE upload_id=?").bind(upload).first();
     return j({upload_id:upload,state:rec.state,received_chunks:row.n,total_chunks:rec.chunk_count,expires_at:rec.expires_at});
   }
   if(p.length===6&&p[4]==="chunks"&&request.method==="PUT"){
     if(rec.state!=="uploading")return mediaError("Upload finalized",409);
     const i=Number(p[5]);if(!Number.isInteger(i)||i<0||i>=rec.chunk_count)return mediaError("Invalid chunk index");
     const expected=Math.min(MAD_CHUNK,rec.bytes-i*MAD_CHUNK),rawLength=request.headers.get("content-length");
     const declared=rawLength===null?null:Number(rawLength);
     if(declared!==null&&(!Number.isInteger(declared)||declared!==expected))return mediaError("Invalid Content-Length",413);
     const expectedHash=request.headers.get("x-chunk-sha256")||"";
     if(!/^[a-f0-9]{64}$/.test(expectedHash))return mediaError("Missing SHA256",422);
     const existing=await env.DB.prepare("SELECT sha256 FROM mad_v1_source_chunks WHERE upload_id=? AND chunk_index=?").bind(upload,i).first();
     if(existing)return existing.sha256===expectedHash?j({chunk_index:i,already_received:true}):mediaError("Chunk conflict",409);
     const reader=request.body?.getReader();
     if(!reader)return mediaError("Missing chunk body",400);
     const parts=[];let received=0;
     while(true){
       const part=await reader.read();if(part.done)break;
       received+=part.value.byteLength;
       if(received>expected){await reader.cancel();return mediaError("Chunk exceeds declared size",413)}
       parts.push(part.value);
     }
     if(received!==expected)return mediaError("Chunk size mismatch",413);
     const bytes=new Uint8Array(expected);let at=0;
     for(const part of parts){bytes.set(part,at);at+=part.byteLength}
     const sha=await hashBytes(bytes);
     if(sha!==expectedHash)return mediaError("Chunk integrity check failed",422);
     await env.MEDIA_KV.put(privateKey("source",upload,i),bytes,{expirationTtl:MAD_TTL});
     const insert=await env.DB.prepare("INSERT INTO mad_v1_source_chunks(upload_id,chunk_index,sha256,bytes) VALUES (?,?,?,?) ON CONFLICT(upload_id,chunk_index) DO NOTHING").bind(upload,i,sha,expected).run();
     if(!insert.meta?.changes)return mediaError("Chunk acceptance race; retry after status",409);
     return j({chunk_index:i,bytes:expected,sha256:sha});
   }
   if(p.length===5&&p[4]==="complete"&&request.method==="POST"){
     const row=await env.DB.prepare("SELECT COUNT(*) AS n,COALESCE(SUM(bytes),0) AS total FROM mad_v1_source_chunks WHERE upload_id=?").bind(upload).first();
     if(row.n!==rec.chunk_count||row.total!==rec.bytes)return mediaError("Upload incomplete or size mismatch",409);
     await env.DB.prepare("UPDATE mad_v1_uploads SET state='complete' WHERE id=? AND state='uploading'").bind(upload).run();
     return j({upload_id:upload,state:"complete",bytes:rec.bytes,sha256:rec.sha256});
   }
 }
 if(p[2]==="jobs"&&p.length===3&&request.method==="POST"){
   let q;try{q=await request.json()}catch{return mediaError("Invalid job data")}
   if(!validMediaId(q?.upload_id,"upload-")||!cleanPrompt(q?.prompt)||q.rights_confirmed!==true||q.people_consent!==true||q.external_ai_approved!==true)return mediaError("Video ownership, recognizable-person consent, external AI approval, and a 12–600 character creative brief are required");
   const u=await env.DB.prepare("SELECT id FROM mad_v1_uploads WHERE id=? AND state='complete' AND expires_at>?").bind(q.upload_id,now).first();
   if(!u)return mediaError("Upload not finalized or expired",409);
   const id="madmedia-"+crypto.randomUUID();
   try{
     await env.DB.prepare("INSERT INTO mad_v1_media_jobs(job_id,upload_id,prompt,rights_confirmed,people_consent,external_ai_approved,state,created_at,updated_at,expires_at) VALUES (?,?,?,1,1,1,'queued',?,?,?)").bind(id,q.upload_id,q.prompt.trim(),now,now,now+MAD_TTL).run();
   }catch{return mediaError("Another render is currently active; wait for it to finish",409)}
   return j({job_id:id,state:"queued",review_only:true,video_output:"1080x1920 h264/aac",note:"Private review draft; not quality or rights certified"},201);
 }
 if(p[2]==="jobs"&&validMediaId(p[3],"madmedia-")){
   const id=p[3];
   const job=await env.DB.prepare("SELECT job_id,state,created_at,updated_at,expires_at,error_code,result_bytes,result_sha256,result_chunks,result_receipt FROM mad_v1_media_jobs WHERE job_id=?").bind(id).first();
   if(!job)return mediaError("Job not found",404);
   if(p.length===4&&request.method==="GET")return j({job_id:id,state:job.state,error_code:job.error_code,result_available:job.state==="review_ready"&&job.expires_at>now,output_bytes:job.state==="review_ready"?job.result_bytes:null,sha256:job.state==="review_ready"?job.result_sha256:null,expires_at:job.expires_at,review_only:true});
   if(p.length===5&&p[4]==="receipt"&&request.method==="GET"){
     return job.state==="review_ready"?j({job_id:id,receipt:JSON.parse(job.result_receipt||"{}"),review_only:true}):mediaError("Draft not ready",409);
   }
   if(p.length===5&&p[4]==="preview"&&request.method==="GET"){
     if(job.state!=="review_ready"||job.expires_at<=now||!Number.isInteger(job.result_chunks)||job.result_chunks<1)return mediaError("Preview not available",409);
     let i=0;
     const stream=new ReadableStream({async pull(controller){
       if(i>=job.result_chunks){controller.close();return}
       try{
         const b=await env.MEDIA_KV.get(privateKey("output",id,i),"arrayBuffer");
         if(!b){controller.error(new Error("Expired private media chunk"));return}
         controller.enqueue(new Uint8Array(b));i++;
       }catch{controller.error(new Error("Private preview unavailable"))}
     }});
     return new Response(stream,{headers:{"content-type":"video/mp4","content-disposition":'attachment; filename="AI-Reel-Engine-1.0-draft.mp4"',"content-length":String(job.result_bytes),"cache-control":"private, no-store","x-content-type-options":"nosniff","accept-ranges":"none"}});
   }
 }
 return mediaError("Media route not found",404);
}

export default {
 async fetch(request,env){
  const url=new URL(request.url),origin=request.headers.get("origin")||"";
  if(url.pathname==="/health"&&request.method==="GET")return j({service:"AI Reel Engine 1.0 by DeluluTech",ready:Boolean(env.DB&&env.MAD_OWNER_CODE_SHA256),mode:"owner-private-video-draft",real_media_enabled:false,private_review_upload_ready:Boolean(env.MEDIA_KV),model_secrets:"GitHub Actions only"});
  const headers=cors(origin);
  if(request.method==="OPTIONS")return ALLOWED_ORIGINS.has(origin)?new Response(null,{status:204,headers}):j({error:"Forbidden origin"},403);
  if(!env.DB)return j({error:"Database unavailable"},503,headers);
  if(!ALLOWED_ORIGINS.has(origin))return j({error:"Forbidden origin"},403,headers);
  if(!await authorized(request,env))return j({error:{message:"Invalid access code"}},401,headers);
  try{
   let response;
   if(url.pathname.startsWith("/v1/media/"))response=await doMedia(request,env,url);
   else if(url.pathname==="/v1/chat/completions"&&request.method==="POST")response=await handleChat(request,env);
   else if(url.pathname==="/v1/models"&&request.method==="GET")response=j({object:"list",data:[{id:"mad-v5",object:"model",owned_by:"delulutech"}]});
   else response=j({error:{message:"Not found"}},404);
   for(const [k,v] of Object.entries(headers))response.headers.set(k,v);
   return response;
  }catch{return j({error:{message:"Service unavailable"}},503,headers)}
 }
};