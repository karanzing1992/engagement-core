# META CORE — Phase 1-C Installed SDK, WACRM Boundary, and Security Certification

**Date:** 2026-11-07 (Asia/Kolkata)  
**Workstream:** META CORE (Engagement Core); WACRM integration is separate and future-facing  
**Repository:** `karanzing1992/engagement-core`  
**Draft PR:** [#215](https://github.com/karanzing1992/engagement-core/pull/215)  
**Checkpoint:** `SOURCE_ONLY / CLEAN_NPM_CI_PASS / TESTS_26_OF_26 / SECURITY_NO_GO / WACRM_CREDENTIAL_AUTHORITY_PENDING`

## 1. Scope and verified outcome

This increment stays entirely inside the isolated META CORE feature branch. It uses the official Meta Graph API **only through a mock in tests** and does not create a public MCP server, register/migrate a phone, alter Meta settings, send real messages, or modify the running WACRM Central/Consumer site.

- Installed `@dojocoding/whatsapp-sdk@0.10.0`, `@dojocoding/whatsapp-mcp@0.5.0`, legacy comparison `wbmcp@0.1.3`, and `@opentelemetry/api@1.9.0`.
- **Actual upstream runtime finding:** Dojo SDK imports `@opentelemetry/api` at runtime, although package metadata marks the peer optional. An initial real import failed `ERR_MODULE_NOT_FOUND`. Explicitly pinning `@opentelemetry/api@1.9.0` corrected the import; no fork needed.
- Committed exact reproducible `integrations/meta/whatsapp-mcp/package-lock.json`, generated using npm 11.19.1 on Dell. **SHA-256** `a527bbe7969a7567f077fa536c80de912fa65c891076534446c7b752ff26f885`.
- A clean independent Dell clone of source commit `7f61cc48d9191e61632e1a3d0f7cb0cda14a6d97` ran `npm ci --ignore-scripts --no-audit --no-fund` and `node --test test/*.test.mjs`: **26 tests passed, 0 failed**, Node v24.22.0; clean worktree afterwards.
- Installed Dojo SDK `GRAPH_API_VERSION` returned `v26.0`. Actual embedded MCP toolset listed **19 tools**; only three read operations are exposed by the META CORE allowlist.
- With a fake `globalThis.fetch` Graph boundary, actual SDK and MCP toolset successfully executed `whatsapp_list_templates` and `whatsapp_get_template` via simulated `https://graph.facebook.com/v26.0/...` **GET** requests. Invalid user and send requests were denied before network. No production Meta token was loaded.

## 2. WACRM source-of-truth integration boundary (not yet connected)

Inspected existing first-party `karanzing1992/moksha_wordpress` main source:

| Existing authority | Observed source behavior | META CORE consequence |
| --- | --- | --- |
| `inc/wacrm-central-meta-coexistence.php` | Owns official Embedded Signup/coexistence, Meta webhook, `wacrm_meta_routes` row with `activation_id`, `waba_id`, `phone_number_id`, active status and encrypted relay secret. Defaults to Graph v26.0. | **Reuse** Central routing and Coexistence. Do not build a second webhook or read a browser credential. |
| Same Central source | Exchanges signup code for access token, sends token in onboarding completion response; the route record **does not persist a per-tenant Meta access token**. | **Credential authority is NOT ready:** do not infer `connectionVault.forTenant()` exists; implement secure per-activation token custody/rotation in a separate owner-reviewed WACRM change. |
| `packages/wacrm-consumer/wacrm-consumer.php` | Holds tenant-local contacts/events and HMAC relay secret, **not** a general META CORE Meta token resolver. | Never fetch Meta app secret/token from an arbitrary Consumer, or migrate customer events. |
| `packages/wacrm-consumer/wacrm-test-console.php` | Has **separate sandbox-only encrypted token configuration**. | Do not reuse a sandbox token as a production Meta token or blend test/live WABA numbers. |

New source-only `src/wacrm-route-boundary.mjs` accepts trusted `readRoute(tenantId)` and `resolveCredential(binding)` providers. The latter is intentionally an **unimplemented external WACRM authority**, not a new vault. The boundary rejects missing providers, inactive or malformed routes, bad activation mapping, wrong tenant, WABA/phone mismatch, mismatched Graph version and incomplete secrets. The authorized META CORE adapter still independently requires a trusted operator grant. Tests cover those denials.

**Important:** `tenantId` is a canonical internal label and must be derived from a verified WACRM activation/site grant, not a browser request or raw route table alone. The WACRM route does not currently include a `tenant_id` field; the eventual `readRoute` implementation must join that record to the existing activation/owner binding.

## 3. Dependency audit and release blocker

Read-only `npm audit --omit=dev --audit-level=high --json` on the installed package tree returned **3 high, 0 critical** affected package entries, traced to one dependency advisory:

- `zod` affected range `<4.6.6`: [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5) — memory exhaustion from oversized constrained collections.
- `@dojocoding/whatsapp-sdk` and `@dojocoding/whatsapp-mcp` are marked high via their vulnerable Zod dependency tree; `npm audit` reported `fixAvailable: false` for their existing pinned resolution.
- Do **not** assume `npm audit fix --force` or Zod major-version overrides are compatible with upstream schema handling. Safe path: an upstream reviewed migration, compatible MIT-licensed patch/fork and full regression, or an independently vetted replacement. Bounded ingress size and authentication are defense-in-depth, not a substitute for a resolved high-severity advisory.

**Release decision: SECURITY_NO_GO.** The project is safe to keep as a draft source/evidence package, not to expose as a public remote MCP or production customer-facing API.

## 4. Tests/acceptance and unverified gates

| Check | State |
| --- | --- |
| Pin package versions and lockfile | **PASS / source** |
| Reproducible clean `npm ci` on Dell | **PASS / runtime** |
| Real Dojo SDK import and embedded MCP tool registration | **PASS / runtime** |
| Simulated official Graph v26 template reads | **PASS / synthetic transport** |
| Tenant/route/credential deny tests | **PASS / 26 total tests** |
| npm advisory audit | **FAIL / high** |
| Authenticated WACRM Central token resolver | **NOT IMPLEMENTED** |
| WACRM live sandbox receive/send/receipts/outbox | **NOT RUN** |
| Remote HTTP MCP OAuth, scope/PKCE/audience/client isolation | **NOT REGISTERED / NOT CERTIFIED** |
| Meta approval scope, Business App coexistence runtime | **OWNER-REPORTED / NOT INDEPENDENTLY REVALIDATED** |
| Production deployment | **NO-GO / NOT ATTEMPTED** |

## 5. Next bounded sprint (P1-D)

1. Resolve GHSA-mrhx-c7xc-m3w5 through reviewed compatible upstream patch or replacement and prove `npm audit` clean at high/critical severity.
2. In the **WACRM owning repository and authorization lane**, implement approved durable per-activation credential custody, decrypt/revoke/rotate and route-binding (no external token exposure), then publish the minimum internal adapter authority contract.
3. Run isolated WACRM Central + Consumer signed-webhook replay, inbox and receipt tests with synthetic data; preserve existing WhatsApp Business mobile app.
4. Only after the preceding gates, register a remote MCP using the canonical [MCP OAuth Registration & Isolation SOP](MCP_OAUTH_REGISTRATION_SOP.md), capture negative cross-client tests and owner release approval.

## 6. Reuse/cost/rollback

Existing first-party WACRM Central + Consumer, Engagement Core and the MIT-licensed Dojo SDK/MCP are reused. No new paid service, message fee, production credential, system user, migration, Meta request or deployment was authorized. App credentials, customer contacts and conversations remain outside the repository. Rollback is to leave draft PR unmerged and remove the isolated adapter from any future build; no current running system is coupled to it.

**Master reporting:** No default-branch merge, live app change or verified platform integration occurred. Do not publish a `VERIFIED_LIVE` Master Registry event for this source-only branch. Ashwakaal Support Channels remains an entirely separate workstream.
