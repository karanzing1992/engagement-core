// Mission Control encrypted Supabase replica, v1.
// Browser supplies only its short-lived WordPress Telegram OTP bearer.
// Edge Function validates it with WordPress and fetches the canonical tasks itself.
// No ChatGPT transcripts, credentials, PINs, OTPs or bearer tokens are persisted.
import { createClient } from "npm:@supabase/supabase-js@2.58.0";

const OWNER_ORIGIN = "https://mokshagoa.com";
const TASKS_URL = OWNER_ORIGIN + "/wp-json/mission-control/v1/tasks";
const te = new TextEncoder();
function json(body: Record<string, unknown>, status=200, origin=""): Response {
  const h: Record<string,string> = {"Content-Type":"application/json; charset=utf-8","Cache-Control":"private, no-store","Vary":"Origin","X-Content-Type-Options":"nosniff"};
  if(origin===OWNER_ORIGIN){h["Access-Control-Allow-Origin"]=OWNER_ORIGIN;h["Access-Control-Allow-Methods"]="GET, POST, OPTIONS";h["Access-Control-Allow-Headers"]="authorization, content-type";}
  return new Response(JSON.stringify(body),{status,headers:h});
}
function b64(bytes:Uint8Array):string {
  let raw="";for(let i=0;i<bytes.length;i+=8192)raw+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(raw);
}
async function ownerTasks(request:Request): Promise<{data:{version:number;entries:unknown[]}}|{error:string;status:number}> {
  const bearer=request.headers.get("authorization")||"";
  if(!/^Bearer [a-f0-9]{64}$/.test(bearer))return{error:"session_required",status:401};
  let r:Response;
  try {r=await fetch(TASKS_URL,{method:"GET",headers:{"Authorization":bearer,"Origin":OWNER_ORIGIN,"Accept":"application/json"},redirect:"error",cache:"no-store",signal:AbortSignal.timeout(12000)});}
  catch{return{error:"owner_auth_unavailable",status:503};}
  if(r.status===401||r.status===403)return{error:"session_invalid",status:401};
  if(!r.ok)return{error:"owner_index_unavailable",status:503};
  let raw:string;try{raw=await r.text();}catch{return{error:"owner_index_unavailable",status:503};}
  if(raw.length>1500000)return{error:"index_too_large",status:413};
  let parsed:unknown;try{parsed=JSON.parse(raw);}catch{return{error:"owner_index_invalid",status:503};}
  if(!parsed||typeof parsed!=="object")return{error:"owner_index_invalid",status:503};
  const index=parsed as {version?:unknown;entries?:unknown};
  if(typeof index.version!=="number"||!Number.isSafeInteger(index.version)||index.version<0||
     !Array.isArray(index.entries)||index.entries.length>5000)return{error:"owner_index_invalid",status:503};
  return{data:{version:index.version,entries:index.entries}};
}
async function backupKey(secret:string):Promise<CryptoKey>{
  const ikm=await crypto.subtle.importKey("raw",te.encode(secret),"HKDF",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"HKDF",hash:"SHA-256",salt:te.encode("bhm-mission-control-backup-v1"),info:te.encode("aes-gcm-owner-task-index")},ikm,{name:"AES-GCM",length:256},false,["encrypt"]);
}
Deno.serve(async (req:Request)=>{
  const origin=req.headers.get("origin")||"";
  if(origin&&origin!==OWNER_ORIGIN)return json({error:"origin_denied"},403);
  if(req.method==="OPTIONS"){
    return origin===OWNER_ORIGIN?new Response(null,{status:204,headers:{"Access-Control-Allow-Origin":OWNER_ORIGIN,"Access-Control-Allow-Methods":"GET, POST, OPTIONS","Access-Control-Allow-Headers":"authorization, content-type","Access-Control-Max-Age":"300","Vary":"Origin"}}):json({error:"origin_denied"},403);
  }
  const route=new URL(req.url).pathname.split("/").filter(Boolean).pop();
  if(route==="health"&&req.method==="GET")return json({ok:true,service:"mission-control-supabase-replica",version:1},200,origin);
  if(!((route==="snapshot"&&req.method==="POST")||(route==="status"&&req.method==="GET")))return json({error:"not_found"},404,origin);
  const auth=await ownerTasks(req);
  if("error" in auth)return json({error:auth.error},auth.status,origin);
  const dbURL=Deno.env.get("SUPABASE_URL")||"",serverSecret=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||"";
  if(!dbURL||!serverSecret)return json({error:"replica_not_configured"},503,origin);
  const db=createClient(dbURL,serverSecret,{auth:{persistSession:false,autoRefreshToken:false}});
  try{
    if(route==="status"){
      const {data,error}=await db.from("mission_control_v1_backups").select("version,item_count,updated_at").eq("vault_id","owner").maybeSingle();
      if(error)return json({error:"storage_unavailable"},503,origin);
      return json({ok:true,stored:!!data,version:data?.version??null,count:data?.item_count??0,updated_at:data?.updated_at??null,source:"supabase-replica"},200,origin);
    }
    const payload=JSON.stringify(auth.data);
    if(payload.length>1300000)return json({error:"index_too_large"},413,origin);
    const iv=crypto.getRandomValues(new Uint8Array(12)),version=auth.data.version;
    const cipher=new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM",iv,additionalData:te.encode("mission-control-v1:"+version)},await backupKey(serverSecret),te.encode(payload)));
    const {data,error}=await db.rpc("mission_control_v1_save_backup",{p_version:version,p_iv:b64(iv),p_ciphertext:b64(cipher),p_count:auth.data.entries.length});
    if(error)return json({error:"storage_unavailable"},503,origin);
    const receipt=Array.isArray(data)?data[0]:data;
    return json({ok:true,stored_version:Number(receipt?.current_version??version),saved:!!receipt?.saved,count:auth.data.entries.length,source:"wordpress-owner-verified"},200,origin);
  }catch{return json({error:"replica_unavailable"},503,origin);}
});
