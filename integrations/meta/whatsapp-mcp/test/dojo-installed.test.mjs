import test from 'node:test';
import assert from 'node:assert/strict';
import { WhatsAppClient, GRAPH_API_VERSION } from '@dojocoding/whatsapp-sdk';
import { createWhatsAppToolset } from '@dojocoding/whatsapp-mcp';
import { createMetaCoreDojoReadAdapter } from '../src/dojo-v26.mjs';

const credentials = Object.freeze({
  accessToken: 'synthetic-not-a-real-meta-token-1234567',
  phoneNumberId: '123456789012', businessAccountId: '123456789013',
  appSecret: 'synthetic-app-secret-not-real', graphApiVersion: 'v26.0'
});
const template = Object.freeze({
  id: '200001', name: 'test_utility', language: 'en_US',
  category: 'UTILITY', status: 'APPROVED', components: []
});

test('installed Dojo v26 SDK and MCP dispatch use mock Graph and prohibit sends', async () => {
  assert.equal(GRAPH_API_VERSION, 'v26.0');
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (input, init = {}) => {
    const url = new URL(typeof input === 'string' ? input : input.url);
    requests.push({ url, method: init.method ?? 'GET' });
    assert.equal(url.origin, 'https://graph.facebook.com');
    assert.ok(url.pathname.startsWith('/v26.0/'));
    assert.equal(init.method ?? 'GET', 'GET');
    const body = url.pathname.endsWith('/message_templates')
      ? { data: [template], paging: { cursors: { after: 'next' } } }
      : template;
    return new Response(JSON.stringify(body), { status: 200, headers: { 'content-type': 'application/json' } });
  };
  try {
    const adapter = createMetaCoreDojoReadAdapter({
      authorizeTenant: async (principal, tenantId) => principal === 'operator-a' && tenantId === 'brand_a',
      resolveConnection: async tenantId => tenantId === 'brand_a' ? credentials : null,
      toolsetFactory: async cfg => {
        const client = new WhatsAppClient(cfg);
        return createWhatsAppToolset({ client, wabaPhoneNumberId: cfg.phoneNumberId });
      }
    });
    const list = await adapter.invoke({ principal: 'operator-a', tenantId: 'brand_a', toolName: 'whatsapp_list_templates', args: { limit: 1 } });
    assert.equal(list.ok, true, JSON.stringify(list));
    assert.equal(list.data.data[0].name, 'test_utility');
    const one = await adapter.invoke({ principal: 'operator-a', tenantId: 'brand_a', toolName: 'whatsapp_get_template', args: { templateId: '200001' } });
    assert.equal(one.ok, true, JSON.stringify(one));
    assert.equal(one.data.id, '200001');
    assert.equal((await adapter.invoke({ principal: 'operator-a', tenantId: 'brand_a', toolName: 'whatsapp_send_text', args: { to: '+15551234567', body: 'NO SEND' } })).error.code, 'tool_not_allowed');
    assert.equal((await adapter.invoke({ principal: 'operator-b', tenantId: 'brand_a', toolName: 'whatsapp_list_templates', args: {} })).error.code, 'forbidden');
    assert.equal(requests.length, 2);
    assert.ok(requests.every(r => r.method === 'GET'));
  } finally { globalThis.fetch = originalFetch; }
});
