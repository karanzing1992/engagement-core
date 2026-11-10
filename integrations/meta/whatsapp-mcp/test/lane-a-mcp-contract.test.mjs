import test from 'node:test';
import assert from 'node:assert/strict';
import {
  WHATSAPP_LANE_A_CATALOG,WHATSAPP_LANE_A_EXCLUDED,
} from '../src/lane-a-capability-catalog.mjs';
import { createWhatsAppLaneAMcpHarness } from '../src/lane-a-mcp-harness.mjs';

const tenantA='wacrm_'+'a'.repeat(40);
const tenantB='wacrm_'+'b'.repeat(40);
const principal=tenantId=>({tenantId,role:'synthetic-operator'});
const trustedPolicy={
  operatorApproved:true,irreversibleApproved:true,optInVerified:true,
  customerWindowOpen:true,templateApproved:true,billableSendApproved:true
};
const names=WHATSAPP_LANE_A_CATALOG.map(x=>x.name);
const harness=(opts={})=>createWhatsAppLaneAMcpHarness({
  authorizeTenant:async (p,tenantId)=>p?.tenantId===tenantId,
  capabilityGrants:names,allowSyntheticWrites:true,...opts,
});
const ctx=(tenantId=tenantA,policy=trustedPolicy)=>({
  verifiedPrincipal:principal(tenantId),tenantId,trustedPolicy:policy
});
const invoke=(h,name,args,context=ctx())=>h.callTool({name,arguments:args},context);
function sample(schema){
  if(schema.enum)return schema.enum[0];
  if(schema.type==='boolean')return true;
  if(schema.type==='number')return 0;
  if(schema.type==='integer')return schema.minimum||1;
  if(schema.type==='array')return [sample(schema.items)];
  if(schema.type==='object')
    return Object.fromEntries((schema.required||[]).map(key=>[key,sample(schema.properties[key])]));
  if(schema.pattern?.includes('wamid'))return 'wamid.ABCDEFG1234';
  if(schema.pattern?.includes('https'))return 'https://example.org/safe.png';
  if(schema.pattern?.includes('[a-z]{2,3}'))return 'en_US';
  if(schema.pattern?.includes('^[0-9]{6,64}'))return '123456789012';
  if(schema.pattern?.includes('[1-9][0-9]'))return '+919999999999';
  if(schema.pattern?.includes('A-Za-z0-9_-'))return 'NEXT';
  return 'synthetic';
}
function argsFor(def){
  const args=sample(def.inputSchema);
  if(/^whatsapp_send_(?:image|video|audio|voice|document|sticker)$/.test(def.name))args.id='123456789012';
  if(def.name==='whatsapp_upload_flow_json')args.flowJson='{"version":"7.2","screens":[]}';
  return args;
}
test('55 registered capabilities have unique names, standard MCP JSON schemas and zero default entitlements',()=>{
  assert.equal(WHATSAPP_LANE_A_CATALOG.length,55);
  assert.equal(new Set(names).size,55);
  assert.ok(WHATSAPP_LANE_A_EXCLUDED.includes('phone_deregister'));
  for(const d of WHATSAPP_LANE_A_CATALOG){
    assert.match(d.name,/^whatsapp_[a-z0-9_]+$/);
    assert.equal(d.inputSchema.type,'object');
    assert.equal(d.inputSchema.additionalProperties,false);
    assert.equal(d.integrationState,'synthetic_contract_only');
  }
  assert.deepEqual(createWhatsAppLaneAMcpHarness({
    authorizeTenant:async()=>true
  }).listTools(),[]);
});
test('all 55 MCP names are listable in explicitly granted synthetic test mode',()=>{
  const listed=harness().listTools();
  assert.equal(listed.length,55);
  assert.deepEqual(listed.map(x=>x.name),names);
  assert.ok(listed.every(x=>x.inputSchema?.type==='object'));
});
test('all 55 tool contracts produce a stable no-network synthetic result',async()=>{
  let checked=0;
  for(const d of WHATSAPP_LANE_A_CATALOG){
    const result=await invoke(harness(),d.name,argsFor(d));
    assert.equal(result.isError,false,d.name+' '+JSON.stringify(result.structuredContent));
    assert.equal(result.structuredContent.simulation,true);
    assert.match(result.structuredContent.syntheticReceipt,/^meta-core-synthetic-[a-f0-9]{24}$/);
    assert.equal(result.structuredContent.integrationState,'pending_provider_binding');
    checked++;
  }
  assert.equal(checked,55);
});
test('new sender operations are never advertised or executable by default',async()=>{
  const h=harness({allowSyntheticWrites:false});
  assert.ok(h.listTools().every(d=>d.annotations.readOnlyHint===true));
  const r=await invoke(h,'whatsapp_send_text',{to:'+919999999999',body:'synthetic'});
  assert.equal(r.structuredContent.error.code,'not_enabled');
});
test('missing tool grant and phone lifecycle mutations are always denied',async()=>{
  const h=harness({capabilityGrants:['whatsapp_get_business_account']});
  assert.equal((await invoke(h,'whatsapp_send_template',{
    to:'+919999999999',name:'hello',language:'en_US'
  })).structuredContent.error.code,'not_enabled');
  assert.equal((await invoke(h,'whatsapp_phone_deregister',{})).structuredContent.error.code,'unknown_tool');
  assert.equal(h.listTools().length,1);
});
test('cross-tenant, anonymous and policy impersonation are denied',async()=>{
  const h=harness();
  const d='whatsapp_get_business_account';
  assert.equal((await invoke(h,d,{},{
    verifiedPrincipal:principal(tenantA),tenantId:tenantB,trustedPolicy
  })).structuredContent.error.code,'forbidden');
  assert.equal((await invoke(h,d,{},{
    verifiedPrincipal:null,tenantId:tenantA,trustedPolicy
  })).structuredContent.error.code,'forbidden');
  assert.equal((await invoke(h,d,{tenantId:tenantA})).structuredContent.error.code,'invalid_input');
});
test('send window, approved template, billable and irreversible approvals are independently required',async()=>{
  const h=harness();
  assert.equal((await invoke(h,'whatsapp_send_text',{
    to:'+919999999999',body:'synthetic'
  },ctx(tenantA,{...trustedPolicy,customerWindowOpen:false}))).structuredContent.error.code,'policy_denied');
  assert.equal((await invoke(h,'whatsapp_send_template',{
    to:'+919999999999',name:'hello',language:'en_US'
  },ctx(tenantA,{...trustedPolicy,templateApproved:false}))).structuredContent.error.code,'policy_denied');
  assert.equal((await invoke(h,'whatsapp_send_template',{
    to:'+919999999999',name:'hello',language:'en_US'
  },ctx(tenantA,{...trustedPolicy,billableSendApproved:false}))).structuredContent.error.code,'policy_denied');
  assert.equal((await invoke(h,'whatsapp_publish_flow',{
    flowId:'123456789012'
  },ctx(tenantA,{...trustedPolicy,irreversibleApproved:false}))).structuredContent.error.code,'policy_denied');
});
test('malformed and unbounded structured input never reaches synthetic plan',async()=>{
  const h=harness();
  const bad=[
    {to:'+919999999999',body:'x'.repeat(4097)},
    {to:'not-e164',body:'synthetic'},
    {to:'+919999999999',body:'synthetic',access_token:'DO_NOT_LEAK'},
    Object.assign(Object.create(null),{to:'+919999999999',body:'synthetic'}),
  ];
  for(const args of bad){
    const r=await invoke(h,'whatsapp_send_text',args);
    assert.equal(r.structuredContent.error.code,'invalid_input');
    assert.ok(!JSON.stringify(r).includes('DO_NOT_LEAK'));
  }
  const getter={to:'+919999999999'};
  Object.defineProperty(getter,'body',{enumerable:true,get(){throw Error('getter') }});
  assert.equal((await invoke(h,'whatsapp_send_text',getter)).structuredContent.error.code,'invalid_input');
});
test('media guards deny ambiguous ID/link and unsafe SSRF input',async()=>{
  const h=harness();
  for(const arg of [
    {to:'+919999999999'},
    {to:'+919999999999',id:'123456789012',link:'https://example.org/a.png'},
    {to:'+919999999999',link:'https://127.0.0.1/image.png'},
    {to:'+919999999999',link:'https://169.254.169.254/metadata'},
    {to:'+919999999999',link:'https://user:pass@example.org/image.png'},
  ]){
    const r=await invoke(h,'whatsapp_send_image',arg);
    assert.equal(r.structuredContent.error.code,'invalid_input');
  }
  assert.equal((await invoke(h,'whatsapp_send_image',{
    to:'+919999999999',id:'123456789012'
  })).isError,false);
});
test('WACRM template read never accepts arbitrary WABA, phone ID, extra fields or foreign template paths',async()=>{
  const h=harness();
  for(const args of [
    {limit:101},{after:'../../etc'}, {wabaId:'123456789012'},
    {after:'x'.repeat(257)}
  ])assert.equal((await invoke(h,'whatsapp_list_templates',args)).structuredContent.error.code,'invalid_input');
  assert.equal((await invoke(h,'whatsapp_get_template',{
    templateId:'../../other-waba'
  })).structuredContent.error.code,'invalid_input');
});
test('flow JSON must be structured and cannot smuggle arbitrary metadata keys',async()=>{
  const h=harness();
  const base={flowId:'123456789012'};
  for(const flowJson of ['not-json','{"screens":{}}','{"screens":[]} ' + 'x']){
    assert.equal((await invoke(h,'whatsapp_upload_flow_json',{...base,flowJson})).structuredContent.error.code,'invalid_input');
  }
  assert.equal((await invoke(h,'whatsapp_upload_flow_json',{
    ...base,flowJson:'{"version":"7.2","screens":[]}'
  })).isError,false);
});
test('receipts never echo user phone, OTP or credential-like synthetic content',async()=>{
  const h=harness();
  const r=await invoke(h,'whatsapp_send_auth_template',{
    to:'+919999999999',name:'otp_template',language:'en_US',otp:'987654'
  });
  assert.equal(r.isError,false);
  assert.ok(!JSON.stringify(r).includes('987654'));
  assert.ok(!JSON.stringify(r).includes('+919999999999'));
  assert.ok(!JSON.stringify(r).includes('otp_template'));
});
test('denial precedes the external authorizer on malformed inputs',async()=>{
  let calls=0;
  const h=harness({authorizeTenant:async()=>{calls++;return true;}});
  const bad=await invoke(h,'whatsapp_send_text',{
    to:'+919999999999',body:'ok',token:'secret'
  });
  assert.equal(bad.structuredContent.error.code,'invalid_input');
  assert.equal(calls,0);
});
