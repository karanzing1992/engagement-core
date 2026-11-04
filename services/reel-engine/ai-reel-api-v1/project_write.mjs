const res=(o,status=200)=>new Response(JSON.stringify(o),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
const err=(message,status=400)=>res({error:{message}},status);
export async function projectWrite(req,env,url){
 const p=url.pathname.split("/").filter(Boolean),id=p[2],db=env.DB,now=Math.floor(Date.now()/1000);
 if(!/^reel-[a-f0-9-]{36}$/.test(id||""))return err("Invalid project",404);
 const exists=await db.prepare("SELECT id FROM mad_v1_projects WHERE id=?").bind(id).first();
 if(!exists)return err("Project not found",404);
 const q=await req.json().catch(()=>null);
 if(p[3]==="assets"){
  if(!/^upload-[a-f0-9-]{36}$/.test(q?.upload_id||"")||q?.rights_confirmed!==true||q?.people_consent!==true||q?.external_ai_approved!==true)return err("Rights, people consent and external AI approval required");
  const upload=await db.prepare("SELECT id FROM mad_v1_uploads WHERE id=? AND state='complete' AND expires_at>?").bind(q.upload_id,now).first();
  if(!upload)return err("Footage incomplete or expired",409);
  const prior=await db.prepare("SELECT project_id FROM mad_v1_project_assets WHERE upload_id=?").bind(q.upload_id).first();
  if(prior&&prior.project_id!==id)return err("Footage assigned to another project",409);
  await db.prepare("INSERT OR IGNORE INTO mad_v1_project_assets(project_id,upload_id,rights_confirmed,people_consent,external_ai_approved,created_at) VALUES (?,?,1,1,1,?)").bind(id,q.upload_id,now).run();
  await db.prepare("UPDATE mad_v1_projects SET updated_at=? WHERE id=?").bind(now,id).run();
  return res({attached:true,upload_id:q.upload_id},201);
 }
 if(p[3]==="messages"){
  const content=q?.content?.trim();
  if(typeof content!=="string"||content.length<2||content.length>1200||/[\\x00-\\x1f]|https?:\\/\\/|github_pat_|ghp_|sk-[A-Za-z0-9]{12}/i.test(content))return err("Use a 2–1200 character creative direction without links or secrets");
  const a={id:crypto.randomUUID(),role:"user",content,created_at:now};
  const b={id:crypto.randomUUID(),role:"assistant",content:"Direction saved for this reel. Create a render to apply it to the attached footage.",created_at:now};
  await db.batch([
   db.prepare("INSERT INTO mad_v1_project_messages(id,project_id,role,content,created_at) VALUES (?,?,?,?,?)").bind(a.id,id,a.role,a.content,now),
   db.prepare("INSERT INTO mad_v1_project_messages(id,project_id,role,content,created_at) VALUES (?,?,?,?,?)").bind(b.id,id,b.role,b.content,now),
   db.prepare("UPDATE mad_v1_projects SET updated_at=? WHERE id=?").bind(now,id)]);
  return res({messages:[a,b],reply_type:"saved_instructions"},201);
 }
 return err("Unknown action",404);
}
