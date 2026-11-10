# META CORE — Phase 1-D Production Readiness & Security Gate

**Date:** 2026-11-07 (Asia/Kolkata)  
**META CORE source:** `karanzing1992/engagement-core`, [draft PR #215](https://github.com/karanzing1992/engagement-core/pull/215)  
**WACRM Central/Consumer source:** `karanzing1992/moksha_wordpress`, [draft PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134)  
**Release classification:** `CANDIDATE_SOURCE_CERTIFIED / EPHEMERAL_WP_STAGING_PASS / CONNECTED_PRODUCTION_NO_GO`.

## 1. Exactly what is verified

| Gate | Evidence | Verdict |
| --- | --- | --- |
| Zod GHSA-mrhx-c7xc-m3w5 | npm override `^4.6.7`, regenerated lock; clean high/critical audit | PASS / current lock |
| META CORE package runtime | Node 24, pinned Dojo 0.10.0/MCP 0.5.0, real imports; [Actions #42364913792](https://github.com/karanzing1992/engagement-core/actions/runs/42364913792) | **39/39 PASS** |
| Two synthetic Graph v26.0 tenants | Real SDK fake-fetch reads + signed Central broker client; deny wrong principal, tool, route, version, payload | PASS / no real Meta |
| WACRM PHP source | [Actions #42365755538](https://github.com/karanzing1992/moksha_wordpress/actions/runs/42365755538): 23 credential custody + 32 tokenless broker + 14 Central→Consumer webhook + 22 Consumer HMAC/inbox + 10 coexistence | **101/101 PASS** |
| Actual disposable WordPress and MySQL | Same Actions: **WordPress 6.9 + MySQL 8** CI; real WP REST server, MySQL vault/nonce and inbox tables, simulated Graph, tokenless Embedded Signup, rollback | **23/23 PASS** |
| Production, customer or Meta mutation | No code merge, live Graph call, remote MCP, credential injection, phone registration, send, unsubscribe, customer data move, or DNS change | PRESERVED / NO ACTION |

The WordPress CI uses an **ephemeral GitHub runner and disposable database** named `wacrm_tmp`, not an operator-owned staging domain. WP HTTP calls are filtered to synthetic fixtures; no live Graph API or phone service receives requests. Its WACRM Crypto implementation now loads the **actual owned `WACRM_Central_Crypto` class** from the SHA-256-verified upstream ZIP (source commit `5045601f6903c566a6e27cfe534430aaa7c89ae4`); the ZIP checksum is verified before execution. This is still a disposable runner—not a connected owner-operated staging or production site. Independent CI [run #42366182545](https://github.com/karanzing1992/moksha_wordpress/actions/runs/42366182545) passed **101/101 PHP synthetic checks** and **23/23 real ephemeral WordPress/MySQL checks with the actual pinned Crypto implementation**. The source ZIP itself was read-only inspected on Dell at SHA-256 `53b8f1289b2e5b69d9c8d0ed47c12c9485a749d41266509f26efe153ad5ab874`.

## 2. New production-candidate design

**Central owns the tokens.** Existing `WACRM_Central_Crypto` AES-GCM handling and activation/license/route associations are reused in an OFF-by-default credential vault. Credentials are encrypted per activation; tenant ID is derived from the verified activation and site hash, never a browser parameter alone. Authorized rotation changes the generation; revocation blanks stored ciphertext. Graph v26 is enforced; wrong WABA/phone, wrong or expired licence, changed site binding and wrong principal deny access.

**No bearer leaves Central in the new flow.** When custody is explicitly enabled, `meta/coexistence/complete` now returns `credential_mode=central_only` and **omits `access_token`**. The legacy response remains available only with the feature flag off, so source integration does not silently break an existing customer installation. The owner must coordinate activation and Consumer version rollout.

**Tokenless private read broker.** A separate opt-in Central REST resource `/wp-json/wacrm-central/v1/meta-core/read` requires HTTPS, a dedicated HMAC client and audience, 90-second timestamp window, cryptographic nonce, DB-atomic replay rejection, and an explicit server-side activation allowlist. The permitted operations are **only** `whatsapp_list_templates` and `whatsapp_get_template`. The Node adapter requires a server-verified principal and grant before reading its trusted Central route. It signs a bounded request but never fetches a Meta bearer token. Central performs the fixed Graph v26 GET and returns only allowlisted template metadata. By-ID reads traverse a bounded exact WABA template edge; they never fetch a global template object whose tenant ownership cannot be established. Sends, subscription writes, phone lifecycle, media, unrestricted Graph call-through and customer messages are absent.

**Hardening of unsafe fallback.** The inspected first-party Central Crypto code can Base64-encode plaintext if OpenSSL is unavailable. The **new vault rejects that behavior** by requiring OpenSSL AES-256-GCM, checking decoded ciphertext length including IV/tag, and verifying an authenticated encryption/decryption round trip. Synthetic Base64-fallback rejection is included in the 23 custody checks. A separate owner-reviewed hardening of the generic upstream Crypto fallback is advisable; do not assume the legacy helper is universally safe merely because this vault now fails closed.

## 3. What still prevents genuine production sign-off

1. **Actual WACRM deployment:** the new code is only in draft branches. There is no authenticated Central↔Node runtime configured with secret injection, TLS trust/network allowlists, approved activation IDs, or monitoring on an owner staging host.
2. **Live-authority verification:** the owner-reported Meta application approval, exact app scopes (`whatsapp_business_management` as applicable), WABA identity, Graph v26 token lifecycle, and Business App coexistence have **not** been independently confirmed against a real official Meta staging/sandbox account. No chargeable API call or live webhook was made.
3. **Remote MCP OAuth:** no public HTTP MCP resource was registered. Before any remote connector, complete `docs/MCP_OAUTH_REGISTRATION_SOP.md`: issuer/JWKS, PKCE S256, client ID, fixed audience, actual scope/owner/tenant enforcement, six cross-client negative tests and consent/revocation checks. Do not treat the internal HMAC broker as client-facing OAuth.
4. **Owner-operated staging:** certify HTTPS proxy, application-layer rate limiting and WP cron nonce garbage collection, actual Central package crypto in the intended deployment, real database restore, key/salt rotation, idempotent retry/outbox semantics, Meta sandbox template membership, and rollback on a dedicated isolated **WACRM** staging domain. Never co-opt CRM staging or Moksha production.
5. **Independent security review:** upstream Dojo still declares Zod 3 and is forced onto Zod 4.6.7. The supported read-only tests and audit are clean, but unrelated Dojo APIs are not certified. No production tool exposure outside the explicit allowlist.
6. **Owner release gate:** final UI acceptance, production config/secrets and activation/merge/deployment remain separate owner-controlled actions.

**Decision:** code and synthetic/ephermal-platform integration are certified for review; **not certified for production traffic**. Both PRs stay draft, unmerged. No phone, customer, account, Ashwakaal or production state is modified.

## 4. Owner-controlled staging configuration (example only, never commit values)

In the **approved isolated WACRM staging WordPress config**, after securely injecting a dedicated secret from the host environment:

```php
define('WACRM_META_CORE_CUSTODY_ENABLED', true);
define('WACRM_META_CORE_BROKER_ENABLED', true);
define('WACRM_META_CORE_ALLOWED_ACTIVATIONS', array(/* explicit approved synthetic activation IDs */));
define('WACRM_META_CORE_BROKER_SECRET', getenv('WACRM_META_CORE_BROKER_SECRET'));
```

Pair with the matching server-only META CORE adapter secret in a **separate protected runtime**; never use WordPress salts or Meta app secret as this HMAC key. No public JS, logs, GitHub Actions secrets output, browser storage or Consumer token fetching. Do not enable either flag on production until staging and owner approval have passed. Use standard HTTPS with a narrow reverse-proxy/WAF allowlist and fixed resource URI.

## 5. Deployment, rollback and cost gates

1. Freeze both exact PR heads, review diffs, audit dependencies, backup WACRM Central options/activation/route/crypto keys plus WordPress database; test restore in isolated staging. Preserve existing phone registrations, Meta subscriptions and Consumer inbox.
2. Install first with feature flags **OFF**, check current services and HMAC relay unchanged, then enable **synthetic staging only** with explicit activation allowlist and dedicated secret. Validate signed templates, negative cross-tenant, legacy and new signup, incoming webhook/idempotent inbox, backups, replay and key rotation.
3. If any check fails: disable both flags, remove the broker route, revoke staging synthetic tokens and restore only isolated staging database from its verified backup. **Never reset, unregister or migrate a WhatsApp Business phone to fix a staging failure.**
4. Release requires written owner acceptance of final UI, Meta App/WABA/coexistence identity, allowed scopes, registered MCP OAuth boundary, migration and credential rotation plan, and source/CI checksums. No automated merging or deployment.
5. Free/open reuse: WordPress (GPL), existing WACRM (owned), Node.js, upstream Dojo SDK/MCP (MIT), Zod 4.6.7 (MIT), WP CLI, standard PHP OpenSSL; no new paid SaaS or Meta billable calls in testing. Future messaging/hosting rates must be separately approved. Upstream WBMCP remains v24-only, blocked on v26.

## 6. Master reporting

This is **SOURCE_ONLY** because neither draft is merged and no approved live platform integration exists. Do **not** claim `VERIFIED_LIVE`, publish a default-branch Master marker, modify Ashwakaal Support Channels or create a duplicate polling mechanism. Sync the Master through its canonical authorized route only after actual approved deployment and consumer acknowledgement.


## Phase 1-E — central Google OAuth candidate source certification (7 November 2026)

The DeluluTech central Google OAuth candidate is in the separately owned [draft PR #57](https://github.com/aarondash5-star/delulutech/pull/57). See the [exact-source certification and release-gate report](https://github.com/aarondash5-star/delulutech/blob/feat/delulutech-central-google-oauth-p1e-20261107/create-projects/wp-manager/authenticated-mcp/docs/DELULUTECH_CENTRAL_AUTH_PHASE1E_CERTIFICATION_20261107.md).

- **PASS / isolated only:** 23/23 Node tests including a fully synthetic signed Google OIDC → real Cloudflare OAuth provider consent → authorization-code exchange → resource-specific access token, and client/tenant/resource negative boundary probes; compiled Cloudflare Worker; dedicated pinned dependency audit 0 vulnerabilities.
- **Critical source fixes:** Cloudflare-compatible Google subject ID without colons, mandatory safe CIMD compatibility flag, allowlisted client check before external metadata fetch, bounded Google token JSON parsing.
- **Verified runtime discovery (read-only Cloudflare):** the existing *production* WP Manager auth Worker already has Google sign-in enabled and Google client bindings; the existing WP Manager staging auth Worker did not expose Google client bindings. This means the live implementation is newer than the inspected PIN-only repository source. Do not replace or export its credentials to META CORE. Prefer parallel separated central issuer staging, new appropriately registered Google callback and explicit grants.
- **NO-GO:** no live central auth Worker, Google client for new issuer, real customer tenant permission mapping, central remote MCP connection, or WACRM deployed OAuth bearer validation has been certified. Independent GitHub Actions on the separate `aarondash5-star/delulutech` PR reported failures with missing job-step evidence; local Dell success does not clear those failures. Both META CORE PR #215 and WACRM PR #134 remain draft.
- **Release gate:** independent CI + security review, real approved Google sign-in on a separate central staging issuer, WACRM read-only tenant-isolation E2E, rollback, then final owner UI acceptance and separately approved production activation. No verified-live Master event for this source-only increment.

