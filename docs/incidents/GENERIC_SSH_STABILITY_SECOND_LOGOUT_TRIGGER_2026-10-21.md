# Generic SSH stability deep-dive — 21 October 2026

## Production condition
Dell and Mac ChatGPT Generic SSH Linux connections restored after independent owner OAuth reauthorization. Production Edge `dell-private-relay` v5 fixes its own unscoped logout. Production `generic-linux-automator` Edge v5 is ACTIVE (unchanged). No root permission, host pairing, worker token, service, or shell-gate configuration changed in this audit.

## New critical issue found, NOT DEPLOYED
The independent production HTML at `https://dell-private-login-ui.vercel.app/` (GET HTTP 200 on 2026-10-21 16:09 UTC) embeds a separate `sb.auth.signOut()` in the **register trusted device** completion handler. Exact verified context (sanitized):
`const r=await call('/register',{pin,jwk},auth);await dbKey('write',pair.privateKey);localStorage.setItem('dell-device-id',r.device_id);$('newpin').value='';await sb.auth.signOut();init();status('Device registered. Enter your PIN to unlock.')`
This is a second independently verified global-logout trigger. Supabase signOut defaults to global scope; registering a trusted device can revoke other Supabase OAuth logins including MCP connector sessions. This precise call MUST be replaced with **`sb.auth.signOut({scope:'local'})`** with bounded error handling and suitable UI semantics. Do not inadvertently log out unrelated sessions. Preserve all PIN enrollment, cryptographic key, trusted-device verification, and authorization logic. Review all other signout/logout calls in served JS and bundles, not only the HTML.

**Access blocker:** Vercel connected tool for team `team_G2LgmXaagvfHMBPaHvcoem4z` and existing project `prj_tVBQSoZ2c8LR9U4czF0BN07NMjEH` returned **403 forbidden / missing team grant** at 2026-10-21 16:10 UTC. Dell host `generic-auto-exec` has no Vercel CLI installed/connected. Do NOT deploy a duplicate frontend or change team/project/account. Owner must grant Vercel app access to target existing team; then patch existing production project, verify published HTML, and regression test owner session isolation.

## Live host and transport findings
- Dell `karan-Inspiron-5379` and Mac `KARAN`: existing `generic-linux-automator` systemd service active + enabled, Restart=always, RestartSec=10 seconds, NRestarts=0 on both current service instances, time synchronization yes, Wi-Fi connected with default route and Supabase DNS resolving, and no captured service error matches in the last two hours.
- Worker Python file SHA256 `45f4e1770d5a70ecc724808cf6d9fff3ec1f5584741037a18bd923ec20102b43` on Dell; Mac source length matched (11922 bytes); full identical hash on Mac not separately checked.
- Existing worker is Python stdlib, uses HTTPS request timeout 25s, 5s polling, exponential jittered backoff up to ~60-62s, journaling for claimed jobs, private key/shell strict checks. No evidence of local service instability; do not blindly overwrite working reliability logic.
- Gateway verifies owner via Supabase `/auth/v1/user` and issues standards-oriented `WWW-Authenticate: Bearer ... invalid_token`; ChatGPT client is responsible for refreshing and reauthorizing. Current gateway does not attempt insecure refresh by worker token, which is appropriate.
- Supabase Auth session count at 2026-10-21 16:08 UTC: 2 active sessions, 2 refresh-token rows, 1 OAuth-owned session; reconnection has recovered some valid sessions.
- Historical Supabase global logout calls immediately preceded `bad_jwt`, `session_not_found`, `refresh_token_not_found` and failed MCP requests. Upstream OAuth error recovery on invalid refresh token is outside the host worker control. Never solve by weakening OAuth verification, granting permanent bearer tokens, or sharing credentials.

## Smoke tests
- Dell and Mac direct `linux_host_status` PASS, paired=true, online=true, shell enabled.
- Authenticated end-to-end SSH `linux_ssh_run` diagnostic (both hosts), receipts exit code 0, no errors.
- Additional two consecutive `linux_probe` checks on each host: ALL FOUR completed, exit_code=0, no stderr, correct shell identity and host.
  - Dell probe receipts `c30f39ac-dc40-44e4-b305-e71f64d4e080`, `61fb3a4e-b211-41ad-8ac1-abffe621e38e`.
  - Mac probe receipts `7b12ecea-b284-4064-b56e-ddc13a6057dd`, `a9bd8ee1-e9b8-4984-9da5-9c0186723e2e`.
- These are finite, short tests; they do NOT validate 24h operation, link loss/recovery, OAuth expiry rollover, or PIN enrollment/regression.

## Safe completion criteria (not yet met)
1. Get Vercel team grant; verify live source for existing PIN project and preserve deployment rollback.
2. Patch **all** unscoped/global browser logouts in existing frontend only; deploy staged/prod via approved path.
3. Inspect live published output; assert no unscoped `signOut()` remains. Test trusted-device registration with separate authenticated owner MCP connection still working.
4. Repeat Dell/Mac authenticated end-to-end probes across normal token refresh and controlled link interruption; record independent OAuth session survival.
5. Observe 24h session health via existing monitoring if available; no claim of permanent zero downtime from short smoke tests.

## External references
- https://supabase.com/docs/guides/auth/signout
- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- https://github.com/supabase/auth/issues/2829

**STACK CHANGE:** verified stability incident finding and smoke test evidence; source-only documentation, Vercel frontend production security fix BLOCKED by account permissions, no new deployment.

## PRODUCTION REMEDIATION VERIFIED — 21 Oct 2026, 16:35 UTC

- The authorized Vercel connection can operate in its default account scope on **the exact existing project** `prj_tVBQSoZ2c8LR9U4czF0BN07NMjEH`. Explicitly passing teamId produced 403 while omitting it returned the same project and production deployment, verified by immutable project ID. This was a connector scope-routing problem, not an inaccessible project.
- Preserved baseline production deployment `dpl_JCYfdrLiESnskbdpVNBcz4shFoJc` for rollback; published `dpl_7wF7mrwcUFCa7wdP1YA6vw3iZhx3`, `READY`, `target=production`, original production domains assigned.
- Original live source 13976 bytes, SHA1 `5e30b8db9c3e93ed7fad784e282208b278ab3ab1`, SHA256 `9c29f04701a2d8587f99e1ec60e9252d2fe4f43a2cee0c03b2e313cfdcb14e99`.
- Source of new release: `integrations/dell-private-login-ui/src/index.html`, Git commit `439fbd707dd20763264865d421abebc7024bb33b`. ONE intentional replacement in trusted device registration:
  - Before: `await sb.auth.signOut();init();`
  - After: `const localSignOut=await sb.auth.signOut({scope:'local'});if(localSignOut.error)throw new Error('Local sign-out failed');init();`
- Staged production-ready preview `dpl_4dy21yBoW7nXVWyWqSCjjkNE7res` passed READY and file tree verification. An earlier preview generated an incorrect nested `src/src/index.html` due to Vercel's existing root directory `src`; it was not published. Correct deployment file parameter is `index.html` and Vercel yields `src/index.html`.
- Production file SHA1 `e2e17b0d446ac335a475662ddf3f5d29ca595e0a`, verified by Vercel deployment file UID and independently over HTTP 200 from **both** Dell and Mac via `https://dell-private-login-ui.vercel.app/`. No unscoped signOut remains on that page, no explicit global scope, page title/PIN onboarding retained. Node ESM syntax check passed (exit code 0). Supabase relay `dell-private-relay` remains v5 with its earlier local logout fix.
- Postrelease end-to-end ChatGPT Linux SSH: Dell identity probe `a353478e-4414-41fc-a2b1-c9dd6c03d934` and shell receipt `d8670736-dc49-43ec-8e27-fb27f124b86c`; Mac identity probe `3502623f-3f47-4857-ad1d-ce3165e7d000` and shell receipt `cc6667ce-f92e-4384-b825-37a35c62a879`. **All four completed exit_code=0**, stderr empty, worker active and enabled.
- No host root/sudo permissions, device pairing, worker credentials, other services, or customer data modified. No extra paid service or replacement bridge.
- NOT YET VALIDATED: a live PIN enrollment flow with a separate concurrently active OAuth session and >24-hour uptime/refresh/reconnect behavior. Smoke tests and static source/readbacks cannot guarantee permanent zero outages. Continue only with explicit controlled tests and keep authorized owner permissions isolated.
- Rollback: Vercel previously live production deployment `dpl_JCYfdrLiESnskbdpVNBcz4shFoJc`; **it contains the flawed unscoped logout and must not be restored without emergency and follow-up patch**. Preferred recovery is forward fix.
- **STACK CHANGE: VERIFIED_LIVE** existing Vercel frontend production session isolation fix. 
