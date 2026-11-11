import test from 'node:test';
import assert from 'node:assert/strict';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const flowId='333333333333';
const ctx={tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-owner'},
  requestId:'flow-metrics-p2-synthetic-1234'};
const graphMetric=(value=138)=>({
  id:flowId,
  metric:{
    data_points:[{data:[{key:'value',value}],timestamp:'2026-11-01T08:00:00+0000'}],
    granularity:'LIFETIME',name:'ENDPOINT_REQUEST_COUNT'
  }
});
function setup(toolName,response){
  const calls={provider:0,route:0};
  const plans=[];
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>({operatorApproved:true}),
    resolveRoute:async()=>{calls.route++;return {
      tenantId:tenant,status:'active',activationId:42,
      wabaId:'123456789012',phoneNumberId:'223456789012'
    };},
    resolveOwnership:async(_route,_name,args)=>({
      wabaIdVerified:true,flowId:args.flowId
    }),
    providers:{host:{executePlan:async envelope=>{
      calls.provider++;plans.push(envelope.plan);return response;
    }}},
    grants:[toolName]
  });
  return {calls,plans,call:args=>mcp.callTool({
    name:toolName,arguments:args
  },ctx)};
}
test('Flow Metrics P2 retains actual Graph metric values, key, name and granularity',async()=>{
  const receipt=graphMetric();
  const {call,calls,plans}=setup('whatsapp_get_flow_metrics',{ok:true,data:receipt});
  const r=await call({flowId});
  assert.equal(r.isError,false,JSON.stringify(r.structuredContent));
  assert.deepEqual(r.structuredContent.data,receipt);
  assert.equal(calls.provider,1);
  assert.equal(plans[0].query.fields,
    'metric.name(ENDPOINT_REQUEST_COUNT).granularity(LIFETIME)');
});
test('Flow Metrics P2 keeps explicit empty measurements but refuses missing metrics',async()=>{
  const empty=graphMetric();
  empty.metric.data_points=[];
  const good=await setup('whatsapp_get_flow_metrics',{ok:true,data:empty}).call({flowId});
  assert.equal(good.isError,false,JSON.stringify(good.structuredContent));
  assert.deepEqual(good.structuredContent.data.metric.data_points,[]);
  for(const receipt of [
    {id:flowId}, {id:flowId,metrics:graphMetric().metric},
    {id:flowId,metric:{}},
    {id:flowId,metric:{name:'ENDPOINT_REQUEST_COUNT',granularity:'LIFETIME'}},
    {id:flowId,metric:{name:'WRONG_METRIC',granularity:'LIFETIME',data_points:[]}},
    {id:flowId,metric:{name:'ENDPOINT_REQUEST_COUNT',granularity:'DAY',data_points:[]}}
  ]){
    const r=await setup('whatsapp_get_flow_metrics',{ok:true,data:receipt}).call({flowId});
    assert.equal(r.isError,true,JSON.stringify(receipt));
    assert.equal(r.structuredContent.error.code,'upstream_unavailable');
  }
});
test('Flow Metrics P2 rejects malformed, out-of-range or non-numeric measurements',async()=>{
  const invalid=[
    {key:'value',value:-1},
    {key:'value',value:3.14},
    {key:'value',value:'138'},
    {key:'value',value:Number.MAX_SAFE_INTEGER+1},
    {key:'value'},
    {key:'cost',value:138},
    {value:138},
    {key:'value',value:Infinity}
  ];
  for(const item of invalid){
    const receipt=graphMetric();
    receipt.metric.data_points[0].data=[item];
    const r=await setup('whatsapp_get_flow_metrics',{ok:true,data:receipt}).call({flowId});
    assert.equal(r.isError,true,JSON.stringify(item));
    assert.equal(r.structuredContent.error.code,'upstream_unavailable');
  }
  const missing=graphMetric();
  missing.metric.data_points[0].data=[];
  const r=await setup('whatsapp_get_flow_metrics',{ok:true,data:missing}).call({flowId});
  assert.equal(r.isError,true);
});
test('Flow metric fields remain denied for every other tool',async()=>{
  const {call}=setup('whatsapp_get_business_account',{ok:true,data:graphMetric()});
  const r=await call({});
  assert.equal(r.isError,false,JSON.stringify(r.structuredContent));
  assert.deepEqual(r.structuredContent.data,{id:flowId});
});
test('Flow metric subtree rejects credential fields, getters and hidden numeric values',async()=>{
  const secret=graphMetric();
  secret.metric.data_points[0].data[0].access_token='SYNTHETIC_SENSITIVE';
  const r=await setup('whatsapp_get_flow_metrics',{ok:true,data:secret}).call({flowId});
  assert.equal(r.isError,true);
  assert.ok(!JSON.stringify(r).includes('SYNTHETIC_SENSITIVE'));
  const accessor=graphMetric();
  Object.defineProperty(accessor.metric.data_points[0].data[0],'value',{
    enumerable:true,get(){throw Error('getter must not execute');}
  });
  const r2=await setup('whatsapp_get_flow_metrics',{ok:true,data:accessor}).call({flowId});
  assert.equal(r2.isError,true);
  const unrelated=graphMetric();
  unrelated.metric.data_points[0].surprise={value:987};
  const r3=await setup('whatsapp_get_flow_metrics',{ok:true,data:unrelated}).call({flowId});
  assert.equal(r3.isError,false,JSON.stringify(r3.structuredContent));
  assert.ok(!JSON.stringify(r3).includes('987'));
});
