import test from 'node:test';
import assert from 'node:assert/strict';
import {createLaneAProviderMcp} from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const principal=()=>({actorId:'synthetic-operator',tenantId:tenant});
const basePolicy=()=>({
  operatorApproved:true,irreversibleApproved:true,optInVerified:true,
  customerWindowOpen:true,templateApproved:true,billableSendApproved:true
});
const route=()=>({tenantId:tenant,status:'active',activationId:9,
  wabaId:'123456789012',phoneNumberId:'223456789012'});
const ctx=()=>({tenantId:tenant,verifiedPrincipal:principal(),requestId:'synthetic-host-request-001'});
const read=(mcp,args)=>mcp.callTool({name:'whatsapp_get_business_account',arguments:args},ctx());
function setup({readPolicy,resolveRoute,host}={}){
  let policyReads=0,providerCalls=0;
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async (...all)=>{policyReads++;return readPolicy?readPolicy(...all):basePolicy();},
    resolveRoute:resolveRoute??(async()=>route()),
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{
      host:{executePlan:async envelope=>{providerCalls++;return host?
        host(envelope):{ok:true,data:{id:'123456789012',name:'synthetic'}};}}
    },
    grants:['whatsapp_get_business_account','whatsapp_send_text'],
    enableWriteCandidates:true
  });
  return {mcp,get policyReads(){return policyReads},
    get providerCalls(){return providerCalls}};
}
test('input must be detached before asynchronous route resolution can mutate it',async()=>{
  const input={to:'+919999999999',body:'Original user-approved body'};
  let received;
  const t=setup({resolveRoute:async()=>{input.body='Unapproved altered body';return route();}});
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>basePolicy(),
    resolveRoute:async()=>{input.body='Unapproved altered body';return route();},
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{dojo:{invoke:async envelope=>{
      received=envelope.args.body;
      return {ok:true,data:{accepted:true,messageId:'wamid.synthetic_12345'}};
    }}},
    grants:['whatsapp_send_text'],enableWriteCandidates:true
  });
  const result=await mcp.callTool({name:'whatsapp_send_text',arguments:input},ctx());
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  assert.equal(received,'Original user-approved body');
  assert.equal(input.body,'Unapproved altered body');
});
test('untrusted input accessors must be rejected before reaching the policy callback',async()=>{
  const input={};
  Object.defineProperty(input,'to',{enumerable:true,value:'+919999999999'});
  Object.defineProperty(input,'body',{enumerable:true,get(){throw Error('getter ran');}});
  let reads=0;
  const t=setup({readPolicy:async()=>{reads++;return basePolicy();}});
  const result=await t.mcp.callTool({name:'whatsapp_send_text',arguments:input},ctx());
  assert.equal(result.isError,true);
  assert.equal(reads,0);
});
test('provider response accessors must not execute while sanitizing',async()=>{
  let reads=0;
  const response={id:'123456789012',name:'synthetic'};
  Object.defineProperty(response,'accepted',{enumerable:true,get(){reads++;throw Error('do not invoke');}});
  const t=setup({host:async()=>({ok:true,data:response})});
  const result=await read(t.mcp,{});
  assert.equal(result.isError,true);
  assert.equal(reads,0);
});
