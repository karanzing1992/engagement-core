/**
 * Engagement Core ↔ WBMCP v0.1.3 (source-only, Phase 1).
 * Reuses Meta's official Cloud API via WBMCP. WACRM remains the inbound
 * webhook/relay authority and future transactional outbound authority.
 * No token, contact, message, or tenant data is stored by this module.
 */

import { types as nodeTypes } from 'node:util';

export const READ_TOOLS = Object.freeze([
  'whatsapp_health_check',
  'whatsapp_get_business_account',
  'whatsapp_get_phone_number',
  'whatsapp_list_phone_numbers',
  'whatsapp_get_business_profile',
  'whatsapp_list_message_templates',
  'whatsapp_get_message_template',
  'whatsapp_validate_phone_number',
]);
export const PREVIEW_TOOLS = Object.freeze([
  'whatsapp_send_text_message',
  'whatsapp_send_template_message',
]);

const readSet = new Set(READ_TOOLS);
const previewSet = new Set(PREVIEW_TOOLS);
const TENANT_PATTERN = /^[a-z0-9][a-z0-9_-]{1,63}$/;
const ID_PATTERN = /^[0-9]{6,64}$/;
// WBMCP v0.1.3 source: src/config/constants.ts (verified 2026-11-07).
// WACRM currently defaults to v26.0. Do not silently downgrade it to v24.0.
export const WBMCP_0_1_3_GRAPH_VERSIONS = Object.freeze(['v22.0', 'v23.0', 'v24.0']);
const compatibleGraphVersions = new Set(WBMCP_0_1_3_GRAPH_VERSIONS);

class GraphVersionMismatch extends Error {
  constructor() {
    super('The tenant Graph API version is incompatible with pinned WBMCP SDK');
    this.name = 'GraphVersionMismatch';
  }
}

function rejected(code, message) {
  return { ok: false, error: { code, message } };
}

/**
 * Legacy WBMCP adapter must reject nested proxies, accessors, cycles and
 * custom array methods before awaiting host authorization or resolving tokens.
 * No SDK receives caller-owned object references.
 */
function cloneLegacyArgs(value, depth = 0, seen = new WeakSet(), budget = { nodes: 0, bytes: 0 }) {
  if (++budget.nodes > 1024 || depth > 12) throw new Error('input_size');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const size = Buffer.byteLength(value, 'utf8');
    if (size > 32768 || (budget.bytes += size) > 65536 || value.includes('\u0000'))
      throw new Error('input_size');
    return value;
  }
  if (!value || typeof value !== 'object' || nodeTypes.isProxy(value) || seen.has(value))
    throw new Error('input_shape');
  seen.add(value);
  if (Array.isArray(value)) {
    if (Object.getPrototypeOf(value) !== Array.prototype) throw new Error('input_array');
    const ds = Object.getOwnPropertyDescriptors(value), len = ds.length?.value;
    if (!Number.isSafeInteger(len) || len > 100 || Reflect.ownKeys(ds).length !== len + 1)
      throw new Error('input_array');
    const out = [];
    for (let i = 0; i < len; i++) {
      const d = ds[String(i)];
      if (!d || !Object.hasOwn(d, 'value')) throw new Error('input_array');
      out.push(cloneLegacyArgs(d.value, depth + 1, seen, budget));
    }
    return out;
  }
  if (Object.getPrototypeOf(value) !== Object.prototype) throw new Error('input_object');
  const ds = Object.getOwnPropertyDescriptors(value), keys = Reflect.ownKeys(ds);
  if (keys.length > 64) throw new Error('input_keys');
  const out = {};
  for (const key of keys) {
    if (typeof key !== 'string' || !/^[A-Za-z0-9_]{1,128}$/.test(key) ||
        ['__proto__','constructor','prototype'].includes(key) ||
        !Object.hasOwn(ds[key], 'value')) throw new Error('input_key');
    Object.defineProperty(out, key, {
      enumerable: true, writable: true, configurable: true,
      value: cloneLegacyArgs(ds[key].value, depth + 1, seen, budget)
    });
  }
  return out;
}

function connectionConfig(connection, previewMode = false) {
  if (!connection || typeof connection !== 'object' || nodeTypes.isProxy(connection) || Array.isArray(connection)) {
    throw new Error('Missing approved tenant connection');
  }
  const { accessToken, phoneNumberId, businessAccountId, graphApiVersion, appSecret } = connection;
  if (typeof accessToken !== 'string' || accessToken.length < 16 ||
      !ID_PATTERN.test(phoneNumberId) || !ID_PATTERN.test(businessAccountId)) {
    throw new Error('Tenant connection is incomplete');
  }
  if (typeof graphApiVersion !== 'string' || !compatibleGraphVersions.has(graphApiVersion)) {
    throw new GraphVersionMismatch();
  }
  return {
    accessToken, phoneNumberId, businessAccountId,
    graphApiVersion,
    ...(appSecret ? { appSecret } : {}),
    readOnly: !previewMode,
    enableDangerousTools: previewMode,
    requireConfirmation: true,
  };
}

/**
 * The host MUST supply its authenticated principal and a trusted
 * authorizeTenant callback before credentials are resolved. That resolver must never return another tenant's token.
 * No remote OAuth/MCP endpoint is registered by this source-only module.
 */
export function createEngagementWhatsAppAdapter({ resolveConnection, authorizeTenant, sdkFactory } = {}) {
  if (typeof resolveConnection !== 'function') {
    throw new TypeError('resolveConnection(tenantId) is required');
  }
  if (typeof authorizeTenant !== 'function') {
    throw new TypeError('authorizeTenant(principal, tenantId, toolName) is required');
  }
  if (sdkFactory !== undefined && typeof sdkFactory !== 'function') {
    throw new TypeError('sdkFactory must be a function');
  }

  async function clientFor(tenantId, previewMode = false) {
    if (typeof tenantId !== 'string' || !TENANT_PATTERN.test(tenantId)) {
      throw new Error('Invalid tenant identifier');
    }
    const connection = await resolveConnection(tenantId);
    const config = connectionConfig(connection, previewMode);
    const factory = sdkFactory || (await import('wbmcp/sdk')).createWhatsAppBusinessClient;
    return factory(config);
  }

  return Object.freeze({
    listTools: () => [
      ...READ_TOOLS.map(name => ({ name, permission: 'read' })),
      ...PREVIEW_TOOLS.map(name => ({ name, permission: 'preview_only' })),
    ],
    async invoke(request = {}) {
      // Reject Proxy-backed envelopes before destructuring/property reflection.
      if (!request || typeof request !== 'object' || nodeTypes.isProxy(request) ||
          Array.isArray(request) || Object.getPrototypeOf(request) !== Object.prototype)
        return rejected('invalid_input', 'Invalid MCP request envelope');
      const requestFields = Object.getOwnPropertyDescriptors(request);
      if (['tenantId','toolName','args','principal'].some(key =>
        requestFields[key] && !Object.hasOwn(requestFields[key], 'value')))
        return rejected('invalid_input', 'Invalid MCP request envelope');
      const tenantId = requestFields.tenantId?.value;
      const toolName = requestFields.toolName?.value;
      const principal = requestFields.principal?.value;
      const args = requestFields.args?.value ?? {};
      if (nodeTypes.isProxy(principal)) return rejected('forbidden', 'Invalid principal');
      if (!readSet.has(toolName) && !previewSet.has(toolName)) {
        return rejected('tool_not_allowed', 'Tool not available in Phase 1');
      }
      if (!args || typeof args !== 'object' || nodeTypes.isProxy(args) ||
          Array.isArray(args) || Object.getPrototypeOf(args) !== Object.prototype)
        return rejected('invalid_input', 'Tool arguments must be an object');
      let safeArgs;
      try { safeArgs = cloneLegacyArgs(args); }
      catch (_) { return rejected('invalid_input', 'Tool arguments failed preflight'); }
      if (previewSet.has(toolName) && safeArgs.dryRun !== true) {
        return rejected('outbound_disabled', 'Only dry-run previews are supported');
      }
      try {
        if (await authorizeTenant(principal, tenantId, toolName) !== true) {
          return rejected('forbidden', 'No grant for this tenant and operation');
        }
      } catch (_) {
        return rejected('forbidden', 'No grant for this tenant and operation');
      }
      let client;
      try {
        client = await clientFor(tenantId, previewSet.has(toolName));
      } catch (err) {
        if (err instanceof GraphVersionMismatch) {
          return rejected('graph_version_mismatch', 'This SDK does not support the configured tenant Graph API version');
        }
        return rejected('connection_unavailable', 'Approved tenant connection unavailable');
      }
      // Any caller-supplied confirmation is dropped. Preview-only calls are
      // admitted to upstream dangerous-tool validation *only* with forced
      // dryRun=true. The local WBMCP SDK was inspected: readOnly=true blocks
      // previews, and its message tool checks dryRun before Meta transport.
      // No live send, account mutation, phone migration or subscriber change
      // is possible through this allowlisted adapter.
      // Safe immutable-by-ownership deep snapshot was captured before awaits.
      delete safeArgs.confirm;
      if (previewSet.has(toolName)) {
        safeArgs.dryRun = true;
      } else {
        delete safeArgs.dryRun;
      }
      try {
        return await client.callTool(toolName, safeArgs);
      } catch (_) {
        return rejected('upstream_unavailable', 'WhatsApp SDK operation failed');
      }
    },
  });
}
