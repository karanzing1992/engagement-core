import test from 'node:test';
import assert from 'node:assert/strict';
import { createEngagementWhatsAppAdapter, READ_TOOLS, PREVIEW_TOOLS } from '../src/adapter.mjs';

const credentials = Object.freeze({ accessToken: 'synthetic-token-abcdefghijkl', phoneNumberId: '123456789012', businessAccountId: '123456789013', graphApiVersion: 'v24.0' });
function setup() {
  const calls = [];
  const adapter = createEngagementWhatsAppAdapter({
    resolveConnection: async tenant => tenant === 'brand_a' ? credentials : null,
    authorizeTenant: (principal, tenant) => principal === 'operator_a' && tenant === 'brand_a',
    sdkFactory: config => {
      calls.push({ kind: 'sdk', config });
      return { callTool: async (name, args) => {
        calls.push({ kind: 'call', name, args });
        return { ok: true, data: { synthetic: true } };
      }};
    },
  });
  return { adapter, calls };
}

test('tool inventory has only curated read and preview tools', () => {
  const { adapter } = setup();
  assert.equal(adapter.listTools().length, READ_TOOLS.length + PREVIEW_TOOLS.length);
  assert.ok(adapter.listTools().every(t => ['read', 'preview_only'].includes(t.permission)));
  assert.ok(!adapter.listTools().some(t => /register|deregister|delete|subscribe|create/.test(t.name)));
});

test('read uses tenant-specific credentials, safe SDK flags and allowed tool', async () => {
  const { adapter, calls } = setup();
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account', args: {} });
  assert.equal(result.ok, true);
  assert.equal(calls[0].config.readOnly, true);
  assert.equal(calls[0].config.enableDangerousTools, false);
  assert.equal(calls[0].config.requireConfirmation, true);
  assert.equal(calls[1].name, 'whatsapp_get_business_account');
});

test('outbound without dry run is rejected before secret access', async () => {
  const { adapter, calls } = setup();
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_send_text_message', args: { recipient_phone_number: '+15551234567', message_body: 'No real send' } });
  assert.equal(result.error.code, 'outbound_disabled');
  assert.equal(calls.length, 0);
});

test('dry-run preview cannot inherit caller confirmation', async () => {
  const { adapter, calls } = setup();
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_send_template_message', args: { recipient_phone_number: '+15551234567', template_name: 'sample', language_code: 'en_US', dryRun: true, confirm: true } });
  assert.equal(result.ok, true);
  assert.equal(calls[0].config.readOnly, false);
  assert.equal(calls[0].config.enableDangerousTools, true);
  assert.equal(calls[0].config.requireConfirmation, true);
  assert.equal(calls[1].args.dryRun, true);
  assert.equal(Object.hasOwn(calls[1].args, 'confirm'), false);
});

test('rejects phone lifecycle, template creation and all unlisted tools', async () => {
  const { adapter, calls } = setup();
  for (const toolName of ['whatsapp_register_phone_number', 'whatsapp_deregister_phone_number', 'whatsapp_create_message_template', 'whatsapp_subscribe_app', '__proto__']) {
    const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName, args: {} });
    assert.equal(result.error.code, 'tool_not_allowed');
  }
  assert.equal(calls.length, 0);
});

test('missing or wrong tenant is isolated and upstream is not reached', async () => {
  const { adapter, calls } = setup();
  for (const tenantId of ['brand_b', '../brand_a', '', undefined]) {
    const result = await adapter.invoke({ tenantId, principal: 'operator_a', toolName: 'whatsapp_get_business_account' });
    assert.ok(['connection_unavailable', 'forbidden'].includes(result.error.code));
  }
  assert.equal(calls.length, 0);
});

test('invalid input, incomplete connection, and SDK failures are safely redacted', async () => {
  const { adapter } = setup();
  assert.equal((await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account', args: [] })).error.code, 'invalid_input');
  const unavailable = createEngagementWhatsAppAdapter({ resolveConnection: async () => credentials, authorizeTenant: () => true, sdkFactory: () => ({ callTool: () => { throw new Error('private secret string'); } }) });
  const result = await unavailable.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account' });
  assert.equal(result.error.code, 'upstream_unavailable');
  assert.ok(!JSON.stringify(result).includes('private secret'));
});

test('cross-principal access is rejected before fetching tenant secret', async () => {
  const { adapter, calls } = setup();
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_b', toolName: 'whatsapp_get_business_account' });
  assert.equal(result.error.code, 'forbidden');
  assert.equal(calls.length, 0);
});

test('WACRM v26.0 does not silently downgrade to upstream WBMCP v24.0', async () => {
  let resolved = 0;
  const adapter = createEngagementWhatsAppAdapter({
    authorizeTenant: () => true,
    resolveConnection: async () => { resolved++; return { ...credentials, graphApiVersion: 'v26.0' }; },
    sdkFactory: () => { throw new Error('Must not instantiate incompatible SDK'); },
  });
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account' });
  assert.equal(result.error.code, 'graph_version_mismatch');
  assert.equal(resolved, 1);
});

test('missing Graph version is rejected rather than accepting upstream default', async () => {
  let called = false;
  const adapter = createEngagementWhatsAppAdapter({
    authorizeTenant: () => true,
    resolveConnection: async () => { const { graphApiVersion, ...rest } = credentials; return rest; },
    sdkFactory: () => { called = true; throw new Error('Unexpected call'); },
  });
  const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account' });
  assert.equal(result.error.code, 'graph_version_mismatch');
  assert.equal(called, false);
});

test('supported versions are passed through explicitly, without a default', async () => {
  for (const graphApiVersion of ['v22.0', 'v23.0', 'v24.0']) {
    let received;
    const adapter = createEngagementWhatsAppAdapter({
      authorizeTenant: () => true,
      resolveConnection: async () => ({ ...credentials, graphApiVersion }),
      sdkFactory: config => { received = config; return { callTool: async () => ({ ok: true }) }; },
    });
    const result = await adapter.invoke({ tenantId: 'brand_a', principal: 'operator_a', toolName: 'whatsapp_get_business_account' });
    assert.equal(result.ok, true);
    assert.equal(received.graphApiVersion, graphApiVersion);
  }
});
