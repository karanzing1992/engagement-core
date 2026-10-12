---
name: wordpress-control
description: Run and manage a connected self-hosted WordPress site safely from ChatGPT.
---

# WordPress Control

Use this skill when a user asks to inspect, edit, publish, operate, or troubleshoot a connected self-hosted WordPress site.

## Operating rules

1. Start with `list_sites` when the site is not explicit. Never invent a site ID.
2. For new content, default to draft unless the user explicitly asks to publish.
3. Read the current object before materially updating existing content, products, SEO, or orders.
4. Prefer narrowly-scoped tools over broad changes.
5. Treat customer-visible order notes and publishing as external side effects; make that clear before the tool call when approval is required.
6. Use `list_changes` before undoing when the intended change is ambiguous.
7. Never request or expose WordPress administrator passwords, application passwords, database passwords, API keys, or hosting credentials.
8. If a site is not connected, use `connect_site`. The pairing code is generated inside WordPress and expires quickly.
9. If a capability is unavailable, explain which WordPress plugin/provider is required rather than attempting raw SQL or arbitrary code execution.
10. Power-mode operations such as unrestricted WP-CLI or arbitrary file writes are not part of the public plugin.

## Moksha first-party WP Manager operational standard (verified 12 Oct 2026)

This private WP Manager plugin is the **preferred existing Engagement Core control plane** for the paired Moksha site, where currently connected. For other websites, always discover the user's separately authorized connections. The private gateway verifies both the owner-scoped Supabase OAuth identity and the WordPress local administrator/site pairing. Do not assume another GPT session, device or Project inherits this authorization.

For an Engagement Core version upgrade:
- `list_sites` → `site_overview`/`list_plugins`/`engine_status`.
- `engine_check` must verify the desired newer signed manifest (Ed25519, checksum, expected source).
- `engine_update` with `dry_run:true` must pass before an explicit actual installation.
- Install through `engine_update` only when authorized, then independently check active plugin version, health, guest pages and `rollback_ready`. Preserve customer/order data and other integrations.
- For a 403: distinguish native REST code vs upstream non-JSON denial without logging credentials, body or headers. Reinspect version and audit; do not turn off security or bypass the signed updater. The historical intermittent 403 had no proven root cause; the signed 0.9.15 deployment ultimately succeeded via the same route.

**GSC:** v0.9.15 includes first-party read-only Google Search Console operations, but Google OAuth authorization is separate and was still pending at the 12 Oct verification. Site Kit can remain active and must not be treated as permission to reuse its tokens. More detail: [private WP Manager runbook](../../../docs/PRIVATE_WP_MANAGER_ACCESS.md).
