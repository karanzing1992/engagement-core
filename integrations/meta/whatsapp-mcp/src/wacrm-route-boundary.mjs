/**
 * META CORE Phase 1-C: WACRM Central route/credential boundary.
 *
 * This does NOT expose or create a WACRM REST endpoint, persist Meta tokens,
 * or obtain credentials from the customer WordPress Consumer. The existing
 * Central code stores WABA/phone route metadata and app secret but does not
 * yet implement a durable, tenant-scoped access-token resolver. That provider
 * remains a separate WACRM owner-reviewed implementation gate.
 */
import { types as nodeTypes } from 'node:util';
const ID = /^[0-9]{6,64}$/;
const TENANT = /^[a-z0-9][a-z0-9_-]{1,63}$/;

export class WacrmConnectionUnavailable extends Error {
  constructor() {
    super('A verified WACRM Central connection is unavailable');
    this.name = 'WacrmConnectionUnavailable';
  }
}

/**
 * Both providers MUST be server-only, bound to WACRM Central's authenticated
 * owner/site context. `readRoute` maps existing `wacrm_meta_routes` rows to:
 * { tenantId, activationId, wabaId, phoneNumberId, status }.
 * `resolveCredential` is NOT in existing WACRM Central; it must be added
 * through a separate reviewed secure-token authority, never a public API.
 */
export function createWacrmCentralConnectionResolver({ readRoute, resolveCredential } = {}) {
  if (typeof readRoute !== 'function' || typeof resolveCredential !== 'function') {
    throw new TypeError('Trusted Central route and credential providers are required');
  }
  return async function resolveConnection(tenantId) {
    if (typeof tenantId !== 'string' || !TENANT.test(tenantId)) {
      throw new WacrmConnectionUnavailable();
    }
    let route;
    try {
      const raw = await readRoute(tenantId);
      if (!raw || typeof raw !== 'object' || nodeTypes.isProxy(raw) ||
          Array.isArray(raw) || Object.getPrototypeOf(raw) !== Object.prototype)
        throw new WacrmConnectionUnavailable();
      const ds = Object.getOwnPropertyDescriptors(raw), snapshot = {};
      for (const key of ['tenantId','status','activationId','wabaId','phoneNumberId']) {
        if (!ds[key] || !Object.hasOwn(ds[key], 'value'))
          throw new WacrmConnectionUnavailable();
        snapshot[key] = ds[key].value;
      }
      route = Object.freeze(snapshot);
    } catch (_) { throw new WacrmConnectionUnavailable(); }
    if (route.tenantId !== tenantId || route.status !== 'active' ||
        !Number.isSafeInteger(route.activationId) || route.activationId < 1 ||
        typeof route.wabaId !== 'string' || !ID.test(route.wabaId) ||
        typeof route.phoneNumberId !== 'string' || !ID.test(route.phoneNumberId)) {
      throw new WacrmConnectionUnavailable();
    }
    let credential;
    try {
      credential = await resolveCredential({
        tenantId, activationId: route.activationId,
        wabaId: route.wabaId, phoneNumberId: route.phoneNumberId,
      });
    } catch (_) { throw new WacrmConnectionUnavailable(); }
    // Never accept caller-supplied WABA, phone, tenant or API version. All
    // credential bindings must match the authoritative Central route.
    if (!credential || credential.tenantId !== tenantId ||
        credential.activationId !== route.activationId ||
        credential.wabaId !== route.wabaId ||
        credential.phoneNumberId !== route.phoneNumberId ||
        credential.graphApiVersion !== 'v26.0' ||
        typeof credential.accessToken !== 'string' || credential.accessToken.length < 16 ||
        typeof credential.appSecret !== 'string' || credential.appSecret.length < 8) {
      throw new WacrmConnectionUnavailable();
    }
    return Object.freeze({
      accessToken: credential.accessToken,
      appSecret: credential.appSecret,
      businessAccountId: route.wabaId,
      phoneNumberId: route.phoneNumberId,
      graphApiVersion: 'v26.0',
    });
  };
}
