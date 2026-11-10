/**
 * META CORE Phase 1-E: additive, opt-in response contract for the WACRM
 * tokenless template broker. No new transport, credential authority or tool.
 *
 * WACRM Central already strips Graph fields. This second, independent boundary
 * fails closed if Central accidentally returns credentials or schema additions.
 */
import { createWacrmCentralBrokerReadAdapter } from './wacrm-central-read-broker.mjs';
import { types as nodeTypes } from 'node:util';

const idPattern = /^\d{6,64}$/;
const cursorPattern = /^[A-Za-z0-9_-]{1,256}$/;
const rowFields = new Set(['id', 'name', 'language', 'status', 'category']);
const pageFields = new Set(['data', 'after']);

function isPlainObject(value) {
  return value !== null && typeof value === 'object' &&
    !nodeTypes.isProxy(value) && !Array.isArray(value) &&
    Object.getPrototypeOf(value) === Object.prototype;
}

function safeString(value, maxBytes) {
  return typeof value === 'string' && value.length > 0 &&
    Buffer.byteLength(value, 'utf8') <= maxBytes &&
    !/[\x00-\x1f\x7f]/.test(value);
}

function sanitizedTemplate(row) {
  if (!isPlainObject(row)) return null;
  const descriptors = Object.getOwnPropertyDescriptors(row);
  const keys = Reflect.ownKeys(descriptors);
  if (keys.some(key => typeof key !== 'string' ||
        !Object.hasOwn(descriptors[key], 'value'))) return null;
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
    const fields = Object.getOwnPropertyDescriptors(data);
    const keys = Reflect.ownKeys(fields);
    if (keys.some(key => typeof key !== 'string' ||
        !Object.hasOwn(fields[key], 'value'))) return null;
    const list = fields.data?.value;
    if (!Object.hasOwn(data, 'data') || keys.length > 2 ||
        keys.some(key => !pageFields.has(key)) ||
        !Array.isArray(list) || nodeTypes.isProxy(list) ||
        (Object.hasOwn(data, 'after') &&
          (typeof fields.after.value !== 'string' ||
           !cursorPattern.test(fields.after.value)))) return null;
    const items = Object.getOwnPropertyDescriptors(list);
    const size = items.length?.value;
    if (!Number.isSafeInteger(size) || size > 100 ||
        Reflect.ownKeys(items).length !== size + 1) return null;
    const rows = [];
    for (let i = 0; i < size; i++) {
      const entry = items[String(i)];
      if (!entry || !Object.hasOwn(entry, 'value')) return null;
      const row = sanitizedTemplate(entry.value);
      if (!row) return null;
      rows.push(row);
    }
    const safe = { data: Object.freeze(rows) };
    if (Object.hasOwn(fields, 'after')) safe.after = fields.after.value;
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
      // Reject outer Proxy wrappers before calling standalone broker.
      if (nodeTypes.isProxy(request)) {
        return { ok: false, error: { code: 'invalid_input', message: 'META CORE read unavailable' } };
      }
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
