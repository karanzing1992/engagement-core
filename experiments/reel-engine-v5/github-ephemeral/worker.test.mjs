import test from "node:test";
import assert from "node:assert/strict";
import worker from "./worker.mjs";
const env={GITHUB_REPO:"karanzing1992/Matrix-House",GITHUB_TOKEN:"test-nonsecret",MCP_ACCESS_TOKEN:"local-test-token"};
async function post(payload,token="local-test-token") {
  return worker.fetch(new Request("https://mcp.example.invalid/mcp",{method:"POST",
    headers:{"content-type":"application/json","authorization":"Bearer "+token},body:JSON.stringify(payload)}),env);
}
test("does not expose private media on health probe",async()=>{
  const r=await worker.fetch(new Request("https://mcp.example.invalid/health"),env);
  assert.equal(r.status,200);
  const d=await r.json();
  assert.equal(d.status,"candidate");
  assert.equal(JSON.stringify(d).includes("test-nonsecret"),false);
});
test("rejects unauthenticated MCP request",async()=>{
  const r=await post({jsonrpc:"2.0",id:1,method:"tools/list"},"invalid-token");
  assert.equal(r.status,401);
  assert.equal(r.headers.get("www-authenticate"),"Bearer");
});
test("MCP initialization and five tooling contracts",async()=>{
  const init=await post({jsonrpc:"2.0",id:1,method:"initialize",params:{protocolVersion:"2025-03-26"}});
  assert.equal((await init.json()).result.serverInfo.name,"mad-v5-github-ephemeral");
  const list=await post({jsonrpc:"2.0",id:2,method:"tools/list"});
  const tools=(await list.json()).result.tools;
  assert.deepEqual(tools.map(x=>x.name),["reel_create_job","reel_submit_prompt","reel_status","reel_get_preview","reel_acknowledge_and_delete"]);
});
test("unrecognized tools fail without invoking network",async()=>{
  const r=await post({jsonrpc:"2.0",id:3,method:"tools/call",params:{name:"publish_to_instagram",arguments:{}}});
  assert.equal(r.status,400);
  assert.equal((await r.json()).error.code,-32601);
});
test("preview cannot be retrieved without valid short-lived signature",async()=>{
  const r=await worker.fetch(new Request("https://mcp.example.invalid/preview/moksha-guest-review-001?expires=1&asset=1&sig=none"),env);
  assert.equal(r.status,400);
});

test("draft release acknowledgement tolerates absent Git tag ref",async()=>{
  const originalFetch=globalThis.fetch;
  const jobId="moksha-guest-review-001";
  const calls=[];
  globalThis.fetch=async(url,opt={})=>{
    const p=String(url);calls.push({url:p,method:opt.method||"GET"});
    if(p.endsWith("/repos/karanzing1992/Matrix-House"))
      return new Response(JSON.stringify({private:true}),{status:200});
    if(p.includes("/releases?"))
      return new Response(JSON.stringify([{id:77,draft:true,tag_name:"mad-v5-tmp-"+jobId,
        body:JSON.stringify({schema:1,job_id:jobId}),assets:[]}]),{status:200});
    if(p.endsWith("/releases/77") && opt.method==="DELETE")
      return new Response(null,{status:204});
    if(p.includes("/git/ref/tags/"))
      return new Response(JSON.stringify({message:"Not Found"}),{status:404});
    throw new Error("Unexpected GitHub mock request");
  };
  try {
    const r=await post({jsonrpc:"2.0",id:10,method:"tools/call",
      params:{name:"reel_acknowledge_and_delete",arguments:{job_id:jobId,force:true}}});
    const data=await r.json();
    assert.equal(data.result.isError,undefined);
    const receipt=JSON.parse(data.result.content[0].text);
    assert.equal(receipt.deleted_release,true);
    assert.equal(receipt.tag_ref_status,"absent");
    assert.equal(calls.filter(c=>c.method==="DELETE").length,1);
  } finally { globalThis.fetch=originalFetch; }
});
