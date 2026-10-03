# Engagement Core

Reusable WordPress engagement inbox. The first adapter is YouTube for **Goa Reset**; the core is brand-agnostic so later adapters can be added for Instagram/Meta and reused by Moksha and Andaz.

## V1 capabilities

- Connect a YouTube channel through Google OAuth 2.0.
- Sync recent channel/video comment threads.
- Reply to top-level comments.
- Hold, publish or reject comments through YouTube moderation APIs.
- Encrypt OAuth client secret and refresh/access tokens with WordPress salts (AES-256-GCM).
- Use WooCommerce Action Scheduler when present; fall back to WP-Cron.
- Store a local engagement inbox in a dedicated WordPress table.

## Goa Reset defaults

- Brand: `Goa Reset`
- YouTube channel ID: `UCSYkzC8ctGKzMK1fhvy6FcA`

## Google Cloud setup

1. Create/select a Google Cloud project.
2. Enable **YouTube Data API v3**.
3. Create an OAuth 2.0 Web application credential.
4. Add the redirect URI shown in Engagement → Goa Reset / YouTube.
5. Paste Client ID and Client Secret in the plugin.
6. Click **Connect YouTube** and select the Goa Reset channel.

Scope used: `https://www.googleapis.com/auth/youtube.force-ssl`.

## Maintained foundations checked before implementation

- `googleapis/google-api-php-client-services`: current generated YouTube service methods for `commentThreads`, `comments.insert`, and `comments.setModerationStatus`.
- `woocommerce/action-scheduler`: maintained recurring/async job primitives. Engagement Core calls the Action Scheduler public API if WooCommerce has loaded it, and falls back to WP-Cron otherwise.

The plugin intentionally uses WordPress HTTP for Google OAuth/API calls rather than bundling the full Google PHP client, keeping runtime compatibility and package size small.

## Known API limitation

YouTube's public Data API does not expose creator hearts or comment-like actions. V1 therefore automates useful supported engagement (read/reply/moderate) and leaves hearts/likes as UI-only actions.
