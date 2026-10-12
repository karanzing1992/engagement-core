# Direct Google Search Console · Engagement Core 0.9.15

**Status:** Source-controlled integration; production activation is a separate step. The module is intentionally disconnected until an administrator explicitly authorizes a **dedicated** Google Cloud Web OAuth client for this WordPress site. Do **not** reuse Site Kit, YouTube or Windsor.ai refresh tokens.

## What is implemented

- Dedicated **read-only** OAuth scope: `https://www.googleapis.com/auth/webmasters.readonly`.
- Encrypted OAuth client secret/access/refresh token via existing `GREC_Secrets` (WordPress salt-derived AES-GCM); secrets never returned in API status or GPT responses.
- WordPress admin submenu **Engagement → Search Console** for saving a dedicated Google OAuth client, connecting, disconnecting, and one-shot manual sync.
- Fixed Google Search Console property: `home_url('/')`; for Moksha this is `https://mokshagoa.com/`. Only published WordPress pages or posts on the same HTTPS host can be inspected, and only by WordPress administrators.
- Google Search Analytics queries for settled `date`, `query`, `page`, or `device` aggregates (28 settled days, conservative 3-day lag; 40 rows max; 6-hour transient cache).
- Index inspection through Google's indexed-version URL Inspection API (does not request or guarantee indexing). Daily WordPress cron stores one aggregate snapshot and a status check for `/mud-bath-goa/` after authorization. Does not spam community Telegram groups.
- GPT/MCP WordPress abilities via the existing Engagement Core / Cowboy MCP gateway: `wp-control/gsc-status` (empty input), `wp-control/gsc-report` (`{"dimension":"date"|"query"|"page"|"device"}`), `wp-control/gsc-inspect` (`{"post_id":12671}`). An authenticated WP administrator `manage_options` is required. Integrations must dynamically discover WordPress abilities if the external client has a fixed-tool catalog.
- No change to Google Site Kit, AIOSEO, WooCommerce checkout, YouTube OAuth or customer data; no GSC Wizard or Windsor subscription required.

## One-time Google setup (administrator)

1. Open [Google Cloud Console](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com) in the Google account that already manages `mokshagoa.com`. Select an appropriate Moksha-owned project and **enable Google Search Console API**; do not use an unrelated brand's Google project.
2. In **Google Auth Platform / Clients**, create an **OAuth 2.0 Web application** client. Complete the consent configuration for your own approved Google account, avoiding unnecessary public publishing. Only the `webmasters.readonly` scope is required.
3. Add the exact Authorized Redirect URI presented on **WordPress → Engagement → Search Console**, normally `https://mokshagoa.com/wp-admin/admin-post.php?action=grec_gsc_callback`. Use the copy shown by WordPress since redirect URI byte-for-byte equality matters.
4. Enter this new OAuth Client ID and Client Secret into the WordPress admin form. The secret is encrypted and never placed in GitHub, task JSON, logs or ChatGPT responses. Do not paste it into this chat.
5. Click **Authorize Google read-only**, authenticate using the account that has access to the **URL-prefix property** `https://mokshagoa.com/`, and approve the prompt. The callback verifies CSRF state and the account's exact Search Console property.
6. Confirm **Connected: Yes** in Engagement → Search Console. Click **Sync now**. Confirm a summary and Mud Bath inspection status; verify actual Google last crawl/canonical. WP-Cron normally runs daily; a site-level reliable cron scheduler is preferable if low visitor volume causes delays.

## Deployment and validation

1. Merge reviewed PR with `STACK CHANGE:` squash subject in this monitored repo to trigger Route A Master Stack ingestion.
2. Deploy using **existing Engagement Core package/update route** only, after verifying healthy signed manifest or Deployer for Git configuration. Do not use WPVibe theme edits or rebuild a new plugin.
3. Verify WP Control `list_plugins` reports **Engagement Core v0.9.15**; WordPress admin submenu appears; credentials show **Not connected** (expected).
4. Once OAuth setup is complete, test `wp-control/gsc-status`, 28-day settled `gsc-report`, and `gsc-inspect` on Mud Bath page post **12671**. Confirm no plaintext credential appears in any response.
5. Verify the independent Route A master registry marker against the source merge SHA. **Never claim live deployment or master ingestion without readback.**

## Limitations and rollback

- Google Search Console's URL Inspection API inspects Google's *indexed version*, not a live crawl. It cannot request indexing for normal wellness pages. URL Inspection results, rankings, crawl dates and indexing are never invented.
- WP-Cron has best-effort scheduling. Google Search Analytics has a settlement delay and may omit low-impression/anonymized queries.
- If an account has *only* the `sc-domain:` property, create/verify the HTTPS URL-prefix property in Search Console (or extend explicit owner-scoped mapping in a later PR). Do not silently read an unrelated property.
- Disconnecting removes stored local Google tokens/snapshots and the schedule but does not revoke Google account consent remotely; revoke under Google Account → Third-party access if required.
- Rollback: revert the source commit; roll back to the previous healthy, verified signed release **0.9.14**. Disconnect token through the dashboard before rollback if desired. Existing Site Kit remains independent.
- Daily Telegram alerts are deliberately not enabled until a **private operator alert destination** is configured; sending search errors to public community destinations is unsafe.

## Tests

`tests/search-console-safety-smoke.php` covers strict site boundaries, external URL rejection, no automatic OAuth, no token disclosure, and fail-closed disconnected behavior. The dedicated PR/push workflow lints this integration on PHP 7.4 and 8.2. No real Google API calls are made in CI.
