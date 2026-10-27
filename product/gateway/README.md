# WP Control gateway

Runtime:

ChatGPT public plugin -> Supabase OAuth/MCP gateway -> paired self-hosted WordPress.

The gateway stores tenant ownership and audit metadata only. It does not store WordPress
administrator passwords, application passwords, database credentials, or hosting credentials.

## Pairing

1. Install WP Control and Cowboy MCP on WordPress.
2. Generate a 15-minute pairing code in WordPress.
3. Sign in to the ChatGPT plugin using WP Control OAuth.
4. Call `connect_site` with the HTTPS WordPress URL and pairing code.
5. WordPress stores the central user UUID plus its local administrator user ID.
6. The gateway stores central user UUID -> site UUID ownership.
7. Every later action is checked at the gateway and revalidated by WordPress.

## Cross-project MCP OAuth registration — mandatory SOP

Before adding/reconnecting ANY MCP connector (WordPress, Dell/Mac SSH, Manbir, or a new project), follow **[MCP OAuth Connection Registration SOP](../../docs/MCP_OAUTH_REGISTRATION_SOP.md)** and copy the **[registration QA checklist](../../docs/templates/MCP_CONNECTION_REGISTRATION_CHECKLIST.md)**. This gateway README is subordinate to that SOP for OAuth identity, token, client routing, callback and isolation questions.

**2026-10-27 live repair:** the Supabase OAuth issuer is still shared across the legacy WordPress, Generic Linux and Manbir MCP gateways. The configured legacy authorization entry `wpcontrol-auth` v18 now forwards to the **neutral `mcp-connection-consent` v3**, which presents separate verified client views for WordPress, Generic Linux and Manbir. `owner-oauth-login` v6 also forwards to the neutral entry instead of WordPress. Distinct *pages* are not separate issuers, and end-to-end cross-client token rejection is **not yet certified** (tracking issue #81). Never register another MCP that directly points to `mokshagoa.com/wp-control/connect/`.

## Supabase OAuth settings required before public connection testing

- OAuth 2.1 server: enabled
- Dynamic client registration: enabled
- Authorization path: /oauth/consent
- Auth Site URL: https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-auth

One Supabase Auth project has **one** Auth Site URL/authorization path. Treat `wpcontrol-auth` as a backwards-compatible **common redirect**, not a WordPress-specific consent handler. New registrations MUST use the neutral, verified-client routing contract and enforce signed OAuth `client_id` + per-resource owner policy at the resource gateway; do not assume this legacy gateway has passed those future release gates.

V1 requests only the standard `email` OAuth scope. Fine-grained WordPress permissions
remain enforced by the gateway and WordPress until custom Supabase OAuth scopes are available.

## Public MCP endpoint

https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-mcp/mcp
