# META CORE — Phase 1-D: Dependency, Tenant Custody and Simulated Integration Certification

**Date:** 2026-11-07 (Asia/Kolkata)  
**Repository:** `karanzing1992/engagement-core` · **draft PR:** [#215](https://github.com/karanzing1992/engagement-core/pull/215)  
**WACRM owning repository:** `karanzing1992/moksha_wordpress` · **separate draft PR:** [#134](https://github.com/karanzing1992/moksha_wordpress/pull/134)  
**State:** `SOURCE_ONLY / ZOD_AUDIT_HIGH_0 / NODE_29_OF_29 / WACRM_PHP_54_OF_54 / CONNECTED_INTEGRATION_PENDING / RELEASE_NO_GO`

## 1. Scope and reproducible evidence

This phase remains source-only on the named feature branches. **No public MCP, Meta request, sends, phone registration/migration, WACRM production change, consumer data transfer or activation of credentials occurred.** Phase 1-C's original 26/26 tests are retained. Phase 1-D extends coverage to 29/29 on the installed Dojo SDK/MCP and validates the WACRM Central token-custody design through an independent PHP CI run.

### META CORE Node and installed SDK

- Clean independent Dell clone of feature commit `722ddc8ac290a57cb7e1a9e20bb142c16a39a7f3`.
- Runtime: Node `v24.22.0`, npm `11.19.1`. Command sequence: `npm ci --ignore-scripts --no-audit --no-fund`, `npm test`, `npm audit --omit=dev --audit-level=high`.
- **29 passed / 0 failed; npm audit found 0 vulnerabilities; working tree clean.** Dell journal task ID `b448690da3bd43289fed78c8f736e50e`, completed with exit code 0.
- Lockfile SHA-256: `1e20985b6a8f04be559e0646892c88f0e65b6db295a958ec313e68ef02534f6c`.
- Actual installed `@dojocoding/whatsapp-sdk@0.10.0` and `@dojocoding/whatsapp-mcp@0.5.0` dispatch **synthetic** Graph `v26.0` template GET requests for **two distinct tenants** against fake in-process `globalThis.fetch`. Tests assert correct bearer/WABA pairs, deny cross-principal credential lookup, deny sending before transport, and revoke/inactive-route denial.
- Node HMAC fixture covers signed timestamp/body relay semantics, wrong-key, tampered, stale and oversized-body rejection; **this is a wire-format simulation**, not a live webhook POST or a PHP↔Node deployed integration.
- `src/dojo-v26.mjs` now bounds nested untrusted arguments before constructing the SDK parser or looking up credentials. Synthetic tests cover huge strings and arrays, cycles, accessors, reserved keys and deep payloads; the adapter still exposes only three allowlisted read tools.

### Zod advisory

Prior lockfile forced Dojo's declared `zod:^3.25.76`, affected by [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5). The isolated candidate uses npm `overrides.zod: "^4.6.7"`, resolving the actual tree to **Zod 4.6.7** and allowing the real SDK's tested read paths to run. An exact regenerated `package-lock.json` is committed.

**Compatibility qualification:** the major-version override is outside Dojo's declared Zod 3 dependency range. Passing the selected read-only API tests and clean audit is **not upstream semantic compatibility certification** for all Dojo tools, remote MCP, future dependency versions or customer-facing traffic. Keep the allowlist and input bounds, monitor Dojo releases/advisories and prefer an upstream-compatible audited patch before production release. `wbmcp@0.1.3` remains excluded for v26 because it only supports v22–v24; never downgrade the tenant API version.

## 2. WACRM Central custody (owning-repository change)

Separate [WACRM draft PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134) introduces an **OFF-by-default**, Central-only encrypted per-activation token store using existing `WACRM_Central_Crypto` and an isolated `wacrm_meta_credentials` table. It requires exact activated site/install/tenant/WABA/phone binding, licence status, a server-verified actor permission callback, explicit graph `v26.0`, and separate authorized rotation/revoke. It never registers a public read-token REST endpoint, alters the Consumer inbox tables or transfers customer events. Plaintext tokens are not stored in database rows or custody receipts.

Independent WACRM GitHub Actions [run #42361007583](https://github.com/karanzing1992/moksha_wordpress/actions/runs/42361007583), job `128369201559`, succeeded with:
- Central custody synthetic checks: **22/22**.
- Existing Consumer HMAC/event parser checks: **22/22**.
- Existing coexistence safety checks: **10/10**.
- PHP syntax for vault and coexistence integration: **PASS**.
- Combined **54/54 synthetic checks**. All ran against fake WP/DB and synthetic credentials, not staging customer data.

The WACRM branch documentation is `docs/WACRM_META_CORE_PHASE1D_CUSTODY_20261107.md`. Dell has no PHP CLI and cannot clone the private WACRM repo using its development identity; consequently PHP source execution was certified through the owning GitHub repository's isolated CI, not on Dell.

## 3. Remaining critical blockers — release gates

1. **Existing legacy token exposure:** WACRM Central's current `complete()` onboarding response still sends `access_token` to the authorized Consumer. Phase 1-D preserves backward compatibility and does not yet remove this exposure. A coordinated Central/Consumer onboarding migration and authenticated proxy must be reviewed, tested and accepted **before enabling the new vault**.
2. **No connected PHP↔Node broker:** Central-side `readRoute`/token resolution and META CORE `resolveConnection` remain intentionally disconnected. Require a private authenticated server-to-server exchange or centrally hosted read operation with explicit principal-to-activation mapping, fixed audience/scope, no token return to a remote MCP client, short-lived authorization, negative cross-tenant tests, observability without secrets, and revocation proof.
3. **No real staging WordPress E2E:** Isolated WP database migration, webhook callback verification, signed Central-to-Consumer relay, inbox writes, deterministic message-status/echo replay, actual event receipt/outbox and rollback still need to run with **synthetic fixtures** on an approved staging site. A JS HMAC mock plus existing PHP unit tests does not establish network integration.
4. **Security and OAuth:** independent review of Dojo Zod-major override and deeper MCP parser compatibility; scope and ingress limits; staging audit/dependency gate; OAuth registration/PKCE/audience/client isolation per `docs/MCP_OAUTH_REGISTRATION_SOP.md` **only before any future remote MCP**.
5. **Meta scope and owner release:** independently validate authorized Meta app permissions and Business App coexistence when approved; no live send, subscribe, migration, register/deregister, webhook reconfiguration or charges without separate owner release approval.

**Gate decision:** `SOURCE_CERTIFIED / PRODUCTION_NO_GO`. The synthetic test phases passed, but the requested connected end-to-end customer integration is **not certified**. Do not merge or enable either PR yet.

## 4. Reuse, licensing and cost

- Reuse: existing first-party WACRM Central coexistence, Central Crypto and Consumer HMAC/event handling; no parallel customer CRM or new webhook system.
- Open-source candidates: [DojoCodingLabs/whatsapp-adapter](https://github.com/DojoCodingLabs/whatsapp-adapter) SDK 0.10.0/MCP 0.5.0 (MIT), Zod 4.6.7 (MIT), Node.js, npm, GitHub CI. Maintain upstream licence notices. Legacy WBMCP (MIT) remains a version-incompatible comparison path.
- No paid SaaS, third-party proxy, production cloud, new customer account, Meta chargeable operation, or real tokens used. Synthetic tests have no Meta billing. Future Graph delivery charges are a distinct owner approval concern.

## 5. Rollback and Master reporting

Leave both PRs **draft/unmerged**, `WACRM_META_CORE_CUSTODY_ENABLED` absent/false, and the META CORE read adapter unmounted. No existing registrations, database contents, messages or active WACRM runtime are coupled to these source branches. If an isolated future staging pilot fails, disable the feature flag and revoke/remove **only synthetic staging credentials** after backing up and documenting the test DB; do not modify production phones or contacts.

This is **source-only**, not a verified platform integration or default-branch publication; **do not emit `VERIFIED_LIVE` Master event** or claim synchronized consumer deployment. Master default-branch publication and independent acknowledgments require their normal source/release gates. **Ashwakaal — Support Channels** remains a separate workstream with separate accounts and tenant data.
