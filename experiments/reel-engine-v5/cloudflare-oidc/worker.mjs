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
export default {async fetch(request,env){
 const u=new URL(request.url);
 if(u.pathname==='/health'&&request.method==='GET')return json({service:'MAD V5 Cloudflare OIDC GitHub Bridge',status:'staging',mode:'synthetic_only',database_bound:!!env.DB,github_auth:'oidc_rs256_pinned_workflow',model_credentials:'remain_in_github_actions',real_guest_media_enabled:false});
 if(!env.DB)return json({error:'Database unavailable'},503);
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