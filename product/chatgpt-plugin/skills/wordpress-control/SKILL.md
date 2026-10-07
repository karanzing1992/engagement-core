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
