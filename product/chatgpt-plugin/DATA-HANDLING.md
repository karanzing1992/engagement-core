# WP Control — Data handling and security model

Last reviewed: 2026-10-07

This document describes the intended public ChatGPT/MCP architecture for WP Control.

## Architecture

ChatGPT / MCP client
→ Supabase OAuth + thin WP Control MCP gateway
→ paired self-hosted WordPress site
→ Engagement Core / bounded WordPress abilities

The central gateway does not receive WordPress administrator passwords, application passwords, database credentials or hosting credentials.

## Central data

WP Control's application tables are intentionally narrow.

### `wpcontrol_sites`

Stores the paired site identity and operational routing metadata, including:

- owner user UUID
- site name / slug
- WordPress base URL
- site status / plan
- declared capabilities
- MCP endpoint metadata
- health-check timestamps/status

### `wpcontrol_pairings`

Used only for short-lived site pairing. Stores:

- site ID
- a hash of the pairing code
- expiry
- claimant user UUID
- claim timestamp

The plaintext pairing code is not stored centrally.

### `wpcontrol_audit`

Stores privacy-minimized execution metadata:

- request ID
- site ID
- actor user UUID
- tool name
- success/failure
- duration
- error code
- timestamp

There is no database column for raw tool input, WordPress content bodies, prompts, OAuth bearer tokens, passwords or API credentials.

## OAuth

Supabase Auth is the OAuth 2.1 authorization server.

The MCP protected-resource metadata advertises:

- `email`
- `offline_access`

OAuth access and refresh tokens are managed by Supabase Auth. WP Control application tables do not persist bearer tokens.

The MCP gateway validates an incoming bearer with Supabase Auth and forwards that bearer to the paired WordPress site for local owner validation. The bearer is processed in request memory and is not written to the WP Control application audit table.

## WordPress-side ownership

Each paired WordPress site stores its expected WP Control owner UUID locally.

For a gateway call, WordPress validates the forwarded Supabase bearer against Supabase Auth, obtains the authenticated user UUID, and requires it to match the locally paired owner UUID.

This prevents the central site routing table alone from granting WordPress access.

## WordPress content and commerce data

Posts, pages, products, orders, SEO fields and related WordPress/WooCommerce data remain on the customer's WordPress installation.

The gateway fetches or forwards only what is necessary to execute the requested typed tool. It does not mirror WordPress content or order databases centrally.

## Audit on WordPress

Engagement Core maintains a local privacy-safe WP Control audit trail.

Local audit records store execution metadata and an input hash rather than raw tool input/content bodies.

## Public tool boundary

The public MCP server exposes typed WordPress operations only.

It intentionally does not expose:

- arbitrary SQL
- arbitrary filesystem access
- unrestricted WP-CLI
- arbitrary PHP/code execution
- WordPress administrator credential retrieval
- database credential retrieval
- hosting credential retrieval

## Content safety defaults

- New posts/pages default to `draft`.
- Publishing must be explicitly requested.
- Existing objects should be read before material updates.
- Reversible WordPress APIs and the undo journal are preferred.
- Duplicate-sensitive operations are marked non-idempotent in MCP metadata.
- Undo is explicitly marked destructive/non-idempotent for approval handling.

## Row-level security

The central WP Control tables enable RLS and use deny-direct policies for normal `anon` and `authenticated` database clients.

Gateway database access is performed server-side. End-user bearer tokens do not gain direct table access.

## Operational secrets

Infrastructure/service credentials belong in server-side secret stores or local WordPress configuration and must not be committed into the public plugin package or returned by MCP tools.
