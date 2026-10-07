const PROJECT='https://saczglesalubroyaucqe.supabase.co';
const REGISTER=PROJECT+'/auth/v1/oauth/clients/register';
const AUTHORIZE=PROJECT+'/auth/v1/oauth/authorize';
const TOKEN=PROJECT+'/auth/v1/oauth/token';
const MCP=PROJECT+'/functions/v1/wpcontrol-mcp/mcp';
const REDIRECT=location.origin+'/canary.html';
const TITLE='WP Control Canary — 2026-10-07 — Safe Reversible Test';
const status=document.querySelector('#status');
const start=document.querySelector('#start');
let rpcId=1;

const say=(data,ok=true)=>{
  status.className=ok?'ok':'bad';
  status.textContent=typeof data==='string'?data:JSON.stringify(data,null,2);
};
const b64url=(bytes)=>btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const randomString=(n=48)=>b64url(crypto.getRandomValues(new Uint8Array(n)));
async function challenge(verifier){
  return b64url(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))));
}
async function startFlow(){
  start.disabled=true;say('Registering a short-lived public PKCE client…');
  const verifier=randomString(48),state=randomString(24);
  const reg=await fetch(REGISTER,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({
    client_name:'WP Control Browser E2E Canary',
    redirect_uris:[REDIRECT],
    token_endpoint_auth_method:'none',
    grant_types:['authorization_code','refresh_token'],
    response_types:['code']
  })});
  if(!reg.ok) throw new Error('dynamic_client_registration_'+reg.status);
  const client=await reg.json();
  sessionStorage.setItem('wpcontrol_canary',JSON.stringify({verifier,state,client_id:client.client_id}));
  const u=new URL(AUTHORIZE);
  u.searchParams.set('response_type','code');
  u.searchParams.set('client_id',client.client_id);
  u.searchParams.set('redirect_uri',REDIRECT);
  u.searchParams.set('state',state);
  u.searchParams.set('code_challenge',await challenge(verifier));
  u.searchParams.set('code_challenge_method','S256');
  u.searchParams.set('scope','email offline_access');
  location.assign(u.toString());
}
async function tokenExchange(code,state){
  const saved=JSON.parse(sessionStorage.getItem('wpcontrol_canary')||'null');
  if(!saved||saved.state!==state) throw new Error('oauth_state_mismatch');
  const p=new URLSearchParams({
    grant_type:'authorization_code',code,client_id:saved.client_id,
    redirect_uri:REDIRECT,code_verifier:saved.verifier
  });
  const r=await fetch(TOKEN,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:p});
  if(!r.ok) throw new Error('token_exchange_'+r.status);
  const t=await r.json();
  if(!t.access_token||!t.refresh_token) throw new Error('missing_oauth_tokens');
  const p2=new URLSearchParams({grant_type:'refresh_token',refresh_token:t.refresh_token,client_id:saved.client_id});
  const rr=await fetch(TOKEN,{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:p2});
  if(!rr.ok) throw new Error('refresh_grant_'+rr.status);
  const t2=await rr.json();
  if(!t2.access_token||!t2.refresh_token) throw new Error('missing_refreshed_tokens');
  sessionStorage.removeItem('wpcontrol_canary');
  return {access:t2.access_token,refresh_ok:true,scope:t2.scope||t.scope||''};
}
async function mcp(access,name,args={}){
  const r=await fetch(MCP,{method:'POST',headers:{
    authorization:'Bearer '+access,'content-type':'application/json','accept':'application/json, text/event-stream'
  },body:JSON.stringify({jsonrpc:'2.0',id:rpcId++,method:'tools/call',params:{name,arguments:args}})});
  if(!r.ok) throw new Error(name+'_http_'+r.status);
  const body=await r.json();
  if(body.error) throw new Error(name+'_rpc_'+(body.error.code||'error'));
  if(body.result?.isError){
    const msg=body.result?.content?.[0]?.text||name+'_failed';
    throw new Error(name+'_'+msg.replace(/[^a-zA-Z0-9_. -]/g,'').slice(0,160));
  }
  return body.result?.structuredContent?.data ?? body.result;
}
function rows(v){
  if(Array.isArray(v)) return v;
  if(!v||typeof v!=='object') return [];
  for(const key of ['items','changes','data','results']){
    const nested=rows(v[key]);
    if(nested.length) return nested;
  }
  return [];
}
function changeIdFrom(v){
  if(!v||typeof v!=='object') return null;
  if(Number.isInteger(Number(v.change_id))&&Number(v.change_id)>0) return Number(v.change_id);
  for(const value of Object.values(v)){
    const found=changeIdFrom(value);
    if(found) return found;
  }
  return null;
}
async function runCanary(access,oauthMeta){
  const report={oauth_code_exchange:true,oauth_refresh:oauthMeta.refresh_ok,oauth_scope:oauthMeta.scope};
  const profile=await mcp(access,'get_profile',{});
  report.profile_ok=!!profile;
  const sites=await mcp(access,'list_sites',{});
  const siteRows=rows(sites);
  report.site_count=siteRows.length;
  if(!siteRows.length) throw new Error('no_connected_sites');
  const site=siteRows.find(s=>String(s.base_url||'').includes('mokshagoa.com'))||siteRows[0];
  const siteId=site.id;
  const overview=await mcp(access,'site_overview',{site_id:siteId});
  report.overview_ok=!!overview;
  report.site_id_matches=siteId==='79e365b9-fdbb-42cc-82c4-78d7fb8d344f';

  const created=await mcp(access,'create_content',{
    site_id:siteId,title:TITLE,content:'Temporary reversible WP Control end-to-end canary.',post_type:'post',status:'draft'
  });
  report.draft_created=!!created;

  const changes=await mcp(access,'list_changes',{site_id:siteId,status:'active',page:1,per_page:50});
  const changeRows=rows(changes);
  report.active_changes_seen=changeRows.length;
  let changeId=changeIdFrom(created);
  if(!changeId){
    const candidate=changeRows.find(c=>JSON.stringify(c).includes(TITLE))||changeRows[0];
    changeId=changeIdFrom(candidate)||(candidate&&Number(candidate.id)>0?Number(candidate.id):null);
  }
  if(!changeId) throw new Error('canary_change_not_found');
  report.change_id_from_write=!!changeIdFrom(created);
  report.change_visible_in_journal=changeRows.some(c=>Number(c.change_id??c.id)===Number(changeId)||JSON.stringify(c).includes(TITLE));

  const undone=await mcp(access,'undo_change',{site_id:siteId,change_id:Number(changeId),force:false});
  report.undo_ok=!!undone;

  const verify=await mcp(access,'list_content',{site_id:siteId,post_type:'post',status:'draft',search:TITLE,page:1,per_page:20});
  const matches=rows(verify).filter(x=>String(x.title||'')===TITLE);
  report.remaining_exact_drafts=matches.length;
  report.verify_removed=matches.length===0;
  return report;
}
async function boot(){
  const q=new URLSearchParams(location.search),code=q.get('code'),state=q.get('state'),error=q.get('error');
  if(error){say({ok:false,error:'oauth_'+error},false);return}
  if(!code){start.addEventListener('click',()=>startFlow().catch(e=>say({ok:false,error:e.message},false)));return}
  start.hidden=true;
  try{
    say('Exchanging OAuth code and testing refresh…');
    const auth=await tokenExchange(code,state);
    history.replaceState({},'',location.pathname);
    say('Running authenticated MCP canary…');
    const report=await runCanary(auth.access,auth);
    say({ok:report.oauth_code_exchange&&report.oauth_refresh&&report.overview_ok&&report.draft_created&&report.undo_ok&&report.verify_removed,...report},report.verify_removed);
  }catch(e){
    history.replaceState({},'',location.pathname);
    say({ok:false,error:String(e.message||e)},false);
  }
}
boot();
