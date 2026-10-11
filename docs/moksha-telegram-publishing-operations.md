# Moksha Telegram — in-house publishing standard
Effective 11 October 2026. Scope: Moksha Wellness Social Media only.
Registry: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit
Protocol: https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md

## Default channel owner and routing
Use existing Engagement Core on https://mokshagoa.com as the **primary Telegram publisher**, not a third-party service. Prefer a currently connected and authenticated first-party WP Control/MCP telegram_publish operation; otherwise use the already authenticated in-house Opera/WordPress Control worker to operate the Engagement Core admin composer. Both routes must call Engagement Core's native Telegram bot integration. If these routes fail, report a real blocker rather than claiming delivery or silently switching to a new bot/service. No new scheduler, publisher or credentials for routine posts.

The first-party protected REST endpoint is POST /wp-json/engagement-core/v1/telegram/publish with telegram.publish scope. Source: src/class-grec-publisher-rest.php; src/class-grec-wp-control.php; product/gateway/supabase/functions/wpcontrol-mcp/lib/server.ts. Presence of this code or a Supabase Edge Function does not prove the MCP tool is attached and callable from a given ChatGPT conversation. WordPress administrator control through the authenticated existing Opera worker remains an in-house fallback.

## Operating safeguards
- Live Engagement Core enabled destinations in WordPress are the runtime authority. The older services/reel-engine/configs/moksha.social.json lists only a primary group; do not overwrite four live groups from this example or assume the config mirrors runtime.
- Confirm publishing targets before each campaign. Send to all enabled groups only when explicitly authorized. Andaz/Exclusiv have separate brand identities; an approved past cross-post is not general permission to share unrelated content, customer data or credentials across ventures.
- Telegram bot credentials remain encrypted in WordPress. Never reveal, regenerate, copy to GitHub or expose in a queue. If the private scoped publishing key is missing, use the existing authenticated control lane rather than generating credentials.
- Use the verified original Moksha logo from brand Drive assets, approved real venue imagery and preferably Goa/India-relevant material; no synthetic or redrawn logo. Use stable WordPress media URLs, not ephemeral sandbox or signed Drive links.
- Recheck time, pricing, complimentary inclusions and booking/location URLs. Distinguish four-hour COMMUNITY WINDOW from any sauna-duration entitlement.
- One campaign = one submit. Use a unique job ID, wait for in-house publish acknowledgement, then read back application-level results. Queue completion is not delivery evidence. Inspect last-publish status/message IDs where available before considering a selective retry.
- Redact secrets, private chats, personal contact data and credentials from Git, Google Docs and logs.

## Verified example: Russian Moksha community announcement, 11 Oct 2026
Offer: 18:00–22:00 community evening (four-hour gathering), wood-fired sauna from ₹500. Complimentary with each session: face mask, salted drinking water, iced tea, watermelon, towels and robes. Ask for arrival notice 45–60 minutes beforehand.
Business WhatsApp: https://wa.me/918999541081
Verified location source: https://maps.app.goo.gl/PPyNYi5XABPkMQsFA
Approved-branded Russian flyer: WordPress media ID 13102;
https://mokshagoa.com/wp-content/uploads/2026/10/moksha-russian-community-2026-10-11.png

Verified active WordPress Engagement Core version: v0.9.14. Admin composer reported Telegram Connected / four enabled destinations. Authenticated private in-house Opera/WordPress Control queue: task 684 prepared caption and image URL; task 685 clicked native Publish to Telegram once; task 686 independently read back its completed WordPress success redirect. Exact admin confirmation: "Telegram published to 4 destination(s)." with grec_type=success. This is aggregate adapter success evidence, not Telegram reach/view analytics or four independently recorded message IDs.

Destinations listed in the live composer AT SEND TIME:
- Primary: -1001827799147
- Moksha: @mokshasauna
- Andaz: @andazarambol
- Exclusiv: @goaunder
These are runtime observations, NOT hardcoded future target lists. Review venture-specific posting authorization on each future campaign. Source: src/class-grec-admin.php, src/class-grec-telegram.php and authenticated https://mokshagoa.com/wp-admin/admin.php?page=engagement-core . Do not put private queue task payloads into public documentation.

## Reusable workflow
1. Confirm a user-authorized campaign and precisely selected enabled destinations.
2. Prepare current Russian copy and a branded, legible official-logo flyer.
3. Upload image to WordPress Media Library and confirm stable, publicly fetchable HTTPS URL.
4. Fill native Telegram composer via authenticated in-house control; choose media type/photo; select levels or destinations when scope is narrower than all enabled.
5. Submit once. Read back the WordPress publishing result and failed/sent counts; collect message IDs if the authorized status route exposes them.
6. Report per-destination status only where validated, otherwise state aggregate confirmation and any limits. Avoid duplicate sends on uncertain worker timeouts.
7. Routine social posts do not require Master Stack events. Report only material technology/policy/release changes through the canonical Git commit or authorized non-GitHub route.

## Change level and rollback
This is source documentation and an operational preference backed by a previously verified live send. It does NOT deploy or modify WordPress plugin binaries, bot keys, group memberships or existing customer records. Roll back by reverting the documentation decision; do not remove Telegram destinations merely to revert this policy.
