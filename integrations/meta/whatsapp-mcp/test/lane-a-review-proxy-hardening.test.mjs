import test from 'node:test';
import assert from 'node:assert/strict';
import {createLaneAProviderMcp} from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const principal=()=>({actorId:'synthetic-security-review',tenantId:tenant});
const route=()=>({tenantId:tenant,status:'active',activationId:44,wabaId:'123456789012',phoneNumberId:'223456789012'});
const ctx=()=>({tenantId:tenant,verifiedPrincipal:principal(),requestId:'synthetic-owner-issued-request-01'});
function configure(){
  const counters={identity:0,policy:0,provider:0};
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>{counters.identity++;return true;},
    authorizeTenant:async()=>true,
    readPolicy:async()=>{counters.policy++;return {};},
    resolveRoute:async()=>route(),
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{host:{executePlan:async()=>{counters.provider++;return {
      ok:true,data:{id:'123456789012',name:'synthetic'}};
    }}},
    grants:['whatsapp_get_business_account']
  });
  return {mcp,counters};
}
function hostile(target,reads){
  return new Proxy(target,{
    getPrototypeOf(){reads.count++;throw Error('trap: getPrototypeOf');},
    ownKeys(){reads.count++;throw Error('trap: ownKeys');},
    getOwnPropertyDescriptor(){reads.count++;throw Error('trap: getOwnPropertyDescriptor');},
    get(){reads.count++;throw Error('trap: get');},
    has(){reads.count++;throw Error('trap: has');}
  });
}
test('P2: unauthenticated proxy argument is denied before any trap or host callback',async()=>{
  const reads={count:0};
  const p=hostile({},reads),{mcp,counters}=configure();
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:p},{});
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'forbidden');
  assert.equal(reads.count,0);
  assert.deepEqual(counters,{identity:0,policy:0,provider:0});
});
test('P2: authorized top-level Proxy args rejected with zero property traps',async()=>{
  const reads={count:0};
  const p=hostile({},reads),{mcp,counters}=configure();
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:p},ctx());
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'invalid_input');
  assert.equal(reads.count,0);
  assert.equal(counters.policy,0);
  assert.equal(counters.provider,0);
});
test('P2: nested input Proxy never inspected and cannot reach policy',async()=>{
  const reads={count:0};
  const args={after:hostile({synthetic:1},reads)};
  const {mcp,counters}=configure();
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:args},ctx());
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'invalid_input');
  assert.equal(reads.count,0);
  assert.equal(counters.policy,0);
});
test('P2: Proxy arrays are denied without reading length, keys or descriptors',async()=>{
  const reads={count:0};
  const args={data:hostile([],reads)};
  const {mcp,counters}=configure();
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:args},ctx());
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'invalid_input');
  assert.equal(reads.count,0);
  assert.equal(counters.policy,0);
});
test('P2: untrusted outer MCP request Proxy cannot execute its traps',async()=>{
  const reads={count:0};
  const request=hostile({name:'whatsapp_get_business_account',arguments:{}},reads);
  const {mcp,counters}=configure();
  const out=await mcp.callTool(request,ctx());
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'invalid_input');
  assert.equal(reads.count,0);
  assert.deepEqual(counters,{identity:0,policy:0,provider:0});
});
test('P2: untrusted authorization context Proxy cannot execute traps',async()=>{
  const reads={count:0};
  const context=hostile(ctx(),reads);
  const {mcp,counters}=configure();
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:{}},context);
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'forbidden');
  assert.equal(reads.count,0);
  assert.deepEqual(counters,{identity:0,policy:0,provider:0});
});
test('P2: nested provider Proxy results cannot execute traps during sanitization',async()=>{
  // The WACRM provider is trusted to resolve promises safely. JavaScript
  // necessarily inspects a raw Promise-resolved proxy's .then property
  // before receiving it; the sanitizer can guard nested provider outputs.
  const reads={count:0};
  let providerCalls=0;
  const p=hostile({id:'123456789012'},reads);
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>({}),resolveRoute:async()=>route(),
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{host:{executePlan:async()=>{
      providerCalls++;return {ok:true,data:{id:'123456789012',data:p}};
    }}},
    grants:['whatsapp_get_business_account']
  });
  const out=await mcp.callTool({name:'whatsapp_get_business_account',arguments:{}},ctx());
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'upstream_unavailable');
  assert.equal(providerCalls,1);
  assert.equal(reads.count,0);
});
