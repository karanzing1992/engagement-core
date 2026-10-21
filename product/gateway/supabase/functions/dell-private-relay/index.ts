import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {createClient} from "npm:@supabase/supabase-js@2.75.0";
const BASE=Deno.env.get("SUPABASE_URL")||"",SRV=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"",ANON=Deno.env.get("SUPABASE_ANON_KEY")||"";
const db=createClient(BASE,SRV,{auth:{persistSession:false,autoRefreshToken:false}});
const HOST="dell-linux";
const PAGE="<!doctype html><html><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Dell Private Login</title><style>body{font:15px system-ui;background:#101820;color:white;margin:12px}input,button{padding:10px;margin:4px;background:#283847;color:white;border:1px solid #789}img{width:100%;max-width:1280px;touch-action:none}#screen{display:none}</style><h3>Dell Private Login</h3><section id=\"login\"><input id=\"email\" placeholder=\"Registered email\"><button id=\"send\">Send code</button><input id=\"code\" placeholder=\"Email code\"><button id=\"verify\">Verify</button></section><section id=\"screen\"><p id=\"state\">Connecting...</p><img id=\"view\"><p><input id=\"text\" placeholder=\"Type into focused website field\" autocomplete=\"off\"><button id=\"type\">Send encrypted input</button><button id=\"enter\">Enter</button><button id=\"tab\">Tab</button><button id=\"logout\">Sign out</button></p></section><script type=\"module\">\nimport {createClient} from 'https://esm.sh/@supabase/supabase-js@2.75.0';\nconst sb=createClient('__BASE__','__ANON__'),$=id=>document.getElementById(id),root=location.href.replace(/\\/$/,'');let key=null;\nasync function api(p,options={}){let t=(await sb.auth.getSession()).data.session?.access_token;if(!t)throw Error('Sign in required');let r=await fetch(root+p,{...options,headers:{authorization:'Bearer '+t,'content-type':'application/json'},cache:'no-store'});if(!r.ok)throw Error('HTTP '+r.status);return r.json()}\n$('send').onclick=async()=>{let r=await sb.auth.signInWithOtp({email:$('email').value});alert(r.error?.message||'Check email for your code')};\n$('verify').onclick=async()=>{let r=await sb.auth.verifyOtp({email:$('email').value,token:$('code').value,type:'email'});r.error?alert(r.error.message):start()};\n$('logout').onclick=async()=>{const {error}=await sb.auth.signOut({scope:'local'});if(error){console.error('Local sign-out failed');return;}location.reload()};\nfunction b64(b){let a=new Uint8Array(b),s='';for(let i=0;i<a.length;i++)s+=String.fromCharCode(a[i]);return btoa(s)}\nasync function encrypted(payload){if(!key)throw Error('Dell key not available');let peer=await crypto.subtle.importKey('jwk',key,{name:'ECDH',namedCurve:'P-256'},false,[]),own=await crypto.subtle.generateKey({name:'ECDH',namedCurve:'P-256'},true,['deriveKey']);let aes=await crypto.subtle.deriveKey({name:'ECDH',public:peer},own.privateKey,{name:'AES-GCM',length:256},false,['encrypt']);let iv=crypto.getRandomValues(new Uint8Array(12));let ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv},aes,new TextEncoder().encode(JSON.stringify(payload)));await api('/input',{method:'POST',body:JSON.stringify({jwk:await crypto.subtle.exportKey('jwk',own.publicKey),iv:b64(iv),ciphertext:b64(ciphertext)})})}\nasync function refresh(){try{let d=await api('/state');key=d.public_key;if(d.frame)$('view').src='data:image/jpeg;base64,'+d.frame;$('state').textContent=d.frame_age_seconds==null?'Preparing desktop':'Last frame '+d.frame_age_seconds+'s ago'}catch(e){$('state').textContent=e.message}}\nasync function start(){try{await api('/state');$('login').style.display='none';$('screen').style.display='block';await refresh();setInterval(refresh,2000)}catch(e){alert('Owner access denied: '+e.message)}}\n$('view').onclick=e=>{let r=e.target.getBoundingClientRect();encrypted({kind:'click',x:Math.round((e.clientX-r.left)/r.width*1280),y:Math.round((e.clientY-r.top)/r.height*800)}).catch(e=>alert(e.message))};\n$('type').onclick=()=>{encrypted({kind:'type',text:$('text').value}).then(()=>$('text').value='').catch(e=>alert(e.message))};\n$('enter').onclick=()=>encrypted({kind:'key',key:'Return'}).catch(e=>alert(e.message));\n$('tab').onclick=()=>encrypted({kind:'key',key:'Tab'}).catch(e=>alert(e.message));\nstart().catch(()=>{});\n</script></html>";
const json=(x:any,status=200)=>new Response(JSON.stringify(x),{status,headers:{"content-type":"application/json","cache-control":"no-store","x-content-type-options":"nosniff","access-control-allow-origin":"null","access-control-allow-headers":"authorization,content-type","access-control-allow-methods":"GET,POST,OPTIONS","vary":"Origin"}});
const bearer=(r:Request)=>(r.headers.get("authorization")||"").match(/^Bearer\s+(\S+)$/i)?.[1]||"";
async function digest(s:string){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(s))),x=>x.toString(16).padStart(2,"0")).join("")}
async function owner(r:Request){
 const t=bearer(r);if(!t)return null;
 const v=await fetch(BASE+"/auth/v1/user",{headers:{apikey:ANON,authorization:"Bearer "+t}});if(!v.ok)return null;
 const u=await v.json();if(!u?.id)return null;
 const m=await db.from("generic_auto_members").select("user_id").eq("user_id",u.id).eq("role","owner").eq("enabled",true).maybeSingle();
 const h=await db.from("generic_auto_hosts").select("host_id").eq("host_id",HOST).eq("owner_id",u.id).eq("enabled",true).maybeSingle();
 return m.data&&h.data?u.id:null;
}
async function worker(r:Request){
 const t=bearer(r);if(t.length<40||t.length>256)return null;
 const h=await db.from("generic_auto_desktop_workers").select("owner_id").eq("host_id",HOST).eq("token_hash",await digest(t)).eq("enabled",true).maybeSingle();return h.data?.owner_id||null;
}
Deno.serve(async(r:Request)=>{
try{
 if(r.method==="OPTIONS")return new Response(null,{status:204,headers:{"access-control-allow-origin":"null","access-control-allow-headers":"authorization,content-type","access-control-allow-methods":"GET,POST,OPTIONS","cache-control":"no-store"}});
 const p=new URL(r.url).pathname.replace(/^\/(?:functions\/v1\/)?dell-private-relay/,"")||"/";
 if(p==="/"&&r.method==="GET")return new Response(PAGE.replace("__BASE__",BASE).replace("__ANON__",ANON),{headers:{"content-type":"text/html; charset=utf-8","cache-control":"no-store","referrer-policy":"no-referrer","x-frame-options":"DENY","content-security-policy":"default-src 'self' https://esm.sh; script-src 'self' 'unsafe-inline' https://esm.sh; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://esm.sh "+BASE+"; frame-ancestors 'none'"}});
 if(p.startsWith("/worker/")){
  const uid=await worker(r);if(!uid)return json({error:"unauthorized_worker"},401);
  if(p==="/worker/frame"&&r.method==="POST"){
   const b=await r.json();if(typeof b.frame!=="string"||b.frame.length>260000||b.public_key?.crv!=="P-256")return json({error:"bad_frame"},400);
   const z=await db.from("generic_auto_desktop_state").upsert({host_id:HOST,owner_id:uid,frame_b64:b.frame,frame_at:new Date().toISOString(),worker_public_jwk:b.public_key,enabled:true},{onConflict:"host_id"});return z.error?json({error:"storage_failed"},500):json({ok:true});
  }
  if(p==="/worker/poll"&&r.method==="POST"){
   const x=await db.from("generic_auto_desktop_inputs").select("id,cipher_json").eq("host_id",HOST).eq("owner_id",uid).eq("status","queued").gte("created_at",new Date(Date.now()-120000).toISOString()).order("created_at").limit(1);
   if(!x.data?.length)return json({command:null});
   const a=x.data[0],v=await db.from("generic_auto_desktop_inputs").delete().eq("id",a.id).eq("status","queued").select("id").maybeSingle();
   return json({command:v.data?a:null});
  }
  return json({error:"not_found"},404);
 }
 const uid=await owner(r);if(!uid)return json({error:"owner_authorization_required"},401);
 if(p==="/state"&&r.method==="GET"){
  const z=await db.from("generic_auto_desktop_state").select("frame_b64,frame_at,worker_public_jwk,enabled").eq("host_id",HOST).eq("owner_id",uid).maybeSingle();
  return json({frame:z.data?.enabled&&z.data?.frame_at&&Date.now()-Date.parse(z.data.frame_at)<30000?z.data.frame_b64:null,public_key:z.data?.worker_public_jwk||null,frame_age_seconds:z.data?.frame_at?Math.floor((Date.now()-Date.parse(z.data.frame_at))/1000):null});
 }
 if(p==="/input"&&r.method==="POST"){
  const b=await r.json();if(JSON.stringify(b).length>7000||b.jwk?.crv!=="P-256"||typeof b.ciphertext!=="string"||typeof b.iv!=="string")return json({error:"invalid_input"},400);
  const count=await db.from("generic_auto_desktop_inputs").select("id",{head:true,count:"exact"}).eq("host_id",HOST).eq("owner_id",uid).eq("status","queued");
  if((count.count||0)>20)return json({error:"too_many_pending"},429);
  const x=await db.from("generic_auto_desktop_inputs").insert({host_id:HOST,owner_id:uid,cipher_json:{jwk:b.jwk,iv:b.iv,ciphertext:b.ciphertext}});
  return x.error?json({error:"queue_failed"},500):json({ok:true});
 }
 return json({error:"not_found"},404);
}catch{return json({error:"internal_error"},500)}
});