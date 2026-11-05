/**
 * Owner-only, event-driven wake and durable reconciliation.
 *
 * The D1 media queue is authoritative. GitHub 204 = "dispatch accepted", not
 * a completed render. A transient/GitHub-side lost event cannot strand a job:
 * Cloudflare cron retries queued jobs after a bounded grace period. No source,
 * prompt, private media or secret is sent in the dispatch payload.
 */
const WAKE_ENDPOINT='https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v5-cloudflare-bridge.yml/dispatches';
const ID=/^madmedia-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const TERMINAL=new Set(['review_ready','failed']);
const MAX_ATTEMPTS=4;
const FAILED_BACKOFF=90;
const INFLIGHT_STALE=120;
const DISPATCH_STALE=480;
function configured(e){return typeof e?.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN==='string' && e.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN.length>=30;}
function safe(r){
  if(!r)return {state:'not_requested',attempts:0};
  return {state:r.state,attempts:r.attempts,last_error_code:r.last_error_code||null,
    dispatched_at:r.dispatched_at||null,last_http_status:r.last_http_status||null};
}
export async function readMediaWake(db,id){
  if(!ID.test(id))return {state:'invalid',attempts:0};
  return safe(await db.prepare('SELECT state,attempts,last_error_code,dispatched_at,last_http_status FROM mad_v1_media_wakes WHERE job_id=?').bind(id).first());
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
  // Missing operator credential is a configuration block, NOT a render retry.
  // Do not consume the finite retry budget before the secret is installed.
  if(!configured(env)){
    await db.prepare("UPDATE mad_v1_media_wakes SET last_error_code='GITHUB_DISPATCH_CREDENTIAL_UNCONFIGURED',updated_at=? WHERE job_id=? AND state IN ('pending','failed')")
      .bind(now,id).run();
    return readMediaWake(db,id);
  }
  const leased=await db.prepare(
    "UPDATE mad_v1_media_wakes SET state='dispatching',attempts=attempts+1,last_attempt_at=?,updated_at=?,last_error_code=NULL,last_http_status=NULL WHERE job_id=? AND attempts<? AND (state='pending' OR (state='failed' AND last_attempt_at<?) OR (state='dispatching' AND last_attempt_at<?) OR (state='dispatched' AND dispatched_at<?))"
  ).bind(now,now,id,MAX_ATTEMPTS,now-FAILED_BACKOFF,now-INFLIGHT_STALE,now-DISPATCH_STALE).run();
  if(!leased.meta?.changes)return readMediaWake(db,id);
  let http=null,error=null;
  try{
    const res=await fetch(WAKE_ENDPOINT,{
      method:'POST',redirect:'manual',
      headers:{'Authorization':'Bearer '+env.MAD_GITHUB_ACTIONS_DISPATCH_TOKEN,
        'Accept':'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28',
        'Content-Type':'application/json',
        'User-Agent':'MAD-V5-Private-Render-Waker/2'},
      body:JSON.stringify({ref:'main',inputs:{media_job_id:id}}),
      signal:AbortSignal.timeout(8000)
    });
    http=res.status;
    if(http!==204)error=http>=300&&http<400?'GITHUB_DISPATCH_UNEXPECTED_REDIRECT':
      http===401||http===403?'GITHUB_DISPATCH_AUTH_REJECTED':
      http===404?'GITHUB_DISPATCH_WORKFLOW_NOT_FOUND':
      http===422?'GITHUB_DISPATCH_INVALID_INPUT':
      http===429?'GITHUB_DISPATCH_RATE_LIMITED':'GITHUB_DISPATCH_HTTP_ERROR';
  }catch(e){
    // Workers rejects redirect:'error' before network I/O. Never log exception
    // messages: failed fetch details can carry sensitive request context.
    error=e?.name==='TimeoutError'||e?.name==='AbortError'?'GITHUB_DISPATCH_TIMEOUT':
      e?.name==='TypeError'?'GITHUB_DISPATCH_FETCH_TYPE_ERROR':'GITHUB_DISPATCH_NETWORK_ERROR';
  }
  if(error){
    await db.prepare("UPDATE mad_v1_media_wakes SET state='failed',last_error_code=?,last_http_status=?,updated_at=? WHERE job_id=? AND state='dispatching' AND last_attempt_at=?")
      .bind(error,http,now,id,now).run();
  }else{
    await db.prepare("UPDATE mad_v1_media_wakes SET state='dispatched',dispatched_at=?,last_http_status=204,last_error_code=NULL,updated_at=? WHERE job_id=? AND state='dispatching' AND last_attempt_at=?")
      .bind(now,now,id,now).run();
  }
  return readMediaWake(db,id);
}
/** Only a recovery watchdog. Normal requests dispatch immediately after insert. */
export async function recoverPendingWakes(env,limit=2){
  if(!env.DB)return {status:'database_unavailable',checked:0};
  if(!configured(env))return {status:'dispatch_key_not_configured',checked:0};
  const now=Math.floor(Date.now()/1000);
  const take=Math.max(1,Math.min(3,limit|0));
  const rows=await env.DB.prepare(
    "SELECT j.job_id FROM mad_v1_media_jobs AS j LEFT JOIN mad_v1_media_wakes AS w ON w.job_id=j.job_id WHERE j.state='queued' AND j.expires_at>? AND (w.job_id IS NULL OR (w.attempts<? AND (w.state='pending' OR (w.state='failed' AND w.last_attempt_at<?) OR (w.state='dispatching' AND w.last_attempt_at<?) OR (w.state='dispatched' AND w.dispatched_at<?)))) ORDER BY j.created_at LIMIT ?"
  ).bind(now,MAX_ATTEMPTS,now-FAILED_BACKOFF,now-INFLIGHT_STALE,now-DISPATCH_STALE,take).all();
  const ids=(rows.results||[]).map(r=>r.job_id).filter(id=>ID.test(id));
  const results=[];
  for(const id of ids){
    // Re-check D1 state and take an atomic wake lease per job.
    results.push((await wakeMediaJob(env,id)).state);
  }
  return {status:'checked',checked:ids.length,results};
}
