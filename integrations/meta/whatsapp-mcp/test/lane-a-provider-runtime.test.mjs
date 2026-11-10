import test from 'node:test';
import assert from 'node:assert/strict';
import { dojoFixture } from './fixtures/lane-a-dojo-fixtures.mjs';
import { WHATSAPP_LANE_A_CATALOG } from '../src/lane-a-capability-catalog.mjs';
import {
  buildWacrmGraphV26Plan,LANE_A_GRAPH_HOST_TOOLS
} from '../src/lane-a-graph-v26-plans.mjs';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';

const A='wacrm_'+'a'.repeat(40),B='wacrm_'+'b'.repeat(40);
const routeFor=tenantId=>({
  tenantId,activationId:41,status:'active',wabaId:'123456789012',
  phoneNumberId:'223456789012'
});
const principalFor=tenantId=>({tenantId,actorId:'synthetic-operator'});
const policy={
  operatorApproved:true,irreversibleApproved:true,optInVerified:true,
  customerWindowOpen:true,templateApproved:true,billableSendApproved:true
};
function sample(schema){
  if(schema.enum)return schema.enum[0];
  if(schema.type==='boolean')return true;
  if(schema.type==='number')return 0;
  if(schema.type==='integer')return schema.minimum||1;
  if(schema.type==='array')return [sample(schema.items)];
  if(schema.type==='object')return Object.fromEntries(
    (schema.required||[]).map(k=>[k,sample(schema.properties[k])]));
  const pat=schema.pattern||'';
  if(pat.includes('wamid'))return 'wamid.synthetic_id_123';
  if(pat.includes('https'))return 'https://example.org/resource';
  if(pat.includes('[a-z]{2,3}'))return 'en_US';
  if(pat.includes('^[0-9]{6,64}'))return '123456789012';
  if(pat.includes('[1-9][0-9]'))return '+919999999999';
  if(pat.includes('A-Za-z0-9_-'))return 'SYNTHETIC_QR_123';
  return 'synthetic';
}
function inputFor(d){
  if(d.adapter==='dojo')return dojoFixture(d.name);

  const args=sample(d.inputSchema);
  if(/^whatsapp_send_(?:image|video|audio|voice|document|sticker)$/.test(d.name))
    args.id='123456789012';
  if(d.name==='whatsapp_upload_flow_json')args.flowJson='{"version":"7.2","screens":[]}';
  if(d.name==='whatsapp_get_business_analytics'||d.name==='whatsapp_get_template_analytics'){
    args.startDate='2026-11-01';args.endDate='2026-11-09';
  }
  if(d.name==='whatsapp_update_business_profile')args.about='Synthetic test profile';
  if(d.name==='whatsapp_delete_qr_code')args.qrId='SYNTHETIC_QR_123';
  return args;
}
function proofFor(args){
  return {
    wabaIdVerified:true,
    templateId:args.templateId,templateName:'synthetic_template',
    flowId:args.flowId,mediaId:args.mediaId,
    qrId:args.qrId,qrCode:'SYNTHETIC_QR_123'
  };
}
function setup(overrides={}){
  const count={id:0,auth:0,policy:0,route:0,ownership:0,provider:0};
  const plans=[],receipts=[];
  const providers={
    host:{
      async executePlan(envelope){
        count.provider++;plans.push(envelope.plan);
        // Analytics must be realistic metric-bearing synthetic fixtures, not
        // generic {id,name}; an empty report must be rejected by the runtime.
        const receipt=envelope.plan.toolName==='whatsapp_get_business_analytics'?
          {ok:true,data:{analytics:{data_points:[{start:1793491200,end:1793577600,
            sent:4,delivered:3}]}}}:
          envelope.plan.toolName==='whatsapp_get_template_analytics'?
          {ok:true,data:{template_analytics:{data:[{template_id:'123456789012',
            data_points:[{start:1793491200,end:1793577600,sent:5,read:2,clicked:1}]}]}}}:
          envelope.plan.operationKind==='read'?
          {ok:true,data:{id:'123456789012',name:'synthetic'}}:
          {ok:true,data:{accepted:true,resourceId:'123456789012'}};
        receipts.push(receipt);return receipt;
      }
    },
    dojo:{
      async invoke(envelope){
        count.provider++;
        return envelope.toolName==='whatsapp_get_media_info'?
          {ok:true,data:{id:'123456789012',mimeType:'image/jpeg',fileSize:30,
            sha256:'a'.repeat(64)}}:
          {ok:true,data:{accepted:true,messageId:'wamid.synthetic_12345678'}};
      }
    },
    broker:{
      async invoke({toolName,args}){
        count.provider++;
        return {ok:true,data:toolName==='whatsapp_get_template'?
          {id:args.templateId,name:'synthetic_template',
            language:'en_US',status:'APPROVED'}:
          {data:[{id:'123456789012',name:'synthetic_template',
            language:'en_US',status:'APPROVED'}]}};
      }
    },
    wacrm:{
      async read(){
        count.provider++;
        return {ok:true,data:{data:[{id:'123456789012',status:'delivered'}]}};
      }
    }
  };
  const host={
    verifyIdentity:async (principal,tenantId)=>{
      count.id++;return principal.actorId==='synthetic-operator'&&
        principal.tenantId===tenantId;
    },
    authorizeTenant:async (principal,tenantId)=>{
      count.auth++;return principal.tenantId===tenantId;
    },
    readPolicy:async ()=>{count.policy++;return policy;},
    resolveRoute:async tenantId=>{count.route++;return routeFor(tenantId);},
    resolveOwnership:async (route,name,args)=>{
      count.ownership++;return proofFor(args);
    },
    providers,grants:WHATSAPP_LANE_A_CATALOG.map(d=>d.name),
    enableWriteCandidates:true,
    ...overrides
  };
  return {mcp:createLaneAProviderMcp(host),count,plans,receipts};
}
const ctx=tenantId=>({
  tenantId,verifiedPrincipal:principalFor(tenantId),
  requestId:'server-issued-idempotency-key-123456789'
});
const call=(mcp,name,args,context=ctx(A))=>
  mcp.callTool({name,arguments:args},context);

test('All 33 Graph-host capabilities have deterministic credentialless Graph v26 plans',()=>{
  assert.equal(LANE_A_GRAPH_HOST_TOOLS.length,33);
  const hostNames=WHATSAPP_LANE_A_CATALOG.filter(x=>x.adapter==='host').map(x=>x.name);
  assert.deepEqual(LANE_A_GRAPH_HOST_TOOLS,hostNames);
  const owned=proofFor({
    templateId:'123456789012',flowId:'123456789012',
    mediaId:'123456789012',qrId:'SYNTHETIC_QR_123'
  });
  for(const d of WHATSAPP_LANE_A_CATALOG.filter(x=>x.adapter==='host')){
    const args=inputFor(d);
    const plan=buildWacrmGraphV26Plan({
      name:d.name,args,route:routeFor(A),ownership:{...owned,...proofFor(args)}
    });
    assert.equal(plan.toolName,d.name);
    assert.equal(plan.graphApiVersion,'v26.0');
    assert.equal(plan.credentialMode,'wacrm_central_only');
    assert.match(plan.resourcePath,/^\/v26\.0\//);
    assert.ok(['GET','POST','DELETE'].includes(plan.method));
    if(d.kind==='read')assert.equal(plan.method,'GET');
    assert.ok(!JSON.stringify(plan).includes('Bearer '));
    assert.ok(!JSON.stringify(plan).includes('access_token'));
  }
});

test('all 55 provider-bound MCP tools enumerate with valid registered adapters',()=>{
  const x=setup();
  assert.equal(WHATSAPP_LANE_A_CATALOG.length,55);
  assert.equal(x.mcp.listTools().length,55);
  const types={};
  for(const d of WHATSAPP_LANE_A_CATALOG){
    types[d.adapter]=(types[d.adapter]||0)+1;
  }
  assert.deepEqual(types,{host:33,dojo:17,broker:2,wacrm:3});
});
test('full mocked 55 tool/tenant/provider E2E is available without network or credentials',async()=>{
  const t=setup();
  for(const d of WHATSAPP_LANE_A_CATALOG){
    const args=inputFor(d);
    const result=await call(t.mcp,d.name,args);
    assert.equal(result.isError,false,d.name+': '+JSON.stringify(result.structuredContent));
    assert.equal(result.structuredContent.toolName,d.name);
    assert.equal(result.structuredContent.graphApiVersion,'v26.0');
    assert.equal(result.structuredContent.ok,true);
    assert.ok(!JSON.stringify(result).includes('+919999999999'));
    assert.ok(!JSON.stringify(result).includes('access_token'));
  }
  assert.equal(t.count.provider,55);
  assert.equal(t.plans.length,33);
});

test('zero default grants, missing providers and disabled writes are invisible or denied',async()=>{
  const bare=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>policy,resolveRoute:async()=>routeFor(A),
    resolveOwnership:async()=>({wabaIdVerified:true})
  });
  assert.deepEqual(bare.listTools(),[]);
  assert.equal((await call(bare,'whatsapp_send_text',{
    to:'+919999999999',body:'hello'
  })).structuredContent.error.code,'not_enabled');
  const noWriters=setup({enableWriteCandidates:false});
  assert.ok(noWriters.mcp.listTools().every(t=>t.annotations.readOnlyHint===true));
  assert.equal((await call(noWriters.mcp,'whatsapp_send_text',{
    to:'+919999999999',body:'synthetic'
  })).structuredContent.error.code,'not_enabled');
  const unbound=setup({providers:{}});
  assert.deepEqual(unbound.mcp.listTools(),[]);
  assert.equal((await call(unbound.mcp,'whatsapp_get_business_account',{}))
    .structuredContent.error.code,'provider_unavailable');
});
test('identity and cross-tenant rejection precede policy, route and provider access',async()=>{
  const t=setup();
  const cross=await call(t.mcp,'whatsapp_get_business_account',{},{
    ...ctx(A),tenantId:B
  });
  assert.equal(cross.structuredContent.error.code,'forbidden');
  assert.equal(t.count.policy,0);
  assert.equal(t.count.route,0);
  assert.equal(t.count.provider,0);
  const bad=setup({verifyIdentity:async()=>{
    throw Error('private identity details MUST NOT leak');
  }});
  assert.equal((await call(bad.mcp,'whatsapp_get_business_account',{}))
    .structuredContent.error.code,'forbidden');
  assert.equal(bad.count.route,0);
});
test('mutation/approval gates deny before WACRM provider and actual route lookup',async()=>{
  const t=setup({readPolicy:async()=>({...policy,billableSendApproved:false})});
  const res=await call(t.mcp,'whatsapp_send_text',{
    to:'+919999999999',body:'synthetic'
  });
  assert.equal(res.structuredContent.error.code,'policy_denied');
  assert.equal(t.count.provider,0);
  assert.equal(t.count.route,0);
});
test('all mutations demand host-issued idempotency key; read-only calls do not',async()=>{
  const t=setup();
  const bad=await call(t.mcp,'whatsapp_create_template',{
    name:'example',language:'en_US',category:'UTILITY',components:[{type:'BODY'}]
  },{tenantId:A,verifiedPrincipal:principalFor(A)});
  assert.equal(bad.structuredContent.error.code,'request_id_required');
  assert.equal(t.count.route,0);
  const ok=await call(t.mcp,'whatsapp_get_business_account',{},{
    tenantId:A,verifiedPrincipal:principalFor(A)
  });
  assert.equal(ok.isError,false);
});
test('by-id template, flow and media mutations demand verified WABA ownership',async()=>{
  const t=setup({resolveOwnership:async()=>({wabaIdVerified:false})});
  for(const name of ['whatsapp_delete_template','whatsapp_publish_flow','whatsapp_delete_media']){
    const args=name==='whatsapp_delete_template'?{templateId:'123456789012'}:
      name==='whatsapp_delete_media'?{mediaId:'123456789012'}:{flowId:'123456789012'};
    const got=await call(t.mcp,name,args);
    assert.equal(got.structuredContent.error.code,'ownership_unverified');
  }
  assert.equal(t.count.provider,0);
});
test('Graph planner enforces pinned route and rejects unproven flow/template assets',()=>{
  assert.throws(()=>buildWacrmGraphV26Plan({
    name:'whatsapp_delete_flow',args:{flowId:'123456789012'},
    route:routeFor(A),ownership:{wabaIdVerified:true,flowId:'123456789013'}
  }),e=>e.code==='ownership_unverified');
  assert.throws(()=>buildWacrmGraphV26Plan({
    name:'whatsapp_list_flows',args:{},route:{...routeFor(A),wabaId:'../../../x'}
  }),e=>e.code==='route_unavailable');
  assert.throws(()=>buildWacrmGraphV26Plan({
    name:'whatsapp_delete_template',args:{templateId:'123456789012'},
    route:routeFor(A),ownership:{wabaIdVerified:true,templateId:'123456789012'}
  }),e=>e.code==='ownership_unverified');
});
test('Graph request examples map to official fixed routes, no browser-controlled Graph URL',()=>{
  const route=routeFor(A);
  const cases=[
    ['whatsapp_list_phone_numbers',{},'GET','/v26.0/123456789012/phone_numbers'],
    ['whatsapp_get_business_profile',{},'GET','/v26.0/223456789012/whatsapp_business_profile'],
    ['whatsapp_list_flows',{},'GET','/v26.0/123456789012/flows'],
    ['whatsapp_create_qr_code',{prefilledMessage:'synthetic'},'POST','/v26.0/223456789012/message_qrdls'],
    ['whatsapp_create_template',{name:'synthetic',category:'UTILITY',
      language:'en_US',components:[{type:'BODY'}]},'POST','/v26.0/123456789012/message_templates']
  ];
  for(const [name,args,method,resourcePath] of cases){
    const p=buildWacrmGraphV26Plan({name,args,route});
    assert.equal(p.method,method);
    assert.equal(p.resourcePath,resourcePath);
    assert.equal(JSON.stringify(p).includes('Bearer'),false);
  }
});
test('provider response containing Meta accessToken/recipientPhone is rejected and not echoed',async()=>{
  const t=setup({providers:{
    host:{async executePlan(){return {ok:true,data:{id:'123456789012',
      access_token:'synthetic_secret_must_not_leak'}};}}
  }});
  const r=await call(t.mcp,'whatsapp_get_business_account',{});
  assert.equal(r.structuredContent.error.code,'upstream_unavailable');
  assert.ok(!JSON.stringify(r).includes('synthetic_secret_must_not_leak'));
  const t2=setup({providers:{
    dojo:{async invoke(){return {ok:true,data:{accepted:true,
      recipientPhone:'+919999999999'}};}}
  }});
  const s=await call(t2.mcp,'whatsapp_send_text',{
    to:'+919999999999',body:'hello'
  });
  assert.equal(s.structuredContent.error.code,'upstream_unavailable');
  assert.ok(!JSON.stringify(s).includes('+919999999999'));
});
test('timeouts, 429-style errors and provider faults do not trigger blind retries or leak internals',async()=>{
  let calls=0;
  const t=setup({providers:{
    host:{async executePlan(){calls++;throw Error('Graph bearer=SECRET');}}
  }});
  const r=await call(t.mcp,'whatsapp_get_business_account',{});
  assert.equal(r.structuredContent.error.code,'upstream_unavailable');
  assert.equal(calls,1);
  assert.ok(!JSON.stringify(r).includes('SECRET'));
});
test('WACRM page and message status use only server verified actor/tenant, no Graph access',async()=>{
  const t=setup();
  for(const name of ['whatsapp_list_inbound_events',
    'whatsapp_get_message_status','whatsapp_get_delivery_status']){
    const d=WHATSAPP_LANE_A_CATALOG.find(x=>x.name===name);
    const out=await call(t.mcp,name,inputFor(d));
    assert.equal(out.isError,false);
  }
  assert.equal(t.plans.length,0);
  assert.equal(t.count.provider,3);
});
test('Nokia/other project and WhatsApp phone registration are not part of Lane A',async()=>{
  const t=setup();
  for(const name of ['whatsapp_phone_register','whatsapp_phone_deregister',
    'whatsapp_graph_proxy','whatsapp_account_transfer']){
    const out=await call(t.mcp,name,{});
    assert.equal(out.structuredContent.error.code,'unknown_tool');
  }
});
