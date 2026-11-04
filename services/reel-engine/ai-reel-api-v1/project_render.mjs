import {wakeMediaJob} from './media_event_wake.mjs';
const respond=(o,status=200)=>new Response(JSON.stringify(o),{status,headers:{"content-type":"application/json","cache-control":"no-store"}});
export async function projectRender(req,env,url){
 const p=url.pathname.split("/").filter(Boolean),id=p[2],db=env.DB,now=Math.floor(Date.now()/1000);
 if(!/^reel-[a-f0-9-]{36}$/.test(id||""))return respond({error:{message:"Invalid project"}},404);
 const project=await db.prepare("SELECT id FROM mad_v1_projects WHERE id=?").bind(id).first();
 if(!project)return respond({error:{message:"Project not found"}},404);
 const asset=await db.prepare("SELECT a.upload_id FROM mad_v1_project_assets a JOIN mad_v1_uploads u ON a.upload_id=u.id WHERE a.project_id=? AND u.state='complete' AND u.expires_at>? ORDER BY a.created_at DESC LIMIT 1").bind(id,now).first();
 if(!asset)return respond({error:{message:"Attach an unexpired source video"}},409);
 const notes=await db.prepare("SELECT content FROM mad_v1_project_messages WHERE project_id=? AND role='user' ORDER BY created_at DESC,id DESC LIMIT 6").bind(id).all();
 const brief=(notes.results||[]).reverse().map(x=>x.content).join(" | ");
 const prompt=("Create a cinematic vertical reel from this project's real source footage. "+(brief||"Start with a strong hook and edit with deliberate, polished pacing.")).slice(0,600);
 if(prompt.length<12)return respond({error:{message:"Creative brief too short"}},400);
 const job="madmedia-"+crypto.randomUUID();
 try{await db.batch([
  db.prepare("INSERT INTO mad_v1_media_jobs(job_id,upload_id,prompt,rights_confirmed,people_consent,external_ai_approved,state,created_at,updated_at,expires_at) VALUES (?,?,?,1,1,1,'queued',?,?,?)").bind(job,asset.upload_id,prompt,now,now,now+172800),
  db.prepare("INSERT INTO mad_v1_versions(version_id,project_id,created_at) VALUES (?,?,?)").bind(job,id,now),
  db.prepare("UPDATE mad_v1_projects SET updated_at=? WHERE id=?").bind(now,id)]);
 }catch{return respond({error:{message:"Another render is active; see Renders and retry"}},409)}
 let wake;try{wake=await wakeMediaJob(env,job)}catch{wake={state:'failed',last_error_code:'WAKE_STATE_UNAVAILABLE'}}
 return respond({job_id:job,project_id:id,state:"queued",wake,review_only:true},201);
}
