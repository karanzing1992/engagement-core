const good=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
const bad=(message,status=400)=>good({error:{message}},status);
const valid=(id)=>/^reel-[a-f0-9-]{36}$/.test(id||"");
export async function projectApi(req,env,url){
 const p=url.pathname.split("/").filter(Boolean),db=env.DB,now=Math.floor(Date.now()/1000);
 if(p.length===2&&p[1]==="projects"){
  if(req.method==="GET"){
   const r=await db.prepare("SELECT id,name,created_at,updated_at FROM mad_v1_projects ORDER BY updated_at DESC LIMIT 100").all();
   return good({projects:r.results||[]});
  }
  if(req.method==="POST"){
   const q=await req.json().catch(()=>null),name=q?.name?.trim();
   if(typeof name!=="string"||name.length<2||name.length>90)return bad("Invalid project name");
   const id="reel-"+crypto.randomUUID();
   await db.prepare("INSERT INTO mad_v1_projects(id,name,created_at,updated_at) VALUES (?,?,?,?)").bind(id,name,now,now).run();
   return good({project:{id,name,created_at:now,updated_at:now}},201);
  }
 }
 const id=p[2];if(p[1]!=="projects"||!valid(id))return bad("Project not found",404);
 const project=await db.prepare("SELECT id,name,created_at,updated_at FROM mad_v1_projects WHERE id=?").bind(id).first();
 if(!project)return bad("Project not found",404);
 if(p.length===3&&req.method==="GET"){
  const [assets,messages,versions]=await Promise.all([
   db.prepare("SELECT a.upload_id,u.file_name,u.bytes,u.expires_at FROM mad_v1_project_assets a JOIN mad_v1_uploads u ON u.id=a.upload_id WHERE a.project_id=? ORDER BY a.created_at DESC").bind(id).all(),
   db.prepare("SELECT id,role,content,created_at FROM mad_v1_project_messages WHERE project_id=? ORDER BY created_at ASC,id ASC LIMIT 300").bind(id).all(),
   db.prepare("SELECT v.version_id AS job_id,v.created_at,j.state,j.error_code,j.result_bytes,j.expires_at FROM mad_v1_versions v JOIN mad_v1_media_jobs j ON j.job_id=v.version_id WHERE v.project_id=? ORDER BY v.created_at DESC").bind(id).all()
  ]);
  return good({project,assets:assets.results||[],messages:messages.results||[],versions:versions.results||[],current_time:now});
 }
 return bad("Unknown project operation",404);
}
