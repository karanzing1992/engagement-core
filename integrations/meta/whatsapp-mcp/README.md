# META CORE — WhatsApp MCP Adapter (Phase 1, SOURCE ONLY)

**Internal product/workstream name:** **META CORE**. This is the shared Meta-platform API/MCP integration layer owned by Engagement Core. Phase 1 supports official WhatsApp Business Cloud API; Instagram, Messenger and other Meta channels are future adapters, not implemented capabilities. META CORE is separate from **WACRM**, which remains the intended customer-facing WhatsApp CRM and source of truth. The name is internal only; it does not rename a Meta application, repository, existing deployed service, OAuth audience, or the upstream WBMCP package.

A tenant-scoped **integration adapter**, not a replacement CRM, WhatsApp inbox, webhook receiver, WACRM broker, or standalone publicly registered MCP service.

## Production-readiness review (latest Phase 1-D checkpoint, 2026-11-07)

**Current: `SOURCE_AND_EPHEMERAL_WP_STAGING_CERTIFIED / CONNECTED_PRODUCTION_NO_GO`.** The installed Node adapter and HMAC-signed, tokenless WACRM Central read client passed **39/39** tests and a clean high/critical npm audit. The WACRM owning draft passed **101/101 offline PHP checks plus 23/23 integration checks on real disposable WordPress 6.9 and MySQL 8**. Read-only templates are scoped to the verified WABA, with explicit HMAC activation grants, replay denial, bounded inputs, encrypted token custody, no bearer in the new signup response, and hard rejection of WACRM Central Crypto's legacy Base64 plaintext fallback.

All tests use **synthetic Meta transports/accounts**; the WordPress run is ephemeral CI, **not an owner-owned staging deployment**. No live Graph calls, credential distribution, registrations, message sends, customer data or production changes. The two PRs remain draft/unmerged pending authenticated staging, OAuth/client isolation, Meta scope/coexistence verification, independent review and owner release approval. See [production-readiness report](../../../docs/META_CORE_PRODUCTION_READINESS_20261107.md) and [WACRM custody PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134).

The original Phase 1-D and Phase 1-C reports below are retained for historical evidence and must not be used as the latest release decision.

## Phase 1-D verified source checkpoint (2026-11-07)

**Current status: `SOURCE_ONLY / NODE_29_OF_29 / ZOD_AUDIT_HIGH_0 / WACRM_PHP_68_OF_68 / CONNECTED_NO_GO / PRODUCTION_NO_GO`.** The clean Dell clone executed the installed pinned Dojo SDK/MCP with **synthetic two-tenant Graph v26** reads and HMAC relay fixtures: **29/29 tests passed**, `npm audit --omit=dev --audit-level=high` found **0 vulnerabilities**. Lockfile SHA-256 is `1e20985b6a8f04be559e0646892c88f0e65b6db295a958ec313e68ef02534f6c`. The transitive Zod tree is overridden to **4.6.7**, outside Dojo's declared Zod 3 semver range; audit is clean for this candidate but all upstream operations are **not** validated. Hardened input bounds precede SDK parsing.

The **separate WACRM Central source-only** [draft PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134) implements encrypted per-activation tenant custody **disabled by default**; independent WACRM PHP CI checks passed **68/68**, including 14 source-level Central-to-Consumer signed webhook and inbox integration checks. A deployed Central-to-Node private broker does not exist, and the old WACRM signup response still sends an access token to the enrolling Consumer. These are mandatory release blockers, along with actual staging WordPress webhook/inbox E2E, OAuth security and owner approval. **No live Meta call, customer data, phone registration, message send or production deployment.**

Full [Phase 1-D certification and rollback](../../../docs/META_CORE_PHASE1D_CERTIFICATION_20261107.md). The Phase 1-C section below is retained as historical baseline rather than current status.

## Phase 1-C certification update (2026-11-07)

The **actual pinned Dojo SDK and MCP packages** were installed on Dell using `npm ci` from a clean clone, with **26/26 tests passing**, including a simulated Graph API v26 template read via the real SDK. Explicitly added `@opentelemetry/api@1.9.0` after the Dojo SDK failed to import it despite marking that peer optional. The lockfile is committed and verified by SHA-256.

**Security release blocker:** `npm audit --omit=dev --audit-level=high` reports **3 high** entries via the vulnerable Zod dependency chain ([GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)). Keep this a source-only draft; do not expose remote MCP tools or accept production traffic until a reviewed compatible mitigation passes independent QA.

**WACRM source finding:** Central's route table holds activation/WABA/phone, state and encrypted relay secret; the present code returns an access token during signup but **does not store a durable, per-tenant access token for META CORE**. The new `src/wacrm-route-boundary.mjs` is a fail-closed integration contract, not an existing credential vault or an operational WACRM connection. WACRM's owning team/lane must supply trusted activation/owner mapping and credential custody before connected QA.

See [full Phase 1-C certification](../../../docs/META_CORE_PHASE1C_CERTIFICATION_20261107.md).

## Phase 1-B decision — official Graph v26.0 path

Current WACRM Central source defaults to **Graph API v26.0**. The originally selected WBMCP 0.1.3 SDK only accepts **v22.0–v24.0** (source verified in `src/config/constants.ts`). Its existing `src/adapter.mjs` is retained as a **legacy candidate** and now rejects missing or incompatible Graph versions rather than silently falling back to v24.

**Preferred v26 candidate:** [DojoCodingLabs/whatsapp-adapter](https://github.com/DojoCodingLabs/whatsapp-adapter), `@dojocoding/whatsapp-sdk` **0.10.0** and `@dojocoding/whatsapp-mcp` **0.5.0**, both MIT licensed in repository source, with an embedded `createWhatsAppToolset` and `GRAPH_API_VERSION = "v26.0"`.

- `src/dojo-v26.mjs` is a narrow, server-only **read adapter** for exactly three Dojo MCP tools: `whatsapp_list_templates`, `whatsapp_get_template`, and `whatsapp_get_media_info`. All sending, uploads, read acknowledgements, phone lifecycle and subscription operations remain **inaccessible**.
- Must be hosted beside the authorized **WACRM Central** connection vault, not in a browser or the Consumer WordPress plugin. Never expose WACRM's Meta app secret to a consumer site.
- It does not yet provide live outbound messages or a remote HTTP MCP endpoint; future WACRM consent, outbox, retries and signed webhooks are the single customer-message flow.
- The 2026-11-07 local synthetic Node suite: **18/18 PASS** across legacy-v24 guard and Dojo-v26 read candidate. SDK factories were mocked, so **no third-party SDK was installed or executed** and **no real Meta request was made**.
- External npm registry requests from the isolated test container timed out. A reproducible `package-lock.json`, actual upstream installed-package compatibility, npm provenance/advisories, Dojo mock transport tests and WACRM sandbox integration remain **open gates**. Do not claim installed SDK parity from source inspection.

## What exists

- Uses the existing upstream [WBMCP](https://github.com/saravanaspar/WBMCP) SDK, pinned to source package version **0.1.3**, to access the **official WhatsApp Business Cloud API**. No WhatsApp Web/session emulation.
- Exposes 8 allowlisted read operations and 2 strictly **dry-run-only** preview operations.
- Requires a **trusted authenticated principal** plus `authorizeTenant(principal, tenantId, toolName)` returning **exactly true** before any credential resolution.
- Loads credentials from a caller-provided `resolveConnection(tenantId)`. The resolver must return only credentials belonging to the verified tenant. No environment-wide shared user token, persisted message storage, or exported secrets.
- Uses WBMCP native `readOnly: true`, `enableDangerousTools: false` for reads. WBMCP requires enabling dangerous-tool handling to execute message *previews*. For preview-only operations the adapter sets `dryRun:true`, strips `confirm`, and exposes no live outbound tool path.
- Rejects registrations/deregistrations, webhook subscription mutations, all delete/update operations, template creation, live sends, and unknown tool names.

## Intended host integration

```js
import { createEngagementWhatsAppAdapter } from './src/adapter.mjs';

const meta = createEngagementWhatsAppAdapter({
  // Authoritative operator/tenant/role enforcement in Engagement Core.
  authorizeTenant: async (verifiedPrincipal, tenantId, toolName) =>
    engagementCorePolicy.canUseTool(verifiedPrincipal, tenantId, toolName),
  // Resolve strictly from the authenticated tenant's approved WACRM central
  // connection store. NEVER take token or WABA from an MCP tool argument.
  resolveConnection: async tenantId => connectionVault.forTenant(tenantId),
});

const health = await meta.invoke({
  principal: serverVerifiedUser,
  tenantId: serverVerifiedTenantId,
  toolName: 'whatsapp_get_business_account',
  args: {},
});
```

The example names `engagementCorePolicy`, `connectionVault`, and `serverVerifiedUser` are **integration contracts**, not implemented services. Do not deploy the snippet without their own authorization tests.

## META CORE and WACRM ownership boundary

| Existing first-party component | Reused responsibility |
| --- | --- |
| `moksha_wordpress/inc/wacrm-central-meta-coexistence.php` | Meta official coexistence onboarding, upstream webhook challenge/signature handling and route binding |
| `moksha_wordpress/packages/wacrm-consumer/wacrm-consumer.php` | HMAC timestamp/body relay verification, WABA+phone matching, event idempotency and contacts/event storage |
| Engagement Core WordPress source | Existing social engagement and scheduling, not a new CRM database |
| Engagement CRM draft PR #73 | Future customer-site authoritative contacts, conversations, staff permissions and transactional outbox |
| META CORE WhatsApp adapter (WBMCP-backed) | Agent-facing allowed official WhatsApp account/tool functions; never a second webhook receiver |

The WACRM Consumer launch safety PR #52 remains draft/unmerged. **Do not connect existing business phone numbers** as part of this Phase 1 source delivery; preserve WhatsApp Business mobile-app coexistence.

## Developer verification

```sh
cd integrations/meta/whatsapp-mcp
node --test test/*.test.mjs
```

The test suites have no network access and inject synthetic SDK implementations. Recorded sandbox result: **18/18 PASS on Node v22.16.0, 2026-11-07** (11 WBMCP adapter + 7 Dojo read candidate). This certifies adapter policy behavior with mocks **only**; it does not validate the installed WBMCP package, Graph version parity, webhook delivery, real credentials, OAuth, Meta approval scope or production sending.

Before a connected test, verify package registry provenance and install pinned package from a reviewed lockfile; check its real `readOnly` and `dryRun` controls in a provider-less test. WBMCP source shows the `readOnly` guard preceding the dangerous-tool execution; this is why preview calls use a separate SDK configuration. The allowlist and forced dry-run are the outer guard. Never open a direct public call-through to the entire WBMCP tool catalog.

## Non-negotiable next gates

1. Direct Meta approval + exact scope + phone/coexistence verified. No re-pair/migration/register/deregister.
2. Generate verified npm lockfile and test real pinned Dojo SDK 0.10.0 / MCP 0.5.0 in an offline fake-transport mode. Confirm v26 path, read-only exports, schemas and auth errors. Legacy WBMCP is v24-only and stays blocked on WACRM v26.
3. Connect to the **existing** WACRM owner/tenant connection vault through a reviewed, narrowly scoped adapter; ensure WACRM and WordPress source-of-truth remain separate from this SDK.
4. Preserve and certify existing webhook signatures, durable per-tenant retries, echo/status/media history and dead-letter/replay semantics.
5. Build only the **WACRM-owned** consent + audited outbox send workflow, with human approvals and WhatsApp policy checks. Do not add send to this adapter without a separate reviewed owner release.
6. Apply `docs/MCP_OAUTH_REGISTRATION_SOP.md` and its checklist **before any remote MCP/OAuth endpoint** is published; do not reuse unrelated OAuth clients or assume a health response grants access.
7. Isolated staging, operator acceptance, rollback, then separate owner-approved production activation.

## Reuse / cost / rollback

- Internal: existing WACRM Central + Consumer, existing Engagement Core and pending CRM draft; no new CRM or webhook system.
- Upstream: [WBMCP](https://github.com/saravanaspar/WBMCP) **v0.1.3, MIT**; include upstream licence if its SDK code is redistributed. No vendored source in this branch. Upstream maintenance/security still needs release and dependency review.
- Alternative: [Meta official sample code](https://github.com/fbsamples/whatsapp-api-examples), whose terms are not an unrestricted OSI licence.
- New dependencies: none installed in production. Node >=20 required for future adapter host. Local synthetic tests cost no API calls. **Meta messaging and hosting are not inherently free**; any chargeable production use needs separate approval and spending controls.
- Rollback: do not merge this draft; if future integration fails, disable/unmount the adapter without changing phone registrations, webhooks, CRM tables or the current WACRM relay.

**Status:** SOURCE_ONLY / MOCK_QA_18_OF_18 / DOJO_V26_CANDIDATE / INSTALLED_SDK_QA_PENDING / CONNECTED_QA_PENDING / PRODUCTION_NO_GO.
