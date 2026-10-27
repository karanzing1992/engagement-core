# MCP Connection Registration & OAuth Isolation — Canonical SOP

**Version:** 1.0 | **Effective:** 27 October 2026 | **Owner:** Moksha Master / Engagement Core
**Authority:** This file is the **source of truth** for registering, reconnecting, migrating, or publishing a new *remote HTTP MCP* connection in any participating project.
**Applicability:** WordPress, Generic SSH Linux (Dell/Mac), Manbir SSH, Pine Engineer, and future project-specific MCP servers. Local stdio MCPs need separate transport-specific handling.
**Issue:** https://github.com/karanzing1992/engagement-core/issues/81
**Master policy:** [MASTER_STACK_UPDATE_PROTOCOL.md](MASTER_STACK_UPDATE_PROTOCOL.md)

> **HARD GATE: NEW MCP = this SOP before registration.** A working login page or healthy /health endpoint is insufficient for "connected and isolated." Finish client identity, token authorization, callback, resource ownership, independent connection tests and registry acknowledgement first. Do not mutate an existing plugin ID, worker pairing, site ownership, or production callback without a recorded migration/rollback.

## 1. Why this exists — incident and actual repair

On 27 Oct 2026, three MCP connections (legacy WP Control, Generic SSH Linux, Pine Manbir SSH) used the same Supabase OAuth issuer, with both shared browser entry points forwarding **all** authorizations to a WordPress-only URL (https://mokshagoa.com/wp-control/connect/). Reconnects for SSH therefore landed in the wrong app and browser OAuth state could collide.

**Actual live change** on Supabase project \`saczglesalubroyaucqe\`:
- \`mcp-connection-consent\` **v3**: neutral consent handler with dedicated \`/wordpress\`, \`/linux\`, \`/manbir\`, \`/mcp\` presentation routes and per-authorization-transaction browser state.
- \`wpcontrol-auth\` **v18** and \`owner-oauth-login\` **v6**: legacy callback entry points now redirect to the neutral consent entry, **not** to the WordPress site.
- Github deploy sources: [consent router](../product/gateway/supabase/functions/mcp-connection-consent/index.ts), [wpcontrol-auth](../product/gateway/supabase/functions/wpcontrol-auth/index.ts), [owner-oauth-login](../product/gateway/supabase/functions/owner-oauth-login/index.ts).
- External read-only checks verified four consent URLs and existing WP/Generic Linux/Pine Manbir MCP \`/health\` endpoints. Following owner reconnection, authenticated \`linux_host_status\` reported **Dell and Mac paired, online, all control/operations/development heartbeats fresh**. No SSH commands were needed for that check.
- Existing Supabase issuer and host/site rows were left intact; original separate WP Manager 2.0 connector is **not** a replacement for or duplicate of legacy WP Control.

**Important limitation as of 27 Oct 2026:** a shared issuer is **not** separate authentication infrastructure. The deployed consent UI classifies display routes using verified authorization details *where identifiable*, with a generic route fallback; it does not by itself establish gateway-level client-specific token isolation. There is **no complete 3×3 cross-MCP token rejection certification** or confirmed login/approve/deny/callback end-to-end matrix. These are OPEN gates in issue #81. Do not write FULLY ISOLATED, SECURITY CERTIFIED, or END-TO-END PASS until tested.

**Known-good rollback:** \`wpcontrol-auth\` v17; \`owner-oauth-login\` v5; \`mcp-connection-consent\` v2 (note v2 is an interim route, not the original WordPress flow). Roll back via existing versioned Supabase deployment procedure, keep owners/hosts intact, and recheck every connection. Do not blindly restore the original cross-connector redirect as a permanent fix.

## 2. Identity architecture decision — choose once per connection

**A. Shared identity provider, *distinct* MCP resources (reuse first).**
Use this when one verified owner identity genuinely controls several devices/services. A Supabase **project** has one Auth Site URL and one OAuth authorization path: the common entry must be neutral and determine the requesting registered OAuth client *after* authenticated \`getAuthorizationDetails(authorization_id)\`. Show project-specific consent and scopes. Each resource server **MUST** validate a signed, issuer/audience-bound token and independently enforce the allowed \`client_id\` plus owner, role, site/host and operation permissions. Scopes alone do not isolate Supabase database access.

**B. Separate identity provider / Supabase project.**
Select when different legal tenants, administrators, trust domains, privacy/security requirements, or separate auth settings require hard isolation. Document user-ID mapping and migration before switching; \`auth.uid()\` and existing paired \`owner_user_id\` are not portable between projects. Never migrate, duplicate, or drop device/pairing/booking data on the assumption that copying an MCP endpoint is sufficient. Obtain owner approval before new project creation or production cutover; assess cost.

**Never confuse** separate browser UI routes, separate OAuth client registrations, separate MCP resource servers, and separate token issuers. They solve different problems. Each is an explicit decision in the registration record.

## 3. Required registration sequence — BLOCK if any gate fails

### Gate 0 — Discover/reuse/ownership
1. Locate existing native MCP plugin/app ID, existing gateway, issuer, repo and current deployment. **Update the existing app**, never create a duplicate by default.
2. Reuse the existing certified OAuth/PKCE library, Supabase Auth server and shared consent **adapter** if appropriate. Compare the applicable [MCP Authorization spec](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [Supabase OAuth Server setup](https://supabase.com/docs/guides/auth/oauth-server/getting-started), [OAuth flows](https://supabase.com/docs/guides/auth/oauth-server/oauth-flows), and [OAuth token security](https://supabase.com/docs/guides/auth/oauth-server/token-security). The protocol and vendor docs are references; no unlicensed implementation is copied. No paid resources provisioned by default.
3. Record project/tenant, intended owner, repo, exact MCP endpoint, deployment version, environment (staging/prod), identity-provider choice, existing auth site/path and ownership scope.

### Gate 1 — Explicit client and resource registration
4. Assign a **stable MCP resource URI** and separate resource metadata (\`/.well-known/oauth-protected-resource\` or spec-compliant path); advertise authorized issuer(s) and \`WWW-Authenticate\` resource metadata on 401.
5. Verify issuer discovery metadata, authorization/token endpoints, PKCE S256, exact allowlisted HTTPS redirect URIs, state checking and supported registration approach. Prefer client metadata documents/pre-registration when available; use DCR when the server/ChatGPT integration needs it. Never trust browser-supplied \`service\`, \`client_id\`, \`redirect_uri\` or project names for authorization.
6. Maintain a per-connector **server-side client identity mapping/approved policy**, keyed by the actual registered OAuth client ID or trust-verified client metadata. Dynamic IDs must have a documented bounded onboarding/approval procedure. Use the client identity returned by the authenticated OAuth authorization-detail API, not branding guessed from a substring of a display name.
7. Keep a separate application/tenant owner access policy: legitimate account *and* explicit site/host/role grant. An authenticated user is not automatically authorized across all MCP servers using the issuer.

### Gate 2 — Callback, consent and browser state
8. A **neutral shared consent entry** may dispatch to named presentation routes only after verifying the \`authorization_id\` using authenticated \`getAuthorizationDetails\`. Mask or omit unrelated brands. Unknown/unapproved client => refuse safely, never authorize with a generic fall-through policy.
9. Scope OAuth transaction state, PKCE verifier and return target by browser tab/transaction and issuer; protect state against cross-tab overwrite and replay. Persist only what is needed and only as long as needed. Treat browser localStorage tokens as sensitive and assess XSS/reuse risk; prefer hardened isolation and secure server-side sessions for high-trust connectors. Never expose secrets in query strings, logs, GitHub, Google Docs or UI.
10. Consent presents the **verified client**, exact requested scopes and affected resource, with distinct approve and deny. Approval/denial returns **only** the URL produced by the trusted OAuth authorization server; never assemble arbitrary redirects from user input. Email OTP/password must restore the correct transaction on a newly opened tab.
11. Use the same PKCE/state/callback rules on mobile, private browsing, tab switching and sign-in retries. Do not accept stale \`authorization_id\` or a replayed code.

### Gate 3 — Gateway authorization/security
12. For each request, verify OAuth access token signature/JWKS, issuer, expiry, audience/resource binding, expected \`client_id\`, required verified owner and permission; reject a token from any other connector **even if the same user authenticated**. Fail closed; no unauthenticated shell, site administration, or broad data endpoints.
13. Enforce per-owner row/site/host access in gateway and data layer (Supabase RLS as applicable). Do not authorize from mutable \`user_metadata\`; never expose \`service_role\` keys in browser code.
14. Preserve action-level allowlists, rate limits, auditable job ownership, device worker signature/nonce protections, and site-specific revalidation. OAuth scopes are not a substitute for operation permissions. Validate that malformed bearer tokens do not fall back to another login handler.

### Gate 4 — Non-destructive rollout + mandatory test matrix
15. Record pre-change function versions, manifests, registered client IDs (no secrets), site/host ownership counts, worker heartbeat and rollback reference. Stage and smoke-test the new flow before changing the live Auth Site URL, plugin metadata or issuer.
16. **Per connector:** test OAuth discovery → initiate login → correct branding → password or OTP → consent detail → approve → exact redirect/callback → authenticated READ-ONLY tool → deny → reconnect → expired/stale session. Capture timestamps, user-visible outcome, runtime version and redacted receipts.
17. **3×3 cross-connector token matrix:** for each WP, Generic Linux and Manbir token, attempt a harmless authenticated read on each of the three MCP gateways. Diagonal must succeed **only with proper owner grant**. All six off-diagonal calls must reject, regardless of same user ID. Verify unsigned, expired, wrong-issuer, wrong-audience, wrong-client, wrong-owner and replay cases fail.
18. **Parallel sessions:** start WP+Linux, Linux+Manbir, WP+Manbir, and same-service second login in distinct tabs; ensure transaction IDs, PKCE verifiers and callbacks never cross or overwrite. Verify target branded page and no leaked auth code/token in unrelated redirects.
19. **Worker/system check:** separately confirm Dell and Mac \`linux_host_status\`, all three lane heartbeats, and Manbir authenticated read; for execution capability, only run an explicitly authorized safe task and confirm its terminal receipt. A \`/health\` 200 or worker heartbeat **does not** certify all commands.
20. Rollback test: confirm the previously approved function/manifest can be reinstated without re-pairing or losing access. Keep logs redacted and distinguish \`NOT_RUN\`, \`FAIL\`, \`PASS\`, and \`BLOCKED\`.

### Gate 5 — Publish/register
21. Record the exact **existing** Plugin Creator ID/version, stable MCP URL, OAuth issuer, Auth Site URL and path, registered client identity policy, supported tools, worker/environment, last tested release, security test matrix, open gaps, owner approval and rollback.
22. Commit the source to the owning repo (\`STACK CHANGE:\` for material changes); record source SHA **and** independently verified live deployment receipt. Update plugin **in place** with an explicit release (only if manifest/capabilities changed). A repo commit does not change a running plugin.
23. Write/update the central Master Registry, perform a Docs readback of the unique change marker, and request explicit acknowledgements from consuming projects. An untested connector remains \`PENDING_AUTH_QA\`, not \`CERTIFIED\`. **Do not label an MCP registration complete until Gate 4 has receipts.**

## 4. Mandatory fields in EVERY new MCP intake / change ticket

Copy [MCP Registration Checklist template](templates/MCP_CONNECTION_REGISTRATION_CHECKLIST.md). Required fields:
- Project, tenant, owner, environment, data sensitivity, worker/site identifiers
- Existing plugin ID/version and MCP endpoint, repo/source commit, deployment version
- Supabase project/issuer/Auth Site URL/authorization path, isolation choice A or B
- Stable MCP resource URI, protected-resource metadata URL, exact client registration mode and approved client identity policy
- Client-specific consent route, scopes, PKCE state storage, callback/return URI verification
- Signed-token \`iss\`, \`aud\`, \`exp\`, \`client_id\` and owner/role/site/host enforcement
- Read-only connection tests, cross-client matrix, concurrency/OTP, negative tests, worker readouts
- Release/rollback receipts, Master Registry marker, consumer acknowledgement
- Explicit state: \`DESIGNED → STAGED → ROUTING_VERIFIED → AUTH_VERIFIED → TOKEN_ISOLATION_VERIFIED → LIVE_CERTIFIED\`. Downgrade to \`BLOCKED\` if a critical failure appears.

**Minimal deterministic acceptance criterion:** correct app login + correct authorized worker/site + no cross-app auth or session bleed + reject foreign client tokens + reproducible rollback + source/registry readback. Any missing item = not certified.

## 5. Existing connection roster (snapshot, not an authority for future versions)

| Connector | Auth / connection | Verified on 27 Oct 2026 | Outstanding |
| --- | --- | --- | --- |
| Legacy WP Control | Shared issuer, distinct UI route \`/wordpress\`; old callback \`wpcontrol-auth\` v18 | Consent page and \`wpcontrol-mcp/health\` | End-to-end WordPress login; cross-client rejection |
| Generic SSH Linux (Dell/Mac) | Shared issuer, distinct UI route \`/linux\` | Both workers online, paired, all 6 lane heartbeats via authenticated status; MCP /health | End-to-end OAuth login/reconnect and cross-client rejection; shell execution was not run for this verification |
| Pine Manbir SSH | Shared issuer, distinct UI route \`/manbir\` | Page and MCP /health | Authenticated tool returned internal error; investigate before certification |
| WP Manager 2.0 | Separate pre-existing auth/backend | Existing connector reported authenticated, no selected site | Site selection/live authorization remains a separate issue; do not duplicate app |

## 6. Change control and escalation

A new MCP connection is **not automatically entitled** to reuse a WordPress login, another project's OAuth client, worker owner grant, RLS policy or privileged plugin tools. Enroll it under its own project record and appropriate domain identity. If isolated issuer migration is required, obtain owner approval, preserve pairings via verified identity migration, stage carefully and certify before production switch.

Incident issue #81 tracks the missing authenticated approval/callback and cross-client token tests. Reuse the fixed router as the *presentation baseline* only; do not misrepresent it as a completed authorization-isolation layer.

**Open-source/reuse/cost gate:** existing owned Supabase Auth + deployed shared router + established MCP spec + official Supabase SDK/docs were selected over building another OAuth server or creating new paid infrastructure. New custom work is restricted to exact adapters/verification required by project trust boundaries; new infrastructure requires a separately approved cost/security decision. Backend operating cost is dependent on existing plan usage; no new cost was approved by this SOP.

**Source precedence:** this SOP → project-specific approved implementation + actual live configuration → the Master Registry release receipt → subordinate project instructions. Resolve discrepancies against live verification and formally amend this SOP; never silently fork a different OAuth pattern.
