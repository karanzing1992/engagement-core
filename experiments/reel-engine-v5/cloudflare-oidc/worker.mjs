// MAD V5 Cloudflare D1 queue; GitHub OIDC only. Synthetic data only, no guest media.
const ISSUER='https://token.actions.githubusercontent.com';
const JWKS=ISSUER+'/.well-known/jwks';
const AUDIENCE='mad-v5-cloudflare-bridge/v1';
const REPO='karanzing1992/engagement-core';
const REPO_ID='1403281267',OWNER_ID='30191163',REF='refs/heads/main';
const WORKFLOW_REF=REPO+'/.github/workflows/mad-v5-cloudflare-bridge.yml@'+REF;
const enc=new TextEncoder(),dec=new TextDecoder();
function json(v,status=200){return new Response(JSON.stringify(v),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff','x-frame-options':'DENY','referrer-policy':'no-referrer'}})}
function b64(s){if(typeof s!=='string'||!/^[A-Za-z0-9_-]+$/.test(s)||s.length>8192)throw Error('Invalid JWT');return Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-s.length%4)%4)),c=>c.charCodeAt(0))}
function part(s){return JSON.parse(dec.decode(b64(s)))}
function validClaims(c){const n=Math.floor(Date.now()/1000);return !!c&&c.iss===ISSUER&&c.aud===AUDIENCE&&c.repository===REPO&&String(c.repository_id)===REPO_ID&&String(c.repository_owner_id)===OWNER_ID&&c.ref===REF&&c.workflow_ref===WORKFLOW_REF&&c.runner_environment==='github-hosted'&&['schedule','workflow_dispatch','issues'].includes(c.event_name)&&Number.isFinite(c.iat)&&Number.isFinite(c.exp)&&Number.isFinite(c.nbf)&&c.iat<=n+30&&c.nbf<=n+30&&c.exp>n&&c.exp-c.iat<=1200&&c.iat>=n-1200&&/^\d{5,15}$/.test(String(c.run_id))}
async function verify(request){
 const a=request.headers.get('authorization')||'';
 if(a.length>9000||!/^Bearer [A-Za-z0-9_.-]+$/.test(a))return null;
 const s=a.slice(7).split('.');if(s.length!==3||a.length>8507)return null;
 try{
  const h=part(s[0]),c=part(s[1]);
  if(h.alg!=='RS256'||typeof h.kid!=='string'||!/^[\w.-]{1,128}$/.test(h.kid)||!validClaims(c))return null;
  if(c.event_name==='issues'&&String(c.actor_id)!==OWNER_ID)return null;
  const r=await fetch(JWKS,{headers:{accept:'application/json'},redirect:'manual'});
  if(r.status!==200)return null;
  const keys=(await r.json()).keys;
  if(!Array.isArray(keys))return null;
  const k=keys.find(k=>k.kid===h.kid&&k.kty==='RSA'&&(!k.alg||k.alg==='RS256')&&k.n&&k.e);
  if(!k)return null;
  const key=await crypto.subtle.importKey('jwk',{kty:'RSA',n:k.n,e:k.e,alg:'RS256',ext:true},{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  if(!await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,b64(s[2]),enc.encode(s[0]+'.'+s[1])))return null;
  return c;
 }catch{return null}
}
async function parseBody(req){if((Number(req.headers.get('content-length'))||0)>4096)throw Error('Large body');const s=await req.text();if(s.length>4096)throw Error('Large body');const data=JSON.parse(s);if(!data||typeof data!=='object'||Array.isArray(data))throw Error('Malformed body');return data}
function validJob(a){
 return Number.isInteger(a.issue_number)&&a.issue_number>=1&&a.issue_number<=999999999&&a.project_id==='moksha_wellness'&&
 ['fixture','live','multimodal'].includes(a.mode)&&['synthetic_test','instagram_reel'].includes(a.profile)&&
 typeof a.prompt==='string'&&a.prompt.length>=12&&a.prompt.length<=600&&!/[\x00-\x08\x0e-\x1f]/.test(a.prompt)&&
 !/https?:\/\/|data:[^ ]+;base64|github_pat_|ghp_|sk-[A-Za-z0-9]{12}/i.test(a.prompt)&&
 Object.keys(a).every(k=>['issue_number','project_id','mode','profile','prompt'].includes(k));
}
async function enqueue(db,a){const now=Math.floor(Date.now()/1000),id='madcf-'+a.issue_number;const res=await db.prepare('INSERT INTO mad_v5_jobs (job_id,project_id,prompt,mode,profile,state,created_at,updated_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT (job_id) DO NOTHING').bind(id,a.project_id,a.prompt,a.mode,a.profile,'queued',now,now,now+86400).run();return {job_id:id,queued:!!res.meta?.changes,synthetic_only:true}}
async function claim(db){const n=Math.floor(Date.now()/1000),claim=crypto.randomUUID();const sql="UPDATE mad_v5_jobs SET state='claimed',claim_id=?,claimed_at=?,updated_at=?,attempts=attempts+1 WHERE job_id=(SELECT job_id FROM mad_v5_jobs WHERE (state='queued' OR (state='claimed' AND claimed_at < ?)) AND attempts<3 AND expires_at > ? ORDER BY created_at LIMIT 1) RETURNING job_id,project_id,prompt,mode,profile,claim_id,attempts";const row=await db.prepare(sql).bind(claim,n,n,n-2700,n).first();return {job:row||null,synthetic_only:true}}
async function complete(db,a,c){
 if(typeof a.job_id!=='string'||!/^(?:madcf-[1-9][0-9]{0,8}|madapp-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})$/.test(a.job_id)||!/^[a-f0-9-]{36}$/.test(a.claim_id||'')||!['passed','failed'].includes(a.status))throw Error('Invalid result');
 if(a.status==='passed'&&!/^[a-f0-9]{64}$/.test(a.sha256||''))throw Error('Missing hash');
 const now=Math.floor(Date.now()/1000);
 const sql="UPDATE mad_v5_jobs SET state=?,result_sha256=?,result_run=?,last_error=?,updated_at=? WHERE job_id=? AND claim_id=? AND state='claimed' AND claimed_at>? AND expires_at>?";
 const r=await db.prepare(sql).bind(a.status,a.status==='passed'?a.sha256:null,'https://github.com/'+REPO+'/actions/runs/'+c.run_id,a.status==='failed'?'REMOTE_SYNTHETIC_FAILURE':null,now,a.job_id,a.claim_id,now-2700,now).run();
 return {accepted:!!r.meta?.changes,job_id:a.job_id,synthetic_only:true};
}
async function status(db,id){if(!/^(?:madcf-[1-9][0-9]{0,8}|madapp-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12})$/.test(id))return null;return db.prepare('SELECT job_id,project_id,mode,profile,state,attempts,result_sha256,result_run,created_at,updated_at,expires_at FROM mad_v5_jobs WHERE job_id=?').bind(id).first()}

/* Media extension: only pinned GitHub-hosted main workflow, RS256 OIDC.
 * Private chunks never appear in public issues, logs or Actions artifacts.
 */
const MEDIA_CHUNK=4*1024*1024, MEDIA_MAX=80*1024*1024;
const MEDIA_JOB=/^madmedia-[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
function mediaKey(part,id,i){return 'private/mad-v1/'+part+'/'+id+'/'+i}
function mediaReady(j,now){return j&&j.state==='claimed'&&j.claimed_at>now-3300&&j.expires_at>now}
async function mediaBridge(req,env,url,claims){
 if(!env.MEDIA_KV)return json({error:'Media storage unavailable'},503);
 const now=Math.floor(Date.now()/1000),p=url.pathname.split('/').filter(Boolean);
 if(p[2]==='media-claim'&&p.length===3&&req.method==='POST'){
   if(claims.event_name!=='schedule'&&claims.event_name!=='workflow_dispatch'&&claims.event_name!=='issues')return json({error:'Denied'},403);
   const lease=crypto.randomUUID();
   const sql="UPDATE mad_v1_media_jobs SET state='claimed',claim_id=?,claimed_at=?,attempts=attempts+1,updated_at=? WHERE job_id=(SELECT job_id FROM mad_v1_media_jobs WHERE (state='queued' OR (state='claimed' AND claimed_at<?)) AND attempts<3 AND expires_at>? ORDER BY created_at LIMIT 1) RETURNING *";
   const j=await env.DB.prepare(sql).bind(lease,now,now,now-3300,now).first();
   if(!j)return json({job:null});
   const upload=await env.DB.prepare("SELECT id,bytes,sha256,mime,chunk_count,file_name FROM mad_v1_uploads WHERE id=? AND state='complete' AND expires_at>?").bind(j.upload_id,now).first();
   if(!upload)return json({error:'Source expired after claim'},409);
   return json({job:{job_id:j.job_id,claim_id:lease,prompt:j.prompt,upload_id:j.upload_id,source_bytes:upload.bytes,source_sha256:upload.sha256,source_mime:upload.mime,source_chunks:upload.chunk_count,source_name:upload.file_name,rights:{source_rights_confirmed:j.rights_confirmed===1,people_consent_confirmed:j.people_consent===1,external_ai_processing_approved:j.external_ai_approved===1}}});
 }
 if(p[2]==='media-source'&&p.length===5&&req.method==='GET'&&MEDIA_JOB.test(p[3])){
   const i=Number(p[4]);const lease=req.headers.get('x-mad-claim-id')||'';
   if(!Number.isInteger(i)||i<0||i>=20||!/^[a-f0-9-]{36}$/.test(lease))return json({error:'Invalid chunk'},400);
   const j=await env.DB.prepare("SELECT * FROM mad_v1_media_jobs WHERE job_id=? AND claim_id=?").bind(p[3],lease).first();
   if(!mediaReady(j,now))return json({error:'Stale claim'},403);
   const u=await env.DB.prepare("SELECT chunk_count FROM mad_v1_uploads WHERE id=? AND state='complete'").bind(j.upload_id).first();
   if(!u||i>=u.chunk_count)return json({error:'Chunk unavailable'},404);
   const has=await env.DB.prepare("SELECT bytes FROM mad_v1_source_chunks WHERE upload_id=? AND chunk_index=?").bind(j.upload_id,i).first();
   if(!has)return json({error:'Chunk not committed'},409);
   const bytes=await env.MEDIA_KV.get(mediaKey('source',j.upload_id,i),'arrayBuffer');
   if(!bytes)return json({error:'Chunk not propagated'},503);
   return new Response(bytes,{headers:{'content-type':'application/octet-stream','content-length':String(bytes.byteLength),'cache-control':'private, no-store'}});
 }
 if(p[2]==='media-output'&&p.length===5&&req.method==='PUT'&&MEDIA_JOB.test(p[3])){
   const i=Number(p[4]),lease=req.headers.get('x-mad-claim-id')||'',sha=req.headers.get('x-chunk-sha256')||'',n=Number(req.headers.get('content-length'));
   if(!Number.isInteger(i)||i<0||i>=20||!Number.isInteger(n)||n<1||n>MEDIA_CHUNK||!/^[a-f0-9]{64}$/.test(sha))return json({error:'Invalid output chunk'},400);
   const j=await env.DB.prepare("SELECT state,claim_id,claimed_at,expires_at FROM mad_v1_media_jobs WHERE job_id=?").bind(p[3]).first();
   if(!mediaReady(j,now)||j.claim_id!==lease)return json({error:'Stale output lease'},403);
   const existed=await env.DB.prepare("SELECT sha256 FROM mad_v1_output_chunks WHERE job_id=? AND chunk_index=?").bind(p[3],i).first();
   if(existed)return existed.sha256===sha?json({chunk_index:i,already_received:true}):json({error:'Output chunk conflict'},409);
   const b=await req.arrayBuffer();if(b.byteLength!==n)return json({error:'Output length mismatch'},400);
   const h=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(x=>x.toString(16).padStart(2,'0')).join('');
   if(h!==sha)return json({error:'Output integrity mismatch'},422);
   await env.MEDIA_KV.put(mediaKey('output',p[3],i),b,{expirationTtl:172800});
   const row=await env.DB.prepare("INSERT INTO mad_v1_output_chunks(job_id,chunk_index,sha256,bytes) VALUES (?,?,?,?) ON CONFLICT(job_id,chunk_index) DO NOTHING").bind(p[3],i,sha,n).run();
   return json({chunk_index:i,stored:!!row.meta?.changes});
 }
 if(p[2]==='media-complete'&&p.length===3&&req.method==='POST'){
   const a=await parseBody(req);
   if(!MEDIA_JOB.test(a.job_id||'')||!/^[a-f0-9-]{36}$/.test(a.claim_id||'')||!['review_ready','failed'].includes(a.status))return json({error:'Invalid completion'},400);
   const j=await env.DB.prepare("SELECT state,claim_id,claimed_at,expires_at FROM mad_v1_media_jobs WHERE job_id=?").bind(a.job_id).first();
   if(!mediaReady(j,now)||j.claim_id!==a.claim_id)return json({error:'Stale claim'},409);
   if(a.status==='review_ready'){
     if(!Number.isInteger(a.chunks)||a.chunks<1||a.chunks>20||!Number.isInteger(a.bytes)||a.bytes<1024||a.bytes>MEDIA_MAX||!/^[a-f0-9]{64}$/.test(a.sha256||''))return json({error:'Invalid render data'},400);
     const x=await env.DB.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(bytes),0) AS bytes FROM mad_v1_output_chunks WHERE job_id=?").bind(a.job_id).first();
     if(x.n!==a.chunks||x.bytes!==a.bytes)return json({error:'Incomplete output'},409);
     const rec=a.receipt;
     if(!rec||typeof rec!=='object'||rec.status!=='PRIVATE_REAL_MEDIA_TECHNICAL_DRAFT'||rec.video?.full_decode!==true||rec.video?.sha256!==a.sha256||rec.music_rights_certified!==false||rec.public_release_certified!==false)return json({error:'Invalid private review receipt'},400);
     const safe={
      status:rec.status,video:rec.video,
      creative_model_called:rec.creative_model_called===true,
      creative_plan_applied:rec.creative_plan_applied===true,
      planning_mode:['groq_v5_unapproved','source_only_fallback'].includes(rec.planning_mode)?rec.planning_mode:'unknown',
      creative_fallback_reason:[
        'director_auth_rejected','director_rate_limited','director_request_rejected',
        'director_plan_invalid','director_response_invalid','director_provider_failure',
        'director_credential_missing'
      ].includes(rec.creative_fallback_reason)?rec.creative_fallback_reason:null,
      director_attempts:Number.isInteger(rec.director_attempts)?Math.max(0,Math.min(3,rec.director_attempts)):0,
      vision_frames_sampled:Number.isInteger(rec.vision_frames_sampled)?Math.max(0,Math.min(8,rec.vision_frames_sampled)):0,
      vision_frames_captioned:Number.isInteger(rec.vision_frames_captioned)?Math.max(0,Math.min(8,rec.vision_frames_captioned)):0,
      vision_status:['no_vision_credential','no_vision_descriptions','descriptions_unreviewed'].includes(rec.vision_status)?rec.vision_status:'unknown',
      proposed_effects_not_executed:Number.isInteger(rec.proposed_effects_not_executed)?Math.max(0,Math.min(1600,rec.proposed_effects_not_executed)):0,
      applied_operations:['source_trim','concat','scale_crop','fade','static_opening_title'],
      soundtrack_source:'authorized_source_audio_only',
      music_rights_certified:false,artistic_quality_certified:false,public_release_certified:false,
      shot_count:rec.shot_count||0,
      toolchain:rec.creative_plan_applied===true?'V5 Groq edit plan + FFmpeg':'V5 FFmpeg fallback'
     };
     const x2=await env.DB.prepare("UPDATE mad_v1_media_jobs SET state='review_ready',result_bytes=?,result_sha256=?,result_chunks=?,result_receipt=?,updated_at=? WHERE job_id=? AND claim_id=? AND state='claimed'").bind(a.bytes,a.sha256,a.chunks,JSON.stringify(safe),now,a.job_id,a.claim_id).run();
     return json({accepted:!!x2.meta?.changes,state:'review_ready'});
   }
   const error=typeof a.error_code==='string'&&/^[A-Z0-9_]{1,64}$/.test(a.error_code)?a.error_code:'RENDER_FAILED';
   const x=await env.DB.prepare("UPDATE mad_v1_media_jobs SET state='failed',error_code=?,updated_at=? WHERE job_id=? AND claim_id=? AND state='claimed'").bind(error,now,a.job_id,a.claim_id).run();
   return json({accepted:!!x.meta?.changes,state:'failed'});
 }
 return json({error:'Unknown media bridge route'},404);
}

export default {async fetch(request,env){
 const u=new URL(request.url);
 if(u.pathname==='/health'&&request.method==='GET')return json({service:'MAD V5 Cloudflare OIDC GitHub Bridge',status:'staging',mode:'synthetic_and_owner_private_draft',private_owner_media_transfer_ready:!!env.MEDIA_KV,database_bound:!!env.DB,github_auth:'oidc_rs256_pinned_workflow',model_credentials:'remain_in_github_actions',real_guest_media_enabled:false});
 if(!env.DB)return json({error:'Database unavailable'},503);
 if(u.pathname.startsWith('/bridge/v1/media-')){
  const caller=await verify(request);if(!caller)return json({error:'Unauthorized'},401);
  try{return await mediaBridge(request,env,u,caller)}catch{return json({error:'Private media operation rejected'},400)}
 }
 if(!u.pathname.startsWith('/bridge/v1/'))return json({error:'Not found'},404);
 if(request.method!=='POST')return json({error:'Method not allowed'},405);
 const action=u.pathname.slice('/bridge/v1/'.length);
 if(!['enqueue','claim','complete','status'].includes(action))return json({error:'Not found'},404);
 const c=await verify(request);if(!c)return json({error:'Unauthorized'},401);
 if(action==='enqueue'&&c.event_name!=='issues')return json({error:'Unauthorized'},401);
 try{
  const a=await parseBody(request);
  if(action==='enqueue')return validJob(a)?json(await enqueue(env.DB,a),201):json({error:'Request rejected'},400);
  if(action==='claim')return Object.keys(a).length?json({error:'Request rejected'},400):json(await claim(env.DB));
  if(action==='complete')return Object.keys(a).some(k=>!['job_id','claim_id','status','sha256'].includes(k))?json({error:'Request rejected'},400):json(await complete(env.DB,a,c));
  if(action==='status')return json({job:await status(env.DB,a.job_id)});
 }catch{return json({error:'Request rejected'},400)}
 return json({error:'Not found'},404);
}};