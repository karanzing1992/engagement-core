// Private V5 media vault: R2-backed upload, download, and expiring previews.
// Required bindings: MEDIA (R2), VAULT_TOKEN (secret), SIGNING_KEY (secret).
const enc = new TextEncoder();
const json = (x, status=200) => new Response(JSON.stringify(x), {status, headers:{'content-type':'application/json','cache-control':'no-store'}});
const keyOk = key => /^(source|render)\/[a-zA-Z0-9][a-zA-Z0-9._/-]{0,180}\.mp4$/.test(key) && !key.split('/').includes('..');
const equal = (a,b) => { if(a.length!==b.length)return false;let x=0;for(let i=0;i<a.length;i++)x|=a.charCodeAt(i)^b.charCodeAt(i);return x===0; };
const hex = a => Array.from(new Uint8Array(a)).map(v=>v.toString(16).padStart(2,'0')).join('');
async function sign(secret, msg) {const k=await crypto.subtle.importKey('raw',enc.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);return hex(await crypto.subtle.sign('HMAC',k,enc.encode(msg)));}
export default {
 async fetch(req,env) {
  const u=new URL(req.url), path=u.pathname;
  if(path==='/health')return json({service:'v5-private-media-vault',storage:!!env.MEDIA,ready:!!(env.MEDIA&&env.VAULT_TOKEN&&env.SIGNING_KEY)});
  if(!env.MEDIA||!env.VAULT_TOKEN||!env.SIGNING_KEY)return json({error:'VAULT_NOT_CONFIGURED'},503);
  if(path==='/sign'&&req.method==='POST') {
   if(!equal(req.headers.get('authorization')||'', 'Bearer '+env.VAULT_TOKEN))return json({error:'unauthorized'},401);
   const body=await req.json().catch(()=>null),key=body?.key,ttl=Math.min(Math.max(Number(body?.ttl||600),30),3600);
   if(typeof key!=='string'||!keyOk(key))return json({error:'invalid_key'},400);
   const exp=Math.floor(Date.now()/1000)+ttl,signature=await sign(env.SIGNING_KEY,`GET\n${key}\n${exp}`);
   return json({url:`${u.origin}/objects/${key}?exp=${exp}&sig=${signature}`,expires_at:exp});
  }
  if(path.startsWith('/objects/')) {
   const key=decodeURIComponent(path.slice('/objects/'.length));
   if(!keyOk(key))return json({error:'invalid_key'},400);
   if(req.method==='PUT') {
    if(!equal(req.headers.get('authorization')||'', 'Bearer '+env.VAULT_TOKEN))return json({error:'unauthorized'},401);
    if(req.headers.get('content-type')?.split(';')[0]!=='video/mp4')return json({error:'mp4_only'},415);
    if(!req.body)return json({error:'missing_body'},400);
    const result=await env.MEDIA.put(key,req.body,{httpMetadata:{contentType:'video/mp4'},customMetadata:{origin:'v5-private-vault'}});
    return json({key,size:result.size,etag:result.httpEtag},201);
   }
   if(req.method==='GET'||req.method==='HEAD') {
    const auth=equal(req.headers.get('authorization')||'', 'Bearer '+env.VAULT_TOKEN);
    let allowed=auth;
    if(!allowed){
     const exp=Number(u.searchParams.get('exp')),sig=u.searchParams.get('sig')||'';
     if(Number.isSafeInteger(exp)&&exp>Math.floor(Date.now()/1000)&&exp<=Math.floor(Date.now()/1000)+3600){
      const expected=await sign(env.SIGNING_KEY,`GET\n${key}\n${exp}`);
      allowed=equal(sig,expected);
     }
    }
    if(!allowed)return json({error:'unauthorized'},401);
    const range=req.headers.get('range');
    const object=await env.MEDIA.get(key,range?{range:req.headers}:{});
    if(!object)return json({error:'not_found'},404);
    const headers=new Headers({'content-type':'video/mp4','cache-control':'private, no-store','accept-ranges':'bytes','x-content-type-options':'nosniff','content-disposition':'inline'});
    object.writeHttpMetadata(headers);
    headers.set('etag',object.httpEtag);
    const partial=!!range&&object.range&&typeof object.range.offset==='number';
    if(partial){const offset=object.range.offset;headers.set('content-range',`bytes ${offset}-${offset+object.range.length-1}/${object.size}`);headers.set('content-length',String(object.range.length));}
    else headers.set('content-length',String(object.size));
    return new Response(req.method==='HEAD'?null:object.body,{status:partial?206:200,headers});
   }
  }
  return json({error:'not_found'},404);
 }
};
