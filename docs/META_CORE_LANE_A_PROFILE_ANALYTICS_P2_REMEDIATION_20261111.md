# META CORE Lane A — P2 Business Profile and Analytics Schema Remediation

Date: **2026-11-11** (Asia/Kolkata)  
Repository: `karanzing1992/engagement-core`  
Source-only remediation branch: `fix/meta-core-lane-a-profile-analytics-p2-20261111`  
Frozen base (audited PR #273): `c0b327443e9aa67e4e83c8915fedc713d98319a6`  
Security issue: [#274](https://github.com/karanzing1992/engagement-core/issues/274)  
Original full-diff approval: [#273](https://github.com/karanzing1992/engagement-core/pull/273), Aaron approval on **original commit only**. New SHA **requires new independent review**.

## Review disposition

### P2-A — business-profile fields silently dropped

**Code:** `integrations/meta/whatsapp-mcp/src/lane-a-provider-runtime.mjs` (sanitizer).  
**Planner contract:** `buildWacrmGraphV26Plan('whatsapp_get_business_profile')` requests `about,address,description,email,profile_picture_url,websites,vertical` from the official Graph v26 business-profile endpoint.

**Fix:** Add a narrowly scoped `profileCopyKeys` for `email`, `websites` and `profile_picture_url`; activate **only** for `whatsapp_get_business_profile` and a direct profile or a record inside the Graph response `data[]` array, using typed structural paths. Do **not** extend the generic `copyKeys` allowlist. Validate email shape and byte length, URL scheme/hostname and embedded credentials, websites' array type and count. Reject empty `data[]` profile rows after sanitization instead of passing `{data:[{}]}`. All prior fail-closed Proxy, getter, credential-field and shared-reference controls remain intact.

**Regression cases:** complete Graph profile response; response containing only previously lost public fields; unrelated business-account response must strip `email/websites/profile_picture_url`; malformed profile values, secret keys, accessors and Proxy nodes fail closed without user-owned traps executing.

### P2-B — analytics dates advertised optional but required by Graph planner

**Code:** `integrations/meta/whatsapp-mcp/src/lane-a-capability-catalog.mjs`.  
**Planner contract:** Both `whatsapp_get_template_analytics` and `whatsapp_get_business_analytics` call `toUnix(args.startDate)` and `toUnix(args.endDate)`.

**Fix:** Set `required=['startDate','endDate']` in both catalog rows, reflected in MCP `tools/list`. The existing strict ingress parser now returns **`invalid_input` before route/provider execution** for missing/invalid date types, rather than allowing schema-valid requests to fail later with `upstream_unavailable`. Actual ISO calendar validation remains the Graph planner's existing responsibility; no new implicit defaults or date ranges were invented.

**Regression cases:** both schemas advertise required dates, `{}`, one-date and null-date calls fail `invalid_input` before route/provider; two valid ISO dates produce the correct Graph v26 plan and sanitized analytics response.

## Source-only verification

- Prior baseline at audited PR #273: 128/128 full Node, 36/36 focused security, CodeQL 0 findings.
- New focused regression file: `integrations/meta/whatsapp-mcp/test/lane-a-profile-analytics-p2.test.mjs` (8 Node cases).
- New branch's isolated workflow uses the pinned Node/CodeQL Actions, `npm ci --ignore-scripts`, synthetic providers only, and workspace-local SARIF evidence.
- **Verification must be repeated at the final new exact SHA** after this documentation commit; do not substitute previous CI. Require >=136/136 full Node, >=44/44 focused tests, zero reported high/critical npm audit vulnerabilities, zero SARIF security findings, and green additional PR checks.
- Preserve initial 55-tool capability scope, zero default grants, `writeEnabled=false`, `liveProviderBound=false`, `productionEnabled=false` and tenant/credential isolation.

## No-release / subsequent authority gates

- This branch is an isolated **source-only** candidate; old audit PR #273 remains frozen, and `main` / draft integration PR #270 remain untouched by this remediation. Other unrelated main changes may occur concurrently.
- Require fresh independent GitHub `APPROVED` or `REQUEST_CHANGES` on the new exact integrated candidate SHA, explicit P2 dispositions and owner source-consolidation/merge authorization. Do **not** mark old #273 threads resolved solely due to these changes.
- Keep **Lane B** blocked pending certified WACRM host trusted-root Promise/thenable handling; DNS resolution, private IPv4/IPv6 blocking, redirect/TLS and outbound egress SSRF controls; verified OAuth resource grants; encrypted tenant credential custody; durable idempotency/outbox, customer consent and sandbox integration.
- No production deployment, real Meta Graph calls, WhatsApp sends, tenant grants, customer data, credential transfers or billing. Ashwakaal — Support Channels remains separate.
- Source-only audit progress is `DOC_VERIFIED / NOT_VERIFIED_LIVE`; do not post a live platform-integration event to Supabase Master.

## Open/free-first

Reuses existing Node, pinned Dojo/Zod, GitHub Actions and CodeQL; **no new third-party runtime dependency or paid service**.
