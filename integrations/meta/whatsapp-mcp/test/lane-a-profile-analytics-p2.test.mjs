import test from 'node:test';
import assert from 'node:assert/strict';
import { createLaneAProviderMcp } from '../src/lane-a-provider-runtime.mjs';
import { WHATSAPP_LANE_A_CATALOG } from '../src/lane-a-capability-catalog.mjs';

const tenant = 'wacrm_' + 'a'.repeat(40);
const ctx = { tenantId: tenant, verifiedPrincipal: { tenantId: tenant, actorId: 'fixture-owner' } };
const profile = {
  about: 'Synthetic wellness profile',
  email: 'support@example.com',
  websites: ['https://www.example.com', 'http://example.org/visit'],
  profile_picture_url: 'https://cdn.example.com/profile.webp',
  address: 'Synthetic location', description: 'Offline test', vertical: 'OTHER'
};
const analytics = { analytics: { data_points: [{ start: 1793491200, end: 1793577600, sent: 2 }] } };
const templateAnalytics = { template_analytics: { data: [{
  template_id: '123456789012', data_points: [{ start: 1793491200, end: 1793577600, clicked: 1 }]
}] } };

function harness(responses = {}) {
  const calls = { identity: 0, policy: 0, route: 0, provider: 0, plans: [] };
  const mcp = createLaneAProviderMcp({
    verifyIdentity: async () => { calls.identity++; return true; },
    authorizeTenant: async () => true,
    readPolicy: async () => { calls.policy++; return {}; },
    resolveRoute: async () => { calls.route++; return {
      tenantId: tenant, status: 'active', activationId: 42,
      wabaId: '123456789012', phoneNumberId: '223456789012'
    }; },
    resolveOwnership: async () => ({ wabaIdVerified: true }),
    providers: { host: {
      executePlan: async ({ plan }) => {
        calls.provider++;
        calls.plans.push(plan);
        return { ok: true, data: responses[plan.toolName] ?? { id: '123456789012' } };
      }
    } },
    grants: [
      'whatsapp_get_business_profile', 'whatsapp_get_business_account',
      'whatsapp_get_business_analytics', 'whatsapp_get_template_analytics'
    ]
  });
  const call = (name, args = {}) => mcp.callTool({ name, arguments: args }, ctx);
  return { mcp, call, calls };
}

test('P2: both analytics MCP catalog schemas and tools/list require startDate and endDate', () => {
  const targets = ['whatsapp_get_business_analytics', 'whatsapp_get_template_analytics'];
  assert.equal(WHATSAPP_LANE_A_CATALOG.length, 55);
  const { mcp } = harness();
  for (const name of targets) {
    const definition = WHATSAPP_LANE_A_CATALOG.find(d => d.name === name);
    assert.deepEqual(definition.inputSchema.required, ['startDate', 'endDate']);
    const listed = mcp.listTools().find(d => d.name === name);
    assert.deepEqual(listed.inputSchema.required, ['startDate', 'endDate']);
  }
});

test('P2: missing either reporting date returns invalid_input before route/provider, not upstream_unavailable', async () => {
  for (const name of ['whatsapp_get_business_analytics', 'whatsapp_get_template_analytics']) {
    for (const args of [
      {}, { startDate: '2026-11-01' }, { endDate: '2026-11-09' },
      { startDate: '2026-11-01', endDate: null }
    ]) {
      const t = harness();
      const result = await t.call(name, args);
      assert.equal(result.isError, true, name + ' ' + JSON.stringify(args));
      assert.equal(result.structuredContent.error.code, 'invalid_input');
      assert.equal(t.calls.route, 0);
      assert.equal(t.calls.provider, 0);
    }
  }
});

test('P2: valid analytics date inputs still plan and return sanitized metric reports', async () => {
  const t = harness({
    whatsapp_get_business_analytics: analytics,
    whatsapp_get_template_analytics: templateAnalytics
  });
  for (const name of ['whatsapp_get_business_analytics', 'whatsapp_get_template_analytics']) {
    const result = await t.call(name, { startDate: '2026-11-01', endDate: '2026-11-09' });
    assert.equal(result.isError, false, JSON.stringify(result.structuredContent));
    assert.ok(Object.hasOwn(result.structuredContent.data,
      name === 'whatsapp_get_business_analytics' ? 'analytics' : 'template_analytics'));
  }
  assert.equal(t.calls.provider, 2);
  assert.equal(t.calls.route, 2);
  for (const plan of t.calls.plans) {
    const serialized = JSON.stringify(plan);
    assert.match(serialized, /1793491200/);
    assert.match(serialized, /1794182400/);
  }
});

test('P2: business profile Graph-requested email, websites and picture survive scoped sanitizer', async () => {
  const t = harness({ whatsapp_get_business_profile: { data: [profile] } });
  const result = await t.call('whatsapp_get_business_profile');
  assert.equal(result.isError, false, JSON.stringify(result.structuredContent));
  assert.deepEqual(result.structuredContent.data.data, [profile]);
  assert.equal(t.calls.provider, 1);
});

test('P2: profile response containing only the previously dropped public fields is non-empty', async () => {
  const minimal = {
    email: 'team@example.com',
    websites: ['https://example.com'],
    profile_picture_url: 'https://img.example.com/avatar.png'
  };
  const t = harness({ whatsapp_get_business_profile: { data: [minimal] } });
  const result = await t.call('whatsapp_get_business_profile');
  assert.equal(result.isError, false, JSON.stringify(result.structuredContent));
  assert.deepEqual(result.structuredContent.data.data, [minimal]);
});

test('P2: business-profile fields do not become global response allowlist keys', async () => {
  const t = harness({ whatsapp_get_business_account: {
    id: '123456789012',
    email: 'private@example.com',
    websites: ['https://private.example.com'],
    profile_picture_url: 'https://private.example.com/photo.png'
  } });
  const result = await t.call('whatsapp_get_business_account');
  assert.equal(result.isError, false);
  assert.deepEqual(result.structuredContent.data, { id: '123456789012' });
  assert.doesNotMatch(JSON.stringify(result), /private@example.com/);
});

test('P2: malformed profile URLs, email and shape fail closed without leaking', async () => {
  const bad = [
    { data: [{ email: 'not-an-email' }] },
    { data: [{ profile_picture_url: 'javascript:alert(1)' }] },
    { data: [{ websites: ['file:///etc/passwd'] }] },
    { data: [{ websites: 'https://example.com' }] },
    { data: [{}] },
    { data: [{ about: 'safe', accessToken: 'synthetic-secret-must-not-leak' }] }
  ];
  for (const payload of bad) {
    const t = harness({ whatsapp_get_business_profile: payload });
    const result = await t.call('whatsapp_get_business_profile');
    assert.equal(result.isError, true, JSON.stringify(payload));
    assert.equal(result.structuredContent.error.code, 'upstream_unavailable');
    assert.doesNotMatch(JSON.stringify(result), /synthetic-secret-must-not-leak/);
  }
});

test('P2: profile response getters and Proxy objects are denied without executing traps', async () => {
  let reads = 0, traps = 0;
  const getterRow = { about: 'safe' };
  Object.defineProperty(getterRow, 'email', {
    enumerable: true, get() { reads++; throw Error('must not execute'); }
  });
  const proxyRow = new Proxy({ email: 'support@example.com' }, {
    getPrototypeOf() { traps++; throw Error('must not execute'); },
    ownKeys() { traps++; throw Error('must not execute'); }
  });
  for (const payload of [{ data: [getterRow] }, { data: [proxyRow] }]) {
    const t = harness({ whatsapp_get_business_profile: payload });
    const result = await t.call('whatsapp_get_business_profile');
    assert.equal(result.isError, true);
    assert.equal(result.structuredContent.error.code, 'upstream_unavailable');
  }
  assert.equal(reads, 0);
  assert.equal(traps, 0);
});
