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
