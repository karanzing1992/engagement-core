import assert from "node:assert/strict";
import {test} from "node:test";
import {dispatchV6} from "./v6_dispatch.mjs";
const job="v6job-"+"f".repeat(32);
const req=(name=job)=>new Request("https://reel-api.delulutech.in/internal/v6/dispatch",
 {method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({job_id:name})});
function env({token=true,state="dispatching"}={}){
 const record={state,expires_at:Math.floor(Date.now()/1000)+1000,source_chunks:1};
 let update=0;
 return {MAD_GITHUB_ACTIONS_DISPATCH_TOKEN:token?"synthetic-token-not-a-real-secret":undefined,
 DB:{prepare(sql){return{bind(){return{first:async()=>sql.startsWith("SELECT")?record:null,
 run:async()=>{update++;return{meta:{changes:1}}}}}}}},get writes(){return update}};
}
test("owner V6 job sends only job id to existing GitHub Actions",async()=>{
 const e=env();let n=0;const previous=globalThis.fetch;
 globalThis.fetch=async (url,opts)=>{
  n++;assert.equal(url,"https://api.github.com/repos/karanzing1992/engagement-core/actions/workflows/mad-v6-kv-filmcraft.yml/dispatches");
  assert.equal(opts.method,"POST");assert.equal(opts.redirect,"manual");
  assert.deepEqual(JSON.parse(opts.body),{ref:"main",inputs:{job_id:job}});
  return new Response(null,{status:204});
 };
 try{const r=await dispatchV6(req(),e);assert.equal(r.status,202);assert.equal(n,1);assert.equal(e.writes,1)}
 finally{globalThis.fetch=previous}
});
test("unknown job IDs cannot trigger any actions",async()=>{
 assert.equal((await dispatchV6(req("bad"),env())).status,400);
});
test("missing V5 dispatch secret blocks V6 without paid fallback",async()=>{
 assert.equal((await dispatchV6(req(),env({token:false}))).status,503);
});
test("unclaimed or expired job cannot dispatch",async()=>{
 assert.equal((await dispatchV6(req(),env({state:"expired"}))).status,409);
});
test("failed GitHub dispatch does not claim success",async()=>{
 const previous=globalThis.fetch;globalThis.fetch=async()=>new Response(null,{status:403});
 try{const e=env();assert.equal((await dispatchV6(req(),e)).status,503);assert.equal(e.writes,0)}
 finally{globalThis.fetch=previous}
});
