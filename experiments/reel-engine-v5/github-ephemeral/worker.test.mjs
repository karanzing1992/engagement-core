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
