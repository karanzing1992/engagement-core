# Mission Control Private MCP — staged v0.1.0
**Date:** 2026-10-24 (IST). **Owner:** Harkaran Labana / karanzing1992. **Scope:** Mission Control only.

## Outcomes and classification
- **VERIFIED LIVE (platform control plane):** Supabase Edge Function mission-control-mcp v2 ACTIVE, verify_jwt=false because requests verify the bearer via Supabase Auth /auth/v1/user internally.
- **VERIFIED DATABASE:** public.mission_control_mcp_inbox_v1 created, then encrypted-only constraint applied before any task data was inserted; 0 rows at verification. RLS on, 3 owner-only policies; anon SELECT/INSERT denied. All human-readable project, chat, task and status content must be server-side AES-256-GCM ciphertext (fresh 96-bit nonce, owner+task ID authenticated AAD). Database CHECK disallows plaintext in human-readable columns.
- **SOURCE ONLY:** Private plugin package at plugins/mission-control/, manifest v0.1.0, skill, portable mcp.json; **not yet installed in ChatGPT account**.
- **UNVERIFIED:** End-to-end ChatGPT OAuth discovery, tool invocation, encrypted write/read and mobile UI. Supabase deploy reports ACTIVE, but HTTP health probe could not be reached from this sandbox (outbound network timeout), and no authenticated user token was extracted or used.
- **NOT IMPLEMENTED:** WordPress vault ingest of the Supabase MCP staging inbox. The existing WordPress → encrypted Supabase backup is separately working and must not be confused with MCP inbox sync. No automatic account-wide ChatGPT chat enumeration or native chat URL extraction.

## Installed/owned reuse and open-source/cost gate
1. Reused WordPress mission-control Telegram OTP owner vault and Supabase mission-control-backup-v1 (already live).
2. Reused Supabase project saczglesalubroyaucqe, its existing OAuth issuer and the established wpcontrol-mcp WebStandardStreamableHTTPServerTransport pattern.
3. Reused maintained MIT-licensed @modelcontextprotocol/sdk 1.25.3, Zod 4.1.13 and supabase-js 2.58.0 (pinned), on existing Supabase Edge infrastructure. New glue only: narrow MCP tool registry, owner-isolated staging, AES-GCM per-task encryption.
4. No new subscription or paid purchase. Provider usage remains subject to the owner's existing Supabase plan, quotas and possible metered overages; no claim of unlimited free execution. Attribution/license notices for upstream packages remain under their respective MIT licenses.
5. Fallback/rollback: leave canonical WordPress dashboard untouched. If the MCP has a problem, disable the custom ChatGPT plugin connection; keep stage entries isolated. Preserve Edge v1/v2 source and migrations; do not destroy rows or keys. Service-role key rotation requires re-encryption/migration of staged payloads because the encryption key is HKDF-derived from that existing runtime key.

## Files
- supabase/functions/mission-control-mcp/index.ts
- supabase/migrations/20261024_mission_control_mcp_inbox_v1.sql
- supabase/migrations/20261024_mission_control_mcp_encrypt_only_v1.sql
- plugins/mission-control/plugin.json
- plugins/mission-control/mcp.json
- plugins/mission-control/skills/mission-control-workflow/SKILL.md

## Backend interface
- MCP URL: https://saczglesalubroyaucqe.supabase.co/functions/v1/mission-control-mcp/mcp
- OAuth resource metadata: https://saczglesalubroyaucqe.supabase.co/functions/v1/mission-control-mcp/.well-known/oauth-protected-resource
- WordPress dashboard: https://mokshagoa.com/mission-control/
- Tools: mission_control_connection, mission_control_open_dashboard, mission_control_capture_task, mission_control_list_staged, mission_control_update_staged, mission_control_readiness.
- Five dashboard categories are All (client aggregate), Working, Done, On Ice, Deprecated. Stage stores the four non-aggregate statuses.

## Testing record
- JS parser syntax test (imports stripped): PASS for v1/v2 source.
- Edge deployment: Supabase reports ACTIVE v2.
- RLS SQL query: TRUE; anon select and insert FALSE; policies SELECT/INSERT/UPDATE all owner-scoped.
- Database encryption-only constraint: present, validated; encrypted payload fields present (IV, ciphertext, version); 0 rows.
- Security and performance advisor: no new-table security findings; new indexes flagged unused (expected for empty staging).
- Direct unauthenticated HTTP health/discovery: NOT VERIFIED due sandbox HTTP timeout / web search fetch denial, not an assertion that the endpoint is down.
- Authenticated MCP tool call: NOT RUN; a signed-in owner handshake is required. Never paste an OTP, access token or service_role into a chat.

## Account plugin installation gate (pending)
Current executor workspace is read-only; Plugin Creator requires an actual absolute local ZIP/tar.gz upload. No valid archive could be created, so **no account plugin ID, release ID, or installation is claimed**. Options:
1. On ChatGPT web, Plugins → + → Add custom MCP server, URL above, OAuth; review permissions, Create as a plugin. This is a host UI action performed by the owner (when plan/workspace permits).
2. When a writable workspace is available, archive only the plugins/mission-control/ subtree into one-root archive and call Plugin Creator create_plugin. Preserve canonical private plugin ID after one successful creation; don't create a duplicate if option 1 already succeeded.

## Next verified steps
1. Owner connects the above URL via ChatGPT plugin UI and completes established Supabase OAuth sign-in. Confirm tool discovery displays exactly six tools.
2. Invoke mission_control_connection read-only, mission_control_readiness; negative-check unauthenticated calls and foreign-user RLS access without weakening authentication.
3. Capture **one synthetic task** with an explicitly synthetic ChatGPT title/link empty; read it back and update status. Verify SQL stores ciphertext and plaintext placeholders only.
4. Implement a narrowly authorized WordPress Telegram OTP ingress of staged rows, with conflict-safe merge, idempotency, and positive readback before marking sync connected; no unilateral WP vault overwrite.
5. Update this handover and Master Registry only after release receipts. No auto-import or release-published claim before tests.
