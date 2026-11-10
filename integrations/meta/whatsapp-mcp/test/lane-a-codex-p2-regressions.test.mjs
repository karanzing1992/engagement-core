import test from 'node:test';
import assert from 'node:assert/strict';
import { WHATSAPP_LANE_A_CATALOG } from '../src/lane-a-capability-catalog.mjs';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';
const tenant='wacrm_'+'a'.repeat(40);
const ctx={tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-owner'},
  requestId:'p2-regression-owner-request-12345'};
function setup(toolName,response){
  const calls={policy:0,provider:0,route:0};
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>{calls.policy++;return {operatorApproved:true};},
    resolveRoute:async()=>{calls.route++;return {tenantId:tenant,status:'active',
      activationId:42,wabaId:'123456789012',phoneNumberId:'223456789012'};},
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{host:{executePlan:async()=>{calls.provider++;return response;}}},
    grants:[toolName]
  });
  return {calls,call:args=>mcp.callTool({name:toolName,arguments:args},ctx)};
}
const catalog=name=>WHATSAPP_LANE_A_CATALOG.find(x=>x.name===name);
test('P2 analytics schemas advertise both dates as required for both tools',()=>{
  for(const name of ['whatsapp_get_template_analytics','whatsapp_get_business_analytics']){
    const d=catalog(name);
    assert.deepEqual(d.inputSchema.required,['startDate','endDate']);
    assert.ok(d.inputSchema.properties.startDate);
    assert.ok(d.inputSchema.properties.endDate);
  }
});
test('P2 analytics absent or partial dates are invalid_input before any trusted host callbacks',async()=>{
  for(const name of ['whatsapp_get_template_analytics','whatsapp_get_business_analytics']){
    for(const args of [{},{startDate:'2026-11-01'},{endDate:'2026-11-09'}]){
      const {calls,call}=setup(name,{ok:true,data:{analytics:{data_points:[]}}});
      const result=await call(args);
      assert.equal(result.isError,true,name+' '+JSON.stringify(args));
      assert.equal(result.structuredContent.error.code,'invalid_input');
      assert.equal(calls.policy,0);
      assert.equal(calls.route,0);
      assert.equal(calls.provider,0);
    }
  }
});
test('P2 analytics valid dates still flow to host and retain analytics output',async()=>{
  for(const name of ['whatsapp_get_template_analytics','whatsapp_get_business_analytics']){
    const key=name==='whatsapp_get_template_analytics'?'template_analytics':'analytics';
    const {call,calls}=setup(name,{ok:true,data:{[key]:{data_points:[{sent:3,start:1793491200,end:1793577600}]}}});
    const result=await call({startDate:'2026-11-01',endDate:'2026-11-09'});
    assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
    assert.equal(result.structuredContent[key].data_points[0].sent,3);
    assert.equal(calls.provider,1);
  }
});
test('P2 public Graph profile fields survive sanitizer only on business-profile operation',async()=>{
  const profile={about:'synthetic business',email:'test@example.org',
    profile_picture_url:'https://cdn.example.org/image.png',
    websites:['https://example.org','https://shop.example.org']};
  const good=setup('whatsapp_get_business_profile',{ok:true,data:{data:[profile]}});
  const result=await good.call({});
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  assert.deepEqual(result.structuredContent.data[0],profile);
  assert.equal(good.calls.provider,1);

  const other=setup('whatsapp_get_business_account',{ok:true,data:{data:[{...profile,id:'123456789012'}]}});
  const unrelated=await other.call({});
  assert.equal(unrelated.isError,false);
  assert.deepEqual(unrelated.structuredContent.data[0],{about:'synthetic business',id:'123456789012'});
});
test('P2 profile sanitized results reject unsafe website and email values',async()=>{
  for(const profile of [
    {email:'wrong email',about:'safe'},
    {websites:['http://127.0.0.1/'],about:'safe'},
    {websites:['https://ok.example.org',42],about:'safe'},
    {profile_picture_url:'javascript:alert(1)',about:'safe'}
  ]){
    const {call}=setup('whatsapp_get_business_profile',{ok:true,data:{data:[profile]}});
    const result=await call({});
    assert.equal(result.isError,true,JSON.stringify(profile));
    assert.equal(result.structuredContent.error.code,'upstream_unavailable');
  }
});
test('P2 profile response never grants credential key access',async()=>{
  const {call}=setup('whatsapp_get_business_profile',{ok:true,
    data:{data:[{email:'test@example.org',access_token:'synthetic-not-a-token'}]}});
  const r=await call({});
  assert.equal(r.isError,true);
  assert.equal(r.structuredContent.error.code,'upstream_unavailable');
  assert.ok(!JSON.stringify(r).includes('synthetic-not-a-token'));
});
