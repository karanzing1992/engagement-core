# Generic Linux SSH OAuth resilience — 21 Oct 2026

Source of truth for staged 1.0.1 patch copied from deployed Supabase Edge Function 1.0.0. Scope: existing Supabase project `saczglesalubroyaucqe`, Edge `generic-linux-automator`, owner-only MCP, Dell and Mac outbound workers.

## Incident / evidence
2026-10-21 05:58–06:03 UTC: /mcp POST HTTP 200. At 06:12–06:13 UTC: six /mcp POST HTTP 401; /auth/v1/oauth/token refresh failed “Invalid Refresh Token: Refresh Token Not Found”. The MCP client supplies and refreshes tokens; Edge Function only validates /auth/v1/user + enabled owner membership. A refreshed / reconnected ChatGPT plugin restored Dell and Mac host status, read-only probes and shell receipts (exit 0) at about 07:26 UTC. Why the refresh credential became invalid is NOT observable and should not be guessed. Dell/Mac polling and pairings were not the fault.

## Patch 1.0.1
- RFC 6750 `WWW-Authenticate: Bearer error="invalid_token"` and OAuth protected-resource discovery for rejected bearer; tells host it must reauthorize. No fallback PIN, worker token, or unauthenticated API.
- 6-second deadline to Supabase `/auth/v1/user`. Transient Auth 429/5xx/timeouts and database membership lookup errors yield 503 + Retry-After, *not* false “invalid login” 401.
- Owner role, worker credentials, pairings, shell dual gate, existing API/tool names and payload contracts unchanged.
- Task receipt adds strictly read-only `stale_running` boolean; never resubmit a possibly executed command.
- Source does not handle refresh tokens or store access credentials. A revoked client refresh token requires owner re-consent, which no server-side repair can bypass.

## Acceptance / rollout
- Static source assertions and PR review; TypeScript/ Deno validation if available; no invalid_token as permissive role bypass.
- After deployment read GET /health to verify version, probe missing auth 401 with OAuth challenge, and verify authenticated linux_host_status, linux_probe + completed linux_task_status for both hosts.
- Auth transient branch needs isolated/controlled mock; **never** induce a live Supabase Auth outage.
- Keep existing previous Edge version as rollback; if auth breaks, redeploy exact previously exported function source with verify_jwt=false (existing function validates credentials internally).
- No auto re-pair, credential rotation, worker restart, or stale queue mutation.
- No mass reauthorization or repeated OTP mail; ask user to reconnect only after an actual 401 invalid_token.
