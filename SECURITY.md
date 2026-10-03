# Security

Do not commit OAuth client secrets, access tokens, refresh tokens, WordPress salts, or production credentials.

Engagement Core stores OAuth secrets and tokens in WordPress options encrypted with AES-256-GCM using keys derived from WordPress authentication salts. Credentials are entered only in the WordPress admin UI.

If a credential is accidentally exposed, revoke/rotate it in Google Cloud immediately and reconnect the affected channel.
