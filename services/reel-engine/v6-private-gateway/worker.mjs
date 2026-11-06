// MAD Reel Engine V6 isolated owner-private Cloudflare Gateway.
// GitHub draft Release media vault, 30-minute access cutoff, D1 history.
// Does NOT change any V5 routes or publish any media.
const REPO="karanzing1992/Matrix-House";
const ORIGINS=new Set(["https://reel.delulutech.in","https://delulutech-ai-reel-engine-v1.pages.dev","https://mad-v6-owner-private-beta.pages.dev"]);
const PREVIEW=/^https:\/\/[a-z0-9-]+\.(?:delulutech-ai-reel-engine-v1|mad-v6-owner-private-beta)\.pages\.dev$/;
const JOB=/^mad-v6-tmp-([a-z][a-z0-9_-]{7,63})$/;
const ID=/^v6job-([a-f0-9]{32})$/;
const SHA=/^[a-f0-9]{64}$/;
const MIME={"video/mp4":".mp4","video/quicktime":".mov","video/webm":".webm"};
const CHUNK=4*1024*1024,MAX=80*1024*1024,DOWNLOAD_WINDOW=1800,PENDING_WINDOW=86400;
const WORKFLOW="mad-v6-owner-private-render.yml";
const toJson=(data,status=200,headers={})=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff",...headers}});
const httpError=(message,status=400)=>toJson({error:{message}},status);
function originHeaders(o){const allowed=ORIGINS.has(o)||PREVIEW.test(o);return allowed?{"access-control-allow-origin":o,"vary":"Origin","access-control-allow-methods":"GET,POST,PUT,OPTIONS","access-control-allow-headers":"Authorization,Content-Type,X-Chunk-SHA256,Range","access-control-expose-headers":"Content-Length,Content-Range,Accept-Ranges","access-control-max-age":"120"}:null}
function iso(s){return new Date(s*1000).toISOString().replace(".000Z","Z")}
function time(s){const t=Date.parse(s);return Number.isFinite(t)?Math.floor(t/1000):NaN}
function digest(b){return crypto.subtle.digest("SHA-256",b).then(x=>Array.from(new Uint8Array(x),v=>v.toString(16).padStart(2,"0")).join(""))}
function token(e){return e.GITHUB_VAULT_TOKEN||""}
async function github(e,method,path,body,raw=false){
 if(!token(e))throw new Error("GH_VAULT_TOKEN_NOT_CONFIGURED");
 const headers={"authorization":"Bearer "+token(e),"accept":raw?"application/octet-stream":"application/vnd.github+json","x-github-api-version":"2022-11-28","user-agent":"mad-v6-owner-private-gateway"};
 let data=undefined;
 if(body!==undefined){data=JSON.stringify(body);headers["content-type"]="application/json"}
 const response=await fetch("https://api.github.com/repos/"+REPO+path,{method,headers,body:data,redirect:"manual"});
 if(response.status===404)return {status:404};
 if(response.status>=300)return {status:response.status,body:(await response.text()).slice(0,150)};
 if(raw)return {status:response.status,response};
 if(response.status===204)return {status:204};
 return {status:response.status,data:await response.json()};
}
async function owner(request,e){
 if(!e.PROJECT_AUTH)return false;
 const auth=request.headers.get("Authorization")||"";
 if(!/^Bearer nk-[A-Za-z0-9_-]{30,120}$/.test(auth))return false;
 try{
   const r=await e.PROJECT_AUTH.fetch(new Request("https://reel-projects.delulutech.in/v1/projects",{method:"GET",headers:{"Authorization":auth,"Origin":"https://reel.delulutech.in"}}));
   return r.ok;
 }catch{return false}
}
async function assertPrivate(e){
 const r=await github(e,"GET","");
 if(r.status!==200||r.data.private!==true||r.data.full_name!==REPO)throw new Error("GitHub vault is not private or authorized");
}
function parseRelease(rel,jobid){
 if(!rel||rel.draft!==true||rel.name!=="MAD V6 PRIVATE MEDIA "+jobid)return null;
 let m;try{m=JSON.parse(rel.body)}catch{return null}
 if(!m||m.schema!=="mad-v6-github-vault/1"||m.job_id!==jobid)return null;
 const tag=rel.tag_name||"";
 if(!(tag==="mad-v6-tmp-"+jobid||/^untagged-[a-f0-9]{8,64}$/.test(tag)))return null;
 if(!Number.isFinite(time(m.created_at))||!["uploading","queued","rendering","review_ready","failed"].includes(m.state))return null;
 if(m.state==="review_ready"){
   const at=time(m.review_ready_at),expires=time(m.expires_at);
   if(!Number.isFinite(at)||expires!==at+DOWNLOAD_WINDOW||!SHA.test(m.output_sha256||""))return null;
 }
 return m;
}
async function row(e,job){return e.DB.prepare("SELECT * FROM mad_v6_vault_jobs WHERE job_id=?").bind(job).first()}
async function release(e,r){const out=await github(e,"GET","/releases/"+r.release_id);if(out.status!==200)throw new Error("Private Release unavailable");const meta=parseRelease(out.data,r.job_id);if(!meta)throw new Error("Private Release manifest invalid");return {rel:out.data,meta}}
async function syncReady(e,r,meta){
 if(meta.state==="review_ready"){
   const expires=time(meta.expires_at),ready=time(meta.review_ready_at),now=Math.floor(Date.now()/1000);
   if(!Number.isFinite(expires)||!Number.isFinite(ready)||expires!==ready+DOWNLOAD_WINDOW)throw new Error("Invalid download deadline");
   const state=now>=expires?"expired":"review_ready";
   await e.DB.prepare("UPDATE mad_v6_vault_jobs SET state=?,expiry_at=?,ready_at=?,output_sha256=?,updated_at=? WHERE job_id=? AND state NOT IN ('expired','failed')")
      .bind(state,expires,ready,meta.output_sha256,now,r.job_id).run();
   return {...r,state,expiry_at:expires,ready_at:ready,output_sha256:meta.output_sha256};
 }
 if(meta.state==="failed")return {...r,state:"failed"};
 return {...r,state:meta.state};
}
async function createUpload(req,e){
 const b=await req.json().catch(()=>null);
 if(!b||typeof b!=="object")return httpError("Invalid upload manifest");
 const name=b.name||"",mime=b.mime||"",bytes=b.size;
 if(!Object.hasOwn(MIME,mime)||!name.endsWith(MIME[mime])||name.length>120||/[\/\\\x00-\x1f]/.test(name)||!Number.isInteger(bytes)||bytes<1024||bytes>MAX||!SHA.test(b.sha256||""))return httpError("Invalid source footage (MP4/MOV/WebM, max 80 MiB)");
 if(!/^reel-[a-f0-9-]{36}$/.test(b.project_id||""))return httpError("Project ID required");
 if(b.rights_confirmed!==true||b.people_consent!==true||b.external_ai_approved!==true)return httpError("Source rights and guest/AI processing consent required");
 if(b.free_gemini_data_use_consent!==true)return httpError("Explicit Gemini free-tier data-use consent required (text observations only)",422);
 const description=(b.source_description||"").trim();
 if(description.length<20||description.length>1000||/[\x00-\x1f]/.test(description))return httpError("Human-reviewed description of visible footage required (20-1000 characters)");
 if((b.audio_mode||"source_ambience_only")!=="source_ambience_only")return httpError("Licensed soundtrack upload awaits independent audio rights certification",422);
 const project=await e.DB.prepare("SELECT id FROM mad_v1_projects WHERE id=?").bind(b.project_id).first();
 if(!project)return httpError("Project not found",404);
 await assertPrivate(e);
 const id="v6job-"+crypto.randomUUID().replace(/-/g,""),now=Math.floor(Date.now()/1000);
 const meta={schema:"mad-v6-github-vault/1",job_id:id,state:"uploading",created_at:iso(now),fixture:false,source_sha256:b.sha256,
             project_id:b.project_id,audio_mode:"source_ambience_only",owner_consent_confirmed:true,
             free_gemini_data_use_consent:true,filename:"source"+MIME[mime],file_name:"source"+MIME[mime],
             human_reviewed:true,source_description:description,source_bytes:bytes,source_chunks:Math.ceil(bytes/CHUNK)};
 const gh=await github(e,"POST","/releases",{tag_name:"mad-v6-tmp-"+id,name:"MAD V6 PRIVATE MEDIA "+id,draft:true,prerelease:true,target_commitish:"main",body:JSON.stringify(meta)});
 if(gh.status!==201||!gh.data.draft)return httpError("Private GitHub Release creation unavailable",503);
 const chunks=Math.ceil(bytes/CHUNK);
 try{
   await e.DB.prepare("INSERT INTO mad_v6_vault_jobs (job_id,project_id,release_id,state,file_name,bytes,source_sha256,chunks,chunk_bytes,created_at,expiry_at,audio_mode,updated_at) VALUES (?,?,?,'uploading',?,?,?,?,?,?,?,?,?)")
   .bind(id,b.project_id,gh.data.id,name,bytes,b.sha256,chunks,CHUNK,now,now+PENDING_WINDOW,"source_ambience_only",now).run();
 }catch{
   await github(e,"DELETE","/releases/"+gh.data.id).catch(()=>{});
   return httpError("Failed to persist private upload",503);
 }
 return toJson({job_id:id,chunk_bytes:CHUNK,chunks,expiry_at:now+PENDING_WINDOW},201);
}
async function chunkUpload(req,e,r,index){
 if(r.state!=="uploading"||r.expiry_at<=Date.now()/1000)return httpError("Upload no longer accepting chunks",409);
 const i=Number(index);
 if(!Number.isInteger(i)||i<0||i>=r.chunks)return httpError("Chunk index invalid");
 const expected=Math.min(CHUNK,r.bytes-i*CHUNK);
 const requestedHash=req.headers.get("x-chunk-sha256")||"";
 if(!SHA.test(requestedHash))return httpError("Chunk SHA-256 missing");
 const existing=await e.DB.prepare("SELECT sha256 FROM mad_v6_vault_chunks WHERE job_id=? AND part_index=?").bind(r.job_id,i).first();
 if(existing)return existing.sha256===requestedHash?toJson({received:true,duplicate:true}):httpError("Chunk hash conflict",409);
 const declaredHeader=req.headers.get("content-length");
 if(declaredHeader!==null&&(!Number.isInteger(Number(declaredHeader))||Number(declaredHeader)!==expected))return httpError("Chunk byte length invalid",413);
 const bytes=await req.arrayBuffer();
 if(bytes.byteLength!==expected||await digest(bytes)!==requestedHash)return httpError("Chunk SHA-256 mismatch",422);
 const url="https://uploads.github.com/repos/"+REPO+"/releases/"+r.release_id+"/assets?name=source-"+String(i).padStart(3,"0")+".part";
 const resp=await fetch(url,{method:"POST",headers:{"authorization":"Bearer "+token(e),"accept":"application/vnd.github+json","x-github-api-version":"2022-11-28","content-type":"application/octet-stream"},body:bytes});
 if(resp.status!==201)return httpError("GitHub private chunk upload failed",503);
 const asset=await resp.json();
 if(asset.size!==expected||asset.digest && asset.digest!=="sha256:"+requestedHash)return httpError("GitHub chunk integrity error",502);
 await e.DB.prepare("INSERT INTO mad_v6_vault_chunks(job_id,part_index,asset_id,bytes,sha256) VALUES (?,?,?,?,?)").bind(r.job_id,i,asset.id,expected,requestedHash).run();
 return toJson({received:true,part_index:i},201);
}
async function completeUpload(e,r){
 if(r.state!=="uploading")return httpError("Upload cannot be finalized in this state",409);
 const tally=await e.DB.prepare("SELECT count(*) AS n,coalesce(sum(bytes),0) AS bytes FROM mad_v6_vault_chunks WHERE job_id=?").bind(r.job_id).first();
 if(tally.n!==r.chunks||tally.bytes!==r.bytes)return httpError("Upload incomplete: missing source chunks",409);
 const {rel,meta}=await release(e,r);
 const assets=new Set((rel.assets||[]).filter(x=>x.state==="uploaded").map(x=>x.name));
 for(let i=0;i<r.chunks;i++){if(!assets.has("source-"+String(i).padStart(3,"0")+".part"))return httpError("GitHub source asset missing",409)}
 if(meta.state!=="uploading")return httpError("Private source manifest state differs",409);
 meta.state="queued";
 const x=await github(e,"PATCH","/releases/"+r.release_id,{body:JSON.stringify(meta)});
 if(x.status!==200)return httpError("Could not finalize private upload",503);
 const now=Math.floor(Date.now()/1000);
 await e.DB.prepare("UPDATE mad_v6_vault_jobs SET state='queued',updated_at=? WHERE job_id=?").bind(now,r.job_id).run();
 return toJson({job_id:r.job_id,state:"queued",source_sha256:r.source_sha256});
}
async function render(req,e,r){
 if(r.state!=="queued"||r.expiry_at<=Date.now()/1000)return httpError("Private job not ready for rendering",409);
 const b=await req.json().catch(()=>null),brief=(b?.brief||"").trim();
 if(brief.length<12||brief.length>1200||/[\x00-\x1f]/.test(brief))return httpError("Creative direction must be 12–1200 characters");
 if(!token(e))return httpError("Private vault GitHub credential missing",503);
 const now=Math.floor(Date.now()/1000);
 const releaseData=await release(e,r);
 if(releaseData.meta.state!=="queued")return httpError("GitHub job manifest is not queued",409);
 releaseData.meta.brief=brief;
 const saved=await github(e,"PATCH","/releases/"+r.release_id,{body:JSON.stringify(releaseData.meta)});
 if(saved.status!==200)return httpError("Could not save private creative direction",503);
 const gh=await github(e,"POST","/actions/workflows/"+WORKFLOW+"/dispatches",{ref:"main",inputs:{release_id:String(r.release_id)}});
 if(gh.status!==204)return httpError("V6 FilmCraft dispatch unavailable; job remains queued",503);
 await e.DB.prepare("UPDATE mad_v6_vault_jobs SET state='rendering',brief=?,updated_at=? WHERE job_id=?").bind(brief,now,r.job_id).run();
 return toJson({job_id:r.job_id,state:"rendering",version:"v6",renderer:"FilmCraft",audio_mode:r.audio_mode},202);
}
async function status(e,r){
 const now=Math.floor(Date.now()/1000);
 if(r.state==="expired"||r.expiry_at<=now&&r.state==="review_ready")return {job_id:r.job_id,state:"expired",download_available:false,expiry_at:r.expiry_at};
 let m=null;
 try{const x=await release(e,r);m=x.meta;r=await syncReady(e,r,m)}catch(err){return {job_id:r.job_id,state:"verification_unavailable",download_available:false}}
 const expires=r.state==="review_ready"?r.expiry_at:null;
 return {job_id:r.job_id,state:r.state,version:"v6",renderer:"FilmCraft",
         expiry_at:expires,download_available:r.state==="review_ready"&&now<expires,
         seconds_remaining:expires?Math.max(0,expires-now):null,
         audio_mode:r.audio_mode,media_bytes:r.bytes,output_sha256:r.state==="review_ready"?r.output_sha256:null,
         published:false};
}
async function download(req,e,r,forDownload){
 const now=Math.floor(Date.now()/1000);
 if(r.state==="expired"||r.state==="review_ready"&&r.expiry_at<=now)return httpError("Download window expired",410);
 const x=await release(e,r);
 r=await syncReady(e,r,x.meta);
 if(r.state!=="review_ready")return httpError("Verified finished video is not ready",409);
 if(now>=r.expiry_at)return httpError("Download window expired",410);
 const video=(x.rel.assets||[]).find(a=>a.name==="v6-output.mp4"&&a.state==="uploaded");
 const receipt=(x.rel.assets||[]).find(a=>a.name==="v6-receipt.json"&&a.state==="uploaded");
 if(!video||!receipt)return httpError("Signed FilmCraft output not verified",503);
 if(video.digest!=="sha256:"+x.meta.output_sha256)return httpError("GitHub final MP4 checksum does not match verified render receipt",502);
 const url="https://api.github.com/repos/"+REPO+"/releases/assets/"+video.id;
 const range=req.headers.get("Range");
 if(range&&!/^bytes=\d*-\d*$/.test(range))return httpError("Invalid range",416);
 const headers={"authorization":"Bearer "+token(e),"accept":"application/octet-stream","x-github-api-version":"2022-11-28"};
 if(range)headers.Range=range;
 let media=await fetch(url,{headers,redirect:"manual"});
 if([302,301,307,308].includes(media.status)){
   const redirect=media.headers.get("location");
   if(!redirect)return httpError("Private media redirect absent",503);
   const u=new URL(redirect);
   if(u.protocol!=="https:"||!(u.hostname==="release-assets.githubusercontent.com"||u.hostname==="objects.githubusercontent.com"||u.hostname.endsWith(".githubusercontent.com")))return httpError("Unsafe private-media redirect",503);
   media=await fetch(u.toString(),{headers:range?{Range:range}:{},redirect:"error"});
 }
 if(media.status!==200&&media.status!==206)return httpError("Private video not retrievable",503);
 const responseType=(media.headers.get("content-type")||"").toLowerCase();
 if(responseType.includes("json")||responseType.includes("html")||media.headers.get("content-length")==="0")return httpError("Private GitHub asset was metadata, not video",502);
 const out={"content-type":"video/mp4","cache-control":"private, no-store, max-age=0","x-content-type-options":"nosniff","content-disposition":(forDownload?"attachment":"inline")+'; filename="moksha-v6-private-reel.mp4"',"accept-ranges":"bytes"};
 for(const name of ["content-range","content-length"]){if(media.headers.get(name))out[name]=media.headers.get(name)}
 return new Response(media.body,{status:media.status,headers:out});
}
async function proxyPrivateProjects(req,e,url){
 const allowed=url.pathname==="/v1/projects"||url.pathname.startsWith("/v1/projects/");
 if(!allowed)return httpError("Private project route forbidden",404);
 if(!["GET","POST","PATCH"].includes(req.method))return httpError("Private project method forbidden",405);
 const headers={
   "Authorization":req.headers.get("Authorization")||"",
   "Origin":"https://reel.delulutech.in",
   "Accept":"application/json"
 };
 const t=req.headers.get("Content-Type");
 if(t==="application/json")headers["Content-Type"]="application/json";
 const remote=new Request("https://reel-projects.delulutech.in"+url.pathname+url.search,
                         {method:req.method,headers,body:req.method==="GET"?undefined:await req.text()});
 const result=await e.PROJECT_AUTH.fetch(remote);
 if(!["application/json","application/json; charset=utf-8"].some(x=>(result.headers.get("content-type")||"").toLowerCase().startsWith(x)))
   return httpError("Unexpected internal project response",502);
 return new Response(result.body,{status:result.status,headers:{"content-type":"application/json","cache-control":"no-store"}});
}
async function catalog(req){
 const u=new URL(req.url);
 const q=(u.searchParams.get("q")||"").trim();
 if(q.length<3||q.length>100)return httpError("Audio search query 3–100 characters");
 const p=new URL("https://api.openverse.org/v1/audio/");
 p.searchParams.set("q",q);p.searchParams.set("license","cc0,by,pdm");p.searchParams.set("page_size","8");p.searchParams.set("category","music");
 let data;try{const x=await fetch(p.toString(),{headers:{"accept":"application/json","user-agent":"MAD V6 music-discovery metadata-only"},signal:AbortSignal.timeout(9000)});if(!x.ok)throw Error("catalog unavailable");data=await x.json()}catch{return httpError("Open-license catalog temporarily unavailable",503)}
 const tracks=(data.results||[]).filter(x=>["cc0","by","pdm"].includes(x.license)&&x.foreign_landing_url?.startsWith("https://")&&x.license_url?.startsWith("https://"))
 .slice(0,8).map(x=>({id:x.id,title:x.title,creator:x.creator,license:x.license,license_url:x.license_url,
                     original_source_page:x.foreign_landing_url,rights_status:"UNVERIFIED_REQUIRES_INDEPENDENT_REVIEW",approved_for_render:false}));
 return toJson({catalog:"Openverse",tracks,license_verified:false,mixing_status:"requires FilmCraft native audio clearance",composed_music:false});
}
async function cleanup(e){
 if(!token(e))return {status:"credential_missing",removed:0};
 await assertPrivate(e);
 const now=Math.floor(Date.now()/1000);
 const rows=await e.DB.prepare("SELECT * FROM mad_v6_vault_jobs WHERE state IN ('uploading','queued','rendering','review_ready','failed') ORDER BY created_at LIMIT 75").all();
 let removed=0,checked=0;
 for(const row of rows.results||[]){
   checked++;
   let rel,m;
   try{({rel,meta:m}=await release(e,row))}catch{continue}
   if(m.state==="review_ready"){
      const expires=time(m.expires_at);
      if(expires>now)continue;
   }else if(time(m.created_at)+PENDING_WINDOW>now)continue;
   const result=await github(e,"DELETE","/releases/"+row.release_id);
   if(result.status===204||result.status===404){
      await e.DB.prepare("UPDATE mad_v6_vault_jobs SET state='expired',expiry_at=?,updated_at=? WHERE job_id=?").bind(now,now,row.job_id).run();
      removed++;
   }
 }
 return {checked,removed};
}
export default {
 async fetch(req,e,ctx){
   const url=new URL(req.url),origin=req.headers.get("Origin")||"",cors=originHeaders(origin);
   if(url.pathname==="/health")return toJson({service:"MAD V6 owner-private GitHub gateway",version:"6.0-beta",auth_bound:!!e.PROJECT_AUTH,github_private_vault_configured:!!token(e),d1_bound:!!e.DB,public_access:false,ready:!!(e.PROJECT_AUTH&&token(e)&&e.DB)});
   if(!cors)return httpError("Origin forbidden",403);
   if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors});
   if(!(await owner(req,e)))return new Response(JSON.stringify({error:{message:"Owner authorization required"}}),{status:401,headers:{"content-type":"application/json",...cors}});
   let res;
   try{
     if(!e.DB)return httpError("Private D1 unavailable",503);
     if(!token(e))return httpError("Private GitHub vault credential not configured",503);
     const parts=url.pathname.split("/").filter(Boolean);
     if(parts[0]==="v1"&&parts[1]==="projects")res=await proxyPrivateProjects(req,e,url);
     else if(parts[0]!=="v6")return httpError("V6 route not found",404);
     else
     if(parts[1]==="catalog"&&parts.length===2&&req.method==="GET")res=await catalog(req);
     else if(parts[1]==="media"&&parts[2]==="uploads"&&parts.length===3&&req.method==="POST")res=await createUpload(req,e);
     else{
       const job=parts[parts[1]==="media"?3:2];
       if(!ID.test(job||""))return httpError("Invalid V6 job ID",400);
       const r=await row(e,job);
       if(!r)return httpError("V6 job not found",404);
       if(parts[1]==="media"&&parts[2]==="uploads"&&parts.length===6&&parts[4]==="chunks"&&req.method==="PUT")res=await chunkUpload(req,e,r,parts[5]);
       else if(parts[1]==="media"&&parts[2]==="uploads"&&parts.length===5&&parts[4]==="complete"&&req.method==="POST")res=await completeUpload(e,r);
       else if(parts[1]==="jobs"&&parts.length===4&&parts[3]==="render"&&req.method==="POST")res=await render(req,e,r);
       else if(parts[1]==="jobs"&&parts.length===4&&parts[3]==="status"&&req.method==="GET")res=toJson(await status(e,r));
       else if(parts[1]==="jobs"&&parts.length===4&&parts[3]==="preview"&&req.method==="GET")res=await download(req,e,r,false);
       else if(parts[1]==="jobs"&&parts.length===4&&parts[3]==="download"&&req.method==="GET")res=await download(req,e,r,true);
       else res=httpError("V6 route not found",404);
     }
   }catch(err){res=httpError("Private V6 service unavailable; consult server audit",503)}
   for(const [k,v] of Object.entries(cors))res.headers.set(k,v);
   return res;
 },
 async scheduled(event,e,ctx){ctx.waitUntil(cleanup(e))},
};
