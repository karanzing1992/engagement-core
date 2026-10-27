# Generic SSH OAuth Consent Emergency Production Release — 27 October 2026

**Owner authorization:** Emergency OAuth remediation + visible one-time email verification code on Generic SSH consent page, explicitly approved in ChatGPT Automation project. The original SSH gateway, Dell/Mac workers and OAuth issuer/token validation were not modified.

**Scope:** Two Edge Functions in Supabase project `saczglesalubroyaucqe`. Exact pre-deployment source obtained from Edge and compared byte-for-byte with canonical Git `main`. Fix tracked as [PR #85](https://github.com/karanzing1992/engagement-core/pull/85). This is a **targeted recovery patch**, not a literal rollback to old binary artifacts: archived `owner-oauth-login` v5 and consent v2 source were not independently available.

## Verified production release

| Function | Previous | Released | Live Edge artifact SHA-256 | Outcome |
|---|---|---|---|---|
| `mcp-connection-consent` | v3 | **v4** | `f49cfcb1da6d40a3c5fac41fd3df4e089113f6992666a56cd15ef911b85118f4` | Active |
| `owner-oauth-login` | v6 | **v7** | `6686fe0ac4236f34099e02ef0601d61e2b67339c9c98f021e8a51e4675e57ed7` | Active |
| `generic-linux-automator` | v10 | **v10 unchanged** | `717858d13a2047de90b8c0bc0047f9d86393b293dece1a55e974c4f67ffb6fbc` | Active |

Changes only:
1. `owner-oauth-login` browser redirect now goes to existing dedicated `mcp-connection-consent/linux` path instead of generic `/mcp`.
2. Consent email sign-in `emailRedirectTo` is derived from its current known route instead of redirecting *every* client through WordPress.
3. One-time code input is **visible by default** in the login section; user can enter a 6–8 digit code, with native `autocomplete=one-time-code`, numeric input mode and explicit Verify email code button. `verifyOtp({email,token,type:'email'})` is unchanged semantically with new local validation.

**Verification evidence:** Exact two single-line source changes initially passed Git parent/diff comparison. Additional UI-only source changes passed embedded JavaScript string parsing, live Edge readback v4/v7, public no-secret HTML selector `#otpbox` showing “Already have a one-time email code? Verify email code”, GET `owner-oauth-login` routing to the actual `/mcp-connection-consent/linux` URL, consent `/health` returning OK and Generic SSH gateway `/health` returning OK. Dell and Mac each retained fresh 3/3 control, operations and development heartbeats at 15:52:45 UTC, no pairing/permission or worker change. The HTML email-code control was independently retrieved from publicly rendered HTML without any OAuth query/OTP values.

**Not yet certified:** Real user-generated email OTP delivery (Supabase email template must include `{{ .Token }}`), actual OTP verification with a fresh authorization transaction, successful approve and callback into ChatGPT, unrelated WordPress and Manbir login regressions, and token cross-app denial matrix. No old authorization ID or code may be reused. Page showing inputs or a healthy worker heartbeat is not the same as working authenticated ChatGPT MCP.

**Restore if needed:** Both pre-release versions are stored unchanged on Git `main` under:
- `product/gateway/supabase/functions/mcp-connection-consent/index.ts` (Edge v3 original; canonical Git blob `e208a263fffb8c66b80c4a6a42bb4afe7337310b`)
- `product/gateway/supabase/functions/owner-oauth-login/index.ts` (Edge v6 original; canonical Git blob `6e07699b19e94bd2c14c43037bb1d1386de3a1d6`)

Redeploy only an approved exact source artifact after comparing SHA-256 and capturing prior version. Do not touch worker pairings, Supabase Auth keys, Generic SSH gateway, or other project integrations. Current PR #85 is source staged, **not merged**; reconcile main source and frozen-source Git baseline only through explicit controlled owner review without silently weakening Generic SSH release freeze. [P0 issue #83](https://github.com/karanzing1992/engagement-core/issues/83) remains open for isolation and CI enforcement.

**Classification:** VERIFIED_LIVE_UI_AND_ROUTE; AUTHENTICATED_E2E_PENDING; SOURCE_RECONCILIATION_PENDING.

## Root-cause correction — HTML moved to dedicated static host, 27 October 2026

**Confirmed root cause:** Supabase's hosted Edge gateway unconditionally rewrites GET `text/html` to `text/plain` on standard `*.supabase.co` domains. Official platform documentation: https://supabase.com/docs/guides/functions/http-methods and https://supabase.com/docs/guides/functions/limits. Thus `mcp-connection-consent` v4 had correct HTML in its source and successful HTTP 200 yet still **displayed raw markup** in normal browsers. Previous claims that successful HTML extraction established a rendered browser UI were inaccurate. Repeated Edge-source redeploys alone cannot fix this platform behavior.

**Emergency production remediation now VERIFIED for rendering and routing:** A **new independent static Vercel project** `generic-ssh-oauth-ui` (`prj_d3PqJxguqfX5vumdwPihm0JjVVkJ`, deployment `dpl_JAmfNZSGBkFFeuy6rVFEZZ8qEBTD`) serves `https://generic-ssh-oauth-ui.vercel.app/linux`. This is an HTML/static client only; it is NOT a second OAuth issuer, Supabase database or SSH runtime. No Git autosync is configured; Vercel Authentication remains restricted to **preview**, because public login pages cannot require pre-existing Vercel accounts. The static page imports pinned Supabase-js, uses the existing project's **publishable-only** key, and has no service-role/worker keys; sends typed email OTP to the existing Supabase Auth API; no extra privileged backend introduced. Request-specific authorization IDs are handled in browser memory/URL and must not be published or reused. Content-security-policy, no-store, no-referrer and no-frame headers set on host.

The existing `owner-oauth-login` Edge Function was patched v7 → **v8** with **one destination change** to `https://generic-ssh-oauth-ui.vercel.app/linux`; live Edge SHA256 `671627d7958a2897b960eaa47a0570478fca748f8996b2c75d7c1b487782a2d6`. Readback of deployed source confirmed v8. Independent no-token GET of `/owner-oauth-login` confirmed final redirect URL `https://generic-ssh-oauth-ui.vercel.app/linux` and rendered title “Generic SSH Linux — Secure Sign In”. Another no-token GET directly to the Vercel alias confirmed HTML rendering even with synthetic invalid query parameters. `mcp-connection-consent` Edge remains **v4** SHA256 `f49cfcb1da6d40a3c5fac41fd3df4e089113f6992666a56cd15ef911b85118f4` (still returns text/plain HTML on the Supabase project domain: this is a historical fallback, not the browser URL). `generic-linux-automator` gateway is unchanged **v10** SHA256 `717858d13a2047de90b8c0bc0047f9d86393b293dece1a55e974c4f67ffb6fbc`. Dell and Mac all 6 SSH transport worker heartbeats remained fresh at 2026-10-27T16:14:31Z. No worker, pairing, root/sudo, DB, Auth issuer, refresh token or other project runtime changes.

**Source and rollback:** Dedicated static UI source template and Vercel headers are pinned in **PR #85** at `product/gateway/browser-ui/generic-ssh-oauth-ui/`; template omits publishable key value, which is supplied only during deployment. The `owner-oauth-login` source in PR #85 is reconciled byte-for-byte with deployed v8. The immutable pre-emergency v7 source remains on Git `main`, but routing back to it will re-expose the platform raw-HTML defect; prefer a verified alternate HTML-capable host for rollback. Git PR remains unmerged due owner source freeze, and new frontend is not auto-deployed from other projects.

**Residual required user QA:** User MUST reconnect existing Generic SSH app to start a *new* authorization; old pasted `/mcp-connection-consent/mcp?authorization_id=…&code=…` URL is a Supabase plaintext endpoint and cannot be repaired or safely reused. Verify actual OTP delivery (email template must include numeric token), typed OTP success, authorization consent, redirect into ChatGPT and authenticated `linux_host_status` plus short read-only 6-lane checks. Until this happens classify as **VERIFIED_LIVE_HTML_AND_REDIRECT, AUTHENTICATED_E2E_PENDING**. Other projects' `wpcontrol-auth` and `manbir` consent UI still use the Supabase Edge hostname and may have the same raw-HTML restriction; do not silently redirect them to Generic SSH's page. No extra spend was incurred for Vercel project creation.
