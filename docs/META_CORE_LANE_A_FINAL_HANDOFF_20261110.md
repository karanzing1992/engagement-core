# META CORE — Lane A v1 Integration Candidate & Handoff

**Date:** 2026-11-10 (Asia/Kolkata)  
**Owning repository:** `karanzing1992/engagement-core`  
**Base:** source-only draft PR #258 at `c7e35107019ca04007d750bd71d22cf8bff018e5`  
**Branch:** `feat/meta-core-lane-a-final-provider-20261110`  
**Classification:** `SOURCE_ONLY / MOCK_PROVIDER_E2E`. **No production or staging deployment is authorized by this document.**

## A. Scope separation

Lane A owns the official WhatsApp API **MCP tool registry and adapter contracts**, the Graph v26 operation request plans, independent synthetic provider QA, security guards, and API semantics/reuse documentation.

**Lane B owns:** Central Google login and OAuth issuer/client/resource grants, authenticated owner-operated WACRM staging, credentials and Meta access tokens, the real WACRM Central broker/outbox/inbox, approved live Meta app/WABA validation, and deploy/rollback. This work does not create a new REST broker, token store, OAuth server, Graph proxy, CRM database, webhook receiver, or another customer-data source of truth.

Ashwakaal — Support Channels is separate. Neither its accounts, identity, permissions nor data are reused here.

## B. Vendor research and open-source cost gate

- [Meta official WhatsApp Cloud API Postman collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api): versioned Graph API and WABA business/messaging permissions.
- [Meta official account phone numbers endpoint](https://www.postman.com/meta/whatsapp-business-platform/request/x5d0w6i/get-all-business-phone-numbers), [business profile](https://www.postman.com/meta/whatsapp-business-platform/request/i21qxwn/get-business-profile), [commerce](https://www.postman.com/meta/whatsapp-business-platform/request/30lrpw8/set-or-update-commerce-settings), [QR codes](https://www.postman.com/meta/whatsapp-business-platform/request/2mp04uj/create-qr-code), [Flow publish](https://www.postman.com/meta/whatsapp-business-platform/request/wcidrlg/publish-flow), and [Flow metrics](https://www.postman.com/meta/whatsapp-business-platform/request/qhqtlpd/get-endpoint-request-error-rate-metric).
- [Meta business message policy](https://whatsappbusiness.com/policy/): recipient consent, 24-hour customer service window, approved templates, human escalation and regional eligibility. Live sends require independently verified Meta app entitlements and owner billing gates.
- **Reuse** existing [DojoCodingLabs WhatsApp SDK/MCP](https://github.com/DojoCodingLabs/whatsapp-adapter), MIT license (`@dojocoding/whatsapp-sdk@0.10.0`, `@dojocoding/whatsapp-mcp@0.5.0`), real 19-tool embedded registry, pinned package lock, and existing [META CORE read broker + Phase 1-E response contract](https://github.com/karanzing1992/engagement-core/pull/257).
- **Reuse** separately WACRM Central's crypto and signed HMAC/inbox APIs in [WACRM PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134). WACRM never releases the Meta bearer to an MCP caller.
- No new dependency, hosting service, model/API credit or chargeable Meta call in Lane A. Future send fees, actual endpoint quota and access remain independent owner decisions.

## C. Source modules and status

| Path | Contract |
| --- | --- |
| `src/lane-a-capability-catalog.mjs` | 55 distinct tool names, category, permission hint, JSON-schema candidate and explicit dangerous exclusions |
| `src/lane-a-mcp-harness.mjs` | Offline MCP tools/list + tools/call, strict bounded JSON, default zero privileges, 24-hour window and template/opt-in/owner consent gates |
| `src/lane-a-graph-v26-plans.mjs` | All 33 `host` tool names deterministically map to fixed Graph v26 paths/methods and typed query/form/JSON request descriptors |
| `src/lane-a-provider-runtime.mjs` | Provider-injection candidate for authenticated, WACRM-routed MCP calls: `dojo`, `broker`, `host`, `wacrm` |
| `test/lane-a-provider-runtime.test.mjs` | Full 55-tool fake provider + two-tenant identity, grant, ownership, leak, no-send and no-retry test matrix |
| `test/lane-a-upstream-dojo-parity.test.mjs` | Actual installed Dojo 19-tool name parity, text/template dispatch through fake client |
| `.github/workflows/meta-core-lane-a-final-ci.yml` | Independent Node 24 test/audit and no-live-provider release marker |

**Important:** 55 registered capabilities does not imply all provider handlers are active. The 33 host operations produce *blueprints*, not Graph HTTP calls. Dojo fake-client dispatch is not a real WACRM outbox. The remote MCP OAuth resource is not built or registered here. The 17 Dojo-owned tool schemas are now derived directly from the installed pinned MCP/Zod definitions and checked by strict safe input validation; the two WACRM-owned template reads retain their deliberately narrower broker schemas. Advanced Graph host operations still require production vendor-version and WACRM transport parity review.

## D. Integration interface for Lane B

`createLaneAProviderMcp` accepts only operator-supplied, non-browser callbacks:

```javascript
createLaneAProviderMcp({
  verifyIdentity,           // verified issuer, resource audience, client, actor/tenant binding
  authorizeTenant,          // actor has specific operation grant for tenant
  readPolicy,               // WACRM-approved recipient opt-in/window/template/spend/owner policy
  resolveRoute,             // WACRM tenantId -> active activationId, WABA and phone IDs
  resolveOwnership,         // WACRM-owned template, media, Flow, QR binding proof
  providers: {
    broker: { invoke },     // existing signed two-tool read broker
    dojo: { invoke },       // WACRM-owned SDK and durable outbox; never raw token on MCP side
    host: { executePlan },  // WACRM Central Graph plan executor
    wacrm: { read }         // WACRM-owned tenant inbox and status reader
  },
  grants: [],               // default DENY; exact enabled names after OAuth owner approval
  enableWriteCandidates: false
});
```

Inputs to `callTool` must contain a **host-proven** `verifiedPrincipal.actorId`, tenant ID and for mutations an externally generated stable `requestId`. The model cannot supply or authorize the issuer, tenant, WABA, token, client, signing secret or approval via tool arguments.

**WACRM outbox must implement** persistent idempotency, recipient opt-in evidence, approved-template membership, customer-service window, Cloud API 429 backoff, bounded queue/dead-letter handling and retries with audit. Lane A does not emulate these WACRM capabilities and never blindly retries a failed send. **Flow publishing/deprecation, template deletion, QR deletion and media deletion** additionally require an owner approval plus a WACRM-verified ownership proof for the actual WABA resource. Account/phone lifecycle operations are entirely excluded.

**Production-safe enablement sequence:** keep all grants OFF, connect Lane B identity validators and credentialless WACRM adapters in dedicated staging, verify security/cross-tenant denial and real Meta sandbox read-only response, then complete owner-approved resource/credential/release gates. Do not enable a send merely because synthetic provider tests pass.

## E. Security acceptance

- Zero default registered tools; explicit per-operation grants and separate write enablement.
- Host-owned issuer/client/audience verification precedes policy, route access and provider calls.
- Every request checks tenant binding and active WACRM activation/WABA/phone mapping.
- Inputs bounded, strict schema, no unknown/dangerous token fields, no object accessors/proxy leakage, media-URL guard, immutable-by-construction Graph v26 path.
- Sensitive or unrecognized Graph response fields are not echoed. Secret/recipient-field regressions fail closed. No raw customer message content or bearer returned to an agent by default.
- All dangerous write operations require host-approved durable request IDs; no automatic send retries. Only the WACRM owner stores customer data or messages.
- Host must enforce TLS egress/DNS SSRF protection, allowlist and rate limits; a source-level HTTPS URL guard **does not replace** network-level constraints.
- Existing Dojo 0.5.0 / Zod 4 forced override is still outside upstream-declared compatibility semver; require independent WACRM endpoint acceptance before live SDK execution.
- Hard release blockers: Lane B real OAuth/tenant grants, dedicated WACRM staging, actual Meta permissions/coexistence/account ownership, final sign-off, key rotation/backup/restore, customer cost policy and owner acceptance.

## F. Completion criteria and rollback

Lane A source handover is accepted only after exact-head Node 24/npm CI runs all old and new tests (including all 55 mock-provider operations and 19 Dojo MCP registry parity), zero high/critical dependency vulnerabilities, verified additive-only diff, and an independent review of the Graph v26 path mapping. **Until that run and review, report source implemented but certification pending.**

For defects, disable all grants and use the **existing** WACRM old read-only path. Rolling back this unmerged branch is non-destructive: close draft PR, no runtime state/migration/keys/customers/phone registration changed. Do **not** post `VERIFIED_LIVE` to the Master Supabase inbox for these source-only changes. Report verified new platform integrations only after Lane B can provide evidence in the authorized event inbox.

## G. Final Lane A engineering and CI checkpoint — 10 November 2026

**Exact source checkpoint before this handoff update:** `a843fd476c27621900662d9f1c870ca26ca4b7c4`.  
**Independent CI:** [GitHub Actions #42852021177](https://github.com/karanzing1992/engagement-core/actions/runs/42852021177), **87/87 Node tests passing, 0 failures, npm audit 0 vulnerabilities** (Node 24, installed pinned dependencies).

- [x] 55 distinct MCP tool contracts and 12 explicit privileged exclusions.
- [x] Full 55-operation fake provider dispatch, including 33 fixed Graph v26 host plans, 17 Dojo-owned tools, two WACRM template broker reads and three WACRM inbox/status reads.
- [x] All 19 real Dojo MCP handlers exercised against the installed SDK's own in-memory `MockWhatsAppClient`; one synthetic media fetch was stubbed explicitly, **zero Meta API calls**.
- [x] For the 17 Dojo-owned tools, JSON input schemas are generated from the installed upstream Zod input definitions, with strict preflight validation and nested SSRF/sensitive-field checks. The other two (template list/get) are intentionally WACRM-bound.
- [x] Genuine `@modelcontextprotocol/sdk` in-memory client/server exchange for `tools/list` and `tools/call`; unauthenticated call denial tested. No public listener or OAuth registration.
- [x] Versioned, machine-readable [55-tool Lane A adoption manifest](../integrations/meta/whatsapp-mcp/manifest/lane-a-whatsapp-mcp-v1.json), default grants empty, production disabled. CI asserts manifest consistency with catalog.
- [x] Fail-closed identity, actor/tenant grants, resource ownership, operation cost/window/approval gates, request-ID requirements and output redaction negative tests.
- [x] Separate approved provider ownership preserved; no second credential vault, WACRM event system or CRM source of truth.
- [x] Explicit rollback: do not merge draft PR until review, close candidate to revert source only; live customer data and WhatsApp registrations remain untouched.

**Lane A classification:** `SOURCE_ENGINEERING_COMPLETE / INDEPENDENT_SYNTHETIC_CI_PASS / READY_FOR_LANE_B_ADOPTION_REVIEW`.

**Not certified:** live WACRM providers, real Graph v26 account/scope responses, exact host-provider payload parity for each conditional Meta operation, Central OAuth resource grants, HTTPS ingress/egress, customer-facing sending policy, durable outbox implementation, paid sends, owner-controlled WACRM staging and live production approval. These are cross-lane / release gates, not claims of Lane A runtime deployment.

**No VERIFIED_LIVE Master event is appropriate for this source-only work.** The separate Ashwakaal — Support Channels workstream remains isolated.
