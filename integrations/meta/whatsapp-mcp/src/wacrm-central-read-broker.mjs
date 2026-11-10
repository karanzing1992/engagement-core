/**
 * META CORE → WACRM Central: server-only signed read broker.
 * This is NOT an OAuth resource, browser SDK, Graph token resolver or
 * production connection. The WACRM Central PHP side performs Graph GET with
 * an encrypted token held exclusively in Central.
 */
import { createHash, createHmac, randomBytes } from 'node:crypto';

export const CENTRAL_BROKER_READ_TOOLS = Object.freeze([
  'whatsapp_list_templates',
  'whatsapp_get_template',
]);

const allowed = new Set(CENTRAL_BROKER_READ_TOOLS);
const tenantPattern = /^wacrm_[a-f0-9]{40}$/;
const idPattern = /^\d{6,64}$/;
const cursorPattern = /^[A-Za-z0-9_-]{1,256}$/;
const expectedPath = '/wp-json/wacrm-central/v1/meta-core/read';

function reject(code) {
  return { ok: false, error: { code, message: 'META CORE read unavailable' } };
}
function cleanArgs(name, args) {
  try {
    if (!args || typeof args !== 'object' || Array.isArray(args) ||
        Object.getPrototypeOf(args) !== Object.prototype) return null;
    const d = Object.getOwnPropertyDescriptors(args);
    const keys = Object.keys(d);
    if (name === 'whatsapp_list_templates') {
      if (keys.length > 2 || keys.some(key => !['limit', 'after'].includes(key))) return null;
      if (keys.some(key => !Object.hasOwn(d[key], 'value'))) return null;
      const clean = {};
      if (Object.hasOwn(d, 'limit')) {
        if (!Number.isInteger(d.limit.value) || d.limit.value < 1 || d.limit.value > 100) return null;
        clean.limit = d.limit.value;
      }
      if (Object.hasOwn(d, 'after')) {
        if (typeof d.after.value !== 'string' || !cursorPattern.test(d.after.value)) return null;
        clean.after = d.after.value;
      }
      return clean;
    }
    if (name === 'whatsapp_get_template' && keys.length === 1 &&
        keys[0] === 'templateId' && Object.hasOwn(d.templateId, 'value') &&
        typeof d.templateId.value === 'string' && idPattern.test(d.templateId.value)) {
      return { templateId: d.templateId.value };
    }
  } catch (_) { /* Proxy traps or malformed descriptors fail closed. */ }
  return null;
}

async function boundedResponseText(response, maxBytes = 131072) {
  if (Number(response.headers.get('content-length')) > maxBytes) throw new Error('Oversize');
  if (!response.body?.getReader) throw new Error('Unsupported response');
  const reader = response.body.getReader();
  const chunks = [];
  let bytes = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maxBytes) throw new Error('Oversize');
      chunks.push(Buffer.from(value));
    }
  } catch (e) {
    await reader.cancel().catch(() => {});
    throw e;
  } finally {
    reader.releaseLock();
  }
  return Buffer.concat(chunks, bytes).toString('utf8');
}

export function createWacrmCentralBrokerReadAdapter({
  authorizeTenant, readRoute, endpoint, sharedSecret, fetchImpl = globalThis.fetch,
  now = () => Math.floor(Date.now() / 1000), nonceFactory = () => randomBytes(16).toString('hex'),
} = {}) {
  if (typeof authorizeTenant !== 'function' || typeof readRoute !== 'function') {
    throw new TypeError('Trusted tenant authorization and Central route resolver required');
  }
  if (typeof endpoint !== 'string' || typeof sharedSecret !== 'string' ||
      sharedSecret.length < 32 || sharedSecret.length > 4096 || typeof fetchImpl !== 'function') {
    throw new TypeError('Central HTTPS broker configuration required');
  }
  let url;
  try { url = new URL(endpoint); } catch (_) { throw new TypeError('Invalid broker endpoint'); }
  if (url.protocol !== 'https:' || !url.hostname || url.pathname !== expectedPath ||
      url.username || url.password || url.hash || url.search) {
    throw new TypeError('Broker endpoint must be the pinned HTTPS REST resource');
  }
  return Object.freeze({
    listTools: () => CENTRAL_BROKER_READ_TOOLS.map(name => ({ name, permission: 'read' })),
    async invoke({ principal, tenantId, toolName, args = {} } = {}) {
      if (!allowed.has(toolName)) return reject('tool_not_allowed');
      const safeArgs = cleanArgs(toolName, args);
      if (typeof tenantId !== 'string' || !tenantPattern.test(tenantId) ||
          safeArgs === null) return reject('invalid_input');
      try {
        if (await authorizeTenant(principal, tenantId, toolName) !== true) return reject('forbidden');
      } catch (_) { return reject('forbidden'); }
      let route;
      try { route = await readRoute(tenantId); }
      catch (_) { return reject('connection_unavailable'); }
      if (!route || route.tenantId !== tenantId || route.status !== 'active' ||
          !Number.isSafeInteger(route.activationId) || route.activationId < 1 ||
          !idPattern.test(route.wabaId) || !idPattern.test(route.phoneNumberId)) {
        return reject('connection_unavailable');
      }

      // Only the server constructs the signed request. No browser-supplied
      // access token, WABA, phone, URL, audience, client or signing key.
      const raw = JSON.stringify({
        tenantId, activationId: route.activationId, toolName, args: safeArgs
      });
      if (Buffer.byteLength(raw) > 16384) return reject('invalid_input');
      const timestamp = String(now());
      const nonce = nonceFactory();
      if (!/^\d{10}$/.test(timestamp) || !/^[a-f0-9]{32}$/.test(nonce)) return reject('broker_unavailable');
      const client = 'meta-core-read-v1';
      const audience = 'wacrm-central';
      const material = [
        'wacrm-meta-read-v1', client, audience, timestamp, nonce,
        createHash('sha256').update(raw).digest('hex'),
      ].join('\n');
      const signature = 'sha256=' + createHmac('sha256', sharedSecret).update(material).digest('hex');
      let response;
      try {
        response = await fetchImpl(url.href, {
          method: 'POST', redirect: 'error', cache: 'no-store',
          signal: AbortSignal.timeout(10000),
          headers: {
            'Content-Type': 'application/json',
            'X-Meta-Core-Client': client,
            'X-Meta-Core-Audience': audience,
            'X-Meta-Core-Timestamp': timestamp,
            'X-Meta-Core-Nonce': nonce,
            'X-Meta-Core-Signature': signature,
          },
          body: raw,
        });
        if (response.status !== 200 ||
            !/^application\/json(?:;|$)/i.test(response.headers.get('content-type') ?? '')) {
          return reject('upstream_unavailable');
        }
        const data = JSON.parse(await boundedResponseText(response));
        if (!data || data.ok !== true || data.tenantId !== tenantId ||
            data.toolName !== toolName || data.graphApiVersion !== 'v26.0' ||
            !data.data || typeof data.data !== 'object') {
          return reject('upstream_unavailable');
        }
        // Raw Graph bearer tokens are never returned by the Central broker.
        // Deny suspicious response fields as defense against accidental regressions.
        if (Object.hasOwn(data, 'accessToken') || Object.hasOwn(data, 'access_token')) {
          return reject('upstream_unavailable');
        }
        return { ok: true, data: data.data };
      } catch (_) {
        return reject('upstream_unavailable');
      }
    },
  });
}
