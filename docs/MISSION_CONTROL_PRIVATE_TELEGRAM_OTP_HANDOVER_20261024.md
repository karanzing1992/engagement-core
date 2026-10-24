# Mission Control — private Telegram OTP handover (24 October 2026)

## Verified reuse and security boundary

- Existing owner-private notification transport: [PRIVATE_TELEGRAM_TASK_NOTIFICATIONS.md](PRIVATE_TELEGRAM_TASK_NOTIFICATIONS.md), WPCode snippet #13358, signed Dell worker dispatch. This sends completion/failure notices; it is **not** an OTP login service.
- Existing owner-paired private Telegram DM uses WordPress option `grec_booking_private_telegram_chat` and encrypted `GREC_Telegram::credentials()`. Original paid-booking snippet #13126 remains untouched.
- Existing Dell `dell-pin-auth` Edge Function handles device-specific PIN + challenge and lockout. It is **not** repurposed for Mission Control and no device secrets or keys are copied.
- New code reuses only the trusted recipient and bot-credential adapter, not the signed task-notification event endpoint. No groups, broadcasts, arbitrary recipient input or extra bot.

## New source and approval state

`integrations/private-auth/mission-control-telegram-otp.php` is a standalone, fixed-function, WordPress/Engagement Core REST module. It defines:

| Route | Method | Authorization | Behavior |
| --- | --- | --- | --- |
| `/wp-json/mission-control/v1/health` | GET | Public | Static service/version only |
| `/wp-json/mission-control/v1/otp/start` | POST | Exact GitHub Pages Origin; global/IP budgets | Generates 6-digit code and sends solely to paired owner DM |
| `/wp-json/mission-control/v1/otp/verify` | POST | Origin, attempt budgets, challenge | Five-minute one-time verification, short bearer session |
| `/wp-json/mission-control/v1/logout` | POST | Owner session | Session revocation |
| `/wp-json/mission-control/v1/tasks` | GET/PUT | Owner session | Encrypted task metadata, revision checking, allowed statuses |

OTP source uses `random_int`, server-side HMAC keyed with WordPress `wp_salt`, one-time random challenge IDs, 5-minute expiry, short-lived 20-minute session tokens, exact private-recipient Telegram receipt checking, strict Origin check and bounded send/verify budgets. Authenticated task metadata uses AES-256-GCM with a key derived from WordPress salts. Public client **never** embeds a PIN, token, Telegram chat ID or bot secret. Storing or exposing full conversation transcripts is out of scope.

**Important limits:** Public `/otp/start` is inherently callable from outside a browser with a spoofed Origin; its global budget limits abuse but cannot prevent all denial-of-service. Deployment should add operator alerts and negative abuse tests. WordPress salt rotation may invalidate at-rest task ciphertext, so establish encrypted backup/restore before live data import. Simultaneous writers are serialized through a bounded mutex plus version check. No generic customer data or payment records are touched.

## Frontend and ChatGPT integration

The frontend source is on [android_gpt_bridge draft PR #16](https://github.com/karanzing1992/android_gpt_bridge/pull/16). It currently provides locally encrypted task metadata, project/chat drill-down, status filters, manual editing, ChatGPT JSON import and original chat deep links. The frontend now has the Telegram OTP adapter and authenticates through this endpoint for task GET/PUT. Its JavaScript syntax has been checked. Browser/network behavior remains unverified until the backend is enabled and Pages is available. The existing `moksha-master-stack-reinforced` private v1.4.1 plugin is skills-only; it cannot enumerate all ChatGPT account histories. Extending its capabilities needs an authorized task-index MCP endpoint and a same-plugin release, not merely a new Skill description.

## Release gates (must pass before activation)

1. **CI:** PHP syntax on supported runtimes plus `tests/mission-control-otp-smoke.php`, all green; static review for input validation, replay, rate limits, SSRF, XSS and CORS.
2. **Site backup and compatibility:** Confirm the live Engagement Core/WordPress version, active paired DM, current WPCode snippet #13126/#13358 and an independently recoverable WPCode rollback. Current WP Manager readback reports Engagement Core 0.9.17 and `rollback_available:false` for the *engine*; this new isolated snippet must have its own rollback plan.
3. **Staging:** Install as an **inactive** snippet on a suitable staging site after reviewing source and stripping the opening `<?php` tag. Mock Telegram delivery; test invalid Origin, rate limits, expired/replayed OTP, group rejection, authorization, encrypted task CRUD, network timeout non-retry and recovery.
4. **Production canary (separately owner-approved):** Activate only the new snippet. Send **one** OTP to the paired private DM with owner confirmation and verify real recipient/message receipt; send none to enabled Telegram groups. Preserve paid-booking and task notification handlers; verify no regressions.
5. **Frontend:** Connect the browser UI to the protected backend, check mobile display and authenticated persistence, then publish a GitHub Pages static shell. Remember ordinary GitHub Pages content is public even when repo private.
6. **Plugin:** Add typed task registry tools through an authorized existing OAuth route, update the **same** private Master plugin after source review, refresh tool discovery and test from the ChatGPT client. Account-wide automatic chat enumeration remains blocked absent a provider-supported grant; owner-export import is the interim source.
7. **Master registry:** Only sync a verified default-branch commit and separately verified live/platform changes. Draft PR is SOURCE_ONLY.

## Open Source / Reuse / Cost Gate

Reuse: existing Engagement Core Telegram credential adapter and paired DM, WordPress REST/transients/options, PHP Sodium/HMAC/OpenSSL, existing GitHub Pages SPA and CI. No third-party package and no new bot. Custom code is limited to the missing owner OTP challenge/verify, session and encrypted task metadata contract. Source test environment is mocked, no real messages. New software charges: none; existing WordPress hosting and Telegram service have ordinary operational/network costs. Rollback: disable only the new module/snippet; existing paid-booking and BHM notification snippets remain enabled and unmodified.

## Current state — source and activation separated

- **Backend CI GREEN:** [PHP checks run #40079703371](https://github.com/karanzing1992/engagement-core/actions/runs/40079703371) passed PHP 7.4/8.1/8.3 syntax and isolated OTP negative-case smoke tests. The previous red run was fixed by closing one assertion parenthesis.
- **WordPress module VERIFIED LIVE (health only):** Owner reviewed and approved WPVibe operation `op_305529ca84394258` and then enabled WPCode **#13375**. A read-only WordPress CLI readback confirms `post_status:publish`, and `GET /wp-json/mission-control/v1/health` through the connected site's REST adapter returns `ok:true`, service `mission-control-owner-otp`, version `0.1.0`. An authenticated connector request to `GET /tasks` without the exact Pages Origin was denied `403 origin_denied` (expected negative result). [WPCode entry](https://mokshagoa.com/wp-admin/admin.php?page=wpcode-snippet-manager&snippet_id=13375). This is NOT a passed OTP send/verify canary.
- **Frontend staged:** [android_gpt_bridge draft PR #16](https://github.com/karanzing1992/android_gpt_bridge/pull/16) now defaults to Telegram OTP and retains offline PIN fallback. The isolated `.github/workflows/mission-control-pages.yml` publishes only the HTML shell. No site is published; the private repository reports `has_pages:false` and Pages must be enabled with GitHub Actions source.
- **Telegram canary PENDING:** No live OTP message or recipient receipt verified yet. Existing paid bookings, signed private notifications and enabled publishing destinations have not been altered.
- **Master plugin PENDING:** Current installed private `moksha-master-stack-reinforced` v1.4.1 is skills-only and cannot enumerate account-wide private chats. Plugin Creator archive update requires an actual writable package; this execution profile denied local writes. A source-only skill/spec may be prepared, but do not claim a plugin release or direct MCP tools.
- No Supabase Edge Function, device permissions, Telegram groups, plugin release or GitHub Pages production configuration changed.

**Next owner action:** Resolve GitHub Pages on the private repository (browser must use `karanzing1992`, and private Pages may require an eligible GitHub plan); then perform ONE owner-confirmed private Telegram OTP canary from the actual allowed browser origin. Keep task sync and public shell behind the end-to-end test gate.

## Hosting decision update — 24 October 2026

Owner switched from GitHub Pages to Cloudflare Workers static assets. The private dashboard repo now stages `apps/mission-control/wrangler.jsonc` and a manual `.github/workflows/mission-control-cloudflare.yml`, with only `index.html` in the public asset artifact. **No deployment:** Cloudflare's login flow was not completed and no exact hostname was verified. Consequently the active WPCode #13375 still restricts requests to `https://karanzing1992.github.io`; do not claim Cloudflare-origin OTP works. Once the actual Cloudflare URL is confirmed, review/edit the exact origin (never wildcard), re-enable if WordPress disables the edited snippet, prove a no-Origin negative test and one private-owner Telegram OTP canary, and then perform authenticated tasks GET/PUT and mobile QA. GitHub Pages remains disabled; no need to upgrade plans.

## WordPress-hosted launch checkpoint — 24 October 2026

Owner approved switching the frontend from Cloudflare/GitHub Pages to existing Moksha WordPress, with Supabase as the intended future task-data service. Supabase's official Edge Functions and Storage documentation confirms that HTML on free shared project domains is returned as `text/plain`; no HTML-hosting workaround, new paid plan or Cloudflare deployment was attempted.

**VERIFIED LIVE frontend:** WordPress page **#13376** at `https://mokshagoa.com/mission-control/` is published, uses the isolated HTML/CSS/JS from this feature branch, and renders the Telegram OTP sign-in overlay. AIOSEO robots `noindex/nofollow/noarchive/nosnippet/noimageindex` were saved, WordPress theme header/footer isolation is page-scoped, and browser rendering/screenshot readback succeeded. No actual chat metadata is publicly embedded; account-wide ChatGPT enumeration still unavailable. The offline browser PIN vault remains optional and distinct from server storage. Existing Moksha pages/theme, booking flow, notification snippets and plugin connections are unchanged.

**OTP integration BLOCKED pending owner review:** Backend source branch now expects exact `https://mokshagoa.com` Origin, and permits Origin-less, authenticated same-origin browser GETs only with Fetch Metadata/referrer proof. It is **not** yet live: WPVibe approval operation `op_4be9535c39564c1c` for enabled WPCode snippet #13375 is pending, and WPCode will save the edited PHP OFF; the owner must review and re-enable. Until then, live page Telegram OTP calls will be rejected by the old GitHub Pages Origin. Do not claim end-to-end login/GET/PUT, delivery or a plugin release. The code is source-only in [Engagement Core PR #70](https://github.com/karanzing1992/engagement-core/pull/70) pending approval and repeat CI.

**Supabase boundary:** Reuse project `saczglesalubroyaucqe` is verified active on Free in the owner's Supabase account and powers existing Master Stack services. Mission Control has **not** created a new table, function, key or persisted user task data there. The current `/tasks` data store remains encrypted WordPress options. A separate audited Supabase data adapter requires owner-scoped bearer validation, RLS, an existing secure server-to-server authorization path and negative access tests before changing the source of truth; no broad `anon` grants or exposed service keys. Cloudflare deploy workflow remains **unexecuted/deprecated pending review**, and no GitHub Pages workflow was revived.

**Open Source / Reuse / Cost Gate:** Reuses owned WordPress hosting, WPCode, Engagement Core private DM authentication, Supabase Free project (future adapter), vanilla JS and GitHub private source. No new paid services or third-party packages. Rollback page #13376 to draft and, if activated, disable only snippet #13375; preserve all other pages/notifications. Browser layout passed; auth, mobile and Supabase end-to-end certification remain pending.
