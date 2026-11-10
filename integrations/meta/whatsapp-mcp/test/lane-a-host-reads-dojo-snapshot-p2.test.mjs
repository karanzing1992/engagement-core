import test from 'node:test';
import assert from 'node:assert/strict';
import { createMetaCoreDojoReadAdapter } from '../src/dojo-v26.mjs';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const ctx={tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-reviewer'}};
const route={tenantId:tenant,status:'active',activationId:42,
  wabaId:'123456789012',phoneNumberId:'223456789012'};
const connection={
  accessToken:'synthetic-token-only-abcdefghijklmnop',
  phoneNumberId:'223456789012',businessAccountId:'123456789012',
  appSecret:'synthetic-secret-only-not-live',graphApiVersion:'v26.0'
};

function hostFixture(name, response){
  const state={identity:0,policy:0,route:0,provider:0,plan:null};
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>{state.identity++;return true;},
    authorizeTenant:async()=>true,
    readPolicy:async()=>{state.policy++;return {};},
    resolveRoute:async()=>{state.route++;return route;},
    resolveOwnership:async(_route,_name,args)=>({
      wabaIdVerified:true,flowId:args.flowId,templateId:args.templateId
    }),
    providers:{host:{executePlan:async({plan})=>{
      state.provider++;state.plan=plan;
      return {ok:true,data:response};
    }}},
    grants:[name]
  });
  return {state,call:(args={})=>mcp.callTool({name,arguments:args},ctx)};
}

test('P2 Graph business-account read retains fields explicitly requested by its plan',async()=>{
  const payload={id:'123456789012',name:'Synthetic Business',
    timezone_id:1,message_template_namespace:'synthetic_namespace_123'};
  const {call,state}=hostFixture('whatsapp_get_business_account',payload);
  const out=await call();
  assert.equal(out.isError,false,JSON.stringify(out.structuredContent));
  assert.deepEqual(out.structuredContent.data,payload);
  assert.match(state.plan.query.fields,/timezone_id,message_template_namespace/);
});

test('P2 QR code read retains full per-record code/message/link result rather than data:[{}]',async()=>{
  const qr={code:'SYNTH_QR_1',prefilled_message:'Hello synthetic world',
    deep_link:'https://wa.me/message/SYNTH123',
    qr_image_url:'https://cdn.example.org/qr.svg'};
  const {call,state}=hostFixture('whatsapp_list_qr_codes',{data:[qr]});
  const out=await call();
  assert.equal(out.isError,false,JSON.stringify(out.structuredContent));
  assert.deepEqual(out.structuredContent.data.data,[qr]);
  assert.equal(state.provider,1);
});

test('P2 empty QR records fail closed; empty legitimate list can be read',async()=>{
  const bad=hostFixture('whatsapp_list_qr_codes',{data:[{}]});
  const out=await bad.call();
  assert.equal(out.isError,true);
  assert.equal(out.structuredContent.error.code,'upstream_unavailable');
  const good=hostFixture('whatsapp_list_qr_codes',{data:[]});
  assert.equal((await good.call()).isError,false);
});

test('P2 extra QR/business-account fields are not globally copied on unrelated reads',async()=>{
  const s=hostFixture('whatsapp_get_phone_number',{
    id:'223456789012',timezone_id:1,
    message_template_namespace:'private_scope_only',
    code:'QR_PRIVATE',prefilled_message:'secret_value',
    deep_link:'https://private.example.org'
  });
  const out=await s.call();
  assert.equal(out.isError,false);
  assert.deepEqual(out.structuredContent.data,{id:'223456789012'});
});

test('P2 explicit Graph flow fields, asset fields and metric rows survive scoped sanitization',async()=>{
  const cases=[
    ['whatsapp_get_flow',{flowId:'123456789012'},
      {id:'123456789012',name:'Synthetic Flow',
        preview:'https://example.org/preview',
        data_channel_uri:'https://example.org/callback',
        whatsapp_business_account:{id:'123456789012'}},
      'preview'],
    ['whatsapp_get_flow_assets',{flowId:'123456789012'},
      {data:[{id:'123456789012',asset_type:'FLOW_JSON',
        download_url:'https://cdn.example.org/flow.json'}]},'data'],
    ['whatsapp_get_flow_metrics',{flowId:'123456789012'},
      {metric:{name:'ENDPOINT_REQUEST_COUNT',granularity:'LIFETIME',
        data_points:[{data:[{key:'value',value:12}],
          timestamp:'2026-11-01T08:00:00+0000'}]}},'metric'],
    ['whatsapp_get_subscription_status',{},
      {data:[{id:'123456789012',subscribed_fields:['messages'],
        override_callback_uri:'https://example.org/webhook'}]},'data']
  ];
  for(const [name,args,response,key] of cases){
    const fixture=hostFixture(name,response);
    const out=await fixture.call(args);
    assert.equal(out.isError,false,name+' '+JSON.stringify(out.structuredContent));
    assert.deepEqual(out.structuredContent.data,response,name);
    assert.ok(Object.hasOwn(out.structuredContent.data,key),name);
  }
});

test('P2 Dojo rejects inherited array toJSON getter before policy, tenant or SDK invocation',async()=>{
  let trap=0,auth=0,resolved=0,dispatched=0;
  const proto=Object.create(Array.prototype);
  Object.defineProperty(proto,'toJSON',{get(){trap++;throw Error('UNTRUSTED_HOOK');}});
  const payload=[];
  Object.setPrototypeOf(payload,proto);
  const adapter=createMetaCoreDojoReadAdapter({
    authorizeTenant:async()=>{auth++;return false;},
    resolveConnection:async()=>{resolved++;return connection;},
    toolsetFactory:async()=>({dispatch:async()=>{dispatched++;return {};} })
  });
  const result=await adapter.invoke({tenantId:'brand_a',principal:'user',
    toolName:'whatsapp_list_templates',args:{limit:1,nested:payload}});
  assert.equal(result.error.code,'invalid_input');
  assert.equal(trap,0);
  assert.equal(auth,0);
  assert.equal(resolved,0);
  assert.equal(dispatched,0);
});

test('P2 Dojo rejects own toJSON getter and custom array prototype without invoking hooks',async()=>{
  let hits=0;
  const own=[];
  Object.defineProperty(own,'toJSON',{get(){hits++;throw Error('UNTRUSTED');}});
  const custom=[];
  Object.setPrototypeOf(custom,Object.create(Array.prototype));
  let auth=0;
  const adapter=createMetaCoreDojoReadAdapter({
    authorizeTenant:async()=>{auth++;return true;},
    resolveConnection:async()=>connection,
    toolsetFactory:async()=>({dispatch:async()=>({isError:false,structuredContent:{ok:true}})})
  });
  for(const array of [own,custom]){
    const result=await adapter.invoke({tenantId:'brand_a',principal:'user',
      toolName:'whatsapp_list_templates',args:{nested:array}});
    assert.equal(result.error.code,'invalid_input');
  }
  assert.equal(hits,0);
  assert.equal(auth,0);
});

test('P2 Dojo snapshots nested argument arrays before asynchronous authorization mutations',async()=>{
  const args={limit:2,extra:{nested:['safe','values']}};
  const seen=[];
  const adapter=createMetaCoreDojoReadAdapter({
    authorizeTenant:async()=>{args.limit=999;args.extra.nested[0]='mutated';return true;},
    resolveConnection:async()=>connection,
    toolsetFactory:async()=>({
      dispatch:async(name,clean)=>{seen.push({name,clean});
        return {isError:false,structuredContent:{synthetic:true}};}
    })
  });
  const result=await adapter.invoke({tenantId:'brand_a',principal:'user',
    toolName:'whatsapp_list_templates',args});
  assert.equal(result.ok,true);
  assert.equal(seen.length,1);
  assert.deepEqual(seen[0].clean,{limit:2,extra:{nested:['safe','values']}});
});
