
const URL_BASE = Deno.env.get("SUPABASE_URL") || "";
const ADMIN_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
const JSON_HDR = {"Content-Type":"application/json"};
const GH_TOKEN = Deno.env.get("MASTER_STACK_GITHUB_TOKEN");
function response(status,data){return new Response(JSON.stringify(data),{status,headers:JSON_HDR});}
function clip(x,n=450){return String(x||"").replace(/\s+/g," ").slice(0,n);}
async function db(path,options={}){
  const hdr={...JSON_HDR,apikey:ADMIN_KEY,Authorization:"Bearer "+ADMIN_KEY,...(options.headers||{})};
  const r=await fetch(URL_BASE+"/rest/v1/"+path,{...options,headers:hdr});
  const txt=await r.text();
  if(!r.ok)throw new Error("Database status "+r.status);
  return txt?JSON.parse(txt):[];
}
async function github(path){
  const hdr={"User-Agent":"Moksha-Master-Stack","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"};
  if(GH_TOKEN)hdr.Authorization="Bearer "+GH_TOKEN;
  const r=await fetch("https://api.github.com"+path,{headers:hdr});
  if(!r.ok)throw new Error("GitHub status "+r.status);
  return r.json();
}
function noteworthy(files,message){
 const keys=files.map(f=>f.filename).filter(n=>n&&!n.includes("bridge/results/")&&!n.includes("app_bridge/results/")&&!n.endsWith("/copilot-instructions.md"));
 return keys.some(p=>/\.(php|ts|tsx|js|jsx|json|toml|yml|yaml|py)$/.test(p)||p.includes("architecture")||p.includes("capability"))
   ||(/STACK CHANGE/i.test(message)&&keys.length>0);
}
async function updateCursor(repo,sha,error){
  const patch={last_checked_at:new Date().toISOString(),last_error:error||null};
  if(sha)patch.last_scanned_sha=sha;
  await db("master_stack_repo_cursors?repo_full_name=eq."+encodeURIComponent(repo),{method:"PATCH",body:JSON.stringify(patch)});
}
async function scan(item){
  const repo=item.repo_full_name;
  const commits=await github("/repos/"+repo+"/commits?per_page=30");
  if(!Array.isArray(commits)||commits.length===0)return {repo,found:0,events:0};
  const last=commits.findIndex(x=>x.sha===item.last_scanned_sha);
  if(last===0){await updateCursor(repo,commits[0].sha,null);return {repo,found:0,events:0};}
  if(last<0)throw new Error("Cursor outside recent 30 commits; retained to avoid skipping");
  const newCommits=commits.slice(0,last).reverse();
  let events=0;
  for(const commit of newCommits){
    const detail=await github("/repos/"+repo+"/commits/"+commit.sha);
    const files=Array.isArray(detail.files)?detail.files:[];
    const msg=String(commit.commit?.message||"");
    if(!noteworthy(files,msg))continue;
    const title=clip(msg.split("\n")[0],170)||"Repository source changed";
    const summary=clip("Changed: "+files.slice(0,9).map(f=>f.filename).join(", ")+". "+title+". Source verified in Git; deployment not verified.",1500);
    await db("rpc/submit_master_stack_change",{method:"POST",body:JSON.stringify({
      p_event_key:repo+":"+commit.sha,
      p_origin_project:repo,
      p_source_url:"https://github.com/"+repo+"/commit/"+commit.sha,
      p_change_type:/security|CVE|vulnerab/i.test(msg)?"security":/release|version|upgrade/i.test(msg)?"release":"capability",
      p_title:title.length>=6?title:"Source change "+commit.sha.slice(0,10),
      p_summary:summary,
      p_source_kind:"repository",
      p_version_hint:null
    })});
    events++;
  }
  await updateCursor(repo,commits[0].sha,null);
  return {repo,found:newCommits.length,events};
}
Deno.serve(async req=>{
 if(req.method!=="POST")return response(405,{ok:false});
 const bearer=req.headers.get("Authorization")||"";
 const jwt=bearer.startsWith("Bearer ")?bearer.slice(7):"";
 let role="";
 try {
   const part=jwt.split(".")[1]||"";
   const decoded=atob(part.replace(/-/g,"+").replace(/_/g,"/"));
   role=JSON.parse(decoded).role||"";
 } catch {return response(403,{ok:false,error:"Forbidden"});}
 if(role!=="service_role")return response(403,{ok:false,error:"Forbidden"});
 if(!URL_BASE||!ADMIN_KEY)return response(503,{ok:false,error:"Service configuration missing"});
 const mode=(await req.json().catch(()=>({}))).mode||"scan";
 if(mode==="health")return response(200,{ok:true,worker:"master-stack-worker",github_private_available:!!GH_TOKEN,google_docs_publisher_configured:false});
 let runId=null,results=[],created=0,checked=0;
 try{
   const r=await db("master_stack_worker_runs",{method:"POST",headers:{"Prefer":"return=representation"},body:JSON.stringify({outcome:"running"})});
   runId=r[0]?.id||null;
   const repos=await db("master_stack_repo_cursors?select=repo_full_name,last_scanned_sha&order=repo_full_name.asc");
   for(const item of repos){
     try{const record=await scan(item);results.push(record);created+=record.events;checked++;}
     catch(e){const error=clip(e?.message,150);results.push({repo:item.repo_full_name,error});await updateCursor(item.repo_full_name,null,error).catch(()=>{});}
   }
   const outcome=results.some(r=>r.error)?"partial":"ok";
   if(runId)await db("master_stack_worker_runs?id=eq."+runId,{method:"PATCH",body:JSON.stringify({
     finished_at:new Date().toISOString(),outcome,repositories_checked:checked,events_created:created,details:{results}
   })});
   return response(200,{ok:true,outcome,repositories_checked:checked,events_created:created,results});
 }catch(e){
   if(runId)await db("master_stack_worker_runs?id=eq."+runId,{method:"PATCH",body:JSON.stringify({finished_at:new Date().toISOString(),outcome:"failed",details:{error:clip(e?.message)}})}).catch(()=>{});
   return response(500,{ok:false,error:"Worker failed; check run log"});
 }
});
