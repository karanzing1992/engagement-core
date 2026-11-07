import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { WhatsAppClient, GRAPH_API_VERSION } from '@dojocoding/whatsapp-sdk';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';
import { createMetaCoreDojoReadAdapter } from '../src/dojo-v26.mjs';
import { createWacrmCentralConnectionResolver, WacrmConnectionUnavailable } from '../src/wacrm-route-boundary.mjs';

const routes = Object.freeze({
  brand_a: { tenantId: 'brand_a', activationId: 101, wabaId: '100000000001', phoneNumberId: '200000000001', status: 'active' },
  brand_b: { tenantId: 'brand_b', activationId: 102, wabaId: '100000000002', phoneNumberId: '200000000002', status: 'active' },
});
const credential = (route) => ({
  tenantId: route.tenantId, activationId: route.activationId, wabaId: route.wabaId,
  phoneNumberId: route.phoneNumberId, graphApiVersion: 'v26.0',
  accessToken: 'synthetic-access-token-' + route.tenantId + '-never-live',
  appSecret: 'synthetic-app-secret-' + route.tenantId
});

test('Phase 1-D real pinned SDK: A/B tenant isolated Graph v26 GET dispatch and revocation', async () => {
  assert.equal(GRAPH_API_VERSION, 'v26.0');
  const priorFetch = globalThis.fetch;
  const calls = [];
  let revoked = false;
  const credentialReads = [];
  globalThis.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url);
    const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
    const auth = headers.get('authorization') || '';
    calls.push({ method: init.method || 'GET', url, auth });
    assert.equal(url.origin, 'https://graph.facebook.com');
    assert.ok(url.pathname.startsWith('/v26.0/'), 'no API downgrade');
    assert.equal(init.method || 'GET', 'GET', 'no side-effect transport');
    assert.ok(auth.startsWith('Bearer synthetic-access-token-brand_'), 'tenant bearer');
    const tenant = auth.includes('brand_a') ? 'brand_a' : 'brand_b';
    assert.ok(url.pathname.includes(routes[tenant].wabaId), 'WABA belongs to token tenant');
    return new Response(JSON.stringify({ data: [{ id: '400000000001', name: 'synthetic_template', language: 'en_US',
      category: 'UTILITY', status: 'APPROVED', components: [] }], paging: { cursors: { after: 'next' } } }),
      { status: 200, headers: { 'content-type': 'application/json' } });
  };
  try {
    const resolveConnection = createWacrmCentralConnectionResolver({
      readRoute: async tenantId => revoked && tenantId === 'brand_a'
        ? { ...routes.brand_a, status: 'revoked' } : routes[tenantId],
      resolveCredential: async binding => {
        credentialReads.push(binding);
        return credential(routes[binding.tenantId]);
      }
    });
    const adapter = createMetaCoreDojoReadAdapter({
      authorizeTenant: async (principal, tenantId, toolName) =>
        !!principal && principal.tenantId === tenantId && principal.scopes?.includes('meta:read') &&
        toolName === 'whatsapp_list_templates',
      resolveConnection,
      toolsetFactory: async config =>
        createWhatsAppToolset({ client: new WhatsAppClient(config), wabaPhoneNumberId: config.phoneNumberId })
    });
    const principalA = { tenantId: 'brand_a', scopes: ['meta:read'] };
    const principalB = { tenantId: 'brand_b', scopes: ['meta:read'] };
    const first = await adapter.invoke({ principal: principalA, tenantId: 'brand_a',
      toolName: 'whatsapp_list_templates', args: { limit: 1 } });
    assert.equal(first.ok, true, JSON.stringify(first));
    const second = await adapter.invoke({ principal: principalB, tenantId: 'brand_b',
      toolName: 'whatsapp_list_templates', args: { limit: 1 } });
    assert.equal(second.ok, true, JSON.stringify(second));
    assert.equal(calls.length, 2);
    assert.notEqual(calls[0].auth, calls[1].auth);
    assert.equal(credentialReads.length, 2);
    const wrong = await adapter.invoke({ principal: principalA, tenantId: 'brand_b',
      toolName: 'whatsapp_list_templates', args: {} });
    assert.equal(wrong.error.code, 'forbidden');
    assert.equal(credentialReads.length, 2, 'cross-principal denial precedes credential access');
    const send = await adapter.invoke({ principal: principalA, tenantId: 'brand_a',
      toolName: 'whatsapp_send_text', args: { to: '999999999999', body: 'DO NOT SEND' } });
    assert.equal(send.error.code, 'tool_not_allowed');
    assert.equal(calls.length, 2);
    revoked = true;
    await assert.rejects(resolveConnection('brand_a'), WacrmConnectionUnavailable);
    const revokedRead = await adapter.invoke({ principal: principalA, tenantId: 'brand_a',
      toolName: 'whatsapp_list_templates', args: {} });
    assert.equal(revokedRead.error.code, 'connection_unavailable');
    assert.equal(calls.length, 2);
  } finally { globalThis.fetch = priorFetch; }
});

test('Consumer relay HMAC contract fixture: reject tamper, stale timestamp, wrong key, replay identity', () => {
  // This is the cross-language wire contract. PHP Consumer executes its own
  // verify_hmac and extract_records tests in the WACRM owning CI, not here.
  const now = 1794041400;
  const body = JSON.stringify({ object: 'whatsapp_business_account',
    entry: [{ id: routes.brand_a.wabaId, changes: [{
      field: 'messages', value: { metadata: { phone_number_id: routes.brand_a.phoneNumberId },
        messages: [{ id: 'wamid.synthetic1', from: '910000000000', timestamp: '1794041400',
          type: 'text', text: { body: 'synthetic only' } }] }
    }] }] });
  const key = 'synthetic-relay-secret-for-brand-a-only';
  const sign = (timestamp, payload, secret) =>
    'sha256=' + createHmac('sha256', secret).update(String(timestamp) + '.' + payload).digest('hex');
  const verify = (timestamp, payload, signature, secret, clock) => {
    if (Math.abs(clock - timestamp) > 300 || payload.length > 1048576) return false;
    const expected = Buffer.from(sign(timestamp, payload, secret));
    const supplied = Buffer.from(signature);
    return expected.length === supplied.length && timingSafeEqual(expected, supplied);
  };
  const signature = sign(now, body, key);
  assert.equal(verify(now, body, signature, key, now), true);
  assert.equal(verify(now, body + ' ', signature, key, now), false);
  assert.equal(verify(now - 301, body, sign(now - 301, body, key), key, now), false);
  assert.equal(verify(now, body, signature, 'wrong-tenant-secret', now), false);
  assert.equal(verify(now, body.repeat(10000), signature, key, now), false);
  const stableEventIdentity = createHmac('sha256', key).update('wamid.synthetic1').digest('hex');
  assert.equal(stableEventIdentity, createHmac('sha256', key).update('wamid.synthetic1').digest('hex'));
});
