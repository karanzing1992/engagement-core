# META CORE — WhatsApp Lane A Capability Research, MCP Contract & Synthetic QA

Date: **2026-11-10** | GitHub owner: `karanzing1992` | Repo: `engagement-core`  
Branch: `feat/meta-core-lane-a-mcp-capabilities-20261110`  
Parent draft: Phase 1-E [PR #257](https://github.com/karanzing1992/engagement-core/pull/257), stacked on Phase 1-D [PR #215](https://github.com/karanzing1992/engagement-core/pull/215).

**State: SOURCE_ONLY / SYNTHETIC MCP CONTRACT. NOT LIVE WHATSAPP, NOT GRAPH-EXECUTABLE, NOT OAUTH CONNECTED.**

## Authority and research

Primary vendor inventory:
- [Meta official WhatsApp Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api) and [workspace overview](https://www.postman.com/meta/whatsapp-business-platform/overview).
- [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/) — Sept 23 2026 update: templates required for business-initiated messaging outside 24h service window; human escalation path for automated support; privacy and consent rules apply.
- [Meta Flows collection/reference](https://www.postman.com/meta/whatsapp-business-platform/request/dxiu763/publish-flow): create/manage/send Flow operations; publishing is not reversible.
- [Meta WABA phone numbers reference](https://www.postman.com/meta/whatsapp-business-platform/request/o84xigu/phone-numbers).

Reuse first:
- Existing META CORE Phase 1-D read-only HMAC [broker](../integrations/meta/whatsapp-mcp/src/wacrm-central-read-broker.mjs) and Phase 1-E [response guard](../integrations/meta/whatsapp-mcp/src/wacrm-broker-response-contract.mjs): **retain**, no new transport.
- Existing WACRM Central crypto and Consumer webhook/inbox ownership in the *separate* [moksha_wordpress PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134), not modified in Lane A.
- [DojoCodingLabs/whatsapp-adapter](https://github.com/DojoCodingLabs/whatsapp-adapter), MIT, pinned `@dojocoding/whatsapp-sdk@0.10.0`, `@dojocoding/whatsapp-mcp@0.5.0`: **reuse its 19-tool embedded MCP/SDK surface**; [upstream tools contract](https://github.com/DojoCodingLabs/whatsapp-adapter/blob/main/docs/mcp/tools.md). The inherited forced Zod 4 override beyond its declared Zod 3 semver remains a review gate.
- Dojo's `createWhatsAppToolset` is an **embedded** integration fit. Do not create another stdio/Web server, webhook receiver, CRM or public OAuth endpoint in Lane A. [Upstream embedded guide](https://github.com/DojoCodingLabs/whatsapp-adapter/blob/main/docs/mcp/embedded.md).

**Open source / reuse / cost:** first-party owned code + upstream MIT + native Node.js only, no new dependencies; this sprint has **zero provider API calls, zero paid sends, zero credential use**, no hosted service. Any future Meta charges remain under separately approved cost and recipient gates. No vendor SDK or binary is copied into the repository.

## Functional inventory and status

The registry in `integrations/meta/whatsapp-mcp/src/lane-a-capability-catalog.mjs` declares **55 MCP-compatible tools** grouped as:

| Area | Tool families | Status |
| --- | --- | --- |
| WABA / phone / profile | account, phone listing/metadata, quality, subscription read, business profile read/write | Read/write contracts, pending host implementation |
| Customer messages | text, image, audio, voice, video, documents, interactive buttons/lists, location, contacts, templates, reactions, stickers | 19 upstream Dojo MCP tools reused where listed; extensions marked host |
| Commerce messages | product, multi-product, catalog | Host integration conditional |
| Templates | list/get via existing tokenless broker, create/update/delete, available analytics | Read broker already separately synthetic-tested; new operations unbound |
| Media | metadata, URL upload, deletion | Dojo existing metadata/upload; deletion host-gated |
| WhatsApp Flows | list/get/assets/metrics, create/update/upload JSON/publish/deprecate/delete, send | Host integration; irreversible operations separately gated |
| QR / commerce settings | list/create/delete QR, commerce read/update | Conditional host integration |
| Inbox / delivery | read inbound events, message/delivery status | **WACRM-owned**, not new Meta Graph history endpoints |

**Important distinctions:** a declared JSON Schema is not provider request/response schema parity. Some advanced templates, rich interactive products, Flow JSON assets and regional features require additional vendor contract fixtures and approved owner adapters. `integrationState=synthetic_contract_only` is deliberately attached to every tool. The harness does **not** call the installed Dojo MCP dispatcher or the WACRM broker. It only produces offline proof of validated permission gates.

**Excluded from this agent-facing MCP registry:** phone register/deregister/migrate, coexistence reconfiguration, WABA subscribe/unsubscribe, credit line sharing, account transfer, business user assignment, group operations, calling, specialized regional payments. Such operations require separate capability research, eligibility, owner authorization and change control—not merely adding a tool.

## Permission separation

Vendor scopes (actual entitlement must be verified by Lane B/Meta app):
- `whatsapp_business_management`: WABA/templates/business-management operations where supported.
- `whatsapp_business_messaging`: sending, media and message acknowledgements where supported.
- `business_management`: conditional portfolio/asset operations, **not** automatically requested.
- WACRM internal `wacrm:read` is an **internal capability marker**, not a Meta permission.

MCP resource grants are **independent of** Meta app scopes. Every future call must pass verifiable issuer/audience/client identity and explicit tenant/actor/capability scope before the WACRM Central route, SDK or Graph transport. Lane B owns those issuer/grant details and the dedicated WACRM staging.

### Lane A synthetic protection

`createWhatsAppLaneAMcpHarness` exports `listTools`, `listCapabilityInventory`, `callTool` with standard MCP Tool and CallToolResult shapes **but no transport or live execution path**.

1. **All 55 tools hidden by default.** Host must explicitly supply per-tool grants; synthetic writes require an additional opt-in.
2. Reject unverified principal and wrong `wacrm_[hex40]` tenant, deny before planning. The model cannot provide tenant, WABA, phone, tokens, client ID, or approval in tool arguments.
3. Validate bounded plain-object structured JSON, no accessors/proxy-shaped payloads, unknown fields or sensitive-key injection.
4. A send under the 24h window requires trusted recipient opt-in, open service window and separate spend approval; template sends require trusted template approval instead of the open-window test. No claims about these being sufficient for live Meta compliance.
5. Profile/template/Flow mutations require trusted operator approval; irreversible operations require a second independent irreversible-approval flag.
6. Media links are syntactically HTTPS/public-host checked; **actual host DNS resolution/redirect/egress controls remain a separate integration gate**.
7. Return only a deterministic synthetic receipt with hash, operation and adapter family—never recipient, OTP, media URL, bearer, Graph response or incoming message. No network callback is accepted.
8. WACRM owns webhook signature verification, retry/outbox, idempotency, message state, real media bytes, consent history and customer records. Never recreate them within this MCP surface.

This branch is a **contract development increment**, not the final production-ready 55-tool implementation. The next Lane A implementation increment maps Dojo's existing 19-tool schemas exactly and adds owner-reviewed adapter/contract fixtures for each extension using synthetic Graph/WACRM transports.

## QA acceptance and cross-lane handoff

Mandatory checks:
- All 55 unique tools enumerate correctly in explicitly granted synthetic mode; none have default grants.
- All 55 accept canonical safe synthetic inputs and return **offline-only** MCP receipts.
- No account/phone registration tools appear in the registry.
- Negative tests: cross tenant, unknown tool, ungranted tool, unauthorized send, template approval, 24h policy, spend approval, irreversible action, input poisoning, malformed URLs, media-link choice, template WABA binding and Flow JSON parsing.
- Existing parent Phase 1-D/1-E suite and pinned npm audit pass on exact SHA, verified from GitHub Actions.
- Future host-integrated tests must verify real Meta v26 request/response contract and WACRM crypto + tokenless broker parity **without live traffic** first.

**Lane B interface when certified:** per-resource verified bearer identity and resource grants; per-tenant WACRM-bound asset and credential authority; WACRM's approved outbound outbox and inbound webhook status; staged configuration/secrets; owner release controls. Never take raw bearer credentials or WABA IDs from MCP tool arguments.

**Deployment/rollback:** This is an additive stacked draft with no production writes, account permission changes, staging deployment, customer data migration or live Meta calls. Roll back by closing the draft branch/PR. Do not merge the parent drafts, modify Lane B's OAuth work, or publish a `VERIFIED_LIVE` Master event for a source-only increment. Ashwakaal Support Channels remains separate.
