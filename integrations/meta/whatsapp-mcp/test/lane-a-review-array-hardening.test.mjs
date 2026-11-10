import test from 'node:test';
import assert from 'node:assert/strict';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const tenant='wacrm_'+'a'.repeat(40);
const route={tenantId:tenant,activationId:44,status:'active',wabaId:'123456789012',phoneNumberId:'223456789012'};
const policy={operatorApproved:true,irreversibleApproved:true,optInVerified:true,
  customerWindowOpen:true,templateApproved:true,billableSendApproved:true};
const input={startDate:'2026-11-01',endDate:'2026-11-02'};

function runtime(name, upstream) {
  return createLaneAProviderMcp({
    verifyIdentity:async()=>true, authorizeTenant:async()=>true,
    readPolicy:async()=>policy, resolveRoute:async()=>route,
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{host:{executePlan:async()=>({ok:true,data:upstream})}},
    grants:[name], enableWriteCandidates:false
  });
}
const call=(name,response)=>runtime(name,response).callTool({
  name,arguments:input
},{tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-reviewer'}});
const name='whatsapp_get_template_analytics';
function report(point={}) {
  return {template_analytics:{data:[{template_id:'123456789012',
    data_points:[{start:1793491200,end:1793577600,sent:12,
      delivered:11,read:9,...point}]}]}};
}

test('P1: analytics array index accessor is rejected without running its getter',async()=>{
  let accessed=0;
  const points=[];
  Object.defineProperty(points,'0',{configurable:true,enumerable:true,
    get(){accessed++;throw Error('synthetic secret from getter');}});
  points.length=1;
  const result=await call(name,{template_analytics:{data:[{
    template_id:'123456789012',data_points:points}]}});
  assert.equal(result.isError,true);
  assert.equal(accessed,0);
  assert.ok(!JSON.stringify(result).includes('synthetic secret'));
});
test('P1: own array map override cannot bypass nested redaction or leak credentials',async()=>{
  let mapCalled=0;
  const points=[{sent:2}];
  points.map=()=>{mapCalled++;return [{access_token:'synthetic-super-secret',
    phone:'+919999999999'}];};
  const result=await call(name,{template_analytics:{data:[{
    template_id:'123456789012',data_points:points}]}});
  assert.equal(result.isError,true);
  assert.equal(mapCalled,0);
  assert.ok(!JSON.stringify(result).includes('synthetic-super-secret'));
  assert.ok(!JSON.stringify(result).includes('+919999999999'));
});
test('P1: own array non-index fields and sparse arrays are rejected fail-closed',async()=>{
  const withExtra=[{sent:1}];
  withExtra.debug='untrusted';
  const sparse=new Array(2);
  sparse[1]={sent:1};
  for(const points of [withExtra,sparse]){
    const result=await call(name,{template_analytics:{data:[{
      template_id:'123456789012',data_points:points}]}});
    assert.equal(result.isError,true);
  }
});
test('P1: nested analytics array payload with credential key must not escape',async()=>{
  const result=await call(name,report({clicked:[
    {type:'url_button',count:3,access_token:'synthetic-secret'}
  ]}));
  assert.equal(result.isError,true);
  assert.ok(!JSON.stringify(result).includes('synthetic-secret'));
});
test('P2: realistic clicked and cost arrays survive bounded nested sanitization',async()=>{
  const result=await call(name,report({
    clicked:[
      {type:'quick_reply_button',count:4},
      {type:'url_button',value:3},
      {type:'unique_url_button',value:2}
    ],
    cost:[
      {type:'amount_spent',value:1.25},
      {type:'cost_per_delivered',value:0.12},
      {type:'cost_per_url_button_click',value:0.5}
    ]
  }));
  assert.equal(result.isError,false,JSON.stringify(result.structuredContent));
  const point=result.structuredContent.data.template_analytics.data[0].data_points[0];
  assert.deepEqual(point.clicked,[{type:'quick_reply_button',count:4},
    {type:'url_button',value:3},{type:'unique_url_button',value:2}]);
  assert.deepEqual(point.cost,[{type:'amount_spent',value:1.25},
    {type:'cost_per_delivered',value:0.12},
    {type:'cost_per_url_button_click',value:0.5}]);
});
test('P2: metric array with more than 100 items remains bounded and denied',async()=>{
  const result=await call(name,report({clicked:Array.from({length:101},()=>({
    type:'url_button',value:1
  }))}));
  assert.equal(result.isError,true);
});
test('analytics buckets remain isolated from unrelated WABA reads',async()=>{
  const other='whatsapp_get_business_account';
  const result=await runtime(other,{id:'123456789012',analytics:{
    data_points:[{sent:22,clicked:[{type:'url_button',value:1}]}]
  }}).callTool({name:other,arguments:{}},{
    tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-reviewer'}
  });
  assert.equal(result.isError,false);
  assert.equal(result.structuredContent.data.analytics,undefined);
});
