/**
 * Engagement Core ↔ WBMCP v0.1.3 (source-only, Phase 1).
 * Reuses Meta's official Cloud API via WBMCP. WACRM remains the inbound
 * webhook/relay authority and future transactional outbound authority.
 * No token, contact, message, or tenant data is stored by this module.
 */

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
const GRAPH_VERSION_PATTERN = /^v[0-9]{1,3}\.[0-9]{1,2}$/;

function rejected(code, message) {
  return { ok: false, error: { code, message } };
}

function connectionConfig(connection, previewMode = false) {
  if (!connection || typeof connection !== 'object' || Array.isArray(connection)) {
    throw new Error('Missing approved tenant connection');
  }
  const { accessToken, phoneNumberId, businessAccountId, graphApiVersion, appSecret } = connection;
  if (typeof accessToken !== 'string' || accessToken.length < 16 ||
      !ID_PATTERN.test(phoneNumberId) || !ID_PATTERN.test(businessAccountId)) {
    throw new Error('Tenant connection is incomplete');
  }
  if (graphApiVersion && !GRAPH_VERSION_PATTERN.test(graphApiVersion)) {
    throw new Error('Invalid configured Graph API version');
  }
  return {
    accessToken, phoneNumberId, businessAccountId,
    ...(graphApiVersion ? { graphApiVersion } : {}),
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
    async invoke({ tenantId, toolName, args = {}, principal } = {}) {
      if (!readSet.has(toolName) && !previewSet.has(toolName)) {
        return rejected('tool_not_allowed', 'Tool not available in Phase 1');
      }
      if (!args || typeof args !== 'object' || Array.isArray(args)) {
        return rejected('invalid_input', 'Tool arguments must be an object');
      }
      if (previewSet.has(toolName) && args.dryRun !== true) {
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
      } catch (_) {
        return rejected('connection_unavailable', 'Approved tenant connection unavailable');
      }
      // Any caller-supplied confirmation is dropped. Preview-only calls are
      // admitted to upstream dangerous-tool validation *only* with forced
      // dryRun=true. The local WBMCP SDK was inspected: readOnly=true blocks
      // previews, and its message tool checks dryRun before Meta transport.
      // No live send, account mutation, phone migration or subscriber change
      // is possible through this allowlisted adapter.
      const safeArgs = { ...args };
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
