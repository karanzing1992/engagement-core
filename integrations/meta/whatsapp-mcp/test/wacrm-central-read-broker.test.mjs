import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, createHash } from 'node:crypto';
import {
  createWacrmCentralBrokerReadAdapter, CENTRAL_BROKER_READ_TOOLS,
} from '../src/wacrm-central-read-broker.mjs';

const secret = 'synthetic-hmac-key-only-please-never-use-in-production-123';
const tenants = Object.freeze({
  a: 'wacrm_' + 'a'.repeat(40),
  b: 'wacrm_' + 'b'.repeat(40),
});
const routes = Object.freeze({
  [tenants.a]: { tenantId: tenants.a, activationId: 42,
    wabaId: '123456789012', phoneNumberId: '223456789012', status: 'active' },
  [tenants.b]: { tenantId: tenants.b, activationId: 43,
    wabaId: '123456789013', phoneNumberId: '223456789013', status: 'active' },
});

function make(overrides = {}) {
  const calls = [];
  let routeReads = 0;
  const adapter = createWacrmCentralBrokerReadAdapter({
    endpoint: 'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read',
    sharedSecret: secret,
    authorizeTenant: async (principal, tenantId) => !!principal &&
      principal.tenantId === tenantId && principal.scopes.includes('meta:read'),
    readRoute: async tenantId => { ++routeReads; return routes[tenantId]; },
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      assert.equal(url, 'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read');
      assert.equal(options.method, 'POST');
      assert.equal(options.redirect, 'error');
      assert.equal(options.cache, 'no-store');
      assert.equal(options.headers['X-Meta-Core-Client'], 'meta-core-read-v1');
      assert.equal(options.headers['X-Meta-Core-Audience'], 'wacrm-central');
      assert.equal(options.headers['Content-Type'], 'application/json');
      const body = JSON.parse(options.body);
      assert.equal(body.tenantId, routes[body.tenantId].tenantId);
      assert.equal(body.activationId, routes[body.tenantId].activationId);
      assert.deepEqual(Object.keys(body), ['tenantId', 'activationId', 'toolName', 'args']);
      assert.ok(!options.body.includes('accessToken'));
      const h = options.headers;
      const material = [
        'wacrm-meta-read-v1', h['X-Meta-Core-Client'], h['X-Meta-Core-Audience'],
        h['X-Meta-Core-Timestamp'], h['X-Meta-Core-Nonce'],
        createHash('sha256').update(options.body).digest('hex'),
      ].join('\n');
      assert.equal(h['X-Meta-Core-Signature'],
        'sha256=' + createHmac('sha256', secret).update(material).digest('hex'));
      return new Response(JSON.stringify({
        ok: true, tenantId: body.tenantId, toolName: body.toolName,
        graphApiVersion: 'v26.0',
        data: body.toolName === 'whatsapp_get_template'
          ? { id: body.args.templateId, name: 'synthetic', status: 'APPROVED' }
          : { data: [{ name: 'synthetic', status: 'APPROVED' }] }
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    },
    ...overrides,
  });
  return { adapter, calls, get routeReads() { return routeReads; } };
}

test('broker exports template reads only; no send, phone or media tools', () => {
  const { adapter } = make();
  assert.deepEqual(adapter.listTools().map(x => x.name), CENTRAL_BROKER_READ_TOOLS);
  assert.ok(adapter.listTools().every(x => x.permission === 'read'));
});

test('signed server-to-server two-tenant GET proxy returns synthetic Graph v26 data', async () => {
  const t = make();
  for (const tenantId of [tenants.a, tenants.b]) {
    const result = await t.adapter.invoke({
      principal: { tenantId, scopes: ['meta:read'] },
      tenantId, toolName: 'whatsapp_list_templates', args: { limit: 1 }
    });
    assert.equal(result.ok, true);
    assert.equal(result.data.data[0].name, 'synthetic');
  }
  assert.equal(t.calls.length, 2);
  assert.notEqual(t.calls[0].options.body, t.calls[1].options.body);
  assert.notEqual(t.calls[0].options.headers['X-Meta-Core-Nonce'],
    t.calls[1].options.headers['X-Meta-Core-Nonce']);
  assert.equal(t.routeReads, 2);
});

test('single template ID is pinned and HMAC signed without revealing any bearer', async () => {
  const t = make();
  const out = await t.adapter.invoke({
    principal: { tenantId: tenants.a, scopes: ['meta:read'] },
    tenantId: tenants.a, toolName: 'whatsapp_get_template',
    args: { templateId: '300000000010' }
  });
  assert.equal(out.ok, true);
  assert.equal(out.data.id, '300000000010');
  assert.ok(!JSON.stringify(out).includes(secret));
  assert.ok(!JSON.stringify(out).includes('accessToken'));
});

test('foreign principal denied before route resolution or network', async () => {
  const t = make();
  const denied = await t.adapter.invoke({
    principal: { tenantId: tenants.a, scopes: ['meta:read'] },
    tenantId: tenants.b, toolName: 'whatsapp_list_templates'
  });
  assert.equal(denied.error.code, 'forbidden');
  assert.equal(t.routeReads, 0);
  assert.equal(t.calls.length, 0);
});

test('missing scope, no principal and thrown authorization always denied', async () => {
  const t = make();
  for (const principal of [null, { tenantId: tenants.a, scopes: [] }]) {
    assert.equal((await t.adapter.invoke({
      principal, tenantId: tenants.a, toolName: 'whatsapp_list_templates'
    })).error.code, 'forbidden');
  }
  assert.equal(t.routeReads, 0);
  assert.equal(t.calls.length, 0);
  const broken = make({ authorizeTenant: () => { throw new Error('never leak'); } });
  assert.equal((await broken.adapter.invoke({
    principal: {}, tenantId: tenants.a, toolName: 'whatsapp_list_templates'
  })).error.code, 'forbidden');
});

test('mutation tools and malformed Graph inputs rejected before route credentials', async () => {
  const t = make();
  const principal = { tenantId: tenants.a, scopes: ['meta:read'] };
  for (const toolName of ['whatsapp_send_text', 'whatsapp_register_phone_number',
    'whatsapp_delete_template', 'whatsapp_get_media_info']) {
    assert.equal((await t.adapter.invoke({ principal, tenantId: tenants.a, toolName })).error.code, 'tool_not_allowed');
  }
  const invalid = [
    ['whatsapp_list_templates', { limit: 500 }],
    ['whatsapp_list_templates', { limit: 2, after: '../../etc' }],
    ['whatsapp_list_templates', { payload: 'unauthorized' }],
    ['whatsapp_get_template', { templateId: '../outside' }],
    ['whatsapp_get_template', { templateId: '123456', extra: 'x' }],
    ['whatsapp_list_templates', Object.assign(Object.create(null), { limit: 1 })],
    ['whatsapp_list_templates', ['oops']],
    ['whatsapp_list_templates', Object.defineProperty({}, 'limit', { enumerable: true, get() { throw new Error('getter not allowed'); } })],
    ['whatsapp_list_templates', new Proxy({}, { getPrototypeOf() { throw new Error('proxy not allowed'); } })],
  ];
  for (const [toolName, args] of invalid) {
    assert.equal((await t.adapter.invoke({ principal, tenantId: tenants.a, toolName, args })).error.code, 'invalid_input');
  }
  assert.equal(t.routeReads, 0);
  assert.equal(t.calls.length, 0);
});

test('unknown, inactive or mismatched Central activation routes are rejected', async () => {
  for (const override of [null, { ...routes[tenants.a], tenantId: tenants.b },
    { ...routes[tenants.a], status: 'revoked' },
    { ...routes[tenants.a], activationId: 0 }]) {
    const t = make({ readRoute: async () => override });
    const out = await t.adapter.invoke({
      principal: { tenantId: tenants.a, scopes: ['meta:read'] },
      tenantId: tenants.a, toolName: 'whatsapp_list_templates'
    });
    assert.equal(out.error.code, 'connection_unavailable');
    assert.equal(t.calls.length, 0);
  }
});

test('HTTPS broker endpoint and dedicated signing key are required', () => {
  for (const endpoint of [
    'http://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read',
    'https://central.synthetic.example/wp-json/wacrm-central/v1/meta/webhook',
    'https://central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read?redirect=evil',
    'https://user:pass@central.synthetic.example/wp-json/wacrm-central/v1/meta-core/read',
  ]) {
    assert.throws(() => make({ endpoint }), TypeError);
  }
  assert.throws(() => make({ sharedSecret: 'weak-secret' }), TypeError);
});

test('wrong broker response tenant, tool, API version, and leaked token are denied', async () => {
  const data = [
    { tenantId: tenants.b, toolName: 'whatsapp_list_templates', graphApiVersion: 'v26.0' },
    { tenantId: tenants.a, toolName: 'whatsapp_get_template', graphApiVersion: 'v26.0' },
    { tenantId: tenants.a, toolName: 'whatsapp_list_templates', graphApiVersion: 'v24.0' },
    { tenantId: tenants.a, toolName: 'whatsapp_list_templates', graphApiVersion: 'v26.0',
      accessToken: 'unexpected-Graph-bearer' },
  ];
  for (const item of data) {
    const t = make({ fetchImpl: async () => new Response(JSON.stringify({
      ok: true, data: {}, ...item,
    }), { headers: { 'Content-Type': 'application/json' } }) });
    const out = await t.adapter.invoke({
      principal: { tenantId: tenants.a, scopes: ['meta:read'] },
      tenantId: tenants.a, toolName: 'whatsapp_list_templates'
    });
    assert.equal(out.error.code, 'upstream_unavailable');
    assert.ok(!JSON.stringify(out).includes('unexpected-Graph-bearer'));
  }
});

test('oversized response, redirect, transport throw and invalid JSON fail closed', async () => {
  const fake = [
    async () => new Response('x'.repeat(160000), { headers: { 'Content-Type': 'application/json' } }),
    async () => new Response('redirect', { status: 302, headers: { location: 'https://evil.example' } }),
    async () => { throw new Error('private-network-details'); },
    async () => new Response('{bad', { headers: { 'Content-Type': 'application/json' } }),
  ];
  for (const transport of fake) {
    const t = make({ fetchImpl: transport });
    const out = await t.adapter.invoke({
      principal: { tenantId: tenants.a, scopes: ['meta:read'] },
      tenantId: tenants.a, toolName: 'whatsapp_list_templates'
    });
    assert.equal(out.error.code, 'upstream_unavailable');
    assert.ok(!JSON.stringify(out).includes('private-network-details'));
  }
});

test('Central broker rejects explicit error and negative-status envelopes despite valid HTTP 200 data',async()=>{
  const payloads=[
    {errors:[{message:'synthetic rejected'}]},
    {errors:[]},
    {error:{message:'synthetic rejected'}},
    {isError:true},
    {isError:false},
    {success:false},
    {success:'false'},
    {accepted:false}
  ];
  for(const extra of payloads){
    const t=make({fetchImpl:async (_url,options)=>{
      const request=JSON.parse(options.body);
      return new Response(JSON.stringify({
        ok:true,tenantId:request.tenantId,toolName:request.toolName,
        graphApiVersion:'v26.0',data:{data:[]},...extra
      }),{status:200,headers:{'Content-Type':'application/json'}});
    }});
    const result=await t.adapter.invoke({
      principal:{tenantId:tenants.a,scopes:['meta:read']},
      tenantId:tenants.a,toolName:'whatsapp_list_templates',args:{limit:1}
    });
    assert.equal(result.ok,false,JSON.stringify(extra));
    assert.equal(result.error.code,'upstream_unavailable');
    assert.ok(!JSON.stringify(result).includes('synthetic rejected'));
  }
});
