/**
 * META CORE Phase 1-B: a read-only, WACRM Central-hosted adapter for
 * @dojocoding/whatsapp-sdk 0.10.0 + @dojocoding/whatsapp-mcp 0.5.0.
 * This is an isolated v26 candidate, not wired to a live account.
 *
 * No outbound MCP tools, phone lifecycle mutations or webhook changes.
 * Do not use this module from the WordPress Consumer or a browser.
 */
export const DOJO_V26_READ_TOOLS = Object.freeze([
  'whatsapp_list_templates',
  'whatsapp_get_template',
  'whatsapp_get_media_info',
]);

const allowed = new Set(DOJO_V26_READ_TOOLS);
const tenantPattern = /^[a-z0-9][a-z0-9_-]{1,63}$/;
const numberIdPattern = /^\d{6,64}$/;

function denied(code, message) { return { ok: false, error: { code, message } }; }

// Bounded structural ingress before auth and SDK/Zod parsing; no JSON stringify
// of untrusted, potentially huge or cyclic structures.
function boundedArgs(root) {
  const stack = [{ value: root, depth: 0 }];
  const seen = new WeakSet();
  let visited = 0;
  try {
    while (stack.length > 0) {
      const { value, depth } = stack.pop();
      if (++visited > 256 || depth > 8) return false;
      if (value === null || typeof value === 'boolean') continue;
      if (typeof value === 'string') {
        if (value.length > 8192) return false;
        continue;
      }
      if (typeof value === 'number') {
        if (!Number.isFinite(value)) return false;
        continue;
      }
      if (typeof value !== 'object' || seen.has(value)) return false;
      seen.add(value);
      if (Array.isArray(value)) {
        if (value.length > 128) return false;
        for (const item of value) stack.push({ value: item, depth: depth + 1 });
        continue;
      }
      const proto = Object.getPrototypeOf(value);
      if (proto !== Object.prototype && proto !== null) return false;
      const keys = Object.keys(value);
      if (keys.length > 32) return false;
      for (const key of keys) {
        if (key.length > 64 || key === '__proto__' || key === 'constructor' || key === 'prototype') return false;
        const d = Object.getOwnPropertyDescriptor(value, key);
        if (!d || !Object.hasOwn(d, 'value')) return false;
        stack.push({ value: d.value, depth: depth + 1 });
      }
    }
  } catch (_) { return false; }
  return true;
}

function configFor(connection) {
  if (!connection || typeof connection !== 'object' || Array.isArray(connection)) {
    throw new Error('No configured tenant connection');
  }
  if (connection.graphApiVersion !== 'v26.0') {
    const e = new Error('Graph version mismatch');
    e.name = 'GraphVersionMismatch';
    throw e;
  }
  for (const name of ['phoneNumberId', 'businessAccountId']) {
    if (typeof connection[name] !== 'string' || !numberIdPattern.test(connection[name])) {
      throw new Error('Missing tenant connection');
    }
  }
  if (typeof connection.accessToken !== 'string' || connection.accessToken.length < 16 ||
      typeof connection.appSecret !== 'string' || connection.appSecret.length < 8) {
    throw new Error('Missing tenant connection');
  }
  return {
    phoneNumberId: connection.phoneNumberId,
    wabaId: connection.businessAccountId,
    token: connection.accessToken,
    appSecret: connection.appSecret,
    graphApiVersion: connection.graphApiVersion,
  };
}

// No host/global token is loaded. The caller owns authenticated tenant grants,
// secret retrieval and HTTP resource authorisation. This is NOT an OAuth MCP.
export function createMetaCoreDojoReadAdapter({ authorizeTenant, resolveConnection, toolsetFactory } = {}) {
  if (typeof authorizeTenant !== 'function' || typeof resolveConnection !== 'function') {
    throw new TypeError('Trusted tenant authorization and credential resolver are required');
  }
  if (toolsetFactory !== undefined && typeof toolsetFactory !== 'function') {
    throw new TypeError('toolsetFactory must be a function');
  }
  return Object.freeze({
    listTools: () => DOJO_V26_READ_TOOLS.map(name => ({ name, permission: 'read' })),
    async invoke({ principal, tenantId, toolName, args = {} } = {}) {
      if (!allowed.has(toolName)) return denied('tool_not_allowed', 'This META CORE tool is not enabled');
      if (typeof tenantId !== 'string' || !tenantPattern.test(tenantId)) return denied('forbidden', 'Tenant authorization failed');
      if (!args || typeof args !== 'object' || Array.isArray(args) || !boundedArgs(args)) return denied('invalid_input', 'Tool arguments exceed safe bounds');
      try {
        if (await authorizeTenant(principal, tenantId, toolName) !== true) {
          return denied('forbidden', 'Tenant authorization failed');
        }
      } catch (_) { return denied('forbidden', 'Tenant authorization failed'); }
      let config;
      try { config = configFor(await resolveConnection(tenantId)); }
      catch (error) {
        return error?.name === 'GraphVersionMismatch'
          ? denied('graph_version_mismatch', 'Tenant Graph version is incompatible with this SDK')
          : denied('connection_unavailable', 'Approved tenant connection unavailable');
      }
      try {
        const build = toolsetFactory || (async cfg => {
          const [{ WhatsAppClient }, { createWhatsAppToolset }] = await Promise.all([
            import('@dojocoding/whatsapp-sdk'), import('@dojocoding/whatsapp-mcp'),
          ]);
          const client = new WhatsAppClient(cfg);
          return createWhatsAppToolset({ client, wabaPhoneNumberId: cfg.phoneNumberId });
        });
        const toolset = await build(config);
        if (!toolset || typeof toolset.dispatch !== 'function') return denied('upstream_unavailable', 'MCP SDK toolset unavailable');
        const result = await toolset.dispatch(toolName, { ...args });
        if (!result || result.isError) return denied('upstream_error', 'WhatsApp read operation failed');
        return { ok: true, data: result.structuredContent ?? {} };
      } catch (_) { return denied('upstream_unavailable', 'WhatsApp SDK operation failed'); }
    },
  });
}
