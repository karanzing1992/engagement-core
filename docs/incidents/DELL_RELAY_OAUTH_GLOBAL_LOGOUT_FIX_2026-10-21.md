# Dell remote-login global logout outage — deployed fix (21 Oct 2026)

**Project:** Moksha Automation / existing Dell private remote viewer; **affected connectors:** Generic SSH Linux (Dell/Mac), potentially other Supabase OAuth MCP integrations. **Ashwakaal:** separate, not affected by a verified channel integration and not a source of authorization.

## Root cause — confirmed evidence
- Supabase `/auth/v1/logout?scope=global` returned 204 at **2026-10-21 06:07:16 UTC** (Linux Firefox) and **15:14:12 UTC** (Android Chrome).
- Immediately after each logout, independently connected MCP OAuth clients received `bad_jwt`, `session_not_found`, then `refresh_token_not_found`, leading to /mcp 401 and failed token renewal.
- Live Edge function `dell-private-relay` version 4 embedded a browser logout handler calling `await sb.auth.signOut()` without scope. Supabase JS defaults to **global** logout. This is an identifiable trigger capable of revoking all user sessions, including ChatGPT integrations.
- Full attribution of each browser click / mobile UI remains unverified; the specific Edge handler is verified defective. No host/SSH crash was demonstrated; the three host workers maintained fresh heartbeats.
- Supabase official behavior: https://supabase.com/docs/guides/auth/signout

## Authorized production change
- Supabase project: `saczglesalubroyaucqe`; existing Edge function `dell-private-relay`.
- **Before:** Edge v4, `verify_jwt=false` (the function performs its existing owner and worker authorization internally).
- **After:** Edge **v5 ACTIVE**, `verify_jwt=false`, bundle SHA256 `0876be74992f73e3ed9db679e02711f2e11d39b6e1f7ff27e169e9dcae0cbe37`.
- A single, strictly scoped text change in the existing browser page:
  - from `await sb.auth.signOut();location.reload()`
  - to `const {error}=await sb.auth.signOut({scope:'local'});if(error){console.error('Local sign-out failed');return;}location.reload()`
- Exact reverse-diff check before deployment passed; full deployed source was read back and confirmed `scope:'local'` present, old unscoped handler absent, and error branch present. No session was signed out deliberately.
- Canonical source restored to source control at `product/gateway/supabase/functions/dell-private-relay/index.ts` in `karanzing1992/engagement-core`, commit `12646fabb3390cef10c38a077a74784186a0d0c2`.
- No SSH config, sudo/root access, host pairing, tokens, owner identities, queued jobs, or standalone services changed. The v4 Edge release remains the recorded rollback reference; do not roll back to the globally destructive logout without deliberate review.

## QA / remaining test gates
- VERIFIED_LIVE: Edge function deployment status/version/source readback. Database read-only heartbeats for `dell-linux`, `mac-linux`, and `pine-manbirs-pc` were fresh (ages 1, 4, 2 seconds at 2026-10-21 ~15:54:44 UTC).
- UNVERIFIED: Interactive browser logout behavior after v5 and end-to-end HTTP route/browser cache, because no authenticated owner session was exercised and external HTTP probe was unavailable.
- UNVERIFIED: Separate `dell-private-login-ui` Vercel deployment code — connected Vercel file listing gave team-scope 403. Inspect for unscoped `signOut()` or direct global logout; avoid redeployment without verified source.
- ChatGPT OAuth sessions revoked **before** v5 require independent owner reauthorization; server patch cannot restore invalid refresh tokens. Do not reconnect or re-pair workers.
- After authorized owner sign-in, perform a bounded browser `Sign out` UI test only after confirming scope and measuring the independent connector status. Never deliberately exercise `scope=global` against the shared owner.
- Open source / reuse / cost: existing Supabase JS API and existing gateway. No new paid services or alternate bridge.

**Rollback:** preserve v5 Git source and live Edge bundle fingerprint; restore v4 only from exact prior Edge release after explicit separate approval, then re-run authentication safety checks. Prefer forward fix over restoring unscoped logout.

**STACK CHANGE:** Production correction to existing Dell private relay; isolate browser logout from ChatGPT OAuth sessions (Edge v5), with remaining Vercel and browser QA explicitly unverified.
