/**
 * META CORE Phase 1-B: a read-only, WACRM Central-hosted adapter for
 * @dojocoding/whatsapp-sdk 0.10.0 + @dojocoding/whatsapp-mcp 0.5.0.
 * This is an isolated v26 candidate, not wired to a live account.
 *
 * No outbound MCP tools, phone lifecycle mutations or webhook changes.
 * Do not use this module from the WordPress Consumer or a browser.
 */
import { types as nodeTypes } from 'node:util';

export const DOJO_V26_READ_TOOLS = Object.freeze([
  'whatsapp_list_templates',
  'whatsapp_get_template',
  'whatsapp_get_media_info',
]);

const allowed = new Set(DOJO_V26_READ_TOOLS);
const tenantPattern = /^[a-z0-9][a-z0-9_-]{1,63}$/;
const numberIdPattern = /^\d{6,64}$/;

function denied(code, message) { return { ok: false, error: { code, message } }; }

// Snapshot nested arguments through own data descriptors BEFORE host callbacks.
// This avoids running an inherited Array#toJSON/getter (or a mutable getter)
// during JSON.stringify(args). The old scanner checked descriptors but later
// serialized the original caller-owned graph, allowing inherited hooks to run.
function boundedArgs(root) {
  const seen = new WeakSet();
  let visited = 0, bytes = 0;
  function clone(value, depth) {
    if (++visited > 256 || depth > 8) throw new Error('input_size');
    if (value === null || typeof value === 'boolean') return value;
    if (typeof value === 'string') {
      const n = Buffer.byteLength(value, 'utf8');
      if (value.length > 8192 || n > 8192 || (bytes += n) > 65536)
        throw new Error('input_size');
      return value;
    }
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value !== 'object' || nodeTypes.isProxy(value) || seen.has(value))
      throw new Error('input_shape');
    seen.add(value);
    if (Array.isArray(value)) {
      // Do not allow custom Array prototypes with inherited toJSON hooks.
      if (Object.getPrototypeOf(value) !== Array.prototype)
        throw new Error('input_array_prototype');
      const ds = Object.getOwnPropertyDescriptors(value);
      const size = ds.length?.value;
      if (!Number.isSafeInteger(size) || size > 128 ||
          Reflect.ownKeys(ds).length !== size + 1)
        throw new Error('input_array');
      const out = [];
      for (let i = 0; i < size; i++) {
        const d = ds[String(i)];
        if (!d || !Object.hasOwn(d, 'value') || d.enumerable !== true)
          throw new Error('input_array_accessor');
        out.push(clone(d.value, depth + 1));
      }
      return out;
    }
    const proto = Object.getPrototypeOf(value);
    if (proto !== Object.prototype && proto !== null)
      throw new Error('input_prototype');
    const ds = Object.getOwnPropertyDescriptors(value);
    const keys = Reflect.ownKeys(ds);
    if (keys.length > 32) throw new Error('input_keys');
    const out = {};
    for (const key of keys) {
      if (typeof key !== 'string' || key.length > 64 ||
          key === '__proto__' || key === 'constructor' || key === 'prototype' ||
          !Object.hasOwn(ds[key], 'value'))
        throw new Error('input_key');
      Object.defineProperty(out, key, {
        enumerable: true, writable: true, configurable: true,
        value: clone(ds[key].value, depth + 1)
      });
    }
    return out;
  }
  try {
    if (!root || typeof root !== 'object' || nodeTypes.isProxy(root) ||
        Array.isArray(root)) return null;
    return clone(root, 0);
  } catch (_) { return null; }
}

function configFor(connection) {
  if (!connection || typeof connection !== 'object' || nodeTypes.isProxy(connection) || Array.isArray(connection)) {
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
    async invoke(request = {}) {
      if (!request || typeof request !== 'object' || nodeTypes.isProxy(request) ||
          Array.isArray(request) || Object.getPrototypeOf(request) !== Object.prototype)
        return denied('invalid_input', 'Invalid request envelope');
      const fields = Object.getOwnPropertyDescriptors(request);
      if (['principal','tenantId','toolName','args'].some(key =>
          fields[key] && !Object.hasOwn(fields[key], 'value')))
        return denied('invalid_input', 'Invalid request envelope');
      const principal = fields.principal?.value;
      const tenantId = fields.tenantId?.value;
      const toolName = fields.toolName?.value;
      const args = fields.args?.value ?? {};
      if (nodeTypes.isProxy(principal))
        return denied('forbidden', 'Tenant authorization failed');
      if (!allowed.has(toolName)) return denied('tool_not_allowed', 'This META CORE tool is not enabled');
      if (typeof tenantId !== 'string' || !tenantPattern.test(tenantId)) return denied('forbidden', 'Tenant authorization failed');
      // A validated descriptor-only deep copy; never serialize caller-owned
      // objects or invoke their inherited toJSON hooks.
      const safeArgs = boundedArgs(args);
      if (safeArgs === null)
        return denied('invalid_input', 'Tool arguments exceed safe bounds');
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
        const result = await toolset.dispatch(toolName, safeArgs);
        if (!result || result.isError) return denied('upstream_error', 'WhatsApp read operation failed');
        return { ok: true, data: result.structuredContent ?? {} };
      } catch (_) { return denied('upstream_unavailable', 'WhatsApp SDK operation failed'); }
    },
  });
}
