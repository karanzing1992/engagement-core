import test from 'node:test';
import assert from 'node:assert/strict';
import { createMetaCoreDojoReadAdapter, DOJO_V26_READ_TOOLS } from '../src/dojo-v26.mjs';

const connection = Object.freeze({ accessToken: 'synthetic-token-not-real-abcdefgh', phoneNumberId: '123456789012', businessAccountId: '123456789013', graphApiVersion: 'v26.0', appSecret: 'synthetic-secret-not-real' });
function setup(overrides = {}) {
  const calls = [];
  const adapter = createMetaCoreDojoReadAdapter({
    authorizeTenant: (principal, tenantId) => principal === 'operator_a' && tenantId === 'brand_a',
    resolveConnection: async id => { calls.push({ type: 'resolve', id }); return connection; },
    toolsetFactory: async config => { calls.push({ type: 'sdk', config }); return { dispatch: async (name, args) => { calls.push({ type: 'dispatch', name, args }); return { isError: false, structuredContent: { items: [] } }; } }; },
    ...overrides,
  });
  return { adapter, calls };
}

test('only three Dojo read tools are exposed; no send, lifecycle or upload', () => {
  const { adapter } = setup();
  assert.deepEqual(adapter.listTools().map(x => x.name), DOJO_V26_READ_TOOLS);
  assert.ok(adapter.listTools().every(x => x.permission === 'read'));
});

test('official v26 SDK receives exact WACRM Central tenant-scoped IDs', async () => {
  const { adapter, calls } = setup();
  const result = await adapter.invoke({ principal: 'operator_a', tenantId: 'brand_a', toolName: 'whatsapp_list_templates', args: { limit: 2 } });
  assert.equal(result.ok, true);
  assert.equal(calls.length, 3);
  assert.equal(calls[1].config.graphApiVersion, 'v26.0');
  assert.equal(calls[1].config.wabaId, connection.businessAccountId);
  assert.equal(calls[2].name, 'whatsapp_list_templates');
});

test('wrong identity or tenant cannot obtain credentials', async () => {
  const { adapter, calls } = setup();
  for (const principal of ['operator_b', null]) {
    const r = await adapter.invoke({ principal, tenantId: 'brand_a', toolName: 'whatsapp_get_template' });
    assert.equal(r.error.code, 'forbidden');
  }
  for (const tenantId of ['brand_b', '../brand_a', '']) {
    const r = await adapter.invoke({ principal: 'operator_a', tenantId, toolName: 'whatsapp_get_template' });
    assert.equal(r.error.code, 'forbidden');
  }
  assert.equal(calls.length, 0);
});

test('message sending and phone changes blocked before credentials', async () => {
  const { adapter, calls } = setup();
  for (const toolName of ['whatsapp_send_text','whatsapp_send_template','whatsapp_mark_as_read','whatsapp_upload_media_from_url','whatsapp_register_phone_number']) {
    assert.equal((await adapter.invoke({ principal:'operator_a', tenantId:'brand_a', toolName, args: { to:'555' } })).error.code, 'tool_not_allowed');
  }
  assert.equal(calls.length, 0);
});

test('v24 and missing API version reject without loading SDK', async () => {
  for (const graphApiVersion of ['v24.0', undefined]) {
    let created = 0;
    const { adapter } = setup({ resolveConnection: async () => ({ ...connection, graphApiVersion }), toolsetFactory: () => { created++; throw new Error('No SDK'); } });
    assert.equal((await adapter.invoke({ principal:'operator_a', tenantId:'brand_a', toolName:'whatsapp_list_templates' })).error.code, 'graph_version_mismatch');
    assert.equal(created, 0);
  }
});

test('incomplete WACRM Central secret prevents calls and never leaks', async () => {
  const { adapter } = setup({ resolveConnection: async () => ({ ...connection, appSecret: '' }) });
  const r = await adapter.invoke({ principal:'operator_a', tenantId:'brand_a', toolName:'whatsapp_list_templates' });
  assert.equal(r.error.code,'connection_unavailable');
  assert.ok(!JSON.stringify(r).includes(connection.accessToken));
});

test('Dojo SDK exceptions and error payloads are redacted', async () => {
  const secret = 'should-never-leak-secret';
  const { adapter } = setup({ toolsetFactory: () => ({ dispatch: async () => { throw new Error(secret); } }) });
  const r = await adapter.invoke({ principal:'operator_a',tenantId:'brand_a',toolName:'whatsapp_get_template' });
  assert.equal(r.error.code,'upstream_unavailable');
  assert.ok(!JSON.stringify(r).includes(secret));
  const { adapter: e } = setup({ toolsetFactory: () => ({ dispatch: async () => ({ isError: true, structuredContent: { error: { message: secret } } }) }) });
  const err = await e.invoke({ principal:'operator_a',tenantId:'brand_a',toolName:'whatsapp_get_template' });
  assert.equal(err.error.code,'upstream_error');
  assert.ok(!JSON.stringify(err).includes(secret));
});
