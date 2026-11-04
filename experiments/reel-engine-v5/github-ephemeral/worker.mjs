import {validateJob,jobTag,parseMetadata,checkSourceAssets,validateChunkRequest,outputAssets,expired} from "./core.mjs";

// Stateless MCP bridge. Media exists only in private GitHub draft release assets and
// ephemeral GitHub Actions runner workspaces. There is no KV/R2/Blob database.
const enc = new TextEncoder();
function equal(a,b) {
  if(typeof a!=="string" || typeof b!=="string" || a.length!==b.length) return false;
  let delta=0; for(let i=0;i<a.length;i++) delta |= a.charCodeAt(i)^b.charCodeAt(i);
  return delta===0;
}
function json(value,status=200,extra={}) {
  return new Response(JSON.stringify(value),{status,headers:{"content-type":"application/json; charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff",...extra}});
}
function safeError(e) { return String(e?.message || e).slice(0,240).replace(/(ghp_|github_pat_|Bearer )[A-Za-z0-9_-]+/g,"[redacted]"); }
function repoConfig(env) {
  if(!env.GITHUB_TOKEN || !env.MCP_ACCESS_TOKEN || !/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(env.GITHUB_REPO||"")) throw Error("MCP is not configured");
  return env.GITHUB_REPO;
}
async function gh(env,path,{method="GET",body,accept="application/vnd.github+json"}={}) {
  const repo=repoConfig(env);
  const r=await fetch("https://api.github.com/repos/"+repo+path,{method,
    headers:{"authorization":"Bearer "+env.GITHUB_TOKEN,"accept":accept,
      "x-github-api-version":"2022-11-28","user-agent":"mad-v5-ephemeral-mcp",
      ...(body===undefined?{}:{"content-type":"application/json"})},
    body:body===undefined?undefined:JSON.stringify(body)});
  if(r.status===204) return null;
  if(!r.ok) throw Error("GitHub API "+r.status+" on "+method);
  return r.json();
}
async function ensurePrivate(env) {
  const r=await gh(env,"");
  if(r.private!==true) throw Error("Private GitHub media repository required");
}
async function findRelease(env,id) {
  const tag=jobTag(id);
  for(let page=1;page<=5;page++) {
    const list=await gh(env,"/releases?per_page=100&page="+page);
    const found=list.find(x=>x.tag_name===tag);
    if(found) return found;
    if(list.length<100) break;
  }
  throw Error("Temporary job not found or expired");
}
async function updateRelease(env,release,data) {
  return gh(env,"/releases/"+release.id,{method:"PATCH",body:{body:JSON.stringify(data)}});
}
async function createJob(env,args) {
  await ensurePrivate(env);
  const meta=validateJob(args);
  try { await findRelease(env,meta.job_id); throw Error("Job already exists"); }
  catch(e) { if(!String(e.message).includes("not found or expired")) throw e; }
  const rel=await gh(env,"/releases",{method:"POST",body:{
    tag_name:jobTag(meta.job_id),target_commitish:env.GITHUB_BASE_REF||"main",
    name:"Private MAD V5 transient "+meta.job_id,
    body:JSON.stringify(meta),draft:true,prerelease:true
  }});
  return {job_id:meta.job_id,upload_path:"/media/"+meta.job_id+"/{chunk_index}",
    chunk_count:meta.chunk_count,chunk_limit_bytes:80*1024*1024,
    ready_for_upload:true,expires_after_hours:24,release_id:rel.id,
    note:"Binary upload requires authenticated HTTP streaming; do not put guest footage in ChatGPT tool JSON or public Git"};
}
async function uploadChunk(request,env,id,index) {
  await ensurePrivate(env);
  const release=await findRelease(env,id),meta=parseMetadata(release);
  const name=validateChunkRequest(meta,index,request);
  const exists=(release.assets||[]).some(a=>a.name===name);
  if(exists) throw Error("Chunk already uploaded");
  const upload="https://uploads.github.com/repos/"+repoConfig(env)+"/releases/"+release.id+
    "/assets?name="+encodeURIComponent(name);
  const result=await fetch(upload,{method:"POST",headers:{
    "authorization":"Bearer "+env.GITHUB_TOKEN,"accept":"application/vnd.github+json",
    "content-type":"application/octet-stream","content-length":request.headers.get("content-length"),
    "x-github-api-version":"2022-11-28","user-agent":"mad-v5-ephemeral-mcp"},
    body:request.body,duplex:"half"});
  if(!result.ok) throw Error("GitHub temporary asset upload failed HTTP "+result.status);
  const asset=await result.json();
  return {job_id:id,asset:name,bytes:asset.size,stored_private:true};
}
async function submit(env,args) {
  await ensurePrivate(env);
  const release=await findRelease(env,args.job_id),meta=parseMetadata(release);
  if(meta.state!=="awaiting_upload" && meta.state!=="dispatch_pending") throw Error("Job already dispatched");
  if(meta.rights.external_ai_processing_approved!==true) throw Error("External Gemini/Groq processing not approved");
  checkSourceAssets(meta,release.assets);
  const data={...meta,state:"dispatch_pending"};
  await updateRelease(env,release,data);
  const workflow=env.GITHUB_WORKFLOW || "mad-v5-private-job.yml";
  try {
    await gh(env,"/actions/workflows/"+encodeURIComponent(workflow)+"/dispatches",
      {method:"POST",body:{ref:env.GITHUB_BASE_REF||"main",inputs:{
        job_id:meta.job_id,release_id:String(release.id)}}});
  } catch(e) {
    throw Error("Dispatch pending; inspect GitHub run and retry only after checking duplication: "+safeError(e));
  }
  await updateRelease(env,release,{...data,state:"submitted"});
  return {job_id:meta.job_id,dispatched:true,certified:false,
    note:"Workflow dispatch is NOT a completed render; inspect reel_status and receipt"};
}
async function jobStatus(env,args) {
  await ensurePrivate(env);
  const release=await findRelease(env,args.job_id),meta=parseMetadata(release);
  const out=outputAssets(release.assets);
  return {job_id:meta.job_id,state:out.ready?"render_available":meta.state,
    output_available:out.ready,created_at:release.created_at,
    uploaded_chunks:(release.assets||[]).filter(a=>/^source-\d{3}\.part$/.test(a.name)).length,
    expected_chunks:meta.chunk_count,certified:false,
    note:"Inspect private receipt and artistic/rights gates before release claims"};
}
async function hmac(env,msg) {
  const key=await crypto.subtle.importKey("raw",enc.encode(env.MCP_ACCESS_TOKEN),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const b=new Uint8Array(await crypto.subtle.sign("HMAC",key,enc.encode(msg)));
  return Array.from(b).map(x=>x.toString(16).padStart(2,"0")).join("");
}
async function previewLink(request,env,args) {
  const release=await findRelease(env,args.job_id),out=outputAssets(release.assets);
  if(!out.ready) throw Error("No completed output artifact");
  const until=Math.floor(Date.now()/1000)+600;
  const token=await hmac(env,args.job_id+":"+out.video_asset_id+":"+until);
  return {job_id:args.job_id,url:new URL(request.url).origin+"/preview/"+args.job_id+
    "?asset="+out.video_asset_id+"&expires="+until+"&sig="+token,
    expires_in_seconds:600,private:true,ack_after_review:true};
}
async function downloadPreview(request,env,id) {
  const uri=new URL(request.url);
  const asset=Number(uri.searchParams.get("asset"));
  const until=Number(uri.searchParams.get("expires"));
  const sig=uri.searchParams.get("sig")||"";
  if(!Number.isSafeInteger(asset)||!Number.isSafeInteger(until)||until<Math.floor(Date.now()/1000)||until>Math.floor(Date.now()/1000)+610) throw Error("Preview expired");
  const expected=await hmac(env,id+":"+asset+":"+until);
  if(!equal(sig,expected)) throw Error("Invalid preview signature");
  const release=await findRelease(env,id),out=outputAssets(release.assets);
  if(!out.ready||out.video_asset_id!==asset) throw Error("Output not ready");
  const upstream=await fetch("https://api.github.com/repos/"+repoConfig(env)+"/releases/assets/"+asset,{
    headers:{"authorization":"Bearer "+env.GITHUB_TOKEN,"accept":"application/octet-stream",
      "x-github-api-version":"2022-11-28","user-agent":"mad-v5-preview",
      ...(request.headers.has("range")?{"range":request.headers.get("range")}:{})},
    redirect:"follow"});
  if(!upstream.ok) throw Error("Private preview unavailable HTTP "+upstream.status);
  const headers={"cache-control":"private, no-store","content-type":"video/mp4",
    "x-content-type-options":"nosniff","content-disposition":"inline; filename=mad-v5-preview.mp4"};
  for(const name of ["content-length","content-range","accept-ranges"]) if(upstream.headers.has(name)) headers[name]=upstream.headers.get(name);
  return new Response(upstream.body,{status:upstream.status,headers});
}
async function acknowledge(env,args) {
  await ensurePrivate(env);
  const release=await findRelease(env,args.job_id);
  const meta=parseMetadata(release);
  if(!outputAssets(release.assets).ready && args.force!==true) throw Error("Cannot acknowledge incomplete output without force");
  await gh(env,"/releases/"+release.id,{method:"DELETE"});
  let tagState="absent";
  const tagRef="/git/ref/tags/"+jobTag(meta.job_id);
  try { await gh(env,tagRef); tagState="present"; }
  catch(e) {
    if(!String(e.message).includes("GitHub API 404 on GET") &&
       !String(e.message).includes("GitHub API 422 on GET")) throw e;
  }
  if(tagState==="present") {
    await gh(env,"/git/refs/tags/"+jobTag(meta.job_id),{method:"DELETE"});
    tagState="deleted";
  }
  return {job_id:meta.job_id,deleted_release:true,tag_ref_status:tagState,
    warning:"GitHub backup/CDN physical erasure is not guaranteed instantaneous"};
}
const toolSpecs=[
  {name:"reel_create_job",description:"Create private temporary source intake for an approved V5 creative prompt.",
    inputSchema:{type:"object",required:["job_id","project_id","prompt","source_sha256","source_bytes","chunk_count","rights"],
    properties:{job_id:{type:"string"},project_id:{type:"string"},prompt:{type:"string"},source_sha256:{type:"string"},source_bytes:{type:"integer"},chunk_count:{type:"integer"},
      verified_shots:{type:"object"},verified_brand:{type:"string"},
      rights:{type:"object",properties:{source_rights_confirmed:{type:"boolean"},people_consent_confirmed:{type:"boolean"},external_ai_processing_approved:{type:"boolean"}}}}}},
  {name:"reel_submit_prompt",description:"Dispatch a fully uploaded private-source V5 job to GitHub Actions, not publish.",inputSchema:{type:"object",required:["job_id"],properties:{job_id:{type:"string"}}}},
  {name:"reel_status",description:"Read private V5 job state and render availability.",inputSchema:{type:"object",required:["job_id"],properties:{job_id:{type:"string"}}}},
  {name:"reel_get_preview",description:"Generate a short-lived private video preview URL for the authenticated caller.",inputSchema:{type:"object",required:["job_id"],properties:{job_id:{type:"string"}}}},
  {name:"reel_acknowledge_and_delete",description:"Delete source and outputs after review acknowledgement.",inputSchema:{type:"object",required:["job_id"],properties:{job_id:{type:"string"},force:{type:"boolean"}}}}
];
async function mcp(request,env) {
  const body=await request.json();
  const id=body.id;
  if(body.method==="initialize") return json({jsonrpc:"2.0",id,result:{
    protocolVersion:"2025-03-26",capabilities:{tools:{}},serverInfo:{name:"mad-v5-github-ephemeral",version:"0.1.0"}}});
  if(body.method==="notifications/initialized") return new Response(null,{status:202});
  if(body.method==="ping") return json({jsonrpc:"2.0",id,result:{}});
  if(body.method==="tools/list") return json({jsonrpc:"2.0",id,result:{tools:toolSpecs}});
  if(body.method!=="tools/call") return json({jsonrpc:"2.0",id,error:{code:-32601,message:"Method not found"}},400);
  const name=body.params?.name,args=body.params?.arguments||{};
  const operation={
    reel_create_job:()=>createJob(env,args),
    reel_submit_prompt:()=>submit(env,args),
    reel_status:()=>jobStatus(env,args),
    reel_get_preview:()=>previewLink(request,env,args),
    reel_acknowledge_and_delete:()=>acknowledge(env,args)
  }[name];
  if(!operation) return json({jsonrpc:"2.0",id,error:{code:-32601,message:"Unknown tool"}},400);
  try {
    const result=await operation();
    return json({jsonrpc:"2.0",id,result:{content:[{type:"text",text:JSON.stringify(result)}]}});
  } catch(e) {
    return json({jsonrpc:"2.0",id,result:{isError:true,content:[{type:"text",text:safeError(e)}]}});
  }
}
export default {
  async fetch(request,env) {
    const u=new URL(request.url);
    if(u.pathname==="/health" && request.method==="GET")
      return json({service:"MAD V5 GitHub ephemeral MCP",status:"candidate",configured:Boolean(env.GITHUB_REPO && env.GITHUB_TOKEN && env.MCP_ACCESS_TOKEN)});
    try {
      repoConfig(env);
      const match=u.pathname.match(/^\/media\/([a-z][a-z0-9_-]{7,63})\/(\d{1,2})$/);
      if(u.pathname.startsWith("/preview/") && request.method==="GET")
        return await downloadPreview(request,env,u.pathname.slice("/preview/".length));
      const token=(request.headers.get("authorization")||"").replace(/^Bearer\s+/i,"");
      if(!equal(token,env.MCP_ACCESS_TOKEN)) return json({error:"Unauthorized"},401,{"www-authenticate":"Bearer"});
      if(match && request.method==="POST") return json(await uploadChunk(request,env,match[1],Number(match[2])),201);
      if(u.pathname==="/mcp" && request.method==="POST") return await mcp(request,env);
      return json({error:"Not found"},404);
    } catch(e) { return json({error:safeError(e)},400); }
  }
};
