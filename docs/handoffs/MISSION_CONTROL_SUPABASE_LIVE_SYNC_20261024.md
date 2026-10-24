# Mission Control — WordPress OTP → encrypted Supabase replica
Date: 2026-10-24 (Asia/Kolkata)
Status: DEPLOYED; OWNER POSITIVE-SYNC CANARY PENDING

## Verified deployments
- Owner dashboard: https://mokshagoa.com/mission-control/ — WordPress page ID 13376, published, code readback and login shell verified after edit at 2026-10-24 17:20:23 local server time.
- WordPress Engagement Core OTP: WPCode #13375 remains published; GET /wp-json/mission-control/v1/health => {ok:true}; user reports Telegram OTP login worked.
- Supabase project: saczglesalubroyaucqe (existing shared owner-controlled project), ap-south-1; do not touch Andaz PMS backup project.
- Supabase Edge Function: mission-control-backup-v1 v1, status ACTIVE, verify_jwt=false because it introspects an opaque owner WordPress Telegram bearer on each authenticated call.
- Public health: https://saczglesalubroyaucqe.supabase.co/functions/v1/mission-control-backup-v1/health => {ok:true,service:"mission-control-supabase-replica",version:1}; browser GET /status without bearer => session_required.
- Table: public.mission_control_v1_backups, RLS enabled; anon/authenticated SELECT denied, service_role SELECT allowed. No policies intentionally (deny-all ordinary clients). Existing unrelated tables untouched.
- Version-fenced RPC public.mission_control_v1_save_backup is SECURITY INVOKER, and EXECUTE revoked from anon/authenticated/public, allowed to service_role only. Security linter INFO about RLS enabled no policy is expected for this private service-only table.
- Source: engagement-core branch feat/mission-control-telegram-otp-20261024, supabase/functions/mission-control-backup-v1/index.ts and supabase/migrations/20261024_mission_control_v1_encrypted_replica.sql.
- Frontend source: android_gpt_bridge branch feat/mission-control-pin-local-v1-20261024, apps/mission-control/index.html; live WordPress page updated surgically preserving its custom HTML block and page-specific CSS.

## Data flow
1. Owner uses existing private Telegram OTP on the live WordPress dashboard. No OTP sent to Supabase.
2. WordPress short-lived bearer remains memory-only in browser. WordPress /tasks is canonical and encrypts metadata at rest using AES-256-GCM.
3. After every successful WordPress save (and after login), dashboard POSTs /snapshot to the Supabase function with the same short-lived bearer. The browser sends NO task payload to Supabase.
4. Supabase function calls WordPress /tasks to verify bearer and fetch canonical task entries; rejects missing/invalid/expired sessions and other origins.
5. The function encrypts the JSON using AES-GCM before writing the single-row encrypted replica. Key HKDF-derived server-side from Supabase's service-role secret, NEVER exposed in browser/source. Database RPC advances only when incoming version is newer.
6. Supabase failures show "backup pending" and do not roll back or interrupt WordPress primary saves.

## Security caveats and recovery
- Supabase service-role secret is used as key material for encryption of the backup. If rotated, existing replica ciphertext becomes unreadable without the old secret or re-seeding from WordPress. WordPress is the canonical recoverable source. Before service-key rotation, re-seed/re-encrypt or deploy a dedicated versioned encryption secret.
- WordPress bearer temporarily crosses from owner browser to Supabase HTTPS for validation. Limit scripts to trusted site; no sensitive transcripts/passwords/OTP are stored. Task titles, project names, chat links and next-action notes encrypted at rest; keep notes minimal.
- No automatic ChatGPT account-wide project/chat enumeration is available in current Master Plugin skill package. Manual entries and personal conversations.json import remain supported.
- Rollback frontend via prior WordPress page 13376 revision (do not edit OTP snippet to roll back, as PHP updates force user reactivation). Supabase function/table isolated and can remain dormant. No paid spend, plugin toggles, root changes or other site modifications.

## QA done
- [x] OTP WP health GET 200; user confirmed OTP login.
- [x] Unauthenticated WP /tasks rejected.
- [x] Supabase Edge deployed and GET /health returned 200.
- [x] Supabase GET /status without bearer rejected session_required.
- [x] WordPress published page code readback confirms Supabase endpoint, after-login/after-write hooks, and status element.
- [x] SQL/RPC grants and RLS privilege checks verified.
- [x] Private Supabase table initially contains zero backup rows.
- [ ] OWNER POSITIVE-SYNC CANARY: sign in via private Telegram OTP; create ONE synthetic test chat (no private text); verify UI Supabase encrypted backup vN and that one row with matching version/count appears; refresh/relogin verifies WordPress persistence.
- [ ] Confirm browser CORS and Edge /snapshot behavior with a valid bearer during user-driven canary. Do not request PIN or OTP in ChatGPT.
- [ ] Dedicated encryption secret/key rotation plan if replica is promoted to disaster-recovery system.
- [ ] Independent E2E import/status/search/edit/delete UX acceptance test (synthetic sample, no private chats).

## Links
- Live dashboard https://mokshagoa.com/mission-control/
- Frontend draft PR https://github.com/karanzing1992/android_gpt_bridge/pull/16
- OTP/backend draft PR https://github.com/karanzing1992/engagement-core/pull/70
