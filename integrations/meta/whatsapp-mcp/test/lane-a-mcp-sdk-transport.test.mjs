import test from 'node:test';
import assert from 'node:assert/strict';
import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {InMemoryTransport} from '@modelcontextprotocol/sdk/inMemory.js';
import {createLaneAProtocolServer} from '../src/lane-a-mcp-protocol.mjs';
import {createLaneAProviderMcp} from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const principal={tenantId:tenant,actorId:'synthetic-owner'};
const verifiedCtx={
  verifiedPrincipal:principal,tenantId:tenant,
  requestId:'host-issued-synthetic-request-1234567890'
};
function makeRuntime(){
 return createLaneAProviderMcp({
   verifyIdentity:async(p,t)=>p.actorId==='synthetic-owner'&&p.tenantId===t,
   authorizeTenant:async(p,t)=>p.tenantId===t,
   readPolicy:async()=>({operatorApproved:true}),
   resolveRoute:async t=>({
      tenantId:t,status:'active',activationId:42,
      wabaId:'123456789012',phoneNumberId:'223456789012'
   }),
   resolveOwnership:async()=>({wabaIdVerified:true}),
   providers:{host:{
     async executePlan({plan}){
       assert.equal(plan.graphApiVersion,'v26.0');
       assert.equal(plan.resourcePath,'/v26.0/123456789012');
       return {ok:true,data:{id:'123456789012',name:'synthetic WABA'}};
     }
   }},
   grants:['whatsapp_get_business_account']
 });
}
test('Real MCP SDK in-memory JSON-RPC tools/list and tools/call run without OAuth or Graph traffic',async()=>{
 const runtime=makeRuntime();
 const server=createLaneAProtocolServer({
   runtime,resolveTrustedContext:async()=>verifiedCtx
 });
 const client=new Client({name:'meta-core-synthetic-ci',version:'1.0.0'},
   {capabilities:{}});
 const [clientTransport,serverTransport]=InMemoryTransport.createLinkedPair();
 try {
   await server.connect(serverTransport);
   await client.connect(clientTransport);
   const listed=await client.listTools();
   assert.equal(listed.tools.length,1);
   assert.equal(listed.tools[0].name,'whatsapp_get_business_account');
   assert.equal(listed.tools[0].inputSchema.type,'object');
   const result=await client.callTool({name:'whatsapp_get_business_account',arguments:{}});
   assert.notEqual(result.isError,true,JSON.stringify(result));
   assert.equal(result.structuredContent?.data?.name,'synthetic WABA');
   const unavailable=await client.callTool({name:'whatsapp_send_text',
     arguments:{to:'+919999999999',body:'DO NOT SEND'}});
   assert.equal(unavailable.isError,true);
   assert.equal(unavailable.structuredContent.error.code,'not_enabled');
 }finally{
   await client.close();await server.close();
 }
});

test('MCP protocol bridge refuses missing host identity and never lets args impersonate tenant',async()=>{
 const server=createLaneAProtocolServer({
   runtime:makeRuntime(),resolveTrustedContext:async()=>null
 });
 const client=new Client({name:'unauthenticated-synthetic',version:'1.0.0'},
   {capabilities:{}});
 const [ct,st]=InMemoryTransport.createLinkedPair();
 try {
   await server.connect(st);await client.connect(ct);
   const r=await client.callTool({name:'whatsapp_get_business_account',
     arguments:{tenantId:tenant}});
   assert.equal(r.isError,true);
   assert.equal(r.structuredContent.error.code,'forbidden');
 }finally{await client.close();await server.close();}
});
