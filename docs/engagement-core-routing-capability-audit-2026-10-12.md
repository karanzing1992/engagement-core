# Engagement Core — Existing Routing Capability Audit (12 October 2026)

**Status:** SOURCE-VERIFIED + PARTIAL LIVE READBACK. **Do not claim a new deployment.**  
**Owner:** Moksha Wellness WordPress `https://mokshagoa.com`; source repository `karanzing1992/engagement-core`.  
**Purpose:** Honor the existing first-party routing work before adopting third-party publisher substitutes or rebuilding services. The account-aware, publisher-specific channel routing capability already exists. This is not yet a universal authenticated dispatcher for every Moksha social account.

## Confirmed source architecture

```text
User approves a campaign
    |
ChatGPT connected native WP Control gateway (if actually installed/connected in this conversation)
  -> Supabase wpcontrol-mcp server.ts tool: telegram_status / telegram_publish
  -> WordPress wp-control/v1/bridge (paired site_id + OAuth user token + local admin)
  -> GREC_WordPress_Control::native_telegram_publish
  -> GREC_Telegram::send_post
     (targets: destination keys/chat IDs; optional levels; text and rich media)
  -> Telegram Bot API per selected recipient
  -> response: individual sent/failed, message_ids; WP last_publish receipt
    |
Alternative: authorized WordPress administrator in native Engagement Core composer
    |
Alternative: authorized scoped first-party REST key:
    POST /wp-json/engagement-core/v1/telegram/publish
    GET  /wp-json/engagement-core/v1/telegram/status

VK: native WP Control vk_status/vk_publish + protected REST /vk/status /vk/publish
OK.ru: protected REST /ok/status /ok/publish + WordPress admin, NOT listed as MCP gateway tool
Snapchat: /snapchat/status + device-handoff queue + separate Public Profile API
          /snapchat/api/status, /profiles, /publish; NOT exposed as a named MCP gateway tool
YouTube: Engagement Core's YouTube OAuth + comment inbox/reply/moderation,
         NOT automatically a YouTube video uploader.
Instagram/Facebook/LinkedIn/Pinterest/Threads/Bluesky/X/GBP:
         use separately verified connected publishing service (currently Metricool);
         do NOT assert native Engagement Core adapters for these without source evidence.
```

## Verified repository implementation inventory

| Feature | Exact evidence | Capability / limitation |
| --- | --- | --- |
| Main plugin | `engagement-core.php` | Declares v0.9.14, loads Telegram/VK/OK/Snapchat publisher classes, WP Control bridge, media queue/ingest, brand assets, updater, YouTube inbox/scheduler. |
| Multi-target Telegram routing | `src/class-grec-telegram.php` | Stores destinations with keys, chat IDs, levels and enabled flags; filters by `targets` and `levels`; native text/photo/video/animation/audio/document; media albums up to 10; per-destination sent/failed and Telegram message IDs; last-publish receipt retained as a WordPress option. |
| Caption overflow | `src/class-grec-telegram.php` | Single video/photo caption <=1024 chars; when longer, media plus a separate text message. Validate content in Russian before send. |
| Protected API | `src/class-grec-publisher-rest.php` | Telegram/VK/OK/Snapchat routes; administrator capability OR independently scoped machine key; `telegram.publish`, `telegram.status`, `vk.publish`, etc. |
| WP control native execution | `src/class-grec-wp-control.php` | `telegram_status`, `telegram_publish` (supports `dry_run`), `vk_status`, `vk_publish`; paired user identity/site and local administrator checks in bridge. |
| MCP gateway tool exposure | `product/gateway/supabase/functions/wpcontrol-mcp/lib/server.ts` | Registers `telegram_status`, `telegram_publish`, `vk_status`, `vk_publish`, signed engine status/update/rollback. **Tools existing in code do not guarantee that this chat has the WP Control MCP plugin currently connected.** |
| VK | `src/class-grec-vk.php` | OAuth token/community flow; text, links, max 10 PHOTOS. WordPress-native VK VIDEO posting is explicitly not supported by this adapter yet. |
| Odnoklassniki | `src/class-grec-ok.php` | Text/link/photo group `mediatopic.post`; requires OAuth/application approval. WordPress-native video support not evidenced. |
| Snapchat device | `src/class-grec-snapchat.php` and `tools/snapchat-handoff-android/` | Queued public-URL media/video handoff for an Android Creative Kit flow, queue claim and completion, separate from automatic public posting. |
| Snapchat API | `src/class-grec-snap-public-api.php` and `docs/snapchat-public-profile-api.md` | OAuth organization/public profile, encrypted WordPress media upload, Story/Spotlight API submit, status/profiles route. Requires allowlisting, profile connection and live publish verification; source code alone is not proof of access. |
| Dedicated Reel Engine | `services/reel-engine/social_publishers.py` | Has separate Telegram multi, VK photo, OK photo publishing helpers using environment secrets; do NOT instantiate a second independent bot when configured WordPress first-party publisher already exists. |
| Brand assets and ingest | `src/class-grec-brand-assets.php`, `src/class-grec-media-ingest.php`, `src/class-grec-media-queue.php` | WordPress brand asset selection, media ingest and queue. The existing Reel Engine README still describes preserving a black logo background; that documentation/code path needs independent revision before it can be called compliant with the new mandatory transparent overlay rule. |

## Evidence from live WordPress on 12 October 2026 (read before connector rate limit)

- WPVibe authenticated site info reported live WordPress **7.1.2**, PHP 8.2.34, active `engagement-core/engagement-core.php` plugin and native `engagement-core/v1` REST namespace.
- The protected namespace listing exposed `/telegram/publish`, `/telegram/status`, `/vk/publish`, `/vk/status`, `/ok/publish`, `/ok/status`, `/snapchat/handoff`, `/snapchat/api/status`, `/snapchat/api/profiles`, `/snapchat/api/publish`.
- Native Telegram status **connected: true**, **4 enabled destinations** (keys: primary, moksha, andaz, exclusiv). Historical last_publish receipt reported sent 4, failed 0, **single-photo** media: this is NOT evidence that the 12-Oct Morning Light video was sent. Real-time campaign-specific send requires its own verified receipt.
- Native VK status **connected: false**, OAuth unconfigured and token not saved. No verified active VK publishing.
- Current Snapchat OAuth/Public Profile status and OK status remain **UNVERIFIED**: WPVibe Free fair-use limit blocked calls. Do not treat registered endpoints as working OAuth.
- The dedicated WP Control MCP tools were NOT surfaced in this ChatGPT session's connected tool inventory at audit time. Their registration in the GitHub server.ts is SOURCE-VERIFIED only. Do not request a new token or claim the gateway is available here merely because the code exists.

## Important routing safeguards / findings

1. **Explicit destinations required.** `GREC_Telegram::enabled_destinations()` with EMPTY filters includes ALL enabled groups, potentially unrelated ventures. For Moksha campaign routes pass e.g. `targets: ['primary','moksha']` only after verifying current association and permissions. NEVER rely on empty targets for an all-channel campaign.
2. **Targets + levels are combined with OR when both present:** `src/class-grec-telegram.php` lines 155–160. This can expand an intended narrow selection to every destination sharing a broad level. Until the behavior is explicitly reviewed and guarded by tests, send **targets only; do not provide levels concurrently**. This is a source-confirmed isolation hazard; no live misdelivery is asserted.
3. **Russian-only is currently an operator rule, not automatically enforced in PHP.** The publisher sanitizes Telegram HTML and validates media/URLs but does NOT detect Cyrillic language or reject English before send. As of 12 Oct, operators/assistants MUST write natural Russian-only captions by default and block English copy; a future opt-in source change should enforce language using an explicit brand/channel policy rather than generic script regex (proper nouns/links must survive). Never say the runtime automatically blocks English today.
4. **No campaign idempotency enforced in core send_post:** the visible flow loops destinations and overwrites a global `grec_telegram_last_publish` WordPress option. It does not accept a campaign idempotency key or store full event history per message. Avoid automatic whole-campaign retries on timeouts; inspect the last receipt and manually reconcile before selecting any failed destination.
5. **Do not assume auto-cross-platform video routing.** WP Control offers native Telegram and VK named MCP tools, not named Instagram/Meta/Pinterest/YouTube video tools; additional source adapters for Snapchat/OK use a different protected-REST/admin lane, and account permissions may not yet be approved. Existing Metricool connected destinations remain distinct and should be managed without duplicating posts.
6. **Protection and routing scopes.** Keys/secret storage are private; never expose them in chat, GitHub or registry. Scoped REST key and bearer/OAuth user bridge are different authenticated lanes; only use an actually authorized attached lane.

## Operational conclusion and near-term priority

- **Use Engagement Core's Telegram route as first choice** for every Telegram video/message, with Russian-only caption, explicit verified Moksha targets, `dry_run` where available and per-target receipt readback.
- Prioritize safely exposing and validating the already-built WP Control MCP `telegram_status` / `telegram_publish` tools to this session rather than creating any new Telegram bot, posting connector or scheduler. Configuration requires user-owned plugin connection/authorization, not guessed API keys.
- Confirm SNAP allowlisting/OAuth when connection is available, and VK reconnect for photo/text; **VK clips/video will still need a separate supported implementation or manual lane**.
- Before upgrading Engagement Core, add tests for target/level semantics, campaign idempotency, Russian-only preflight, and delivery status audit; do not silently change broad fan-out semantics on production.
- Record all capabilities as **source implemented / live route observed / account connected / published receipt verified** separately.

## Safe rollback / change scope
This is source-level architecture and documentation **only**. No WordPress code, plugin binary, secret, group assignment, credential, target list or prior campaign delivery has been changed. Revert this documentation commit to restore previous documentation. Any runtime fix requires its own compatibility/testing, checkpoint, deployment authorization and post-deploy verification.

## Source links
- https://github.com/karanzing1992/engagement-core/blob/main/engagement-core.php
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-telegram.php
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-publisher-rest.php
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-wp-control.php
- https://github.com/karanzing1992/engagement-core/blob/main/product/gateway/supabase/functions/wpcontrol-mcp/lib/server.ts
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-vk.php
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-ok.php
- https://github.com/karanzing1992/engagement-core/blob/main/src/class-grec-snap-public-api.php
