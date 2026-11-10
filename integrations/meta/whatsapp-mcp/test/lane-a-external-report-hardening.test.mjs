import test from 'node:test';
import assert from 'node:assert/strict';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const principal={tenantId:tenant,actorId:'audit-fixture'};
const context={tenantId:tenant,verifiedPrincipal:principal,requestId:'security-owner-request-2026'};
const policy=()=>({operatorApproved:true,irreversibleApproved:true,
  optInVerified:true,customerWindowOpen:true,templateApproved:true,billableSendApproved:true});
const route={tenantId:tenant,status:'active',activationId:4,
  wabaId:'123456789012',phoneNumberId:'223456789012'};
function fixture(name='whatsapp_get_business_account',response={ok:true,data:{id:'123456789012'}}){
  const state={identity:0,policy:0,provider:0,seen:null};
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>{state.identity++;return true;},
    authorizeTenant:async()=>true,
    readPolicy:async(_p,_t,_n,args)=>{state.policy++;state.seen=args;return policy();},
    resolveRoute:async()=>route,
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{
      host:{executePlan:async()=>{state.provider++;return response;}},
      dojo:{invoke:async()=>{state.provider++;return {ok:true,data:{
        accepted:true,messageId:'wamid.synthetic_audit_12345'}};}}
    },
    grants:[name],enableWriteCandidates:true
  });
  const call=(args,ctx=context)=>mcp.callTool({name,arguments:args},ctx);
  return {state,call};
}
test('P2 contract: shared argument references are denied as non-tree JSON without policy calls',async()=>{
  const x={name:'reused'};
  const f=fixture('whatsapp_send_contacts');
  const r=await f.call({contacts:[x,x],to:'+919999999999'});
  assert.equal(r.isError,true);
  assert.equal(r.structuredContent.error.code,'invalid_input');
  assert.equal(f.state.policy,0);
});
test('P2 contract: cyclic references are denied, even when otherwise contact-shaped',async()=>{
  const x={name:'alice',phone:'+919999999999'}; x.self=x;
  const f=fixture('whatsapp_send_contacts');
  const r=await f.call({contacts:[x],to:'+919999999999'});
  assert.equal(r.isError,true);
  assert.equal(f.state.policy,0);
});
test('P2 contract: shared provider output identities fail closed without leaking data',async()=>{
  const one={id:'123456789012'};
  const f=fixture('whatsapp_get_business_account',{ok:true,data:{data:[one,one]}});
  const r=await f.call({});
  assert.equal(f.state.provider,1);
  assert.equal(r.isError,true);
  assert.equal(r.structuredContent.error.code,'upstream_unavailable');
});
test('P2 phone: contact phone reaches trusted policy only in declared contacts[] schema',async()=>{
  const f=fixture('whatsapp_send_contacts');
  await f.call({to:'+919999999999',contacts:[{name:'synthetic contact',phone:'+918888888888'}]});
  assert.equal(f.state.policy,1,'valid schema contact phone should not be preflight-blocked');
  assert.equal(f.state.seen.contacts[0].phone,'+918888888888');
  assert.equal(Object.isFrozen(f.state.seen.contacts[0]),true);
});
test('P2 phone: non-contact phone property rejected before policy for messaging and reads',async()=>{
  for(const [name,args] of [
    ['whatsapp_send_text',{to:'+919999999999',body:'safe',phone:'+919999999999'}],
    ['whatsapp_get_business_account',{phone:'+919999999999'}],
    ['whatsapp_send_contacts',{to:'+919999999999',contacts:[{name:'x',phone:'+918888888888',metadata:{phone:'+919999999999'}}]}]
  ]){
    const f=fixture(name),r=await f.call(args);
    assert.equal(r.isError,true,name);
    assert.equal(r.structuredContent.error.code,'invalid_input',name);
    assert.equal(f.state.policy,0,name);
    assert.equal(f.state.provider,0,name);
  }
});
test('P2 phone: raw upstream phone key denied; approved display_phone_number retained',async()=>{
  const good=fixture('whatsapp_get_business_account',{
    ok:true,data:{id:'123456789012',display_phone_number:'+919999999999'}
  });
  const a=await good.call({});
  assert.equal(a.isError,false);
  assert.equal(a.structuredContent.data.display_phone_number,'+919999999999');
  const bad=fixture('whatsapp_get_business_account',{
    ok:true,data:{id:'123456789012',phone:'+919999999999'}
  });
  const b=await bad.call({});
  assert.equal(b.isError,true);
  assert.equal(b.structuredContent.error.code,'upstream_unavailable');
  assert.ok(!JSON.stringify(b).includes('+919999999999'));
});
test('P3 budget: aggregate 64 KiB + one byte denied before trusted policy',async()=>{
  const f=fixture('whatsapp_get_business_account');
  const r=await f.call({a:'A'.repeat(32768),b:'B'.repeat(32768),c:'C'});
  assert.equal(r.isError,true);
  assert.equal(r.structuredContent.error.code,'invalid_input');
  assert.equal(f.state.policy,0);
  assert.equal(f.state.provider,0);
});
test('P3 budget: exactly 64 KiB can cross snapshot but not unsupported input schema',async()=>{
  const f=fixture('whatsapp_get_business_account');
  const r=await f.call({a:'A'.repeat(32768),b:'B'.repeat(32768)});
  assert.equal(f.state.policy,1,'64 KiB snapshot boundary should be inclusive');
  assert.equal(r.isError,true,'unknown catalog args still forbidden by ingress schema');
  assert.equal(f.state.provider,0);
});
test('P3 budget: many individually small values are cumulatively bounded',async()=>{
  const input={};
  for(let i=0;i<30;i++)input['f'+i]='x'.repeat(3000);
  const f=fixture('whatsapp_get_business_account');
  const r=await f.call(input);
  assert.equal(r.isError,true);
  assert.equal(f.state.policy,0);
});
test('Lane B media SSRF boundary: local/metadata URLs never reach provider',async()=>{
  for(const url of [
    'https://127.0.0.1/metadata',
    'https://169.254.169.254/latest/meta-data',
    'https://10.1.2.3/synthetic',
    'http://example.com/file',
    'https://localhost/file'
  ]){
    const f=fixture('whatsapp_upload_media_from_url');
    const r=await f.call({sourceUrl:url,mimeType:'image/png'});
    assert.equal(r.isError,true,url);
    assert.equal(f.state.provider,0,url);
  }
});
