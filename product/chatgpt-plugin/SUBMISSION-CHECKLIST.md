# WP Control — ChatGPT submission checklist

Last reviewed: 2026-10-12 (with historic canary evidence retained)

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
- [x] Auth UI project includes an ignored-build rule scoped to `product/oauth-ui` at both repo and Vercel project level.

## Private ChatGPT WP Control plugin release and live verification — 12 October 2026

**Private v0.1.0 plugin RELEASE CREATED (not publicly listed):**
[Open the private WP Control plugin](https://chatgpt.com/plugins/plugins_6acc7c8bf3488191bac0a54bd4c50e60).
Plugin ID `plugins_6acc7c8bf3488191bac0a54bd4c50e60`, release `pluginrel_6acc7c8e367c81919c6396efebbf6258`, version `0.1.0`, discoverability `PRIVATE`. Plugin Creator independently retrieved the release manifest, `.mcp.json`, `mcp.json` and private onboarding skill. The manifest's MCP server points to the **existing**, unchanged, private OAuth-enabled gateway `https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-mcp/mcp` and requests dynamic client registration with `email`, `offline_access`. No secret, user token, bot credential or pairing code is bundled. Its onboarding rules insist on Russian Telegram copy and explicitly selected Moksha destinations, never partner groups.

**Production infrastructure verified 12 October, READ ONLY:**
- Supabase listed `wpcontrol-mcp` ACTIVE version **12**; `wpcontrol-auth` ACTIVE version **4**; `wp-control-gateway` ACTIVE version **3**.
- Readback of all **three live deployed** `wpcontrol-mcp` files (`index.ts`, `lib/core.ts`, `lib/server.ts`) exactly matched current `engagement-core` GitHub contents, and live `wpcontrol-auth/index.ts` exactly matched its GitHub source. Therefore **no redundant Edge Function redeployment is required or claimed**.
- Connected WPWriter confirmed `https://mokshagoa.com` site live; `Engagement Core 0.9.14`, `Cowboy MCP 1.7.1`, `MCP Adapter 0.7.0`, and site connector active. WPVibe site read was blocked by daily Free-plan limit.
- Read-only authoritative Supabase `public.wpcontrol_sites` query confirmed an **already ACTIVE, owner-associated Moksha Wellness Goa site pairing**, created October 7. **Do not ask the owner to generate another pairing code** unless authenticated `list_sites` later proves the current OAuth principal lacks the paired site.
- Read-only `public.wpcontrol_audit` verified that earlier authenticated gateway requests on **7 October 2026** successfully ran `site_overview`, `create_content` draft, `list_changes`, `undo_change`, and `list_content`. These are *historical successful canaries*; latest audit record was 7 October, NOT a fresh 12 October plugin-origin canary.
- ChatGPT private plugin release exists, but neither the private `wp-control-native` Skill nor the gateway-native `list_sites`, `site_overview`, `telegram_status`, `telegram_publish` tools are available to the assistant in the **existing conversation tool inventory** as of 12 October. Search of public plugins does not list this private plugin; lack of public search results is NOT evidence of release failure. ChatGPT-side activation and end-to-end *from this conversation* are therefore **UNVERIFIED**.
- The legacy Vercel `wp-control-auth-ui` project's last surfaced production deployment was CANCELED, and an attempt to list more Vercel deployments returned 403 (team-scope unauthorized). This does NOT prove OAuth login broken: current deployed `wpcontrol-auth` code points to the WordPress consent route `https://mokshagoa.com/wp-control/connect/`. Do not treat the obsolete Vercel domain as authoritative without checking the actual user-authored OAuth flow.
- No public Telegram post, WordPress mutation, code release, new OAuth registration or WordPress plugin binary update was performed by this verification.

**Next safe ChatGPT activation test:**
1. Open/select the private plugin inside an eligible ChatGPT chat/workflow and complete provider OAuth consent through its own UI if the host requests it; never paste access tokens in conversation.
2. Confirm native tools surface in that chat; call `list_sites` to read the already paired Moksha site. Reuse the returned actual site ID.
3. Read-only canary: `site_overview`, `engine_status`, `telegram_status`. Verify runtime enabled destinations and current publication receipt; do not mistake an old 11-Oct Telegram receipt for the 12-Oct Morning Light reel.
4. For a user-authorized Moksha Telegram campaign, `telegram_publish(dry_run=true,targets=['primary','moksha'],levels omitted)` first; target identities must be verified. Russian-only final caption; send only with explicit approval and report Telegram message IDs individually.
5. Only if authorized end-to-end reads succeed, verify fresh draft/undo transaction and update the submission checklist accordingly. Existing draft/undo audit is useful earlier evidence; NOT a current test of this new private plugin's UI wiring.

**Operator status taxonomy:** private plugin RELEASED vs HOST SELECTED vs OAuth CONNECTED vs existing site PAIRED vs tool INVOKABLE vs dispatch RECEIPT. Do not collapse these stages into one `deployed/working` label. Deployment rollback: leave unchanged Supabase functions and WordPress plugin intact; disable/unselect the ChatGPT private plugin release if its newly packaged interface fails. This note is source documentation; not a production binary change.

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
