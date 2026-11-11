import test from 'node:test';
import assert from 'node:assert/strict';
import {
  createContractEnforcedWacrmBrokerAdapter, sanitizeWacrmTemplateResult,
} from '../src/wacrm-broker-response-contract.mjs';

const tenantA = 'wacrm_' + 'a'.repeat(40);
const tenantB = 'wacrm_' + 'b'.repeat(40);
const key = 'synthetic-signing-key-no-live-secret-phase1e-123456';
const template = Object.freeze({
  id: '300000000010', name: 'synthetic_template', language: 'en_US',
  status: 'APPROVED', category: 'UTILITY',
});

function make(output, onAuthorize = null) {
  const calls = [];
  let routeReads = 0;
  const adapter = createContractEnforcedWacrmBrokerAdapter({
    endpoint: 'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read',
    sharedSecret: key,
    authorizeTenant: async (principal, tenantId, toolName) => {
      if(onAuthorize)onAuthorize();
      return !!principal && principal.tenantId === tenantId &&
      principal.scopes?.includes('meta:read') &&
      ['whatsapp_list_templates', 'whatsapp_get_template'].includes(toolName);
    },
    readRoute: async tenantId => {
      routeReads++;
      return { tenantId, activationId: 42, wabaId: '123456789012',
        phoneNumberId: '223456789012', status: 'active' };
    },
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      const request = JSON.parse(options.body);
      assert.equal(url, 'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read');
      assert.equal(options.method, 'POST');
      assert.ok(options.headers['X-Meta-Core-Signature'].startsWith('sha256='));
      assert.ok(!options.body.includes('access_token'));
      const data = typeof output === 'function' ? output(request) : output;
      return new Response(JSON.stringify({
        ok: true, tenantId: request.tenantId, toolName: request.toolName,
        graphApiVersion: 'v26.0', data,
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    },
    now: () => 1794321000,
    nonceFactory: () => '1'.repeat(32),
  });
  return { adapter, calls, get routeReads() { return routeReads; } };
}
const auth = tenantId => ({ tenantId, scopes: ['meta:read'] });
const list = (adapter, tenantId = tenantA, args = {}) =>
  adapter.invoke({ principal: auth(tenantId), tenantId,
    toolName: 'whatsapp_list_templates', args });

test('Phase 1-E: WACRM v26 page schema is preserved for two synthetic tenants', async () => {
  const t = make({ data: [template], after: 'NEXT_CURSOR' });
  for (const tenantId of [tenantA, tenantB]) {
    const result = await list(t.adapter, tenantId, { limit: 1 });
    assert.equal(result.ok, true);
    assert.deepEqual(result.data, { data: [{ ...template }], after: 'NEXT_CURSOR' });
    assert.equal(Object.isFrozen(result.data.data[0]), true);
  }
  assert.equal(t.calls.length, 2);
  assert.equal(t.routeReads, 2);
});

test('Phase 1-E: exact WABA-scoped get-template result and ID match', async () => {
  const t = make(template);
  const ok = await t.adapter.invoke({ principal: auth(tenantA), tenantId: tenantA,
    toolName: 'whatsapp_get_template', args: { templateId: template.id } });
  assert.equal(ok.ok, true);
  assert.deepEqual(ok.data, template);
  const mismatch = make({ ...template, id: '300000000011' });
  const bad = await mismatch.adapter.invoke({ principal: auth(tenantA), tenantId: tenantA,
    toolName: 'whatsapp_get_template', args: { templateId: template.id } });
  assert.equal(bad.error.code, 'upstream_unavailable');
});

test('Phase 1-E: deny nested or top-level Graph credential regressions', async () => {
  const payloads = [
    { data: [{ ...template, access_token: 'synthetic-secret-must-not-leak' }] },
    { data: [template], access_token: 'synthetic-secret-must-not-leak' },
    { data: [template], paging: { next: 'https://example.invalid/secret' } },
    { data: [{ ...template, url: 'https://example.invalid/secret' }] },
    { data: [{ ...template, credentials: { bearer: 'synthetic' } }] },
  ];
  for (const data of payloads) {
    const t = make(data);
    const result = await list(t.adapter);
    assert.equal(result.error?.code, 'upstream_unavailable');
    assert.ok(!JSON.stringify(result).includes('synthetic-secret-must-not-leak'));
  }
});

test('Phase 1-E: malformed pages and rows deny instead of returning partial data', async () => {
  const payloads = [
    { data: 'not-an-array' },
    { data: new Array(101).fill(template) },
    { data: [{ ...template, id: '../wrong' }] },
    { data: [{ ...template, name: 'x'.repeat(191) }] },
    { data: [{ ...template, language: null }] },
    { data: [{ ...template, status: 'APPROVED\nBearer token' }] },
    { data: [null] },
    { data: [template], after: '../../wrong' },
    { data: [template], after: 'x'.repeat(257) },
    { data: [template], debug: true },
  ];
  for (const data of payloads) {
    const result = await list(make(data).adapter);
    assert.equal(result.error?.code, 'upstream_unavailable', JSON.stringify(data).slice(0,120));
  }
});

test('Phase 1-E: malformed prototype fields are rejected by standalone sanitizer', () => {
  const poisoned = JSON.parse('{"data":[{"id":"300000000010","name":"safe","language":"en_US","status":"APPROVED","__proto__":{"access_token":"secret"}}]}');
  assert.equal(sanitizeWacrmTemplateResult('whatsapp_list_templates', poisoned), null);
  assert.equal(sanitizeWacrmTemplateResult('whatsapp_get_template', template, '999999999999'), null);
  assert.equal(sanitizeWacrmTemplateResult('whatsapp_send_text', { data: [template] }), null);
});

test('Phase 1-E: foreign tenant and forbidden send never reach route or transport', async () => {
  const t = make({ data: [template] });
  const wrong = await t.adapter.invoke({ principal: auth(tenantA), tenantId: tenantB,
    toolName: 'whatsapp_list_templates', args: {} });
  assert.equal(wrong.error.code, 'forbidden');
  const send = await t.adapter.invoke({ principal: auth(tenantA), tenantId: tenantA,
    toolName: 'whatsapp_send_text', args: { text: 'DO NOT SEND' } });
  assert.equal(send.error.code, 'tool_not_allowed');
  assert.equal(t.routeReads, 0);
  assert.equal(t.calls.length, 0);
  assert.deepEqual(t.adapter.listTools().map(x => x.name),
    ['whatsapp_list_templates', 'whatsapp_get_template']);
});

test('Phase 1-E: Central empty list is a valid read-only response', async () => {
  const t = make({ data: [] });
  const result = await list(t.adapter);
  assert.deepEqual(result, { ok: true, data: { data: [] } });
});

test('P2 wrapper snapshots toolName and expectedId before asynchronous broker auth',async()=>{
  const args={templateId:template.id};
  const request={principal:auth(tenantA),tenantId:tenantA,
    toolName:'whatsapp_get_template',args};
  const t=make(template,()=>{
    // Attempts to rewrite expected result after the signed broker took a
    // private argument snapshot must not affect post-fetch validation.
    args.templateId='300000000011';
    request.toolName='whatsapp_list_templates';
  });
  const result=await t.adapter.invoke(request);
  assert.equal(result.ok,true,JSON.stringify(result));
  assert.deepEqual(result.data,template);
  assert.equal(t.calls.length,1);
  const signed=JSON.parse(t.calls[0].options.body);
  assert.equal(signed.toolName,'whatsapp_get_template');
  assert.equal(signed.args.templateId,template.id);
  assert.equal(args.templateId,'300000000011');
});
test('P2 wrapper rejects Proxy args before descriptor traps or host callbacks',async()=>{
  let traps=0,authCalls=0;
  const args=new Proxy({templateId:template.id},{
    getOwnPropertyDescriptor(){traps++;throw Error('forbidden proxy trap');}
  });
  const t=make(template,()=>{authCalls++;});
  const res=await t.adapter.invoke({principal:auth(tenantA),tenantId:tenantA,
    toolName:'whatsapp_get_template',args});
  assert.equal(res.ok,false);
  assert.equal(res.error.code,'invalid_input');
  assert.equal(traps,0);
  assert.equal(authCalls,0);
  assert.equal(t.calls.length,0);
});
