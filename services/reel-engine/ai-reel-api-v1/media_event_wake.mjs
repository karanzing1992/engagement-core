/**
 * MAD V5 event-driven private render wake.
 *
 * A successful GitHub 204 means "workflow accepted", NOT "render started".
 * All source files stay in private KV; no source, prompt or token in dispatch.
 * Requires MAD_GITHUB_ACTIONS_DISPATCH_TOKEN (GitHub App installation token or
 * fine-grained token scoped to Actions:write on karanzing1992/engagement-core).
 * D1 migration 011_event_wake.sql MUST be deployed before enabling this code.
 */
const WAKE_ENDPOINT='https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v5-cloudflare-bridge.yml/dispatches';
const ID=/^madmedia-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const TERMINAL=new Set(['review_ready','failed']);
function safe(r){
  if(!r)return {state:'not_requested',attempts:0};
  return {state:r.state,attempts:r.attempts,last_error_code:r.last_error_code||null,
    dispatched_at:r.dispatched_at||null,last_http_status:r.last_http_status||null};
}
export async function readMediaWake(db,id){
  if(!ID.test(id))return {state:'invalid',attempts:0};
  const r=await db.prepare('SELECT state,attempts,last_error_code,dispatched_at,last_http_status FROM mad_v1_media_wakes WHERE job_id=?').bind(id).first();
  return safe(r);
}
export async function wakeMediaJob(env,id){
  if(!ID.test(id))return {state:'invalid',attempts:0};
  const db=env.DB,now=Math.floor(Date.now()/1000);
  const job=await db.prepare('SELECT state,expires_at FROM mad_v1_media_jobs WHERE job_id=?').bind(id).first();
  if(!job)return {state:'missing',attempts:0};
  if(job.state!=='queued'||job.expires_at<=now)
    return {state:TERMINAL.has(job.state)?'already_finished':'not_queued',attempts:0};
  await db.prepare(
    "INSERT OR IGNORE INTO mad_v1_media_wakes(job_id,state,attempts,created_at,updated_at) VALUES (?,'pending',0,?,?)"
  ).bind(id,now,now).run();
  // Atomic lease; duplicate clicks or concurrent submits do not dispatch twice.
  // An ambiguous network result may be retried only after 90 seconds.
  const leased=await db.prepare(
    "UPDATE mad_v1_media_wakes SET state='dispatching',attempts=attempts+1,last_attempt_at=?,updated_at=?,last_error_code=NULL,last_http_status=NULL WHERE job_id=? AND attempts<4 AND (state='pending' OR (state='failed' AND last_attempt_at<?) OR (state='dispatching' AND last_attempt_at<?))"
  ).bind(now,now,id,now-30,now-90).run();
  if(!leased.meta?.changes)return readMediaWake(db,id);
  let status=null,code=null;
  const token=env.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN;
  if(typeof token!=='string'||token.length<30)code='GITHUB_DISPATCH_CREDENTIAL_UNCONFIGURED';
  else{
    try{
      const res=await fetch(WAKE_ENDPOINT,{
        method:'POST',redirect:'error',
        headers:{'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
          'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json',
          'User-Agent':'MAD-V5-Private-Render-Waker/1'},
        body:JSON.stringify({ref:'main',inputs:{media_job_id:id}}),
        signal:AbortSignal.timeout(8000)
      });
      status=res.status;
      if(status!==204)code=status===401||status===403?'GITHUB_DISPATCH_AUTH_REJECTED':
        status===404?'GITHUB_DISPATCH_WORKFLOW_NOT_FOUND':status===422?'GITHUB_DISPATCH_INVALID_INPUT':
        status===429?'GITHUB_DISPATCH_RATE_LIMITED':'GITHUB_DISPATCH_HTTP_ERROR';
    }catch{code='GITHUB_DISPATCH_NETWORK_ERROR';}
  }
  if(code){
    await db.prepare("UPDATE mad_v1_media_wakes SET state='failed',last_error_code=?,last_http_status=?,updated_at=? WHERE job_id=? AND state='dispatching' AND last_attempt_at=?")
      .bind(code,status,now,id,now).run();
  }else{
    await db.prepare("UPDATE mad_v1_media_wakes SET state='dispatched',dispatched_at=?,last_http_status=204,last_error_code=NULL,updated_at=? WHERE job_id=? AND state='dispatching' AND last_attempt_at=?")
      .bind(now,now,id,now).run();
  }
  return readMediaWake(db,id);
}
