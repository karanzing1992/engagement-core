import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PINNED_DOJO_OWNED_NAMES,getPinnedDojoInputJsonSchema,validatePinnedDojoArgs
} from '../src/lane-a-upstream-dojo-schemas.mjs';
import { createWhatsAppLaneAMcpHarness } from '../src/lane-a-mcp-harness.mjs';

const names=PINNED_DOJO_OWNED_NAMES;
const tenant='wacrm_'+'a'.repeat(40);
const principal={tenantId:tenant};
const authorizeTenant=async(p,t)=>p?.tenantId===t;
const grant=()=>createWhatsAppLaneAMcpHarness({
  authorizeTenant,capabilityGrants:names,allowSyntheticWrites:true
});
const ctx={verifiedPrincipal:principal,tenantId:tenant,
  trustedPolicy:{operatorApproved:true,irreversibleApproved:true,optInVerified:true,
    customerWindowOpen:true,templateApproved:true,billableSendApproved:true}};
const invoke=(name,args)=>grant().callTool({name,arguments:args},ctx);

test('actual pinned Dojo 17 hosted tool schemas are advertised losslessly to MCP',()=>{
  assert.equal(names.length,17);
  const tools=grant().listTools();
  assert.equal(tools.length,17);
  for(const d of tools){
    const actual=getPinnedDojoInputJsonSchema(d.name);
    assert.deepEqual(d.inputSchema,actual,d.name);
    assert.equal(d.inputSchema.additionalProperties,false,d.name);
    assert.equal(d.inputSchema.type,'object',d.name);
  }
});

test('all important nested Dojo input shapes pass upstream Zod and trusted MCP ingress',async()=>{
  const valid=[
    ['whatsapp_send_contacts',{to:'+919999999999',contacts:[
      {name:{formatted_name:'Synthetic Guest'},phones:[{phone:'+919999999999'}]}]}],
    ['whatsapp_send_interactive_buttons',{to:'+919999999999',body:'Choose',
      buttons:[{id:'A',title:'One'}],header:{type:'text',text:'Choices'}}],
    ['whatsapp_send_interactive_list',{to:'+919999999999',body:'Choose',
      button:'Options',sections:[{title:'Section',rows:[{id:'A',title:'One'}]}],
      header:{type:'text',text:'Items'}}],
    ['whatsapp_send_template',{to:'+919999999999',name:'approved_utility',
      language:'en_US',components:[{type:'body',parameters:[
        {type:'text',text:'Guest'}]}]}],
    ['whatsapp_send_carousel_template',{to:'+919999999999',
      name:'approved_carousel',language:'en_US',
      cards:[{header:{type:'image',mediaId:'123456789012'},
        buttons:[{subType:'quick_reply',payload:'one'}]}]}],
  ];
  for(const [name,args] of valid){
    assert.ok(validatePinnedDojoArgs(name,args),name+' Zod parse');
    assert.equal((await invoke(name,args)).isError,false,name);
  }
});
test('strict upstream validation + independent policy guard refuse sensitive/unsafe nested fields',async()=>{
  const invalid=[
    ['whatsapp_send_text',{to:'not_e164',body:'test'}],
    ['whatsapp_send_text',{to:'+919999999999',body:'x'.repeat(4097)}],
    ['whatsapp_send_image',{to:'+919999999999',link:'https://127.0.0.1/a.jpg'}],
    ['whatsapp_send_image',{to:'+919999999999',link:'https://user:pass@example.org/a.jpg'}],
    ['whatsapp_send_image',{to:'+919999999999',link:'https://[::1]/a.jpg'}],
    ['whatsapp_send_text',{to:'+919999999999',body:'test',access_token:'DO_NOT_LEAK'}],
    ['whatsapp_send_template',{to:'+919999999999',name:'approved',language:'en_US',
      components:[{type:'body',parameters:[{type:'text',access_token:'DO_NOT_LEAK'}]}]}],
    ['whatsapp_send_image',{to:'+919999999999',id:'123456789012',
      link:'https://example.org/a.jpg'}]
  ];
  for(const [name,args] of invalid){
    assert.equal(validatePinnedDojoArgs(name,args),null,name);
    const r=await invoke(name,args);
    assert.equal(r.structuredContent.error.code,'invalid_input',name);
    assert.ok(!JSON.stringify(r).includes('DO_NOT_LEAK'));
  }
  const getter={to:'+919999999999'};
  Object.defineProperty(getter,'body',{enumerable:true,get(){throw Error('getter');}});
  assert.equal(validatePinnedDojoArgs('whatsapp_send_text',getter),null);
  const cycle={to:'+919999999999',body:'test'};cycle.extra=cycle;
  assert.equal(validatePinnedDojoArgs('whatsapp_send_text',cycle),null);
});
test('Dojo broker-managed template reads cannot bypass WACRM Central',()=>{
  assert.equal(getPinnedDojoInputJsonSchema('whatsapp_list_templates'),null);
  assert.equal(getPinnedDojoInputJsonSchema('whatsapp_get_template'),null);
  assert.equal(validatePinnedDojoArgs('whatsapp_list_templates',{}),null);
});

test('P2 standalone harness rejects inherited Array toJSON hook without invoking it',async()=>{
  const {createWhatsAppLaneAMcpHarness}=await import('../src/lane-a-mcp-harness.mjs');
  let hits=0,auth=0;
  const proto=Object.create(Array.prototype);
  Object.defineProperty(proto,'toJSON',{get(){hits++;throw Error('should not execute');}});
  const contacts=[];
  Object.setPrototypeOf(contacts,proto);
  const h=createWhatsAppLaneAMcpHarness({
    authorizeTenant:async()=>{auth++;return false;},
    capabilityGrants:['whatsapp_send_contacts'],allowSyntheticWrites:true
  });
  const tenant='wacrm_'+'a'.repeat(40);
  const result=await h.callTool({
    name:'whatsapp_send_contacts',
    arguments:{to:'+919999999999',contacts}
  },{tenantId:tenant,verifiedPrincipal:{tenantId:tenant},
    trustedPolicy:{optInVerified:true,customerWindowOpen:true,billableSendApproved:true}});
  assert.equal(result.isError,true);
  assert.equal(result.structuredContent.error.code,'invalid_input');
  assert.equal(hits,0);
  assert.equal(auth,0);
});
