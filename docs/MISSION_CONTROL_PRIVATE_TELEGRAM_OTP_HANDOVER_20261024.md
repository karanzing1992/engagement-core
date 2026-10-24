# Mission Control — private Telegram OTP handover (24 October 2026)

## Verified reuse and security boundary

- Existing owner-private notification transport: [PRIVATE_TELEGRAM_TASK_NOTIFICATIONS.md](PRIVATE_TELEGRAM_TASK_NOTIFICATIONS.md), WPCode snippet #13358, signed Dell worker dispatch. This sends completion/failure notices; it is **not** an OTP login service.
- Existing owner-paired private Telegram DM uses WordPress option `grec_booking_private_telegram_chat` and encrypted `GREC_Telegram::credentials()`. Original paid-booking snippet #13126 remains untouched.
- Existing Dell `dell-pin-auth` Edge Function handles device-specific PIN + challenge and lockout. It is **not** repurposed for Mission Control and no device secrets or keys are copied.
- New code reuses only the trusted recipient and bot-credential adapter, not the signed task-notification event endpoint. No groups, broadcasts, arbitrary recipient input or extra bot.

## New source (not installed)

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

The frontend source is on [android_gpt_bridge draft PR #16](https://github.com/karanzing1992/android_gpt_bridge/pull/16). It currently provides locally encrypted task metadata, project/chat drill-down, status filters, manual editing, ChatGPT JSON import and original chat deep links. A frontend adapter must authenticate with this new OTP route and route task GET/PUT through it before declaring live cloud synchronization. The existing `moksha-master-stack-reinforced` private v1.4.1 plugin is skills-only; it cannot enumerate all ChatGPT account histories. Extending its capabilities needs an authorized task-index MCP endpoint and a same-plugin release, not merely a new Skill description.

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

## Current state

**SOURCE_ONLY**. No WordPress snippet installed/activated, no OTP sent, no Supabase Edge Function deployed or modified, no Master plugin release updated, no GitHub Pages publication. Do not call this a live authentication service based only on source commits or CI.
