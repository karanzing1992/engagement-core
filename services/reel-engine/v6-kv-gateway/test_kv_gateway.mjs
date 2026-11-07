import assert from "node:assert/strict";
import {test} from "node:test";
import {DatabaseSync} from "node:sqlite";
import {createHash,webcrypto} from "node:crypto";
import worker from "./worker.mjs";
const origin="https://mad-v6-owner-private-beta.pages.dev";
const base="https://mad-v6-kv-private-beta.karanbizweb360.workers.dev";
const owner="Bearer nk-"+("a".repeat(40));
const md=()=>Math.floor(Date.now()/1000);
const SHA=b=>createHash("sha256").update(Buffer.from(b)).digest("hex");
const bytes=Buffer.from("000000186674797069736f6d0000000069736f6d6d703431"+"a".repeat(4000));
function database(){
 const db=new DatabaseSync(":memory:");
 db.exec("CREATE TABLE mad_v1_projects (id TEXT PRIMARY KEY)");
 db.prepare("INSERT INTO mad_v1_projects(id) VALUES (?)").run("reel-"+"a".repeat(36));
 db.exec("CREATE TABLE mad_v6_kv_jobs (job_id TEXT PRIMARY KEY,project_id TEXT NOT NULL,file_name TEXT NOT NULL,mime TEXT NOT NULL,bytes INTEGER NOT NULL,source_sha256 TEXT NOT NULL,source_chunks INTEGER NOT NULL,source_description TEXT NOT NULL,brief TEXT,state TEXT NOT NULL,claim_id TEXT,claimed_at INTEGER,attempts INTEGER NOT NULL DEFAULT 0,output_chunks INTEGER,output_bytes INTEGER,output_sha256 TEXT,receipt_json TEXT,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,ready_at INTEGER,expires_at INTEGER NOT NULL,error_code TEXT)");
 db.exec("CREATE TABLE mad_v6_kv_parts (job_id TEXT NOT NULL,kind TEXT NOT NULL,idx INTEGER NOT NULL,bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,PRIMARY KEY(job_id,kind,idx))");
 const mock={prepare(sql){return {bind(...args){return {first:async()=>db.prepare(sql).get(...args)??null,all:async()=>({results:db.prepare(sql).all(...args)}),
 run:async()=>{const r=db.prepare(sql).run(...args);return {success:true,meta:{changes:r.changes}}}}}}}};
 return {db,mock};
}
const kv=()=>{const storage=new Map();return {storage,async put(k,v){storage.set(k,Buffer.from(v))},
 async get(k,type){const value=storage.get(k);if(!value)return null;return type==="json"?JSON.parse(value.toString("utf8")):Uint8Array.from(value).buffer},
 async delete(k){storage.delete(k)}}};
function client(path,opts={}){
 const headers={Origin:origin,Authorization:owner,...opts.headers};
 return new Request(base+path,{method:opts.method||"GET",headers,body:opts.body});
}
function toJSON(data){return JSON.stringify(data)}
async function authorize(eventName="workflow_dispatch",actorId="30191163"){
 const keys=await webcrypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
 const pub=await webcrypto.subtle.exportKey("jwk",keys.publicKey);
 const b64=s=>Buffer.from(s).toString("base64url");
 const header=b64(JSON.stringify({alg:"RS256",typ:"JWT",kid:"local-test"}));
 const claims=b64(JSON.stringify({iss:"https://token.actions.githubusercontent.com",aud:"mad-v6-cloudflare-kv/1",
 repository:"karanzing1992/engagement-core",repository_id:"1403281267",repository_owner_id:"30191163",
 ref:"refs/heads/main",workflow_ref:"karanzing1992/engagement-core/.github/workflows/mad-v6-kv-filmcraft.yml@refs/heads/main",
 runner_environment:"github-hosted",event_name:eventName,actor_id:actorId,run_id:"42170000000",
 iat:md()-10,nbf:md()-10,exp:md()+300}));
 const signature=Buffer.from(await webcrypto.subtle.sign("RSASSA-PKCS1-v1_5",keys.privateKey,Buffer.from(header+"."+claims))).toString("base64url");
 return {token:header+"."+claims+"."+signature,public:{...pub,kid:"local-test"}};
}
test("owner source upload -> signed OIDC GStreamer-output handoff -> range preview -> 30min expiry",async()=>{
 const {db,mock}=database(),storage=kv(),proof=await authorize();
 const env={DB:mock,MEDIA_KV:storage,
  PROJECT_AUTH:{fetch:async()=>new Response('{"projects":[]}',{status:200,headers:{"content-type":"application/json"}})},
  DISPATCH_API:{fetch:async request=>{
   assert.equal(new URL(request.url).pathname,"/internal/v6/dispatch");
   const b=await request.json();
   db.prepare("UPDATE mad_v6_kv_jobs SET state='sent' WHERE job_id=?").run(b.job_id);
   return new Response(JSON.stringify({state:"dispatched"}),{status:202});
  }}};
 const old=globalThis.fetch;
 globalThis.fetch=async url=>{
  assert.equal(String(url),"https://token.actions.githubusercontent.com/.well-known/jwks");
  return new Response(JSON.stringify({keys:[proof.public]}),{status:200,headers:{"content-type":"application/json"}});
 };
 try{
  const unauthorized=await worker.fetch(client("/v6/media/uploads",{method:"POST",headers:{Authorization:"Bearer invalid"},body:"{}"}),env,{});
  assert.equal(unauthorized.status,401);
  const invalidOrigin=await worker.fetch(new Request(base+"/health",{headers:{Origin:"https://attacker.invalid"}}),env,{});
  assert.equal(invalidOrigin.headers.get("access-control-allow-origin"),null);
  const h=await worker.fetch(client("/health"),env,{});
  assert.equal((await h.json()).requires_github_vault_token,false);
  const manifest={name:"synthetic.mp4",mime:"video/mp4",size:bytes.length,sha256:SHA(bytes),
   project_id:"reel-"+"a".repeat(36),source_description:"SYNTHETIC QA: original matte and basic shapes, no identifiable people.",
   rights_confirmed:true,people_consent:true,external_ai_approved:true,free_gemini_data_use_consent:true,
   audio_mode:"source_ambience_only"};
  const created=await worker.fetch(client("/v6/media/uploads",{method:"POST",headers:{"Content-Type":"application/json"},body:toJSON(manifest)}),env,{});
  assert.equal(created.status,201);
  const init=await created.json(),id=init.job_id;
  assert.match(id,/^v6job-[a-f0-9]{32}$/);
  const part=await worker.fetch(client("/v6/media/uploads/"+id+"/chunks/0",{method:"PUT",
   headers:{"X-Chunk-SHA256":SHA(bytes)},body:bytes}),env,{});
  assert.equal(part.status,201);
  const finish=await worker.fetch(client("/v6/media/uploads/"+id+"/complete",{method:"POST"}),env,{});
  assert.equal(finish.status,200);
  const wake=await worker.fetch(client("/v6/jobs/"+id+"/render",{method:"POST",headers:{"Content-Type":"application/json"},
   body:toJSON({brief:"Make a cinematic synthetic nature reel for authorized QA."})}),env,{});
  assert.equal(wake.status,202);
  const sign=async(path,opts={})=>worker.fetch(client(path,{...opts,headers:{Authorization:"Bearer "+proof.token,"X-V6-Claim":opts.claim||"",...opts.headers}}),env,{});
  const claimed=await sign("/internal/v6/jobs/"+id+"/claim",{method:"POST"});
  assert.equal(claimed.status,200);
  const job=await claimed.json();assert.equal(job.source_sha256,SHA(bytes));
  const media=await sign("/internal/v6/jobs/"+id+"/source/0",{claim:job.claim_id});
  assert.equal(media.status,200);
  assert.equal(SHA(await media.arrayBuffer()),SHA(bytes));
  const output=Buffer.concat([bytes,Buffer.from("V6-FILMCRAFT-SYNTHETIC-OUTPUT")]);
  const stored=await sign("/internal/v6/jobs/"+id+"/output/0",{method:"PUT",claim:job.claim_id,
    headers:{"X-Chunk-SHA256":SHA(output)},body:output});
  assert.equal(stored.status,200);
  const receipt={engine:"ffmpeg",video_stream_verified:true,audio_stream_verified:true,full_decode_passed:true,output_audio_verified:true,visual_presence_check:{visible:true,frames_examined:3},ffmpeg_invocations:4,audio_mode:"source_ambience_only",music_mixed:false,published:false,sha256:SHA(output)};
  const completed=await sign("/internal/v6/jobs/"+id+"/complete",{method:"POST",claim:job.claim_id,
   headers:{"Content-Type":"application/json"},
   body:toJSON({state:"review_ready",chunks:1,bytes:output.length,sha256:SHA(output),receipt})});
  assert.equal(completed.status,200);
  const s=await worker.fetch(client("/v6/jobs/"+id+"/status"),env,{});
  const status=await s.json();assert.equal(status.download_available,true);assert.ok(status.seconds_remaining<=1800);
  const preview=await worker.fetch(client("/v6/jobs/"+id+"/preview"),env,{});
  assert.equal(preview.status,200);assert.equal(SHA(await preview.arrayBuffer()),SHA(output));
  const range=await worker.fetch(client("/v6/jobs/"+id+"/preview",{headers:{Range:"bytes=10-99"}}),env,{});
  assert.equal(range.status,206);assert.equal(Buffer.from(await range.arrayBuffer()).compare(output.subarray(10,100)),0);
  db.prepare("UPDATE mad_v6_kv_jobs SET expires_at=? WHERE job_id=?").run(md()-1,id);
  const expired=await worker.fetch(client("/v6/jobs/"+id+"/download"),env,{});
  assert.equal(expired.status,410);
  let cleanupTask=null;await worker.scheduled({},env,{waitUntil:p=>{cleanupTask=p}});await cleanupTask;
  assert.equal(storage.storage.size,0);
  console.log("V6_KV_SIGNED_E2E_SIMULATED_PASS owner auth/source SHA/OIDC/FFmpeg receipt/206/410/KV deletion");
 }finally{globalThis.fetch=old;db.close()}
});

test("only signed GitHub issue events from repository owner can enter synthetic QA",async()=>{
 const {db,mock}=database(),store=kv();
 const ownerProof=await authorize("issues","30191163");
 const other=await authorize("issues","11111111");
 const original=globalThis.fetch;
 const e={DB:mock,MEDIA_KV:store,PROJECT_AUTH:{fetch:async()=>new Response("{}",{status:200})}};
 globalThis.fetch=async()=>new Response(JSON.stringify({keys:[ownerProof.public]}),{status:200});
 try{
  const make=jwt=>new Request(base+"/internal/v6/jobs/v6job-"+"a".repeat(32)+"/claim",
    {method:"POST",headers:{Authorization:"Bearer "+jwt}});
  const authorized=await worker.fetch(make(ownerProof.token),e,{});
  assert.equal(authorized.status,403); // Owner issue cannot claim any non-synthetic job, even an absent one.
  const denied=await worker.fetch(make(other.token),e,{});
  assert.equal(denied.status,401);
 }finally{globalThis.fetch=original;db.close()}
});


test("owner issue JWT seeds synthetic MP4 only, rejects nonowner signed issues and customer claim",async()=>{
 const {db,mock}=database(),store=kv();
 const proof=await authorize("issues","30191163");
 const forged=await authorize("issues","10001111");
 const old=globalThis.fetch;
 globalThis.fetch=async ()=>new Response(JSON.stringify({keys:[proof.public]}),{status:200});
 const env={DB:mock,MEDIA_KV:store};
 const id="v6job-"+"b".repeat(32);
 const synthetic=Buffer.alloc(2048);
 synthetic.write("ftyp",4);
 const upload=jwt=>new Request(base+"/internal/v6/jobs/"+id+"/seed",{method:"POST",
  headers:{Authorization:"Bearer "+jwt,"Content-Type":"video/mp4","Content-Length":String(synthetic.length),"X-Chunk-SHA256":SHA(synthetic)},body:synthetic});
 try{
   const denied=await worker.fetch(upload(forged.token),env,{});
   assert.equal(denied.status,401);
   const created=await worker.fetch(upload(proof.token),env,{});
   assert.equal(created.status,201);
   const row=db.prepare("SELECT project_id,state,source_sha256 FROM mad_v6_kv_jobs WHERE job_id=?").get(id);
   assert.equal(row.project_id,"synthetic-owner-qa");
   assert.equal(row.source_sha256,SHA(synthetic));
   assert.equal(store.storage.size,1);
   const replay=await worker.fetch(upload(proof.token),env,{});
   assert.equal(replay.status,409);
   const other="v6job-"+"c".repeat(32);
   const now=md();
   db.prepare("INSERT INTO mad_v6_kv_jobs(job_id,project_id,file_name,mime,bytes,source_sha256,source_chunks,source_description,brief,state,created_at,updated_at,expires_at) VALUES(?,?,?,?,?,?,1,?,?,'sent',?,?,?)")
    .run(other,"reel-"+"a".repeat(36),"private.mp4","video/mp4",2048,SHA(synthetic),
      "Owner footage must not be available to issue-driven tests","Original user film brief",now,now,now+3600);
   const claim=new Request(base+"/internal/v6/jobs/"+other+"/claim",{method:"POST",
    headers:{Authorization:"Bearer "+proof.token}});
   const blocked=await worker.fetch(claim,env,{});
   assert.equal(blocked.status,403);
   assert.equal(db.prepare("SELECT state FROM mad_v6_kv_jobs WHERE job_id=?").get(other).state,"sent");
   console.log("SIGNED_SYNTHETIC_QA_UPLOAD_PASS_REAL_USER_MEDIA_DENIED");
 }finally{globalThis.fetch=old;db.close()}
});


test("owner-verified Openverse track transfer -> signed FFmpeg mix receipt; false rights fail closed",async()=>{
 const {db,mock}=database(),storage=kv(),proof=await authorize();
 const env={DB:mock,MEDIA_KV:storage,
  PROJECT_AUTH:{fetch:async()=>new Response("{}",{status:200})},
  DISPATCH_API:{fetch:async req=>{
   const {job_id}=await req.json();
   db.prepare("UPDATE mad_v6_kv_jobs SET state='sent' WHERE job_id=?").run(job_id);
   return new Response("{}",{status:202});
  }}};
 const original=globalThis.fetch;
 globalThis.fetch=async()=>new Response(JSON.stringify({keys:[proof.public]}),{status:200});
 try{
  const manifest={name:"synthetic.mp4",mime:"video/mp4",size:bytes.length,sha256:SHA(bytes),
   project_id:"reel-"+"a".repeat(36),source_description:"SYNTHETIC QA: colored shapes only, no guest faces or people.",
   rights_confirmed:true,people_consent:true,external_ai_approved:true,free_gemini_data_use_consent:true};
  const created=await worker.fetch(client("/v6/media/uploads",{method:"POST",headers:{"Content-Type":"application/json"},body:toJSON(manifest)}),env,{});
  assert.equal(created.status,201);
  const id=(await created.json()).job_id;
  const uploaded=await worker.fetch(client("/v6/media/uploads/"+id+"/chunks/0",{method:"PUT",
   headers:{"X-Chunk-SHA256":SHA(bytes)},body:bytes}),env,{});
  assert.equal(uploaded.status,201);
  assert.equal((await worker.fetch(client("/v6/media/uploads/"+id+"/complete",{method:"POST"}),env,{})).status,200);
  const audio=Buffer.from("SYNTHETIC AUDIO BYTES - NOT A REAL RECORDING".repeat(50));
  const source="https://commons.wikimedia.org/wiki/File:Test_open_audio";
  const lic="https://creativecommons.org/publicdomain/zero/1.0/";
  const track={source:"Openverse",id:"a".repeat(32),title:"QA Synthetic Track",
   creator:"Test Author",license:"cc0",license_url:lic,original_source_page:source};
  const evidence={reviewer_confirmed_rights:true,track_id:track.id,original_source_page:source,
   license_url:lic,source_license_proof_url:source,reviewed_by:"Test Reviewer",reviewed_on:"2026-11-07"};
  const music={mime:"audio/mpeg",bytes:audio.length,sha256:SHA(audio),track,evidence};
  const prepare=async payload=>worker.fetch(client("/v6/media/uploads/"+id+"/music",
   {method:"POST",headers:{"Content-Type":"application/json"},body:toJSON(payload)}),env,{});
  assert.equal((await prepare({...music,evidence:{...evidence,reviewer_confirmed_rights:false}})).status,422);
  assert.equal((await prepare(music)).status,201);
  const premature=await worker.fetch(client("/v6/jobs/"+id+"/render",{method:"POST",
   headers:{"Content-Type":"application/json"},body:toJSON({brief:"Private synthetic CC0 audiovisual review only"})}),env,{});
  assert.equal(premature.status,409);
  const send=async digest=>worker.fetch(client("/v6/media/uploads/"+id+"/music",
   {method:"PUT",headers:{"X-Chunk-SHA256":digest},body:audio}),env,{});
  assert.equal((await send("a".repeat(64))).status,422);
  assert.equal((await send(SHA(audio))).status,201);
  const wake=await worker.fetch(client("/v6/jobs/"+id+"/render",{method:"POST",
   headers:{"Content-Type":"application/json"},body:toJSON({brief:"Private synthetic CC0 audiovisual review only"})}),env,{});
  assert.equal(wake.status,202);
  const sign=(path,opts={})=>worker.fetch(client(path,{...opts,headers:{
   Authorization:"Bearer "+proof.token,"X-V6-Claim":opts.claim||"",...opts.headers}}),env,{});
  const claim=await sign("/internal/v6/jobs/"+id+"/claim",{method:"POST"});
  assert.equal(claim.status,200);
  const j=await claim.json();
  assert.equal(j.audio_mode,"licensed_music");
  assert.equal(j.music_sha256,SHA(audio));
  const media=await sign("/internal/v6/jobs/"+id+"/music",{claim:j.claim_id});
  assert.equal(media.status,200);
  assert.equal(SHA(await media.arrayBuffer()),SHA(audio));
  const out=Buffer.concat([bytes,Buffer.from("VERIFIED SYNTHETIC RESULT")]);
  assert.equal((await sign("/internal/v6/jobs/"+id+"/output/0",{method:"PUT",claim:j.claim_id,
   headers:{"X-Chunk-SHA256":SHA(out)},body:out})).status,200);
  const receipt={engine:"ffmpeg",video_stream_verified:true,audio_stream_verified:true,
   full_decode_passed:true,ffmpeg_invocations:4,output_audio_verified:true,
   visual_presence_check:{visible:true,frames_examined:3},audio_mode:"licensed_music",
   music_mixed:true,music_sha256:SHA(audio),published:false,sha256:SHA(out)};
  const complete=async r=>sign("/internal/v6/jobs/"+id+"/complete",{method:"POST",claim:j.claim_id,
   headers:{"Content-Type":"application/json"},body:toJSON({state:"review_ready",
   chunks:1,bytes:out.length,sha256:SHA(out),receipt:r})});
  assert.equal((await complete({...receipt,music_mixed:false})).status,422);
  assert.equal((await complete(receipt)).status,200);
  db.prepare("UPDATE mad_v6_kv_jobs SET expires_at=? WHERE job_id=?").run(md()-1,id);
  let cleaning=null;await worker.scheduled({},env,{waitUntil:p=>cleaning=p});await cleaning;
  assert.equal(storage.storage.size,0);
 }finally{globalThis.fetch=original;db.close()}
});
