/**
 * META CORE Phase 1-E: additive, opt-in response contract for the WACRM
 * tokenless template broker. No new transport, credential authority or tool.
 *
 * WACRM Central already strips Graph fields. This second, independent boundary
 * fails closed if Central accidentally returns credentials or schema additions.
 */
import { createWacrmCentralBrokerReadAdapter } from './wacrm-central-read-broker.mjs';

const idPattern = /^\d{6,64}$/;
const cursorPattern = /^[A-Za-z0-9_-]{1,256}$/;
const rowFields = new Set(['id', 'name', 'language', 'status', 'category']);
const pageFields = new Set(['data', 'after']);

function isPlainObject(value) {
  return value !== null && typeof value === 'object' &&
    !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
}

function safeString(value, maxBytes) {
  return typeof value === 'string' && value.length > 0 &&
    Buffer.byteLength(value, 'utf8') <= maxBytes &&
    !/[\x00-\x1f\x7f]/.test(value);
}

function sanitizedTemplate(row) {
  if (!isPlainObject(row)) return null;
  const keys = Object.keys(row);
  if (keys.length < 4 || keys.length > 5 || keys.some(key => !rowFields.has(key)) ||
      !idPattern.test(row.id) ||
      !safeString(row.name, 190) ||
      !safeString(row.language, 190) ||
      !safeString(row.status, 190) ||
      (Object.hasOwn(row, 'category') && !safeString(row.category, 64))) return null;
  for (const required of ['id', 'name', 'language', 'status']) {
    if (!Object.hasOwn(row, required)) return null;
  }
  const copy = { id: row.id, name: row.name, language: row.language, status: row.status };
  if (Object.hasOwn(row, 'category')) copy.category = row.category;
  return Object.freeze(copy);
}

/** Returns null on any schema deviation; copies only explicitly permitted fields. */
export function sanitizeWacrmTemplateResult(toolName, data, expectedId) {
  try {
    if (toolName === 'whatsapp_get_template') {
      const row = sanitizedTemplate(data);
      return row && row.id === expectedId ? row : null;
    }
    if (toolName !== 'whatsapp_list_templates' || !isPlainObject(data)) return null;
    const keys = Object.keys(data);
    if (!Object.hasOwn(data, 'data') || keys.length > 2 ||
        keys.some(key => !pageFields.has(key)) ||
        !Array.isArray(data.data) || data.data.length > 100 ||
        (Object.hasOwn(data, 'after') &&
          (typeof data.after !== 'string' || !cursorPattern.test(data.after)))) return null;
    const rows = [];
    for (const item of data.data) {
      const row = sanitizedTemplate(item);
      if (!row) return null;
      rows.push(row);
    }
    const safe = { data: Object.freeze(rows) };
    if (Object.hasOwn(data, 'after')) safe.after = data.after;
    return Object.freeze(safe);
  } catch (_) {
    // Includes unexpected proxy traps, accessors and malformed values.
    return null;
  }
}

/**
 * Preferred construction for any *future* META CORE deployment.
 * The existing signed broker retains its own auth, HMAC and tenant checks.
 * This wrapper never opens an alternate route or authorizes a new operation.
 */
export function createContractEnforcedWacrmBrokerAdapter(config) {
  const broker = createWacrmCentralBrokerReadAdapter(config);
  return Object.freeze({
    listTools: () => broker.listTools(),
    async invoke(request = {}) {
      const response = await broker.invoke(request);
      if (response?.ok !== true) return response;
      let expectedId;
      try {
        if (request?.toolName === 'whatsapp_get_template') {
          const descriptor = Object.getOwnPropertyDescriptor(request.args, 'templateId');
          expectedId = descriptor && Object.hasOwn(descriptor, 'value')
            ? descriptor.value : undefined;
        }
      } catch (_) { /* fail closed below */ }
      const safe = sanitizeWacrmTemplateResult(request?.toolName, response.data, expectedId);
      return safe === null
        ? { ok: false, error: { code: 'upstream_unavailable', message: 'META CORE read unavailable' } }
        : { ok: true, data: safe };
    },
  });
}
