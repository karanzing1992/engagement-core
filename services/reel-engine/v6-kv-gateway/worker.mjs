import {seedSynthetic} from "./synthetic_seed.mjs";
// MAD V6 Cloudflare KV media gateway, independent of V5 routes.
// Owner PWA + signed GitHub OIDC: no GitHub vault credential or model keys.
const ORIGINS=new Set(["https://mad-v6-owner-private-beta.pages.dev"]);
const PREVIEW=/^https:\/\/[a-z0-9-]+\.mad-v6-owner-private-beta\.pages\.dev$/;
const JOB=/^v6job-[a-f0-9]{32}$/;
const SHA=/^[a-f0-9]{64}$/;
const CHUNK=4*1024*1024,MAX=80*1024*1024,RENDER_WINDOW=86400,DELIVERY_WINDOW=1800;
const ENGINE_REPO="karanzing1992/engagement-core",REPO_ID="1403281267",OWNER_ID="30191163";
const WORKFLOW="mad-v6-kv-filmcraft.yml";
const OIDC_AUD="mad-v6-cloudflare-kv/1",OIDC_ISS="https://token.actions.githubusercontent.com";
const OIDC_WF=ENGINE_REPO+"/.github/workflows/"+WORKFLOW+"@refs/heads/main";
const KEY=(type,id,i)=>"private/mad-v6/"+type+"/"+id+"/"+i;
const TIME=()=>Math.floor(Date.now()/1000);
const json=(d,s=200)=>new Response(JSON.stringify(d),{status:s,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"}});
const error=(s,n=400)=>json({error:{message:s}},n);
const cors=o=>ORIGINS.has(o)||PREVIEW.test(o)?{"access-control-allow-origin":o,"vary":"Origin","access-control-allow-methods":"GET,POST,PUT,OPTIONS","access-control-allow-headers":"Authorization,Content-Type,X-Chunk-SHA256,X-V6-Claim,Range","access-control-expose-headers":"Content-Length,Content-Range,Accept-Ranges","access-control-max-age":"120"}:null;
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),b=>b.toString(16).padStart(2,"0")).join("");
const b64=s=>Uint8Array.from(atob(s.replace(/-/g,"+").replace(/_/g,"/")+"=".repeat((4-s.length%4)%4)),x=>x.charCodeAt(0));
function parseJWT(s){if(typeof s!=="string"||!s||s.length>8000||!/^[A-Za-z0-9_.-]+$/.test(s))return null;const t=s.split(".");if(t.length!==3)return null;try{return {body:JSON.parse(new TextDecoder().decode(b64(t[1]))),head:JSON.parse(new TextDecoder().decode(b64(t[0]))),parts:t}}catch{return null}}
async function verifyGitHub(req){
 const header=req.headers.get("authorization")||"";
 if(!header.startsWith("Bearer "))return false;
 const x=parseJWT(header.slice(7));
 if(!x||x.head.alg!=="RS256"||typeof x.head.kid!=="string"||x.head.kid.length>128)return false;
 const c=x.body,n=TIME();
 if(c.iss!==OIDC_ISS||c.aud!==OIDC_AUD||c.repository!==ENGINE_REPO||String(c.repository_id)!==REPO_ID||
    String(c.repository_owner_id)!==OWNER_ID||c.ref!=="refs/heads/main"||c.workflow_ref!==OIDC_WF||
    !(c.event_name==="workflow_dispatch"||(c.event_name==="issues"&&String(c.actor_id)===OWNER_ID))||c.runner_environment!=="github-hosted"||
    !Number.isFinite(c.iat)||!Number.isFinite(c.exp)||!Number.isFinite(c.nbf)||
    c.iat>n+30||c.nbf>n+30||c.iat<n-1200||c.exp<=n||c.exp-c.iat>1200||
    !/^[0-9]{5,15}$/.test(String(c.run_id)))return false;
 try{
   const response=await fetch(OIDC_ISS+"/.well-known/jwks",{headers:{"accept":"application/json"},redirect:"manual"});
   if(response.status!==200)return false;
   const keys=(await response.json()).keys;
   const jwk=Array.isArray(keys)?keys.find(k=>k.kid===x.head.kid&&k.kty==="RSA"&&k.n&&k.e):null;
   if(!jwk)return false;
   const key=await crypto.subtle.importKey("jwk",{kty:"RSA",n:jwk.n,e:jwk.e,alg:"RS256",ext:true},
     {name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
   return (await crypto.subtle.verify("RSASSA-PKCS1-v1_5",key,b64(x.parts[2]),
     new TextEncoder().encode(x.parts[0]+"."+x.parts[1])))?c:false;
 }catch{return false}
}
async function owner(req,e){
 const token=req.headers.get("authorization")||"";
 if(!/^Bearer nk-[A-Za-z0-9_-]{30,120}$/.test(token))return false;
 if(!e.PROJECT_AUTH)return false;
 try{
  const result=await e.PROJECT_AUTH.fetch(new Request("https://reel-projects.delulutech.in/v1/projects",
   {headers:{"Authorization":token,"Origin":"https://reel.delulutech.in"}}));
  return result.ok;
 }catch{return false}
}
async function projectProxy(req,e,u){
 if(!/^\/v1\/projects(?:\/[a-zA-Z0-9_-]+(?:\/(?:assets|messages|versions))?)?$/.test(u.pathname))return error("Project route not allowed",404);
 if(!["GET","POST","PATCH"].includes(req.method))return error("Method not allowed",405);
 const body=req.method==="GET"?undefined:await req.text();
 if(body?.length>20000)return error("Project request too long",413);
 const t=await e.PROJECT_AUTH.fetch(new Request("https://reel-projects.delulutech.in"+u.pathname+u.search,
  {method:req.method,headers:{"Authorization":req.headers.get("authorization")||"","Origin":"https://reel.delulutech.in",
  "Content-Type":"application/json"},body}));
 const contentType=t.headers.get("content-type")||"";
 if(!contentType.toLowerCase().includes("application/json"))return error("Unexpected internal project response",502);
 return new Response(t.body,{status:t.status,headers:{"content-type":"application/json","cache-control":"no-store"}});
}
async function getJob(e,id){return e.DB.prepare("SELECT * FROM mad_v6_kv_jobs WHERE job_id=?").bind(id).first()}
async function chunks(e,id,kind){return e.DB.prepare("SELECT idx,bytes,sha256 FROM mad_v6_kv_parts WHERE job_id=? AND kind=? ORDER BY idx").bind(id,kind).all()}
async function makeUpload(req,e){
 let b;try{b=await req.json()}catch{return error("Invalid upload JSON")}
 const name=b?.name||"",mime=b?.mime||"",size=b?.size,ext={"video/mp4":".mp4","video/quicktime":".mov","video/webm":".webm"}[mime];
 if(!ext||!name.endsWith(ext)||name.length>120||/[/\\\x00-\x1f]/.test(name)||!Number.isInteger(size)||size<1024||size>MAX||!SHA.test(b.sha256||""))
  return error("Unsupported media (max 80 MiB)");
 if(!/^reel-[a-f0-9-]{36}$/.test(b.project_id||""))return error("Invalid project");
 const desc=(b.source_description||"").trim();
 if(desc.length<20||desc.length>1000||/[\x00-\x1f]/.test(desc))return error("Reviewed visible-shot description required");
 if(b.rights_confirmed!==true||b.people_consent!==true||b.external_ai_approved!==true||b.free_gemini_data_use_consent!==true)
  return error("Explicit source, people and AI/free-tier consent required",422);
 if((b.audio_mode||"source_ambience_only")!=="source_ambience_only")return error("Unlicensed soundtrack blocked",422);
 const p=await e.DB.prepare("SELECT id FROM mad_v1_projects WHERE id=?").bind(b.project_id).first();
 if(!p)return error("Project not found",404);
 const id="v6job-"+crypto.randomUUID().replace(/-/g,""),now=TIME(),count=Math.ceil(size/CHUNK);
 const r=await e.DB.prepare("INSERT INTO mad_v6_kv_jobs(job_id,project_id,file_name,mime,bytes,source_sha256,source_chunks,source_description,state,created_at,updated_at,expires_at) VALUES(?,?,?,?,?,?,?,?,'uploading',?,?,?)")
  .bind(id,b.project_id,name,mime,size,b.sha256,count,desc,now,now,now+RENDER_WINDOW).run();
 if(!r.success)return error("Upload database unavailable",503);
 return json({job_id:id,chunk_bytes:CHUNK,chunks:count,state:"uploading"},201);
}
async function chunkPut(req,e,id,n){
 const row=await getJob(e,id),i=Number(n);
 if(!row)return error("Job not found",404);
 if(row.state!=="uploading"||row.expires_at<=TIME())return error("Upload no longer active",409);
 if(!Number.isInteger(i)||i<0||i>=row.source_chunks)return error("Invalid chunk",400);
 const expected=Math.min(CHUNK,row.bytes-i*CHUNK),digest=req.headers.get("x-chunk-sha256")||"";
 if(!SHA.test(digest))return error("Chunk integrity header required");
 const prior=await e.DB.prepare("SELECT sha256 FROM mad_v6_kv_parts WHERE job_id=? AND kind='source' AND idx=?").bind(id,i).first();
 if(prior)return prior.sha256===digest?json({stored:true,duplicate:true}):error("Chunk hash conflict",409);
 const declared=req.headers.get("content-length");
 if(declared!==null&&Number(declared)!==expected)return error("Chunk size mismatch",413);
 const data=await req.arrayBuffer();
 if(data.byteLength!==expected||await hash(data)!==digest)return error("Source chunk checksum mismatch",422);
 await e.MEDIA_KV.put(KEY("source",id,i),data,{expirationTtl:RENDER_WINDOW});
 const stored=await e.DB.prepare("INSERT OR IGNORE INTO mad_v6_kv_parts(job_id,kind,idx,bytes,sha256) VALUES(?,'source',?,?,?)").bind(id,i,expected,digest).run();
 if(!stored.success)return error("Chunk metadata unavailable",503);
 return json({stored:true,index:i},201);
}
async function finishUpload(e,id){
 const row=await getJob(e,id);if(!row)return error("Job not found",404);
 if(row.state!=="uploading")return error("Upload cannot be finalized",409);
 const rows=(await chunks(e,id,"source")).results||[];
 if(rows.length!==row.source_chunks||rows.reduce((s,v)=>s+v.bytes,0)!==row.bytes||
    rows.some((v,i)=>v.idx!==i))return error("Source chunks incomplete",409);
 const update=await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='uploaded',updated_at=? WHERE job_id=? AND state='uploading'").bind(TIME(),id).run();
 if(!update.meta?.changes)return error("Upload completion race",409);
 return json({job_id:id,state:"uploaded",source_sha256:row.source_sha256});
}

const AUDIO_MAX=4*1024*1024;
async function prepareMusic(req,e,id){
 const j=await getJob(e,id);
 if(!j)return error("Job not found",404);
 if(j.state!=="uploaded"||j.expires_at<=TIME())return error("Music must be uploaded before dispatch",409);
 const b=await req.json().catch(()=>null),t=b?.track,v=b?.evidence;
 if(!b||!t||!v||t.source!=="Openverse"||
    !["cc0","pdm","by"].includes(t.license)||t.id!==v.track_id||
    t.original_source_page!==v.original_source_page||t.license_url!==v.license_url||
    !String(t.original_source_page||"").startsWith("https://")||
    !String(v.source_license_proof_url||"").startsWith("https://")||
    !String(t.license_url||"").startsWith(t.license==="cc0"?"https://creativecommons.org/publicdomain/zero/":
     t.license==="pdm"?"https://creativecommons.org/publicdomain/mark/":"https://creativecommons.org/licenses/by/")||
    !t.title||!t.creator||v.reviewer_confirmed_rights!==true||
    !String(v.reviewed_by||"").trim()||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(v.reviewed_on||"")||
    (t.license==="by"&&v.attribution_approved!==true)||
    !Number.isInteger(b.bytes)||b.bytes<1024||b.bytes>AUDIO_MAX||
    !SHA.test(b.sha256||"")||
    !["audio/mpeg","audio/wav","audio/ogg","audio/flac","audio/mp4"].includes(b.mime))
     return error("Music license, reviewer evidence or audio file invalid",422);
 if(await e.MEDIA_KV.get(KEY("musicmeta",id,0)))return error("Music already selected",409);
 const meta={track:t,evidence:v,bytes:b.bytes,sha256:b.sha256,mime:b.mime,ready:false};
 await e.MEDIA_KV.put(KEY("musicmeta",id,0),JSON.stringify(meta),{expirationTtl:RENDER_WINDOW});
 return json({music_state:"prepared",size_limit:AUDIO_MAX,published:false},201);
}
async function putMusic(req,e,id){
 const j=await getJob(e,id);if(!j)return error("Job not found",404);
 if(j.state!=="uploaded"||j.expires_at<=TIME())return error("Music upload unavailable",409);
 const m=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
 if(!m||m.ready)return error("Music not prepared or already transferred",409);
 const sha=req.headers.get("x-chunk-sha256"),size=req.headers.get("content-length");
 if(sha!==m.sha256||(size!==null&&Number(size)!==m.bytes))return error("Music header mismatch",422);
 const bytes=await req.arrayBuffer();
 if(bytes.byteLength!==m.bytes||await hash(bytes)!==m.sha256)return error("Music SHA256 mismatch",422);
 await e.MEDIA_KV.put(KEY("music",id,0),bytes,{expirationTtl:RENDER_WINDOW});
 m.ready=true;
 await e.MEDIA_KV.put(KEY("musicmeta",id,0),JSON.stringify(m),{expirationTtl:RENDER_WINDOW});
 return json({music_state:"ready",music_sha256:m.sha256,published:false},201);
}

async function dispatch(req,e,id){
 const b=await req.json().catch(()=>({})),brief=(b.brief||"").trim();
 if(brief.length<12||brief.length>1200||/[\x00-\x1f]/.test(brief))return error("Creative direction must be 12–1200 characters");
 const music=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
 if(music&&!music.ready)return error("Licensed music upload incomplete",409);
 if(!e.DISPATCH_API)return error("Existing GitHub dispatch service unavailable",503);
 const now=TIME();
 const r=await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='dispatching',brief=?,updated_at=? WHERE job_id=? AND state='uploaded' AND expires_at>?").bind(brief,now,id,now).run();
 if(!r.meta?.changes)return error("Job is not ready for dispatch",409);
 try{
   const result=await e.DISPATCH_API.fetch(new Request("https://reel-api.delulutech.in/internal/v6/dispatch",
     {method:"POST",headers:{"Authorization":req.headers.get("authorization")||"","Origin":"https://reel.delulutech.in",
     "Content-Type":"application/json"},body:JSON.stringify({job_id:id})}));
   if(result.status!==202&&result.status!==204)throw Error("Dispatch unavailable");
 }catch{
   await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='uploaded',updated_at=?,error_code='DISPATCH_NOT_READY' WHERE job_id=? AND state='dispatching'")
    .bind(TIME(),id).run();
   return error("Existing GitHub Actions dispatch not ready",503);
 }
 return json({job_id:id,state:"dispatching",renderer:"FFmpeg V7 Cinematic",published:false},202);
}
function publicState(j){
 const now=TIME(),expiry=j.ready_at?j.expires_at:null;
 const state=(expiry!==null&&now>=expiry)||j.state==="expired"?"expired":j.state;
 return {job_id:j.job_id,state,renderer:"FFmpeg V7 Cinematic",version:"v7-ffmpeg-private",
         download_available:state==="review_ready"&&expiry>now,
         expiry_at:expiry,seconds_remaining:expiry===null?null:Math.max(0,expiry-now),
         output_sha256:state==="review_ready"?j.output_sha256:null,
         audio_mode:j.receipt_json?JSON.parse(j.receipt_json).audio_mode:"not_certified_until_render",published:false,error_code:j.error_code||null};
}
async function preview(req,e,j,download){
 const state=publicState(j);
 if(state.state==="expired")return error("Private download deadline passed",410);
 if(j.state!=="review_ready"||!state.download_available)return error("Video not ready",409);
 const items=(await chunks(e,j.job_id,"output")).results||[];
 if(items.length!==j.output_chunks||items.reduce((s,v)=>s+v.bytes,0)!==j.output_bytes)return error("Private video chunks incomplete",503);
 let start=0,end=j.output_bytes-1,status=200;
 const range=req.headers.get("range");
 if(range){
  const m=/^bytes=(\d+)-(\d*)$/.exec(range);
  if(!m)return error("Unsupported range",416);
  start=Number(m[1]);end=m[2]?Number(m[2]):end;
  if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||end>=j.output_bytes)return error("Range invalid",416);
  status=206;
 }
 let offset=0;
 const selected=[];
 for(const part of items){
  const from=offset,to=offset+part.bytes-1;offset+=part.bytes;
  if(to<start||from>end)continue;
  selected.push({idx:part.idx,first:Math.max(0,start-from),last:Math.min(part.bytes-1,end-from)});
 }
 let index=0;
 const stream=new ReadableStream({async pull(c){
   if(index>=selected.length){c.close();return}
   if(TIME()>=j.expires_at){c.error(Error("Expired"));return}
   const item=selected[index++],data=await e.MEDIA_KV.get(KEY("output",j.job_id,item.idx),"arrayBuffer");
   if(!data){c.error(Error("Missing private video"));return}
   c.enqueue(new Uint8Array(data).slice(item.first,item.last+1));
 }});
 const headers={"content-type":"video/mp4","cache-control":"private, no-store","accept-ranges":"bytes",
   "content-length":String(end-start+1),"content-disposition":(download?"attachment":"inline")+'; filename="moksha-v6-private-reel.mp4"'};
 if(status===206)headers["content-range"]="bytes "+start+"-"+end+"/"+j.output_bytes;
 return new Response(stream,{status,headers});
}
async function catalog(req){
 const q=(new URL(req.url).searchParams.get("q")||"").trim();
 if(q.length<3||q.length>100)return error("Search 3–100 characters");
 try{
  const u=new URL("https://api.openverse.org/v1/audio/");u.searchParams.set("q",q);
  u.searchParams.set("license","cc0,by,pdm");u.searchParams.set("page_size","8");
  const r=await fetch(u,{headers:{"Accept":"application/json"},signal:AbortSignal.timeout(8000)});
  if(!r.ok)throw Error("Unavailable");
  const data=await r.json();
  return json({catalog:"Openverse",tracks:(data.results||[]).filter(x=>
    ["cc0","by","pdm"].includes(x.license)&&x.foreign_landing_url?.startsWith("https://")&&
    x.license_url?.startsWith("https://")).slice(0,8).map(x=>({id:x.id,title:x.title,creator:x.creator,
    license:x.license,license_url:x.license_url,original_source_page:x.foreign_landing_url,
    approved_for_render:false,rights_status:"UNVERIFIED_REQUIRES_INDEPENDENT_REVIEW"})),
    license_verified:false,approved_for_render:false});
 }catch{return error("Music catalog temporarily unavailable",503)}
}
async function internal(req,e,path){
 const claims=await verifyGitHub(req);
 if(!claims)return error("Authenticated GitHub runner required",401);
 const p=path.split("/").filter(Boolean),now=TIME(),id=p[3];
 if(!JOB.test(id||""))return error("Invalid private render job",400);
 if(p[4]==="seed"&&p.length===5&&req.method==="POST"){
  if(claims.event_name!=="issues"||String(claims.actor_id)!==OWNER_ID)return error("Owner-signed synthetic QA only",403);
  return seedSynthetic(req,e,id,now);
 }
 if(p[4]==="claim"&&req.method==="POST"){
  if(claims.event_name==="issues"){
   const current=await getJob(e,id);
   if(!current||current.project_id!=="synthetic-owner-qa")return error("Issue QA cannot claim customer media",403);
  }
  const preparedMusic=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
  if(preparedMusic&&!preparedMusic.ready)return error("Music not ready",409);
  const lease=crypto.randomUUID();
  const update=await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='rendering',claim_id=?,claimed_at=?,attempts=attempts+1,updated_at=? WHERE job_id=? AND state IN ('sent','dispatching') AND expires_at>? RETURNING *")
   .bind(lease,now,now,id,now).first();
  if(!update)return error("Private render already claimed or expired",409);
  const parts=(await chunks(e,id,"source")).results||[];
  if(parts.length!==update.source_chunks)return error("Private source not fully uploaded",409);
  const selectedMusic=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
  if(selectedMusic&&!selectedMusic.ready)return error("Music not ready",409);
  return json({job_id:id,claim_id:lease,source_sha256:update.source_sha256,source_chunks:update.source_chunks,
    source_bytes:update.bytes,mime:update.mime,source_description:update.source_description,brief:update.brief,
    audio_mode:selectedMusic?.ready?"licensed_music":"source_ambience_only",
    music_sha256:selectedMusic?.sha256||null,music_bytes:selectedMusic?.bytes||0,
    music_mime:selectedMusic?.mime||null,music_track:selectedMusic?.track||null,
    music_evidence:selectedMusic?.evidence||null,
    rights_confirmed:true,people_consent:true,free_gemini_consent:true});
 }
 const j=await getJob(e,id);
 if(!j)return error("Private job not found",404);
 if(claims.event_name==="issues"&&j.project_id!=="synthetic-owner-qa")return error("Issue QA restricted to synthetic media",403);
 const lease=req.headers.get("x-v6-claim")||"";
 if(j.state!=="rendering"||j.claim_id!==lease||!lease||j.claimed_at<now-3300||j.expires_at<=now)return error("Invalid or stale private claim",403);
 if(p[4]==="source"&&p.length===6&&req.method==="GET"){
  const i=Number(p[5]);
  if(!Number.isInteger(i)||i<0||i>=j.source_chunks)return error("Invalid source part",400);
  const b=await e.MEDIA_KV.get(KEY("source",id,i),"arrayBuffer");
  if(!b)return error("Private source not propagated",503);
  return new Response(b,{headers:{"content-type":"application/octet-stream","cache-control":"no-store","content-length":String(b.byteLength)}});
 }
 if(p[4]==="music"&&p.length===5&&req.method==="GET"){
  const meta=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
  if(!meta?.ready)return error("Private licensed audio not ready",403);
  const bytes=await e.MEDIA_KV.get(KEY("music",id,0),"arrayBuffer");
  if(!bytes)return error("Private licensed audio unavailable",503);
  return new Response(bytes,{headers:{"content-type":"application/octet-stream",
   "cache-control":"no-store","content-length":String(bytes.byteLength)}});
 }
 if(p[4]==="output"&&p.length===6&&req.method==="PUT"){
  const i=Number(p[5]),sha=req.headers.get("x-chunk-sha256")||"";
  if(!Number.isInteger(i)||i<0||i>=20||!SHA.test(sha))return error("Invalid output part");
  const body=await req.arrayBuffer();
  if(body.byteLength<1||body.byteLength>CHUNK||await hash(body)!==sha)return error("Output chunk checksum invalid",422);
  const prior=await e.DB.prepare("SELECT sha256 FROM mad_v6_kv_parts WHERE job_id=? AND kind='output' AND idx=?").bind(id,i).first();
  if(prior)return prior.sha256===sha?json({stored:true,duplicate:true}):error("Output part conflict",409);
  await e.MEDIA_KV.put(KEY("output",id,i),body,{expirationTtl:3600});
  await e.DB.prepare("INSERT INTO mad_v6_kv_parts(job_id,kind,idx,bytes,sha256) VALUES(?,'output',?,?,?)").bind(id,i,body.byteLength,sha).run();
  return json({stored:true,index:i});
 }
 if(p[4]==="complete"&&req.method==="POST"){
  const body=await req.json().catch(()=>({}));
  if(body.state==="failed"){
   await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='failed',error_code='PRIVATE_FFMPEG_FAILED',updated_at=? WHERE job_id=? AND claim_id=?")
    .bind(now,id,lease).run();
   return json({job_id:id,state:"failed"});
  }
  const arr=(await chunks(e,id,"output")).results||[];
  if(body.state!=="review_ready"||!Number.isInteger(body.chunks)||!Number.isInteger(body.bytes)||
     !SHA.test(body.sha256||"")||body.chunks<1||body.chunks>20||body.bytes<1024||body.bytes>MAX||
     arr.length!==body.chunks||arr.reduce((s,v)=>s+v.bytes,0)!==body.bytes||
     arr.some((v,i)=>v.idx!==i))return error("Verified final MP4 chunks/sha required",422);
  const selectedMusic=await e.MEDIA_KV.get(KEY("musicmeta",id,0),"json");
  if(selectedMusic?.ready){
   if(body.receipt?.audio_mode!=="licensed_music"||body.receipt?.music_mixed!==true||
      body.receipt?.music_sha256!==selectedMusic.sha256)return error("Licensed audio receipt mismatch",422);
  }else if(body.receipt?.audio_mode!=="source_ambience_only"||body.receipt?.music_mixed!==false)
    return error("Unexpected soundtrack receipt",422);
  const visual=body.receipt?.visual_presence_check;
  if(body.receipt?.engine!=="ffmpeg"||body.receipt?.version!=="v7-source-beta"||
    body.receipt?.cinematic_finish_applied!==true||body.receipt?.release_lane!=="v7-private"||
    body.receipt?.video_stream_verified!==true||
    body.receipt?.audio_stream_verified!==true||body.receipt?.full_decode_passed!==true||
    !Number.isInteger(body.receipt?.ffmpeg_invocations)||body.receipt.ffmpeg_invocations<1||
    body.receipt?.output_audio_verified!==true||visual?.visible!==true||
    !Number.isInteger(visual?.frames_examined)||visual.frames_examined<3||
    body.receipt?.published!==false||body.receipt?.sha256!==body.sha256)
      return error("FFmpeg video frames, audio or signed receipt not certified",422);
  const receipt=JSON.stringify(body.receipt);
  if(receipt.length>15000)return error("Private receipt too large",413);
  const result=await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='review_ready',output_chunks=?,output_bytes=?,output_sha256=?,receipt_json=?,ready_at=?,expires_at=?,updated_at=? WHERE job_id=? AND claim_id=? AND state='rendering'")
   .bind(body.chunks,body.bytes,body.sha256,receipt,now,now+DELIVERY_WINDOW,now,id,lease).run();
  if(!result.meta?.changes)return error("Completion lease race",409);
  return json({job_id:id,state:"review_ready",expires_at:now+DELIVERY_WINDOW,published:false});
 }
 return error("Signed private media route not found",404);
}
async function cleanup(e){
 if(!e.DB||!e.MEDIA_KV)return;
 const now=TIME();
 const rows=(await e.DB.prepare("SELECT job_id,source_chunks,output_chunks,state FROM mad_v6_kv_jobs WHERE expires_at<=? AND state!='expired' LIMIT 30").bind(now).all()).results||[];
 for(const r of rows){
  // Requests are always denied by D1 expiry even before eventual KV deletion.
  for(let i=0;i<Math.min(20,r.source_chunks||0);i++)await e.MEDIA_KV.delete(KEY("source",r.job_id,i));
  for(let i=0;i<Math.min(20,r.output_chunks||0);i++)await e.MEDIA_KV.delete(KEY("output",r.job_id,i));
  await e.MEDIA_KV.delete(KEY("music",r.job_id,0));
  await e.MEDIA_KV.delete(KEY("musicmeta",r.job_id,0));
  await e.DB.prepare("UPDATE mad_v6_kv_jobs SET state='expired',updated_at=? WHERE job_id=? AND expires_at<=?")
    .bind(now,r.job_id,now).run();
 }
}
export default {
 async fetch(req,e,ctx){
  const u=new URL(req.url),origin=req.headers.get("origin")||"",headers=cors(origin);
  if(u.pathname==="/health")return withCors(json({service:"MAD V6 private KV",ready:!!(e.DB&&e.MEDIA_KV&&e.PROJECT_AUTH),
    storage:"cloudflare_kv",dispatch_connected:!!e.DISPATCH_API,requires_github_vault_token:false,published:false}),headers);
  if(u.pathname.startsWith("/internal/v6/")){
   if(!e.DB||!e.MEDIA_KV)return error("Private bridge unavailable",503);
   return internal(req,e,u.pathname);
  }
  if(!headers)return error("Origin forbidden",403);
  if(req.method==="OPTIONS")return new Response(null,{status:204,headers});
  if(!await owner(req,e))return withCors(error("Owner access required",401),headers);
  let r;
  try{
    if(!e.DB||!e.MEDIA_KV)return withCors(error("Private KV or D1 unavailable",503),headers);
    const p=u.pathname.split("/").filter(Boolean);
    if(p[0]==="v1"&&p[1]==="projects")r=await projectProxy(req,e,u);
    else if(p[0]==="v6"&&p[1]==="catalog"&&req.method==="GET")r=await catalog(req);
    else if(p[0]==="v6"&&p[1]==="media"&&p[2]==="uploads"&&p.length===3&&req.method==="POST")r=await makeUpload(req,e);
    else if(p[0]==="v6"&&p[1]==="media"&&p[2]==="uploads"&&JOB.test(p[3]||"")&&p.length===6&&p[4]==="chunks"&&req.method==="PUT")r=await chunkPut(req,e,p[3],p[5]);
    else if(p[0]==="v6"&&p[1]==="media"&&p[2]==="uploads"&&JOB.test(p[3]||"")&&p.length===5&&p[4]==="complete"&&req.method==="POST")r=await finishUpload(e,p[3]);
    else if(p[0]==="v6"&&p[1]==="media"&&p[2]==="uploads"&&JOB.test(p[3]||"")&&p.length===5&&p[4]==="music"&&req.method==="POST")r=await prepareMusic(req,e,p[3]);
    else if(p[0]==="v6"&&p[1]==="media"&&p[2]==="uploads"&&JOB.test(p[3]||"")&&p.length===5&&p[4]==="music"&&req.method==="PUT")r=await putMusic(req,e,p[3]);
    else if(p[0]==="v6"&&p[1]==="jobs"&&JOB.test(p[2]||"")&&p.length===4&&p[3]==="render"&&req.method==="POST")r=await dispatch(req,e,p[2]);
    else if(p[0]==="v6"&&p[1]==="jobs"&&JOB.test(p[2]||"")){
       const j=await getJob(e,p[2]);
       if(!j)r=error("Private job not found",404);
       else if(p[3]==="status"&&req.method==="GET")r=json(publicState(j));
       else if(p[3]==="preview"&&req.method==="GET")r=await preview(req,e,j,false);
       else if(p[3]==="download"&&req.method==="GET")r=await preview(req,e,j,true);
       else r=error("Private route not found",404);
    }else r=error("Private route not found",404);
  }catch{r=error("Private V6 service unavailable",503)}
  return withCors(r,headers);
 },
 async scheduled(_event,e,ctx){ctx.waitUntil(cleanup(e))},
};
function withCors(resp,headers){for(const [key,value] of Object.entries(headers||{}))resp.headers.set(key,value);return resp}
