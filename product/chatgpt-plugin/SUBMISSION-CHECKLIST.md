# WP Control — ChatGPT submission checklist

Last reviewed: 2026-10-07

## Runtime endpoint

- MCP: `https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-mcp/mcp`
- OAuth issuer: `https://saczglesalubroyaucqe.supabase.co/auth/v1`
- Consent UI: `https://wp-control-auth-ui.vercel.app/`
- WordPress production implementation: Engagement Core `src/class-grec-wp-control.php`

## Verified

- [x] MCP `initialize` returns HTTP 200.
- [x] `tools/list` exposes 19 typed tools.
- [x] Unauthenticated tool calls return an MCP OAuth challenge with protected-resource metadata.
- [x] OAuth discovery exposes dynamic client registration.
- [x] Dynamic public client registration succeeds.
- [x] PKCE S256 is advertised.
- [x] Protected-resource metadata advertises `email` and `offline_access`.
- [x] A PKCE authorization request using `email offline_access` is accepted and routed to the canonical consent UI.
- [x] Magic-link callback preserves the OAuth `authorization_id` explicitly.
- [x] MCP server metadata version is 0.1.1.
- [x] Duplicate-sensitive writes such as content creation and order notes are marked non-idempotent.
- [x] `undo_change` is marked destructive and non-idempotent.
- [x] New content defaults to draft.
- [x] Public MCP surface exposes no raw SQL, filesystem or WP-CLI tool.
- [x] WordPress bridge rejects missing bearer tokens.
- [x] Invalid or expired pairing codes fail without exposing pairing data.
- [x] Central WP Control tables use RLS deny-direct policies for anon/authenticated clients.
- [x] Central audit schema stores tool metadata only; no raw tool input/body/token column.
- [x] Supabase security advisor reports no WP Control table security lint.
- [x] OAuth consent UI is Git-backed and deployed from this repository.

## Must pass before external submission

- [ ] Complete a fresh founder OAuth login on the canonical consent UI.
- [ ] Confirm refresh-token issuance/renewal with `offline_access`.
- [ ] Generate a short-lived WordPress pairing code and connect the Moksha canary site.
- [ ] Verify `list_sites` and `site_overview` through authenticated MCP.
- [ ] Create a clearly named draft canary; never publish it.
- [ ] Verify the draft appears in `list_changes`.
- [ ] Undo the canary change.
- [ ] Verify the draft is gone/reverted.
- [ ] Confirm central and local audits contain metadata only and no secrets/raw content.
- [ ] Remove the stale inactive `engagement-core.disabled` copy only after the complete canary succeeds.
- [ ] Re-run Supabase security/performance advisors after final changes.
- [ ] Test in ChatGPT Developer Mode using endpoint scan + OAuth.
- [ ] Verify write-action confirmation behavior in ChatGPT.
- [ ] Add/verify a public privacy policy suitable for directory review.
- [ ] Add/verify support contact and developer identity used for submission.
- [ ] Review public app/plugin name, description, icon and screenshots before submission.

## Tool-risk expectations

Read-only:
`get_profile`, `list_sites`, `site_overview`, `list_content`, `get_content`,
`list_products`, `get_product`, `list_orders`, `get_order`, `seo_audit`,
`list_changes`.

Writes but intended to be recoverable or narrowly scoped:
`connect_site`, `create_content`, `update_content`, `update_product`,
`add_order_note`, `update_seo`, `flush_cache`.

Explicitly destructive/reversal action:
`undo_change`.

## Product rules

- Never request or store WordPress administrator, database or hosting credentials centrally.
- Authenticate users through Supabase OAuth.
- Pair sites using one-time short-lived codes generated in WordPress.
- Forward the authenticated Supabase bearer token to WordPress for local owner validation.
- Default all newly created content to draft unless the user explicitly requests publication.
- Prefer reversible WordPress APIs and the undo journal.
- Keep public tooling typed and bounded; power-mode WP-CLI/filesystem access is not part of the public app.
