# META CORE Phase 1-E — DeluluTech shared Google sign-in and production security acceptance

Date: 7 November 2026 (IST). Status: DESIGN ONLY, no deployment, no live auth or Meta change.

## Owner clarifications and evidence classification

1. Reuse the existing WACRM Central/Consumer environment as the META CORE integration target. No additional CRM database, webhook authority, or duplicate service.
2. The owner confirmed that the Meta WhatsApp developer app was approved on 7 November 2026. Do not repeat App Review. Engagement Core Phase 1-C and the later production-readiness document still label this OWNER_REPORTED, NOT_PROVIDER_INDEPENDENTLY_VERIFIED. Close the documentation gap by attaching the existing non-secret permission/access receipt and exact Meta test-business/WABA identity, followed by an explicitly authorized non-publishing Graph v26 read-only check. No secrets in GitHub, logs or chat.

## Reuse: WP Manager Cloudflare OAuth

Source inspected in aarondash5-star/delulutech branch production/wp-manager:
- create-projects/wp-manager/authenticated-mcp/cloudflare/native-auth/auth-server.mjs uses the maintained Cloudflare workers-oauth-provider OAuthAuthorizationServer, issuer https://auth.prod.wpmanager.delulutech.in, one WP Manager resource, a username/PIN session and individual OAuth consent.
- resource-server.mjs validates tokens using a Cloudflare Service Binding; requires client ID and user ID, read/write scopes, owner-scoped site access and independent WP administrator write grant.
- dashboard.mjs separates the browser client from the ChatGPT OAuth client; it does not transfer WP grants.
- The inspected WP Manager production-source branch does not establish that Google sign-in is already deployed. Check the actual authorized runtime and any later branches before asserting that it is. Existing WP Manager PR #17 remains draft.

Recommended: reuse this infrastructure with the maintained Cloudflare OAuth provider v1 multi-resource support; add Google OpenID Connect as shared user identity. Proposed eventual issuer https://auth.delulutech.in, **not** yet provisioned or DNS approved. Google issues identity (validate signature, iss, aud, exp, state/nonce and stable sub), while the DeluluTech authorization server issues separate per-resource OAuth access grants. Never use a Google ID token directly to authorize WP Manager, CRM or META CORE.

Each app must have its own exact resource URI, registered client identity, redirect allowlist, permitted scopes and tenant-role bindings. Google login alone grants no product or site rights. Product-owned data and credentials stay separate. WP Manager retains its WordPress site grants, WACRM retains encrypted Meta tokens, CRM retains customer ownership. META CORE validates OAuth identity, client, exact resource audience and tenant/permission, then invokes its existing independent HMAC WACRM Central broker; never exchange browser Google tokens for Meta bearer credentials.

Do not rename or hot-swap the production WP Manager issuer. Prepare a parallel central issuer and migration/rollback plan. Existing WP Manager tokens, sessions and site pairings must remain intact until opt-in consent and client isolation have been independently tested. Google/OAuth browser session cookies must be host-only Secure HttpOnly __Host- with CSRF protections. Require OAuth authorization code with PKCE S256, individual client consent, fixed resource/audience, token revocation and replay protection. No universal cross-product bearer.

Source/standards:
https://github.com/cloudflare/workers-oauth-provider
https://developers.cloudflare.com/agents/model-context-protocol/guides/securing-mcp-server/
https://github.com/cloudflare/workers-oauth-provider/blob/main/docs/authorization-server.md
https://developers.google.com/identity/openid-connect/openid-connect
https://github.com/karanzing1992/engagement-core/blob/main/docs/MCP_OAUTH_REGISTRATION_SOP.md

## Phase 1-E implementation order

A. Freeze currently running WP Manager OAuth/WordPress pairing configuration and review authorized source + version; identify whether a separately approved Google adapter already exists.
B. In an isolated staging Worker, adapt existing WP Manager issuer/consent code for one central Google-login identity, without changing active WP Manager issuer or credentials. Add explicit per-product resource list and independently scoped client and tenant policy.
C. Register META CORE as a read-only OAuth resource and connect the validated tenant context to the existing WACRM signed broker. Reject all mismatched audience/client/owner/tenant/scope calls before any Graph access. Keep default broker/custody flags OFF.
D. Run an independent 2 users × 2 tenants × 2 clients × 2 resources negative test matrix, including forged Google ID token, invalid PKCE/state/nonce, consent CSRF, refresh/revoke, old WP Manager site access and cross-tenant WABA denial. Test permitted read-only templates with a controlled approved test WABA.
E. Complete independent security review and owner UI signoff. No live sends, phone migration, automated messaging or DNS changes until separately approved.

## Point 4 — security review and owner acceptance

Security reviewer must be independent of implementing lane, working from frozen exact META CORE PR #215 and WACRM PR #134 commit SHAs. Use CodeQL/Semgrep Community, npm audit/OSV and PHP security review. Save a dated SHA-linked risk register, repro steps, fix SHAs, retest logs, dependency/license report, credentials-and-PII redaction tests, and the verified WACRM rollback/restore receipt.

P0 focus:
- Dojo pinned SDK declares Zod 3 but the candidate forces Zod 4.6.7. Prefer removing Dojo from the production transport if only the first-party tokenless WACRM Graph-template broker is needed; otherwise independently prove full shipped read-path API compatibility before release. Do not equate npm audit 0 to compatibility.
- Existing generic WACRM Central Crypto historically falls back to Base64 plaintext without OpenSSL; the new Meta vault rejects fallback, but all other callers need a separate compatibility-aware audit.
- Verify exact OAuth issuer/resource/client/owner scopes, HMAC nonce and key rotation, replay/SSRF/misrouting defenses, WABA ownership, tenant isolation, no Meta bearer/token returns, webhook signed delivery and retry/outbox.
- Rehearse database backup/restore and a feature-flag-off rollback on WACRM staging without registering/migrating phones or touching production customer data.

Acceptance condition is independent SECURITY_PASS with zero open P0, followed by an owner-facing single test of Google sign-in → app/client consent → authorized WACRM tenant selection → template read → logout/revocation → denied wrong-tenant access. Owner signs the one-time final UI/release acceptance after reviewing a test report and video. Production deployment and Master VERIFIED_LIVE remain separate approval and post-deploy verification gates.

Existing verified tests: META CORE 39/39 Node; WACRM 101/101 offline PHP and 23/23 disposable WordPress/MySQL with SHA-256 verified first-party Central Crypto. These are synthetic/isolated tests, not actual provider production certification.

Cost: reuse first-party Cloudflare + maintained open-source OAuth/Google OIDC integration and WACRM. No additional paid identity provider, chargeable API request or infrastructure release was authorized.
