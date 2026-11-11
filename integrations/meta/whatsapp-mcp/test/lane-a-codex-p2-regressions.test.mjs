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
    grants:[toolName],enableWriteCandidates:true
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
test('P2 analytics absent or partial dates reject before route or provider dispatch',async()=>{
  for(const name of ['whatsapp_get_template_analytics','whatsapp_get_business_analytics']){
    for(const args of [{},{startDate:'2026-11-01'},{endDate:'2026-11-09'}]){
      const {calls,call}=setup(name,{ok:true,data:{analytics:{data_points:[]}}});
      const result=await call(args);
      assert.equal(result.isError,true,name+' '+JSON.stringify(args));
      assert.equal(result.structuredContent.error.code,'invalid_input');
      // The existing host design invokes readPolicy before its ingress
      // schema validator; no route or provider is invoked on rejection.
      assert.equal(calls.policy,1);
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
    assert.equal(result.structuredContent.data[key].data_points[0].sent,3);
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
  assert.deepEqual(result.structuredContent.data.data[0],profile);
  assert.equal(good.calls.provider,1);

  const other=setup('whatsapp_get_business_account',{ok:true,data:{data:[{...profile,id:'123456789012'}]}});
  const unrelated=await other.call({});
  assert.equal(unrelated.isError,false);
  assert.deepEqual(unrelated.structuredContent.data.data[0],{about:'synthetic business',id:'123456789012'});
});
test('P2 profile individual public fields survive full provider roundtrip',async()=>{
  const fields=[
    {about:'synthetic business'},
    {email:'test@example.org'},
    {profile_picture_url:'https://cdn.example.org/image.png'},
    {websites:['https://example.org']},
    {about:'synthetic business',email:'test@example.org'},
  ];
  for(const field of fields){
    const {call}=setup('whatsapp_get_business_profile',{ok:true,data:{data:[field]}});
    const result=await call({});
    assert.equal(result.isError,false,
      JSON.stringify({field,result:result.structuredContent}));
  }
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

test('P2 mutation resourceId requires a supported, nonempty identifier',async()=>{
  const bad=[null,false,true,0,42,'','short','not a valid ID',
    {},{id:'123456789012'},[],['123456789012'],'a'.repeat(129)];
  for(const resourceId of bad){
    for(const receipt of [{resourceId},{accepted:true,resourceId}]){
      const {call,calls}=setup('whatsapp_update_business_profile',
        {ok:true,data:receipt});
      const response=await call({about:'synthetic business'});
      assert.equal(response.isError,true,JSON.stringify(receipt));
      assert.equal(response.structuredContent.error.code,'upstream_unavailable');
      assert.equal(calls.provider,1);
      assert.ok(!JSON.stringify(response).includes('not a valid ID'));
    }
  }
});
test('P2 mutation resourceId permits Graph IDs and bounded Meta QR codes',async()=>{
  for(const resourceId of [
    '123456789012','meta-core-synthetic-confirmation_12345','AWHPX5O6XYVUM1'
  ]){
    const {call}=setup('whatsapp_update_business_profile',
      {ok:true,data:{resourceId}});
    const r=await call({about:'synthetic business'});
    assert.equal(r.isError,false,JSON.stringify({resourceId,result:r.structuredContent}));
    assert.equal(r.structuredContent.data.resourceId,resourceId);
  }
});
test('P2 malformed provider wrapper status or explicit error fails closed',async()=>{
  for(const response of [
    {ok:'false',data:{accepted:true}},
    {ok:null,data:{accepted:true}},
    {ok:0,data:{accepted:true}},
    {isError:'true',data:{accepted:true}},
    {isError:true,data:{accepted:true}},
    {ok:true,error:{message:'synthetic failure'},data:{accepted:true}},
    {ok:true,data:{accepted:true,error:{message:'synthetic failure'}}}
  ]){
    const {call}=setup('whatsapp_update_business_profile',response);
    const r=await call({about:'synthetic business'});
    assert.equal(r.isError,true,JSON.stringify(response));
    assert.equal(r.structuredContent.error.code,'upstream_unavailable');
    assert.ok(!JSON.stringify(r).includes('synthetic failure'));
  }
  const {call}=setup('whatsapp_update_business_profile',
    {ok:true,isError:false,data:{accepted:true}});
  const good=await call({about:'synthetic business'});
  assert.equal(good.isError,false,JSON.stringify(good.structuredContent));
});

test('P2 explicit negative read status cannot masquerade as a successful read',async()=>{
  for(const flag of [{success:false},{accepted:false},{success:'false'},
    {accepted:0},{success:null}]){
    const {call}=setup('whatsapp_get_business_account',
      {ok:true,data:{id:'123456789012',...flag}});
    const result=await call({});
    assert.equal(result.isError,true,JSON.stringify(flag));
    assert.equal(result.structuredContent.error.code,'upstream_unavailable');
  }
  const positive=await setup('whatsapp_get_business_account',
    {ok:true,data:{id:'123456789012',success:true}}).call({});
  assert.equal(positive.isError,false,JSON.stringify(positive.structuredContent));
});
test('P2 nested provider error fields cannot be sanitized into successful reads',async()=>{
  for(const field of ['error','errors']){
    const payload={id:'123456789012',data:[{
      id:'223456789012',[field]:{message:'synthetic negative result'}
    }]};
    const {call}=setup('whatsapp_get_business_account',{ok:true,data:payload});
    const result=await call({});
    assert.equal(result.isError,true,field);
    assert.equal(result.structuredContent.error.code,'upstream_unavailable');
    assert.ok(!JSON.stringify(result).includes('synthetic negative result'));
  }
});

test('P2 envelope negative mutation receipts cannot be lost during unwrapping',async()=>{
  for(const envelope of [
    {ok:true,accepted:false,data:{resourceId:'123456789012'}},
    {ok:true,success:false,data:{accepted:true}},
    {ok:true,accepted:'false',data:{success:true}},
    {ok:true,accepted:null,data:{accepted:true}},
    {ok:true,accepted:true,success:false,
      structuredContent:{resourceId:'123456789012'}}
  ]){
    const {call}=setup('whatsapp_update_business_profile',envelope);
    const result=await call({about:'synthetic'});
    assert.equal(result.isError,true,JSON.stringify(envelope));
    assert.equal(result.structuredContent.error.code,'upstream_unavailable');
  }
  const {call}=setup('whatsapp_update_business_profile',
    {ok:true,accepted:true,data:{resourceId:'123456789012'}});
  const good=await call({about:'synthetic'});
  assert.equal(good.isError,false,JSON.stringify(good.structuredContent));
});

test('P2 envelope error array is rejected before selecting successful provider data',async()=>{
  for(const [name,args] of [
    ['whatsapp_update_business_profile',{about:'synthetic'}],
    ['whatsapp_get_business_account',{}]
  ]){
    for(const response of [
      {ok:true,errors:[{message:'synthetic provider rejection'}],
        data:{resourceId:'123456789012',id:'123456789012',accepted:true}},
      {ok:true,errors:[],
        structuredContent:{resourceId:'123456789012',id:'123456789012',accepted:true}},
      {ok:true,errors:null,
        data:{resourceId:'123456789012',id:'123456789012',accepted:true}}
    ]){
      const {call}=setup(name,response);
      const result=await call(args);
      assert.equal(result.isError,true,JSON.stringify({name,response}));
      assert.equal(result.structuredContent.error.code,'upstream_unavailable');
      assert.ok(!JSON.stringify(result).includes('synthetic provider rejection'));
    }
    const errorGetter={ok:true,data:{resourceId:'123456789012',id:'123456789012',accepted:true}};
    let getterCalls=0;
    Object.defineProperty(errorGetter,'errors',{enumerable:true,get(){
      getterCalls++;throw Error('unexpected getter invocation');
    }});
    const rejected=await setup(name,errorGetter).call(args);
    assert.equal(rejected.isError,true);
    assert.equal(getterCalls,0);
  }
});

test('P2 nested provider status must not be dropped while unwrapping successful envelopes',async()=>{
  for(const name of ['whatsapp_update_business_profile','whatsapp_get_business_account']){
    const args=name==='whatsapp_update_business_profile'?{about:'synthetic'}:{};
    const candidates=[
      {ok:false,resourceId:'123456789012',id:'123456789012'},
      {ok:'false',resourceId:'123456789012',id:'123456789012'},
      {ok:null,resourceId:'123456789012',id:'123456789012'},
      {isError:true,resourceId:'123456789012',id:'123456789012'},
      {isError:'false',resourceId:'123456789012',id:'123456789012'},
      {errors:[],resourceId:'123456789012',id:'123456789012'}
    ];
    for(const payload of candidates){
      const result=await setup(name,{ok:true,data:payload}).call(args);
      assert.equal(result.isError,true,JSON.stringify({name,payload}));
      assert.equal(result.structuredContent.error.code,'upstream_unavailable');
    }
    const traps={id:'123456789012',resourceId:'123456789012'};
    let invoked=0;
    Object.defineProperty(traps,'isError',{enumerable:true,get(){
      invoked++;throw Error('read of getter is prohibited');
    }});
    const result=await setup(name,{ok:true,data:traps}).call(args);
    assert.equal(result.isError,true);
    assert.equal(invoked,0);
  }
});
