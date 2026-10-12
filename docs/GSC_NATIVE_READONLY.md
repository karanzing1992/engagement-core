# Native Google Search Console — Engagement Core 0.9.15

**Deployment readback (12 October 2026):** Engagement Core **0.9.15 installed and active** on Moksha WordPress through private WP Manager signed updater; Supabase private `wpcontrol-mcp` gateway **Edge v16** deployed with four GSC read-only tools; release service **Edge v8**; signature, health, paired bridge and rollback to **0.9.14** verified. **Google OAuth is still unconnected/pending** until an authorized administrator completes consent. Do not conflate installed code, typed tool availability, and an active Google grant. See [private WP Manager runbook](PRIVATE_WP_MANAGER_ACCESS.md).

## Why

- Independent, first-party Google Search Console API access instead of requiring GSC Wizard or a Windsor.ai subscription.
- Reuse existing Engagement Core encrypted secrets (AES-256-GCM tied to WordPress salts), WordPress admin and existing owner-scoped WP Control / Supabase MCP gateway.
- Do **not** copy Site Kit tokens, Windsor.ai tokens, Google sign-ins or Google Cloud secrets from another app.

## Operator connection (one-time, explicit)

1. In a **Google-owned Cloud project**, enable **Google Search Console API**. Set up OAuth consent (minimum required `https://www.googleapis.com/auth/webmasters.readonly` scope). Configure the authorized Google users / app verification as required by Google.
2. Create OAuth 2.0 **Web Application** client ID and secret. In the Redirect URIs section, add exactly `https://mokshagoa.com/wp-admin/admin-post.php?action=grec_gsc_oauth`.
3. Open **WordPress admin → Engagement → Search Console** after the deployment of Engagement Core 0.9.15. Paste client ID and client secret into the WordPress admin form. Do not post credentials in ChatGPT or GitHub.
4. Choose **Connect Google (read-only)**. Authenticate with the Google account that already has access to the Search Console property `https://mokshagoa.com/`. Confirm the narrow readonly Google consent.
5. After both the WordPress package and MCP gateway are deployed, call `gsc_status` and one harmless `gsc_search` for the last 28 settled days, then `gsc_sitemaps`. Test `gsc_inspect` for `https://mokshagoa.com/mud-bath-goa/` only after connection.
6. Confirm the existing Site Kit connection still works. Do not disable Site Kit. No automated indexing requests or SEO edits are part of this integration.

The new read-only GPT tools are `gsc_status`, `gsc_search`, `gsc_inspect`, `gsc_sitemaps`. Through native WordPress Abilities they are `wp-control/gsc-status`, `wp-control/gsc-search`, `wp-control/gsc-inspect`, `wp-control/gsc-sitemaps`.

## Security and privacy

- OAuth client secret and refresh/access tokens are encrypted at rest; stored in WordPress options with autoload disabled. Never returned through MCP/status.
- Admin configuration and redirect are `manage_options`-only, with CSRF protection: admin nonce, state transient, one-time state verified against the same WordPress admin.
- OAuth uses **read-only** scope, never the broad write `webmasters` permission.
- API endpoint origins are constants, never client-supplied; no redirects.
- Search performance is limited to at most 90 days per call, 250 rows, allowlisted dimensions, one same-host canonical page filter. Google URL Inspection only permits same-site, HTTPS query-free URLs; no SSRF.
- Daily WordPress cron caches aggregate impressions/clicks locally, with no private keyword exports or automated external notifications.
- The Google API does **not** allow requesting indexing for normal pages. The Indexing API is restricted to eligible JobPosting/BroadcastEvent cases; never use it for Moksha rituals.
- Existing site DNS, WooCommerce, AIOSEO, Site Kit and all other Engagement Core integrations untouched.

## Operational controls

- Disconnect from WordPress Engagement → Search Console, which deletes this integration's token and cached snapshot and clears its cron. This does not revoke Google grants in your Google account; use Google account permissions to revoke the external grant if needed.
- Rollback code: revert source PR merge and rebuild signed Engagement Core package + gateway. Tokens remain encrypted in WordPress options; disconnect first if removing the feature permanently.
- WordPress 7.1.x, PHP >=7.4; smoke tests run on PHP 7.4/8.2/8.3.
- No public API endpoint, no separate webhook, no new paid integration or new plugin.

## Deployment boundaries

Merging source on GitHub alone does **not** install Engagement Core on Moksha WordPress nor deploy the separate Supabase Edge Function. Release requires the existing signed-update workflow and existing authenticated WP Control gateway deployment flow. If that workflow cannot be invoked/verified, keep the change explicitly **source ready / pending deployment**.

Central Master Stack: after the versioned source is merged to main with a **STACK CHANGE:** subject, the existing Route A worker ingests the commit into the canonical Google Doc. Check the marker before reporting Registry completion.
