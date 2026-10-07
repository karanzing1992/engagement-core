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

## Supabase OAuth settings required before public connection testing

- OAuth 2.1 server: enabled
- Dynamic client registration: enabled
- Authorization path: /oauth/consent
- Auth Site URL: https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-auth

V1 requests only the standard `email` OAuth scope. Fine-grained WordPress permissions
remain enforced by the gateway and WordPress until custom Supabase OAuth scopes are available.

## Public MCP endpoint

https://saczglesalubroyaucqe.supabase.co/functions/v1/wpcontrol-mcp/mcp
