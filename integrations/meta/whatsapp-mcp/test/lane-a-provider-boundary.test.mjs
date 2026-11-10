import test from 'node:test';
import assert from 'node:assert/strict';
import {WHATSAPP_LANE_A_CATALOG} from '../src/lane-a-capability-catalog.mjs';
import {createLaneAProviderHarness} from '../src/lane-a-provider-boundary.mjs';

const A='wacrm_'+'a'.repeat(40);
const B='wacrm_'+'b'.repeat(40);
const all=WHATSAPP_LANE_A_CATALOG.map(x=>x.name);
const approval=Object.freeze({
  operator:true,irreversible:true,optIn:true,cost:true,windowOpen:true,templateApproved:true
});
const route=tenantId=>({
  tenantId,activationId:42,wabaId:'123456789012',phoneNumberId:'223456789012',status:'active'
});
const principal=tenantId=>({tenantId,actorId:'synthetic_owner'});
function make(overrides={}){
  let auth=0, reads=0, dispatches=0;
  const h=createLaneAProviderHarness({
    authorize:async()=>{auth++;return true;},
    resolveRoute:async t=>{reads++;return route(t);},
    adapterFactory:async (kind,op)=>({
      synthetic:true,
      execute:async operation=>{
        dispatches++;
        assert.equal(operation.adapter,kind);
        assert.equal(operation.wabaId,'123456789012');
        return {ok:true,receipt:{
          operation:op.name,state:'simulated',
          reference:'syntheticreceipt1',readOnly:op.kind==='read'
        }};
      }
    }),
    ...overrides
  });
  return {h,get auth(){return auth},get reads(){return reads},get dispatches(){return dispatches}};
}
const invoke=(h,name,extra={})=>h.dispatch({
  principal:principal(A),tenantId:A,toolName:name,args:{},
  approval,grant:'synthetic_verified',environment:'synthetic',...extra
});
test('all 55 capability families bind to a synthetic-only adapter with WACRM route authority',async()=>{
  const t=make();
  for(const name of all){
    const result=await invoke(t.h,name);
    assert.equal(result.ok,true,name+':'+JSON.stringify(result));
    assert.equal(result.receipt.operation,name);
    assert.equal(result.receipt.state,'simulated');
    assert.ok(!JSON.stringify(result).includes(A));
    assert.ok(!JSON.stringify(result).includes('123456789012'));
  }
  assert.equal(t.dispatches,55);
  assert.equal(t.reads,55);
  assert.equal(t.auth,55);
});
test('no network or provider access without explicit synthetic environment/grant',async()=>{
  const t=make();
  for(const change of [{environment:'production'},{grant:'live'},{environment:undefined},
    {grant:undefined},{environment:'staging'}]){
    assert.equal((await invoke(t.h,'whatsapp_get_business_account',change)).error.code,'not_enabled');
  }
  assert.equal(t.reads,0);
  assert.equal(t.auth,0);
  assert.equal(t.dispatches,0);
});
test('missing principal, other tenant, disallowed actor all deny before route or transport',async()=>{
  const t=make();
  for(const change of [
    {principal:null},{principal:principal(B)},
    {tenantId:B,principal:principal(A)}
  ])assert.equal((await invoke(t.h,'whatsapp_get_business_account',change)).error.code,'forbidden');
  assert.equal(t.reads,0);assert.equal(t.auth,0);
  const denied=make({authorize:async()=>false});
  assert.equal((await invoke(denied.h,'whatsapp_get_business_account')).error.code,'forbidden');
  assert.equal(denied.reads,0);
});
test('stale, cross-tenant and revoked routes block ALL providers before implementation',async()=>{
  const routes=[null,{...route(A),status:'revoked'},{...route(A),tenantId:B},
    {...route(A),activationId:0},{...route(A),wabaId:'broken'}];
  for(const r of routes){
    let dispatched=false;
    const t=make({
      resolveRoute:async()=>r,
      adapterFactory:async()=>{dispatched=true;throw Error('should not resolve');},
    });
    assert.equal((await invoke(t.h,'whatsapp_get_business_account')).error.code,'route_unavailable');
    assert.equal(dispatched,false);
  }
});
test('send, template, destructive and operator-gated updates require separate trusted flags',async()=>{
  const t=make();
  const candidates=[
    ['whatsapp_send_text',{...approval,windowOpen:false}],
    ['whatsapp_send_text',{...approval,optIn:false}],
    ['whatsapp_send_text',{...approval,cost:false}],
    ['whatsapp_send_template',{...approval,templateApproved:false}],
    ['whatsapp_send_template',{...approval,cost:false}],
    ['whatsapp_publish_flow',{...approval,irreversible:false}],
    ['whatsapp_delete_template',{...approval,operator:false}],
    ['whatsapp_create_template',{...approval,operator:false}]
  ];
  for(const [name,p] of candidates){
    const r=await invoke(t.h,name,{approval:p});
    assert.ok(r.error?.code==='policy_denied'||r.error?.code==='approval_required',name);
  }
  assert.equal(t.reads,0);assert.equal(t.dispatches,0);
});
test('malicious/credential provider output is refused even in synthetic mode',async()=>{
  for(const receipt of [
    {state:'simulated',access_token:'secret'},
    {state:'simulated',recipientPhone:'+919999999999'},
    {operation:'whatsapp_phone_deregister',state:'simulated'},
    {state:'approved_production'},
    {reference:'../secrets'},
    {retryAfter:9999999999},
  ]){
    const t=make({adapterFactory:async()=>({
      synthetic:true,execute:async()=>({ok:true,receipt})
    })});
    const r=await invoke(t.h,'whatsapp_get_business_account');
    assert.equal(r.error.code,'provider_unavailable');
    assert.ok(!JSON.stringify(r).includes('secret'));
    assert.ok(!JSON.stringify(r).includes('+919999999999'));
  }
});
test('fake adapter exceptions redact implementation information',async()=>{
  const t=make({adapterFactory:async()=>({
    synthetic:true,execute:async()=>{throw Error('sensitive fake provider token');}
  })});
  const result=await invoke(t.h,'whatsapp_list_flows');
  assert.equal(result.error.code,'provider_unavailable');
  assert.ok(!JSON.stringify(result).includes('sensitive'));
});
test('unknown & excluded lifecycle capabilities are never executed',async()=>{
  const t=make();
  for(const name of ['whatsapp_phone_register','whatsapp_phone_deregister',
    'whatsapp_waba_subscribe_app','whatsapp_account_transfer']){
    assert.equal((await invoke(t.h,name)).error.code,'unsupported_tool');
  }
  assert.equal(t.auth,0);
});
