import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createEngagementWhatsAppAdapter } from '../src/adapter.mjs';
import { createMetaCoreDojoReadAdapter } from '../src/dojo-v26.mjs';
import { createWacrmCentralBrokerReadAdapter } from '../src/wacrm-central-read-broker.mjs';
import { createContractEnforcedWacrmBrokerAdapter, sanitizeWacrmTemplateResult } from '../src/wacrm-broker-response-contract.mjs';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';
import { validatePinnedDojoArgs } from '../src/lane-a-upstream-dojo-schemas.mjs';
import { createWhatsAppLaneAMcpHarness } from '../src/lane-a-mcp-harness.mjs';

const tenant='wacrm_'+'a'.repeat(40);
function poison(){
  let traps=0;
  const fail=()=>{traps++;throw Error('UNTRUSTED_PROXY_TRAP_EXECUTED');};
  return {proxy:new Proxy({},{
    get:fail,getPrototypeOf:fail,ownKeys:fail,getOwnPropertyDescriptor:fail,
    set:fail,has:fail
  }),get count(){return traps;}};
}
function oldBrokerConfig(state){
  return {
    endpoint:'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read',
    sharedSecret:'synthetic-signing-key-only-1234567890123456789012345',
    authorizeTenant:async()=>{state.host++;return true;},
    readRoute:async()=>{state.host++;throw Error('No live route');},
    fetchImpl:async()=>{state.host++;throw Error('No external fetch');}
  };
}
test('P3-A WBMCP standalone rejects Proxy envelope and nested input without trap/host access',async()=>{
  const state={host:0};
  const a=createEngagementWhatsAppAdapter({
    authorizeTenant:async()=>{state.host++;return true;},
    resolveConnection:async()=>{state.host++;throw Error('No connection');},
    sdkFactory:()=>{state.host++;throw Error('No SDK');}
  });
  for(const p of [poison(),poison()]){
    const r=await a.invoke(p.proxy);
    assert.equal(r.error.code,'invalid_input');
    assert.equal(p.count,0);
  }
  const p=poison();
  const r=await a.invoke({tenantId:'brand_a',principal:'operator_a',
    toolName:'whatsapp_get_business_account',args:{nested:[p.proxy]}});
  assert.equal(r.error.code,'invalid_input');
  assert.equal(p.count,0);
  let accesses=0;
  const q={tenantId:'brand_a',toolName:'whatsapp_get_business_account',principal:'operator_a'};
  Object.defineProperty(q,'args',{enumerable:true,get(){accesses++;throw Error('getter');}});
  assert.equal((await a.invoke(q)).error.code,'invalid_input');
  assert.equal(accesses,0);
  assert.equal(state.host,0);
});
test('P3-A Dojo standalone rejects Proxy envelopes and nested arrays without trap/host access',async()=>{
  const state={host:0};
  const a=createMetaCoreDojoReadAdapter({
    authorizeTenant:async()=>{state.host++;return true;},
    resolveConnection:async()=>{state.host++;throw Error('No connection');},
    toolsetFactory:()=>{state.host++;throw Error('No SDK');}
  });
  const p=poison();
  assert.equal((await a.invoke(p.proxy)).error.code,'invalid_input');
  assert.equal(p.count,0);
  const nested=poison();
  const r=await a.invoke({tenantId:'brand_a',principal:'operator_a',
    toolName:'whatsapp_list_templates',args:{limit:1,nested:[nested.proxy]}});
  assert.equal(r.error.code,'invalid_input');
  assert.equal(nested.count,0);
  assert.equal(state.host,0);
});
test('P3-A signed broker and enforced wrapper reject Proxy arguments before auth/transport',async()=>{
  const state={host:0};
  const raw=createWacrmCentralBrokerReadAdapter(oldBrokerConfig(state));
  const wrapped=createContractEnforcedWacrmBrokerAdapter(oldBrokerConfig(state));
  for(const adapter of [raw,wrapped]){
    const outer=poison();
    const r=await adapter.invoke(outer.proxy);
    assert.equal(r.error.code,'invalid_input');
    assert.equal(outer.count,0);
    const args=poison();
    const out=await adapter.invoke({tenantId:tenant,principal:{tenantId:tenant},
      toolName:'whatsapp_list_templates',args:args.proxy});
    assert.equal(out.error.code,'invalid_input');
    assert.equal(args.count,0);
  }
  assert.equal(state.host,0);
});
test('P3-A response sanitizer rejects Proxy row, page or array without any traps',()=>{
  for(const make of [
    p=>sanitizeWacrmTemplateResult('whatsapp_get_template',p,'300000000010'),
    p=>sanitizeWacrmTemplateResult('whatsapp_list_templates',p),
    p=>sanitizeWacrmTemplateResult('whatsapp_list_templates',{data:[p]}),
    p=>sanitizeWacrmTemplateResult('whatsapp_list_templates',{data:p})
  ]){
    const p=poison();
    assert.equal(make(p.proxy),null);
    assert.equal(p.count,0);
  }
  let reads=0;
  const row={name:'synthetic',language:'en_US',status:'APPROVED'};
  Object.defineProperty(row,'id',{enumerable:true,get(){reads++;throw Error('getter');}});
  assert.equal(sanitizeWacrmTemplateResult('whatsapp_get_template',row,'300000000010'),null);
  assert.equal(reads,0);
});
test('P3-C literal dotted or bracketed key cannot impersonate contact phone structural path',async()=>{
  let policies=0,provider=0;
  const mcp=createLaneAProviderMcp({
    verifyIdentity:async()=>true,authorizeTenant:async()=>true,
    readPolicy:async()=>{policies++;return {
      operatorApproved:true,irreversibleApproved:true,optInVerified:true,
      customerWindowOpen:true,templateApproved:true,billableSendApproved:true
    };},
    resolveRoute:async()=>({tenantId:tenant,status:'active',activationId:4,
      wabaId:'123456789012',phoneNumberId:'223456789012'}),
    resolveOwnership:async()=>({wabaIdVerified:true}),
    providers:{dojo:{invoke:async()=>{provider++;return {ok:true,data:{
      accepted:true,messageId:'wamid.synthetic_12345'
    }};}}},
    grants:['whatsapp_send_contacts'],enableWriteCandidates:true
  });
  const ctx={tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-operator'},
    requestId:'security-host-request-1234'};
  const valid={to:'+919999999999',contacts:[{
    name:{formatted_name:'Synthetic'},phones:[{phone:'+918888888888'}]
  }]};
  for(const evil of [
    {...valid,'contacts[].phones[]':{phone:'+917777777777'}},
    {to:valid.to,contacts:[{'phones[].phone':'+917777777777'}]},
    {...valid,'contacts':[{name:{formatted_name:'S'},'phones[]':{phone:'+917777777777'}}]}
  ]){
    const result=await mcp.callTool({name:'whatsapp_send_contacts',arguments:evil},ctx);
    assert.equal(result.structuredContent.error.code,'invalid_input');
    assert.equal(policies,0);
    assert.equal(provider,0);
  }
  const r=await mcp.callTool({name:'whatsapp_send_contacts',arguments:valid},ctx);
  assert.equal(r.isError,false,JSON.stringify(r.structuredContent));
  assert.equal(policies,1);
  assert.equal(provider,1);
});
test('P3-C encoded loopback and known wildcard-DNS endpoints fail offline URL preflight',async()=>{
  const invalid=[
    'https://0x7f000001/data.jpg','https://2130706433/data.jpg',
    'https://0177.0.0.1/data.jpg','https://127.0.0.1.nip.io/data.jpg',
    'https://127.0.0.1.sslip.io/data.jpg','https://lvh.me/data.jpg',
    'https://localhost.localtest.me/data.jpg'
  ];
  for(const sourceUrl of invalid){
    assert.equal(validatePinnedDojoArgs('whatsapp_upload_media_from_url',
      {sourceUrl,mimeType:'image/jpeg'}),null,sourceUrl);
  }
  assert.ok(validatePinnedDojoArgs('whatsapp_upload_media_from_url',
    {sourceUrl:'https://cdn.example.org/data.jpg',mimeType:'image/jpeg'}));
  let authorized=0;
  const harness=createWhatsAppLaneAMcpHarness({
    authorizeTenant:async()=>{authorized++;return true;},
    capabilityGrants:['whatsapp_create_flow'],allowSyntheticWrites:true
  });
  const ctx={tenantId:tenant,verifiedPrincipal:{tenantId:tenant,actorId:'synthetic-operator'},
    trustedPolicy:{operatorApproved:true}};
  for(const endpointUri of [
    'https://127.0.0.1.nip.io/flow','https://2130706433/flow','https://lvh.me/flow'
  ]){
    const res=await harness.callTool({name:'whatsapp_create_flow',arguments:{
      name:'Synthetic',categories:['SIGN_UP'],endpointUri
    }},ctx);
    assert.equal(res.isError,true,endpointUri);
  }
  assert.equal(authorized,0);
});
test('P3-B Phase 1-D workflow has immutable pinned checkout and Node actions',()=>{
  const text=readFileSync(new URL('../../../../.github/workflows/meta-core-phase1d-certify.yml',
    import.meta.url),'utf8');
  assert.match(text,/uses: actions\/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1/);
  assert.match(text,/uses: actions\/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1/);
  assert.doesNotMatch(text,/uses: actions\/(?:checkout|setup-node)@v\d+/);
});
