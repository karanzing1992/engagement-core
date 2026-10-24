# Moksha signed public-media handoff — 24 October 2026

Status: **SOURCE ONLY / draft — NOT INSTALLED, NOT PUBLISHED**.

## Scope and reuse

Approved owner goal: transfer the already finished 20.1 MB guest-review MP4 from Dell to the real WordPress Media Library, get its stable HTTPS URL, then use Metricool. No rerender or new hosting.

Reuse: WordPress REST, wp_handle_sideload, wp_insert_attachment, wp_generate_attachment_metadata; built-in PHP sodium Ed25519; and Dell's installed Python cryptography 41.0.7. No paid dependency. The existing Engagement Core private 800 MiB Reel Uploads vault is unchanged and remains intentionally nonpublishing.

The new bridge is needed because live WP Manager offers no binary upload MCP method, Cowboy MCP accepts only remote URLs or whole base64 messages, the Dell WordPress browser session redirected to login, and the connected Supabase project has no Storage buckets.

## Bounded API contract

- Routes: GET /wp-json/wp-control/v1/media-handoff/health; POST media-handoff/start, media-handoff/{id}/chunk/{part}, and media-handoff/{id}/finish.
- Default disabled. Must have WordPress options grec_public_media_enabled='1', grec_public_media_site_host='mokshagoa.com', and a base64 raw Ed25519 public key in grec_public_media_ed25519_key.
- Private Ed25519 signer stays on Dell mode 0600, never in source, WordPress, task arguments or logs. Requests sign method, route, timestamp, random nonce, body SHA-256, and host. Expiry, tampering and replay are refused.
- Only owner-approved Moksha MP4s up to 64 MiB; 4 MiB parts; safe filenames; no arbitrary URL downloads or execution. Bytes stay outside public docroot until complete SHA-256, size and MP4-header verification. WordPress imports through its own media routines and rechecks SHA-256 after import. It returns attachment ID plus HTTPS URL.
- A media attachment receipt is not a social publication receipt. Metricool publish/schedule is separately authorized and verified once.

## Release and acceptance gates

1. PHP 7.4/8.1/8.3 lint; client syntax; correct and altered signatures, expiry, replay, host binding, wrong MIME, length and file hash tests.
2. Preserve *both* current main-source changes and live signed 0.9.17 Supabase OAuth login changes. Main and signed commit 3af88c9689ffc72c390e1229e3112587c88e3822 diverged; do not downgrade either.
3. Obtain an immutable signed Ed25519 package and verified rollback before production. As observed 24 October, live Engagement Core was 0.9.17 healthy and signature valid, but rollback_available=false; therefore installation must stop until a recoverable snapshot is verified. Follow engine_status -> engine_check -> dry-run -> approved install -> readback.
4. Enroll only Moksha site public key, activate by approved administrator route, verify negative auth tests. No SSH/root changes, broad media permissions, new public storage or private-vault promotion.
5. Verify exact Dell final MP4, public WordPress media GET/HEAD and hash before Metricool. Use exact connected Moksha destinations, collect channel-specific live links, distinguish scheduled/accepted/published.
6. On verified material default-branch change, use Master Stack Route A and confirm canonical Doc marker. Source-only PR is not an installed tool.

## Recovery

Default-disabled code has no live effect. If installed, set grec_public_media_enabled=0 through an authorized administrator control to disable the new routes; confirm health false. Restore signed prior package only if the rollback has passed verification. Do not directly overwrite plugin files, extract or copy credentials, broaden privileges, modify the private upload vault, or disable rollback plugin moksha-wp-control-native. Clean up only generated scoped transfer-session files after successful verification.

References: [Reel operation procedure](reel-engine-assistant-operating-procedure.md), [private ingest](private-large-ingest.md), [signed WordPress release controls](PRIVATE_WP_MANAGER_ACCESS.md).
