# MCP Connection Caution — READ BEFORE ADDING OR RECONNECTING A PLUGIN

> **MANDATORY CROSS-PROJECT SAFETY NOTICE** — applies to every new remote MCP connection, reauthorization, plugin migration, auth callback change, issuer change, device pairing, and reconnection. **Read this before touching a running connector.**
>
> **Status:** policy/source document; this README does *not* by itself change OAuth settings, publish a plugin, or certify a connection.

**Canonical SOP:** [MCP OAuth Registration & Isolation SOP](docs/MCP_OAUTH_REGISTRATION_SOP.md)  
**Required intake & independent QA:** [MCP Connection Registration Checklist](docs/templates/MCP_CONNECTION_REGISTRATION_CHECKLIST.md)  
**Central Master protocol:** [Master Stack Update Protocol](docs/MASTER_STACK_UPDATE_PROTOCOL.md)  
**Prior incident / open certification:** [engagement-core issue #81](https://github.com/karanzing1992/engagement-core/issues/81)

## STOP — do not proceed when

1. **You cannot identify the correct project, tenant, owner, connector/plugin ID, MCP endpoint, OAuth issuer, and registered client.** Search the existing plugin and repo first; never create a duplicate to sidestep broken login.
2. **A login/consent page has another project's branding or domain.** Stop and check the Auth Site URL, OAuth authorization path, server-side OAuth client identity, and callback routing. Never let an SSH connector authorize through a WordPress-only consent page.
3. **The design relies on app-name text, browser query parameters, email, or untrusted metadata to decide authorization.** Display routing must use authenticated authorization-detail data. The MCP gateway must independently validate signed tokens and server-side client permissions. Do not trust a `?service=` or `?client_id=` selector.
4. **The same OAuth issuer is being used without a documented sharing decision.** A shared issuer is *permitted only* with deliberate owner/tenant boundaries, validated `client_id`, issuer/audience/resource checks, and per-host/site/action authorization. Different-looking login pages are **not** token isolation. Separate issuer when trust or ownership boundaries require it.
5. **You intend to replace the issuer or Supabase project without mapping the old user and pairings.** A new user UUID can orphan Dell/Mac/Manbir host ownership or WordPress site pairing. Snapshot non-secret IDs, grants, heartbeat, versions and rollback first; migration needs approval and staging.
6. **The OAuth redirect is not an exact allowlisted HTTPS callback; the state/PKCE flow is ambiguous; or simultaneous tabs overwrite each other.** Require authorization-code+PKCE S256, state verification, replay protection and a server-provided approval/deny redirect. Test password and email OTP returns.
7. **Authentication is mistaken for authorization.** Valid user login, a `/health` response, or a fresh worker heartbeat does **not** grant shell, admin, booking, payments, files or another project's data. Authorize each resource, role, tenant, site, host, lane and operation separately. Fail closed.
8. **A bearer token from one plugin is accepted by an unrelated plugin.** This is a release blocker even for the same signed-in user. Each gateway must enforce its allowed verified `client_id`, issuer, audience/resource, expiration, token signature, and owner grant. Test the cross-client denial matrix.
9. **Secrets or personal data would appear in Git, a README, an issue, tool output, browser URL/logs, screenshots or Master Registry.** Never publish OAuth codes, bearer/refresh tokens, passwords, service-role keys, device PINs, customer records or worker signing secrets. Store secrets only via approved protected configuration.
10. **Only positive or cosmetic checks passed.** A correct branded page, HTTP 200 and paired host are useful *partial* results, not end-to-end authorization certification. Test discovery, login, approve, deny, callback, real read-only MCP call, concurrency, invalid/expired/foreign token rejection and rollback.
11. **A plugin/app is recreated instead of updated in place.** Preserve plugin ID, stable endpoint, owner connection and existing worker pairing unless an explicitly approved migration is independently verified. Source commit, Supabase function deployment, installed plugin release and active ChatGPT Project instructions are different artifacts and do not hot-reload one another.
12. **An agent claims a fix across every project solely because this README exists.** Propagation requires confirmed source in each participating repository, plugin release when skill content changed, project/worker adoption and independent acknowledgement. Use precise `SOURCE_ONLY`, `ROUTING_VERIFIED`, `AUTH_VERIFIED`, `TOKEN_ISOLATION_VERIFIED`, `LIVE_CERTIFIED` or `BLOCKED` labels.

## Mandatory registration workflow

1. **Inventory** existing plugin ID/version, registered OAuth client/resource/issuer, Auth Site URL, callback, host/site grants, code repository, deployment and owner.
2. **Decide isolation**: shared identity provider with distinct, enforced client/resource permissions **or** fully separate issuer and identity migration. Document the reason.
3. **Fill the official [registration checklist](docs/templates/MCP_CONNECTION_REGISTRATION_CHECKLIST.md)** and link it in the owning project issue or change record.
4. **Stage without disruption**: preserve backups/rollback and existing paired devices or sites. Prefer the approved existing MCP/Supabase/Auth patterns. No new paid service or project without authorization.
5. **Independently test** correct consent route and client identity, PKCE/state, sign-in and approval/deny, return callback and authenticated *read-only* tool, 3×3 foreign-token denial when multiple clients share an issuer, and host/site authorization. No destructive test without owner approval.
6. **Publish + reconcile** source SHA, deployed function/version, retained plugin ID/release, security test receipts and Master Registry readback. Consumer ACK is required before claiming a cross-project rollout.
7. **On any failure** stop the connection change, keep existing workers running where safe, and follow the documented rollback; do not defeat a safety gate by weakening token validation or switching to anonymous access.

## Incident lesson — 27 October 2026

Legacy WP Control, Generic SSH Linux (Dell/Mac), and Pine Manbir SSH used a shared Supabase OAuth issuer and a WordPress-specific entry page. The fix introduced a neutral consent route with distinct presentation paths and updated legacy redirects. Read-only public routing and health checks passed; Dell and Mac also returned fresh **authenticated** paired worker/three-lane status after reconnection. This **does not prove** the three gateways reject each other's OAuth client tokens. That cross-gateway security test and Manbir authenticated-flow certification remain open in [issue #81](https://github.com/karanzing1992/engagement-core/issues/81).

**Important:** This README is a caution gate, not a copy/paste permission to reuse the same OAuth issuer for unrelated tenants.

## Ownership and precedence

**Canonical document (do not fork):** [engagement-core/MCP_CONNECTION_CAUTION_README.md](https://github.com/karanzing1992/engagement-core/blob/main/MCP_CONNECTION_CAUTION_README.md). Individual projects should link to it and the SOP; project-specific extensions are allowed only if they tighten security and record distinct resource/issuer/owner policy. Exact runtime configuration and verified receipts override stale descriptions, and discrepancies require a reviewed SOP update.

**When in doubt:** **STOP registration; preserve existing connectivity; review the canonical SOP and issue #81.** No live MCP connection is certified without independent resource authorization QA.
