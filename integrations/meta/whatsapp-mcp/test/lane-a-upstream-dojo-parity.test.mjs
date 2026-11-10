import test from 'node:test';
import assert from 'node:assert/strict';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';
import { WHATSAPP_LANE_A_CATALOG } from '../src/lane-a-capability-catalog.mjs';

test('Lane A matches all 19 real pinned Dojo 0.5.0 MCP tool names without duplicate alternatives',()=>{
  const client={};
  const upstream=createWhatsAppToolset({client,wabaPhoneNumberId:'223456789012'});
  const upstreamNames=upstream.tools.map(x=>x.name);
  const localNames=new Set(WHATSAPP_LANE_A_CATALOG.map(x=>x.name));
  const providerCandidates=WHATSAPP_LANE_A_CATALOG
    .filter(x=>x.adapter==='dojo'||x.adapter==='broker').map(x=>x.name);
  assert.equal(upstreamNames.length,19);
  assert.equal(new Set(upstreamNames).size,19);
  assert.deepEqual(new Set(upstreamNames),new Set(providerCandidates));
  for(const d of upstream.tools){
    assert.ok(localNames.has(d.name));
    assert.equal(typeof d.description,'string');
    assert.ok(d.inputSchema&&typeof d.inputSchema==='object');
  }
  assert.equal(upstream.resources.length,2);
  assert.equal(upstream.prompts.length,1);
});

test('Installed Dojo MCP executes synthetic text and approved-template tools against fake client only',async()=>{
  const calls=[];
  const client={
    async sendText(args){
      calls.push({tool:'text',args});
      return {messages:[{id:'wamid.synthetic_text_001'}]};
    },
    async sendTemplate(args){
      calls.push({tool:'template',args});
      return {messages:[{id:'wamid.synthetic_template_002'}]};
    },
  };
  const upstream=createWhatsAppToolset({client,wabaPhoneNumberId:'223456789012'});
  const textResult=await upstream.dispatch('whatsapp_send_text',{
    to:'+919999999999',body:'Synthetic only; never send over Meta'
  });
  assert.notEqual(textResult.isError,true,JSON.stringify(textResult));
  assert.equal(textResult.structuredContent.messageId,'wamid.synthetic_text_001');
  const templateResult=await upstream.dispatch('whatsapp_send_template',{
    to:'+919999999999',name:'synthetic_utility',language:'en_US'
  });
  assert.notEqual(templateResult.isError,true,JSON.stringify(templateResult));
  assert.equal(templateResult.structuredContent.messageId,'wamid.synthetic_template_002');
  assert.deepEqual(calls.map(c=>c.tool),['text','template']);
  assert.equal(calls[0].args.to,'+919999999999');
  assert.equal(calls[1].args.name,'synthetic_utility');
  // The fake client has NO HTTP method or credential. The toolset cannot reach Meta.
});

test('Installed Dojo MCP rejects unknown tools and invalid args without calling fake client',async()=>{
  let sent=0;
  const toolset=createWhatsAppToolset({
    client:{sendText:async()=>{sent++;throw Error('should not send');}},
    wabaPhoneNumberId:'223456789012',
  });
  const unknown=await toolset.dispatch('whatsapp_phone_register',{});
  assert.equal(unknown.isError,true);
  assert.equal(unknown.structuredContent.error.code,'unknown_tool');
  const invalid=await toolset.dispatch('whatsapp_send_text',{body:'no recipient'});
  assert.equal(invalid.isError,true);
  assert.equal(invalid.structuredContent.error.code,'invalid_args');
  assert.equal(sent,0);
});
