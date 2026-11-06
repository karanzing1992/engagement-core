import assert from "node:assert/strict";
import {test} from "node:test";
import worker from "./worker.mjs";
const ORIGIN="https://mad-v6-owner-private-beta.pages.dev";
const GH="https://api.github.com/repos/karanzing1992/Matrix-House";
const token="Bearer nk-"+("A".repeat(40));
function request(path,{method="GET",body,origin=ORIGIN,auth=token}={}){
 const headers={};
 if(origin!==null)headers.Origin=origin;
 if(auth!==null)headers.Authorization=auth;
 if(body!==undefined)headers["Content-Type"]="application/json";
 return new Request("https://mad-v6-owner-private-beta.karanbizweb360.workers.dev"+path,
   {method,headers,body:body===undefined?undefined:JSON.stringify(body)});
}
function env({vault=false,allow=true,d1=true,rows={}}={}){
 const sql=[];
 const DB=d1?{prepare(q){sql.push(q);return {bind(...args){return {async first(){if(q.includes("FROM mad_v6_vault_jobs"))return rows[args[0]]??null;
 if(q.includes("FROM mad_v1_projects"))return {id:args[0]};return null},async run(){return {success:true}}}}}}}:null;
 return {PROJECT_AUTH:{async fetch(r){return new Response(allow?'{"projects":[]}':'{"error":"denied"}',
    {status:allow?200:401,headers:{"content-type":"application/json"}})}},DB,
    GITHUB_VAULT_TOKEN:vault?"TEST_ONLY_FAKE_GITHUB_TOKEN_00000000000":undefined,sql};
}
test("browser health has CORS and correctly reports isolated credential absence",async()=>{
 const e=env();
 const r=await worker.fetch(request("/health"),e,{});
 assert.equal(r.status,200);
 assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
 const h=await r.json();
 assert.equal(h.ready,false);
 assert.equal(h.github_private_vault_configured,false);
 assert.equal(h.auth_bound,true);
});
test("unknown origins never receive V6 media or project data",async()=>{
 const e=env();
 const r=await worker.fetch(request("/v1/projects",{origin:"https://attacker.invalid"}),e,{});
 assert.equal(r.status,403);
 assert.equal(r.headers.get("access-control-allow-origin"),null);
});
test("invalid owner bearer is rejected before any vault access",async()=>{
 const e=env();
 const r=await worker.fetch(request("/v6/catalog?q=forest",{auth:null}),e,{});
 assert.equal(r.status,401);
 assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
});
test("owner project gateway works without GitHub vault secret",async()=>{
 const e=env();
 const r=await worker.fetch(request("/v1/projects"),e,{});
 assert.equal(r.status,200);
 assert.deepEqual((await r.json()).projects,[]);
 assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
});
test("media upload fails closed with browser-readable error when GitHub token absent",async()=>{
 const e=env();
 const r=await worker.fetch(request("/v6/media/uploads",{method:"POST",body:{}}),e,{});
 assert.equal(r.status,503);
 assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
 assert.match((await r.json()).error.message,/credential/);
});
test("Openverse catalog discovery remains available to owners without GitHub token",async()=>{
 const before=globalThis.fetch;
 globalThis.fetch=async input=>{
   assert.match(String(input),/^https:\/\/api.openverse.org\/v1\/audio\//);
   return new Response(JSON.stringify({results:[{
     id:"synthetic",title:"Synthetic Catalog Test",creator:"Test",
     license:"by",license_url:"https://creativecommons.org/licenses/by/4.0/",
     foreign_landing_url:"https://commons.wikimedia.org/wiki/Test"
   }]}),{status:200,headers:{"content-type":"application/json"}});
 };
 try{
   const r=await worker.fetch(request("/v6/catalog?q=ambient"),env(),{});
   assert.equal(r.status,200);
   assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
   const o=await r.json();
   assert.equal(o.tracks.length,1);
   assert.equal(o.tracks[0].approved_for_render,false);
   assert.equal(o.tracks[0].rights_status,"UNVERIFIED_REQUIRES_INDEPENDENT_REVIEW");
 }finally{globalThis.fetch=before}
});
test("expired V6 video denies download with exact HTTP 410 even with configured vault",async()=>{
 const job="v6job-"+("c".repeat(32));
 const now=Math.floor(Date.now()/1000);
 const e=env({vault:true,rows:{[job]:{job_id:job,release_id:1,state:"review_ready",
    expiry_at:now-1,ready_at:now-1801}}});
 const r=await worker.fetch(request("/v6/jobs/"+job+"/download"),e,{});
 assert.equal(r.status,410);
 assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
});
test("expired V6 preview is denied without retrieving private Release",async()=>{
 const job="v6job-"+("a".repeat(32));
 const e=env({vault:true,rows:{[job]:{job_id:job,state:"expired",expiry_at:1}}});
 const r=await worker.fetch(request("/v6/jobs/"+job+"/preview"),e,{});
 assert.equal(r.status,410);
});
test("separately provisioned vault token cannot create source Release in public repository",async()=>{
 const b={project_id:"reel-"+("a".repeat(36)),name:"shot.mp4",mime:"video/mp4",
   size:1024,sha256:"b".repeat(64),rights_confirmed:true,people_consent:true,
   external_ai_approved:true,free_gemini_data_use_consent:true,
   source_description:"Synthetic owner-reviewed source footage on matte backdrop.",
   audio_mode:"source_ambience_only"};
 const before=globalThis.fetch;
 globalThis.fetch=async(input)=>{
  assert.equal(String(input),GH);
  return new Response(JSON.stringify({full_name:"karanzing1992/Matrix-House",private:false}),
    {status:200,headers:{"content-type":"application/json"}});
 };
 try{
  const r=await worker.fetch(request("/v6/media/uploads",{method:"POST",body:b}),env({vault:true}),{});
  assert.equal(r.status,503);
  assert.equal(r.headers.get("access-control-allow-origin"),ORIGIN);
 }finally{globalThis.fetch=before}
});
