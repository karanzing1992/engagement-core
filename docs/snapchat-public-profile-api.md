# Snapchat Public Profile API — Engagement Core

Official references:
- https://developers.snap.com/marketing-api/Public-Profile-API/GetStarted
- https://developers.snap.com/marketing-api/Public-Profile-API/ProfileAssetManagement

## Supported modes

1. **Official Public Profile API** (new): authenticated server-side story/Spotlight publishing from WordPress Media Library, with encrypted media upload, access token refresh, per-site profile configuration, and publish receipts. **Requires Snapchat allowlisting.**
2. **Android Creative Kit handoff** (existing): opens media in Snapchat Preview on the phone; final share remains manual. Has separate Creative Kit Client ID and device key. Remains a fallback.

Do not confuse the two Snapchat application IDs. The Public Profile API OAuth app **must be created under Snapchat Ads Manager → Business Dashboard → Business Details**, not the generic Snap Developer Portal.

## Required one-time Snapchat steps

1. Sign in with the business's Snapchat account at https://ads.snapchat.com/ and create a Business Organization and Public Profile if needed.
2. Create a **Marketing API OAuth App** under Business Dashboard → Business Details. Register the exact query-free redirect displayed on **WordPress → Engagement → Snapchat API**, e.g.:
   `https://mokshagoa.com/wp-json/engagement-core/v1/snapchat/api/oauth/callback`
3. Retain the **Client ID** and **Client Secret** privately. Only provide **Client ID**, never Client Secret, to your Snapchat point of contact and request **Public Profile API allowlisting** with the use case: automated publishing of owned wellness-brand Stories and Spotlights, media/rights management, and first-party metrics. Snapchat does not guarantee an approval date.
4. In the plugin's Snapchat API screen, save the Client ID, Client Secret, Organization UUID, and relevant Public Profile UUID.
5. Click **Connect Snapchat OAuth**, approve the `snapchat-profile-api` scope, then **Verify API access**. Verification must return the selected profile from the organization list.
6. Publish one approved test Story; verify it appears on the actual Public Profile. Then publish a test Spotlight and verify it becomes visible. A successful API POST is only **submitted**, not proof of actual public visibility/moderation.
7. After live verification, connect the existing ChatGPT/WordPress publishing key with its `snapchat.publish` scope, or use an authenticated administrator. Do not put tokens in GitHub or logs.

The Public Profile OAuth Client ID must be allowlisted before profile requests will succeed. A `403 AUTHORIZATION_PERMISSION_DENIED` should be treated as permission or allowlist failure, not retried indefinitely.

## Direct publishing

Authenticated WordPress API:

```http
GET  /wp-json/engagement-core/v1/snapchat/api/status
GET  /wp-json/engagement-core/v1/snapchat/api/profiles
POST /wp-json/engagement-core/v1/snapchat/api/publish
Content-Type: application/json
X-GREC-Publish-Key: <scoped machine key>
```

Story payload:

```json
{"attachment_id":123,"destination":"story","ttl":"ONE_DAY"}
```

Spotlight payload:

```json
{"attachment_id":123,"destination":"spotlight","description":"A moment of calm in Arambol 🌿 #Goa #Wellness","locale":"en_IN"}
```

- Choose media already uploaded to the site's own WordPress Media Library; arbitrary external URLs are intentionally not accepted by the direct API.
- Videos must be MP4, >=540×960; Story length 5–60 seconds, Spotlight 6–60 seconds. Spotlight descriptions up to 160 characters.
- An unexpired media object is required. The adapter uploads immediately before submitting the post to avoid Snapchat's 24-hour expiration.
- Upload is **AES-256-CBC encrypted**, no OpenSSL salt. Media is streamed to a temporary encrypted file, then uploaded in <=32 MiB parts; the temporary file is deleted.
- The adapter caps media at 96 MiB to protect shared hosting memory/time limits; very large files should instead be transcoded by the existing render pipeline.
- Story TTL: `ONE_DAY`, `TWO_DAYS`, `THREE_DAYS`, `ONE_WEEK` or omit to use Snapchat default.
- No recurring polling or new GitHub Actions is required for each post; existing publishing orchestrators can call the private WordPress endpoint.
- Machine key permissions are checked using Engagement Core's scoped publisher auth; OAuth secrets and refresh tokens are encrypted at rest using `GREC_Secrets` and are never returned to clients.

## Production readiness

- Unit smoke test: `php tests/snapchat-crypto-smoke.php`
- Syntax: `php -l src/class-grec-snap-public-api.php`
- QA must confirm that an actual approved Snapchat organization, OAuth app, allowlisted Client ID, and public profile are available.
- A successful API read test **does not verify Story/Spotlight publishing permissions**.
- Record the posted request/Spotlight ID; distinguish `submitted_to_snapchat` from verified public visibility.
- Do not deploy this feature branch to Moksha production until syntax, OAuth callback, encrypted upload, Story/Spotlight test, and rollback review are complete.

## Separation of concerns

Brand configuration stays in encrypted WordPress options and admin inputs, not in shared library code. The same plugin may serve Moksha, Andaz, or third-party licensees with their own Snapchat Business OAuth apps, Organization UUIDs, Public Profile UUIDs and tokens. The core adapter is brand-neutral.
