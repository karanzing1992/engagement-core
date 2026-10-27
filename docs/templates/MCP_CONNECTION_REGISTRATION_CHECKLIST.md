# MCP registration / reconnection intake and QA checklist

**Canonical mandatory SOP:** [MCP_OAUTH_REGISTRATION_SOP.md](../MCP_OAUTH_REGISTRATION_SOP.md)

> Make one filled copy per MCP endpoint, each connector/client identity and each environment. Do not store passwords, device codes, OAuth authorization codes, raw bearer tokens, service-role keys or guest data here.

## A. Ownership and reuse (Gate 0)

- [ ] Existing connector/plugin inspected; no duplicate plugin or unapproved new backend
- [ ] Official MCP/Supabase docs and approved existing implementation reviewed, license/cost decision recorded
- **Project / tenant / owner:**
- **Environment / data classification:**
- **Existing Plugin Creator app/native plugin ID + version:**
- **Repository / source full commit SHA:**
- **Current live deployment / Gateway Edge Function versions:**
- **MCP server endpoint:**
- **Site(s) / host worker(s) owner-scoped IDs (non-secret):**
- **New external service costs:** none / owner-approved, with rationale

## B. OAuth topology and registration (Gates 1–2)

- [ ] Shared-issuer mode A vs isolated-issuer mode B explicitly selected
- [ ] If migrating issuers, user identity and pairing migration approved and verified
- **Supabase project (if used) / issuer URL:**
- **Auth Site URL + authorization path:**
- **MCP canonical resource URI / resource metadata URL:**
- **OAuth discovery proof / issuer metadata:**
- **Registration:** pre-registered / metadata document / DCR
- **Approved client ID(s) or verified DCR policy (non-secret):**
- **Client-specific consent route / visible name:**
- **Exact redirect URIs and PKCE S256 support:**
- [ ] `authorization_id` verified by trusted Auth API, not freeform query routing
- [ ] Sign-in and OTP return preserves transaction; state/PKCE/replay tests
- [ ] Correct scopes and explicit approve/deny; server-provided redirect only
- [ ] Browser tab/session safety reviewed (storage, CSP, token handling)

## C. MCP and backend security (Gate 3)

- [ ] Signed token verified: signature/JWKS, issuer, audience/resource, expiration
- [ ] Allowed verified `client_id` or approved policy enforced server-side
- [ ] Owner/role/tenant/site/host permission checked independently of OAuth scope
- [ ] Unauthorized other-plugin clients rejected; no anonymous privilege fallback
- [ ] Protected-resource discovery and `WWW-Authenticate` response verified
- [ ] RLS and service-role secret separation verified (if Supabase)
- [ ] Device/shell/site operation-level allowlist and audit preserved

## D. Test matrix (Gate 4)

| Test | Evidence link/redacted receipt | PASS/FAIL/NOT_RUN |
| --- | --- | --- |
| OAuth discovery / pre-auth 401 | | |
| Correct project consent/brand | | |
| Password or email OTP login | | |
| Approval and callback | | |
| Denial and reconnect | | |
| Valid *own-client* read-only tool | | |
| WP token => Linux gateway denied | | |
| WP token => Manbir gateway denied | | |
| Linux token => WP gateway denied | | |
| Linux token => Manbir gateway denied | | |
| Manbir token => WP gateway denied | | |
| Manbir token => Linux gateway denied | | |
| Wrong owner / issuer / audience / expired token denied | | |
| Concurrent tabs and state/PKCE replay denied | | |
| Dell and Mac host/lane heartbeat (where applicable) | | |
| Manbir authenticated status (where applicable) | | |
| Rollback non-destructive rehearsal | | |

- **Certifying reviewer / UTC date:**
- **Residual risks / linked issue:**
- **Worker execution receipt:** NOT_RUN unless explicitly authorized and actually tested

## E. Publish and registry (Gate 5)

- [ ] Old manifest/runtime/backup/rollback versions recorded
- [ ] Actual deployed version/source commit verified independently
- [ ] Existing plugin ID preserved; release updated if necessary
- [ ] Master Doc record written and read back, unique marker:
- [ ] Other consuming projects explicitly ACKed their version
- **Acceptance state (choose one):** DESIGNED / STAGED / ROUTING_VERIFIED / AUTH_VERIFIED / TOKEN_ISOLATION_VERIFIED / LIVE_CERTIFIED / BLOCKED
- **Go/no-go:** Only LIVE_CERTIFIED with all required proof allows a claim of full MCP OAuth isolation.
