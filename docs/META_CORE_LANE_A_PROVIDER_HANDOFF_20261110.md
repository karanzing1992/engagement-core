# META CORE Lane A — Provider-interface development checkpoint

Date: 2026-11-10 | Owning repo: `karanzing1992/engagement-core` | Development branch: `feat/meta-core-lane-a-provider-transport-20261110`  
Parent: [Lane A PR #258](https://github.com/karanzing1992/engagement-core/pull/258) | Lane B: separate chat / no changes.

## Source-only implementation

- Added `src/lane-a-provider-boundary.mjs`: tenant/activation/WABA/phone-bound host-adapter **synthetic** invocation interface for every catalogued WhatsApp MCP capability, without fetching Meta tokens or creating a direct Graph proxy.
- The interface requires trusted principal and tenant, `environment=synthetic`, `grant=synthetic_verified`, separately verified policy approvals, a WACRM Central-owned route, and an explicitly injected `synthetic:true` adapter. It emits only allowlisted, non-PII receipts, never raw Graph responses, customer contacts, phone numbers, access tokens, webhooks or message content.
- Added negative tests for all 55 synthetic provider contracts, wrong tenants, disabled modes, lifecycle exclusions, revoked route, denied approvals and malicious/secret-bearing provider responses.
- Added **actual upstream Dojo 0.5.0 MCP dispatch** tests using an in-memory client for all 19 upstream tools, plus invalid input and SSRF-denial tests. This certifies upstream handler dispatch to test doubles, **not** actual WhatsApp Graph API operations or Cloud API acceptance.
- Existing 55-tool catalog, deny-by-default harness, Phase 1-E redaction guard and WACRM tokenless read broker remain unchanged.

## Residual A-lane engineering before certification for integration

1. Add exact JSON Schema compatibility adapters for every Dojo tool; some first-pass 55-tool contracts are intentionally conservative or incomplete. Never advertise them as exact provider schemas until verified against upstream code.
2. Implement vendor-specific read/write adapter contracts for management, Flows, QR, commerce, analytics, media, templates, and WACRM events with request/response fixture parity. This synthetic adapter boundary does not itself make external calls or implement those Graph endpoints.
3. Validate 429/retry/backoff, durable WACRM outbox/idempotency and operator authorization with independently replayable tests.
4. Inspect SDK v0.5.0 behavior with forced Zod 4 override, specifically non-read tools, and complete independent security review.
5. Deliver immutable interface manifest for Lane B. Lane B alone owns live Central OAuth grants, WACRM deployment, credentials and integrated staging.
6. Keep the source PR draft; no merge/deploy/sends or live registration until owner release.

## Reuse and cost gate

Reuse pinned [DojoCodingLabs WhatsApp SDK/MCP (MIT)](https://github.com/DojoCodingLabs/whatsapp-adapter), existing first-party WACRM Central crypto/broker, Node built-in crypto and current tests. No new dependencies, paid services, Meta traffic, tokens, account changes or customer data. The provider adapter interface is the smallest needed integration glue; it is not a duplicate CRM, webhook server or OAuth issuer. The official Meta [Postman Business Platform](https://www.postman.com/meta/whatsapp-business-platform/overview) is the target API reference. Rollback: abandon new unmerged branch. No database or production changes.

**Truth classification: SOURCE_ONLY / SYNTHETIC_TESTED (once CI verifies).** Ashwakaal Support Channels is excluded. No VERIFIED_LIVE Master event.
