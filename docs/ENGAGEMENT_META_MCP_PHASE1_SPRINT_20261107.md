# META CORE — Phase 1 WhatsApp MCP Sprint Checkpoint

**Date:** 2026-11-07  
**Internal project name:** META CORE  
**Owning platform:** Engagement Core  
**Future integration target:** separately developed WACRM  
**Repository:** `karanzing1992/engagement-core`  
**Branch:** `feat/meta-whatsapp-mcp-phase1-20261107`  
**Lifecycle:** SOURCE_ONLY. No Meta calls, number changes, WACRM deployment, plugin update or production authorization.

## Internal naming and boundaries

**META CORE** is the canonical internal name for the reusable official Meta Graph API and MCP integration library. WhatsApp Business is **Phase 1**; Instagram, Facebook Messenger and other Meta channels are planned subsequent adapters, subject to their own provider permissions and QA. This is **not** a rename of Engagement Core or WACRM, and does not represent a separate CRM or customer-data store. Retain the existing repository, feature branch, source paths and draft PR identifiers for continuity; provider-facing app registration, public product names, OAuth identities, tokens and production deployments remain unchanged.

## Decision

Adapt the maintained first-party WACRM transport and the open-source WBMCP official Cloud API SDK; do **not** build a parallel WhatsApp backend or replace existing mobile-app coexistence. Expose a restricted tool facade rather than its full 61-tool catalog.

## Source baseline and verified reuse

- WACRM central Meta coexistence broker and signed Consumer relay exist in `karanzing1992/moksha_wordpress` (source inspected). Existing history, echo, contact and status extraction remain with WACRM.
- `moksha_wordpress` PR [#52](https://github.com/karanzing1992/moksha_wordpress/pull/52) remains open, draft, unmerged. Historical launch audit: [WACRM latest update](ENGAGEMENT_CORE_WA_CRM_LATEST_UPDATE.md).
- Engagement CRM foundation PR [#73](https://github.com/karanzing1992/engagement-core/pull/73) remains open, draft, unmerged. WordPress-local CRM remains the intended authoritative store; it is not an active dependency of this adapter.
- Upstream: [saravanaspar/WBMCP](https://github.com/saravanaspar/WBMCP) package `0.1.3`, MIT (confirmed in upstream package.json and LICENSE); exposes official WhatsApp Cloud API via SDK, dryRun, readOnly and confirmation guards.
- Meta App Review approval was reported by the owner on 7 November; **direct provider permission and production-number readback have not been performed**. Do not upgrade provider status without evidence.
- `Ashwakaal — Support Channels` remains an entirely separate workstream; no shared credentials, messages, contacts or support accounts.

## Delivered in this META CORE source branch

1. `integrations/meta/whatsapp-mcp/package.json`: pinned upstream SDK (not installed or deployed).
2. `src/adapter.mjs`: read allowlist, preview-only sends, tenant-grant callback, per-tenant credential resolver, restricted SDK flags and redacted failure responses.
3. `test/adapter.test.mjs`: 8 synthetic contract/policy tests.
4. `integrations/meta/whatsapp-mcp/README.md`: WACRM separation, host contract, future integration acceptance gates and rollback.

## Phase 1-B — 2026-11-07 source-verified compatibility and security increment

**Finding:** Current first-party WACRM Central code defaults to **Meta Graph API v26.0**. Pinned WBMCP 0.1.3 upstream `src/config/constants.ts` only lists `v22.0`, `v23.0` and `v24.0`. The original META CORE adapter is therefore not suitable for the current WACRM v26 tenant without an intentional SDK change. It now **fails closed** with `graph_version_mismatch`, including when Graph version is omitted, instead of using the older default.

**Preferred reuse alternative:** [DojoCodingLabs/whatsapp-adapter](https://github.com/DojoCodingLabs/whatsapp-adapter), current source package versions `@dojocoding/whatsapp-sdk@0.10.0` and `@dojocoding/whatsapp-mcp@0.5.0` (MIT); SDK source `packages/whatsapp-sdk/src/types/constants.ts` explicitly defaults to `v26.0`. Its embedded `createWhatsAppToolset` provides an existing MCP surface, avoiding a from-scratch gateway. Candidate vendor/source inspection is **not** installed-package certification.

**New source work:** `integrations/meta/whatsapp-mcp/src/dojo-v26.mjs` provides a trusted-WACRM-Central-only, v26-pinned **read-only** wrapper around three Dojo MCP tools. `test/dojo-v26.test.mjs` adds seven synthetic tests: read allowlist, exact tenant credential mapping, cross-user/tenant denial, mutating-tool denial, Graph mismatch, missing app secret and error redaction. Three additional WBMCP compatibility tests cover v26 rejection, missing-version rejection and explicit supported-version behavior.

**Executed offline QA:** `node --test test/*.test.mjs` on Node **v22.16.0** → **18 tests passed, 0 failed**, synthetic client/toolset factories only. No npm dependencies were installed or executed; npm registry lookup timed out in the isolated sandbox. No Meta Graph call, credential access, hosted MCP endpoint, actual WACRM handshake, production deployment or live send occurred.

**Next certification:** Obtain reproducible lockfile with pinned package integrity using an authorized network-capable development environment; run actual Dojo SDK/MCP against isolated fake fetch transport, validate v26 request construction and resource permission filtering, audit upstream dependencies, then connect to the existing authorized WACRM Central resolver with owner/tenant grants. No Consumer-hosted Meta app secret; keep inbound history/webhooks in existing WACRM. Review PR #52 separately without blind merge.

**Cost and rollback:** Both Dojo packages are MIT in their checked GitHub source, no purchase or new infrastructure was authorized, and this is an additive draft-branch candidate. Retain current WACRM release and disable/remove the unconnected candidate if upstream validation fails. Meta usage may be billable only after separate authorization.

**Master status:** Feature branch `SOURCE_ONLY`, not a merged/default-branch or platform-verified integration; **no Master Registry event published**.

## Tests and assurance

- Local Node v22.16.0: `node --test test/*.test.mjs` => **18 passed, 0 failed** (11 legacy/compat tests + 7 v26 Dojo read tests; synthetic SDK factories only).
- Negative cases: unknown/dangerous tools, phone lifecycle, live text send, wrong tenant, wrong principal, caller-supplied confirmation and error redaction.
- **Not tested:** real `wbmcp` npm installation, Graph API connection, Meta webhook, actual WACRM integration, live end-to-end conversation, production operator auth, rate/retention/consent, OAuth/MCP registration.
- No webhook replacement; original WACRM HMAC relay and data ownership are preserved.

## Next bounded sprint increments

**P1-B — upstream and compatibility:** source-version audit and synthetic v26 candidate completed; **remaining**: lockfile, real installed Dojo SDK tests with mock Graph HTTP transport and independent dependency/security review.

**P1-C — WACRM handshake:** map existing Central connection authority and Consumer REST/events to the per-tenant resolver; do not send tokens into WordPress browser/client. Define normalized inbound/outbound schemas and idempotency/receipt contract. Reconcile WACRM PR #52 without blind merge.

**P1-D — isolated sandbox end-to-end:** independently validate signed relay retries, wrong-WABA/phone denial, one test conversation's inbound and reply lifecycle, status/echo reconciliation, consent, staff authorization, durable outbox, and rollback. Do not touch an existing production Business-app number.

**P1-E — OAuth/remote MCP registration:** after source/staging acceptance, complete the canonical security checklist before adding a new publicly reachable MCP app or endpoint; do not repurpose an unrelated OAuth audience or credentials.

**Exit state:** A reviewer-approved PR + connected sandbox evidence + documented release decision. Production remains NO-GO until explicit separate authorization.

## Open Source / Reuse / Cost Gate

Reuse first-party WACRM broker and Consumer, Engagement Core social infrastructure and WBMCP SDK v0.1.3 (MIT). No Chatwoot, parallel CRM, paid provider or new server. This branch has no billable API calls. Future WBMCP package security/compatibility and Meta charging model must be verified at its real deployment gate. The original WACRM/Engagement live systems are the rollback baseline.

## Master reporting

This is a draft feature branch, **not** a new default-branch stack version or platform integration. Do not publish as a `VERIFIED_LIVE` Master event. After separately reviewed default-branch merge, use the existing source-linked Master route and verify Google Doc readback. No independent Ashwakaal event is created.
