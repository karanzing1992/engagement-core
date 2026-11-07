# Engagement Core — Meta WhatsApp MCP adapter (Phase 1, SOURCE ONLY)

A tenant-scoped **integration adapter**, not a replacement CRM, WhatsApp inbox, webhook receiver, WACRM broker, or standalone publicly registered MCP service.

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

## WACRM ownership boundary

| Existing first-party component | Reused responsibility |
| --- | --- |
| `moksha_wordpress/inc/wacrm-central-meta-coexistence.php` | Meta official coexistence onboarding, upstream webhook challenge/signature handling and route binding |
| `moksha_wordpress/packages/wacrm-consumer/wacrm-consumer.php` | HMAC timestamp/body relay verification, WABA+phone matching, event idempotency and contacts/event storage |
| Engagement Core WordPress source | Existing social engagement and scheduling, not a new CRM database |
| Engagement CRM draft PR #73 | Future customer-site authoritative contacts, conversations, staff permissions and transactional outbox |
| This WBMCP adapter | Agent-facing allowed official WhatsApp account/tool functions; never a second webhook receiver |

The WACRM Consumer launch safety PR #52 remains draft/unmerged. **Do not connect existing business phone numbers** as part of this Phase 1 source delivery; preserve WhatsApp Business mobile-app coexistence.

## Developer verification

```sh
cd integrations/meta/whatsapp-mcp
node --test test/*.test.mjs
```

The test suite has no network access and injects a synthetic SDK implementation. Recorded sandbox result: **8/8 PASS on Node v22.16.0, 2026-11-07**. This certifies adapter policy behavior with mocks **only**; it does not validate the installed WBMCP package, Graph version parity, webhook delivery, real credentials, OAuth, Meta approval scope or production sending.

Before a connected test, verify package registry provenance and install pinned package from a reviewed lockfile; check its real `readOnly` and `dryRun` controls in a provider-less test. WBMCP source shows the `readOnly` guard preceding the dangerous-tool execution; this is why preview calls use a separate SDK configuration. The allowlist and forced dry-run are the outer guard. Never open a direct public call-through to the entire WBMCP tool catalog.

## Non-negotiable next gates

1. Direct Meta approval + exact scope + phone/coexistence verified. No re-pair/migration/register/deregister.
2. Test real pinned upstream SDK offline; verify deny-without-dryRun, preview only, and error sanitization.
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

**Status:** SOURCE_ONLY / MOCK_QA_8_OF_8 / CONNECTED_QA_PENDING / PRODUCTION_NO_GO.
