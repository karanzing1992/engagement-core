# Engagement Core CRM — Master Product Specification & Build Status
**Document version:** 1.0 · **Date:** 2026-10-25 · **Owner workstream:** Engagement Core CRM
**Status:** DOCUMENTED / DEVELOPMENT SOURCE EXISTS / **NOT STAGING-CERTIFIED / PRODUCTION NO-GO**
**Canonical status path:** `engagement-core/docs/ENGAGEMENT_CORE_CRM_SOURCE_OF_TRUTH_20261025.md` on `main`
**Implementation:** [Draft PR #73](https://github.com/karanzing1992/engagement-core/pull/73), branch `feat/eccrm-wp-native-foundation-20261025`
**Build:** `packages/engagement-core-crm` version `0.1.0-dev`; standalone plugin **not merged into `main`**.
**Instruction for development:** **Documentation checkpoint first.** Do not treat this document as authorization to continue coding or to merge/install/publish; await the next owner execution instruction.

## 1. Frozen owner requirement and architecture decision

Owner direction, 25 October 2026:
- The CRM must be **a self-sufficient, first-party, independently installable WordPress plugin**. **All core CRM data, inbox, records, access control, automations and operational UI live on the customer's WordPress site** and WordPress-managed SQL database.
- **AI may run anywhere outside WordPress** (cloud, customer self-hosted, local models), through selectable provider-neutral adapters. External AI must be **optional**, not a dependency for ordinary CRM operations or the authoritative store for CRM records.
- **Omnichannel**: receive and send authorized communications/data across WhatsApp, Instagram, Facebook, Telegram, email, web chat, forms, other supported channels, and named external APIs.
- **Bidirectional integrations** for **Engagement Core**, **StayCore** and **Booking Core**, plus other authorized external destinations. The CRM coordinates customer context and workflows, **not** uncontrolled cross-system writes.
- **Commercially distributable, our own code and brand**. Avoid a Groundhogg/FluentCRM CRM-core dependency. Reuse our first-party integrations and legally suitable FOSS infrastructure; check all component licenses/rights.
- Mobile-first operator experience, granular staff rights, auditability, bounded event delivery, data privacy, backup/restore, plugin upgrades/rollback and separation between customers.

### Explicit negative decisions
1. **No separately hosted CRM backend** or vendor-managed master customer database; WordPress is the CRM system of record.
2. External AI must not read broad CRM data by default, own contact storage, bypass WordPress capabilities, or send communications without the configured operator/consent policy.
3. Neither StayCore reservations nor Booking Core appointment/availability data become CRM-owned authoritative records.
4. No live Meta WhatsApp app migration/deregistration/coexistence changes without separate owner approval and vendor verification.
5. No new paid dependencies or external services without critical-necessity documentation and explicit purchase authorization.
6. No reuse of Ashwakaal Support Channels accounts, credentials or customer data; separate workstream.

## 2. Target logical architecture (planned)

```text
Customer WordPress installation (self-contained CRM)
┌──────────────────────────────────────────────────────────────────┐
│ Engagement Core CRM plugin                                      │
│ Contacts + identity links + conversations + inbox + deals       │
│ Tasks + workflows + consent + audit + dashboard + permissions   │
│ Dedicated WP-prefixed SQL tables (customer-site-owned)          │
│ Authenticated REST API / WordPress Abilities API                │
│ Channel adapters / internal adapters / event outbox + DLQ       │
│ Reliable workers (server cron; Action Scheduler evaluation)     │
└─────────┬───────────────────────────────────────────┬────────────┘
          ↕ signed/integrity-checked integrations      ↕ scoped AI
 Engagement Core ↔ StayCore ↔ Booking Core         Any authorized external
 WhatsApp ↔ Email ↔ Telegram ↔ Web ↔ Social       AI/model/agent provider
 Other authorized APIs, events and data sources       (optional)
```

Architecture notes:
- **One CRM installation = one primary isolation boundary.** Multisite/shared-database/multi-customer arrangements require separate tenancy/security tests; do not assume a shared install isolates customers.
- Standardized inbound events and outbox intents shall include `event_id`, `tenant/site_id`, `source_system`, `entity_type`, `entity_external_id`, `occurred_at`, `schema_version`, `consent_context`, correlation/idempotency keys, and redaction policy. This is a **target contract**, not implemented wire format.
- On inbound: authenticate source → validate/limit payload → deduplicate → map identity with least-privilege → persist domain event → update CRM state → enqueue downstream work → acknowledge only when safely stored.
- On outbound: operator/agent authorization → consent and policy check → transactional outbox → destination adapter → retry/backoff → delivery receipt/reconciliation → dead-letter/alerts after bounded failures.
- No source system may silently overwrite another system's authoritative fields. Conflict policy, provenance and reconciliation must be explicit.

## 3. Data model and domain boundaries

| Domain | WordPress CRM owns | External authority / separation |
| --- | --- | --- |
| Contacts | CRM profile, local identity references, tags, lifecycle, consent pointers | Source identity must be verified before merging |
| Conversations | Customer-facing interaction thread, assignment, approved drafts, delivery state | Channel provider owns transport receipt/provider message ID |
| Opportunities | CRM opportunities, stage, owner, follow-up tasks | Billing/booking transactions remain with owning core |
| Guest context | Authorized references and derived CRM context | **StayCore** owns guest stay/reservation/check-in state |
| Booking context | Authorized references, follow-up and reminder state | **Booking Core** owns availability, services, appointments |
| Engagement | Customer journey and campaign interaction references | **Engagement Core** owns publishing/campaign operations |
| Events | Site-local audit, durable outbox, retry state, receipt trace | Provider payload ownership and privacy policy enforced |
| AI context | Short-lived, minimized task input, policy and approval trace | External provider only receives explicitly permitted context |

Suggested table families for future design: `contacts`, `identities`, `organizations`, `conversations`, `messages`, `channels`, `opportunities`, `tasks`, `workflow_definitions`, `workflow_runs`, `consent`, `events`, `outbox`, `dead_letters`, `audit`, `integration_accounts`. **Only `contacts`, `identities` and `events` have source-code schema in v0.1.0-dev; the others are NOT built.**

## 4. v0.1.0-dev — exact existing work

**Source evidence:** [plugin README](https://github.com/karanzing1992/engagement-core/blob/feat/eccrm-wp-native-foundation-20261025/packages/engagement-core-crm/README.md); [source in draft PR #73](https://github.com/karanzing1992/engagement-core/pull/73).

Implemented *in an unmerged development branch*:
- Standalone WordPress plugin bootstrap (WP >=6.9, PHP >=8.1), no dependency on another CRM vendor.
- Three local WordPress-prefixed SQL table definitions: `eccrm_contacts`, `eccrm_identities`, `eccrm_events`.
- `manage_eccrm` capability assigned to site administrators by activation.
- Admin-only contact entry form with WordPress nonce, validation and bounded recent-contact table; not a finished mobile-first React interface.
- Permission-checked REST contacts API: GET/POST `/wp-json/eccrm/v1/contacts`, GET/PATCH `/wp-json/eccrm/v1/contacts/{id}`.
- Validated basic contact fields, source/external-ID deduplication and protection against generic PATCH changing source identity.
- Local-only event records of changed field names (no transport worker, no payload replication of raw contact fields).
- Read-only internal WordPress Abilities API `engagement-core-crm/list-contacts`, with `show_in_rest=false` and capability check. **No external AI connection or external ability permission certification.**

**Developer package:** `engagement-core-crm-v0.1.0-dev-STAGING-ONLY.zip` (prior session attachment); SHA-256 `ef82995f23b63d41e928f9c2bbd32314a88f3a5d6a09c1f07e893daa4924dd93` as recorded in offline QA. **Do not infer the GitHub repository hosts a downloadable ZIP release.**

**Offline QA reported and recorded:** PHP 8.4.24 lint on all plugin PHP files plus synthetic test harness; 16/16 synthetic smoke assertions passed; ZIP contents and archive integrity checked. GitHub source was read back. Dell development lane successfully confirmed the Git branch SHA via `git ls-remote`; **PHP CLI was absent on that Dell lane**. These are **not** real WordPress/database integration tests, full independent Dev Tool Yard certification or production acceptance.

## 5. Explicitly missing / blocking capabilities

| Priority | Component | Current state | Required acceptance evidence |
| --- | --- | --- | --- |
| P0 | Real WordPress plugin installation | **Untested** | Isolated WP + SQL activation/migration/roles/CRUD/auth/CSRF test and rollback |
| P0 | Unified inbox & conversations | **Not built** | Inbound text/media, reply, assignment, notes, delivery state and thread integrity |
| P0 | Channel adapters | **Not connected** | Provider approval, authenticated receive/send, consent, idempotency, receipts per channel |
| P0 | Durable event processing | **Not built** | Transactional outbox, queue, bounded retry/backoff, DLQ, monitoring/reconciliation |
| P0 | Integration contracts | **Not implemented** | Engagement Core/StayCore/Booking Core API schema, authority map, errors, consent |
| P0 | Security and data lifecycle | **Incomplete** | Granular roles, least privilege, audit, backup, retention, export/delete and threat review |
| P0 | Human approval policies | **Not built** | Consequential actions rejected by default; evidence of approved/rejected cases |
| P1 | Leads, pipelines, organizations, tasks | **Not built** | CRUD + transitions + assignment + workflow integration |
| P1 | Mobile-first production UI | **Not built** | Real phone viewports, keyboard navigation, accessibility and agent usability |
| P1 | Provider-neutral AI adapters | **Not connected** | BYO cloud/local providers, scoped tools, no-AI fallback, provider switching |
| P1 | Commercial release system | **Not built** | GPL-compliance/SBOM, independent ZIP/updates, branding, license terms, rollback |
| P1 | Load/upgrade/disaster recovery | **Unverified** | Benchmarks, WP upgrades, DB migrations, restore exercise and tenant isolation tests |

**Current overall decision:** **DEV SOURCE GO / STAGING NOT YET CERTIFIED / PRODUCTION NO-GO**.

## 6. Original WACRM separation

[2026-10-25 WACRM production audit](https://github.com/karanzing1992/engagement-core/blob/main/docs/ENGAGEMENT_CORE_WA_CRM_LATEST_UPDATE.md) remains independently authoritative for the existing WhatsApp CRM/broker.

- WACRM Central + Consumer live implementation is in private `karanzing1992/moksha_wordpress`, not inside the new CRM package.
- WACRM Consumer v0.1.0 already has HMAC-signed relay receiver, customer-hosted event/contact data and a restricted event viewer. That is a **candidate adapter**, not a certified two-way inbox.
- WACRM draft PR #52 for launch-safety gates was unmerged at the latest audit; Meta approval and official Business App Coexistence must be separately confirmed.
- New CRM must **not migrate, deregister, onboard or modify the existing WhatsApp Business mobile-app number** as part of source development.

## 7. Source reuse, licenses, costs

| Resource | Reason | Rights / state |
| --- | --- | --- |
| Existing Engagement Core code | Social adapters, publishing, secrets, existing tool routing | First-party; reuse by bounded connectors; no live plugin edits |
| Existing WACRM source | Signed Meta webhook handling, routing/event evidence | First-party; preserve sandbox vs production and separate customer site data |
| [WordPress Plugin / REST APIs](https://developer.wordpress.org/plugins/) | Native CRM hosting, auth, routes | WP GPL ecosystem; reuse now |
| [WordPress Abilities API](https://developer.wordpress.org/apis/abilities-api/) | Discoverable, scoped AI actions | WP native; internal ability started |
| [Action Scheduler](https://github.com/woocommerce/action-scheduler) | Possible reliable job scheduling | Review pinned version, GPL-3.0-or-later and overlap before adopting; not bundled |
| Groundhogg / FluentCRM | Alternative full CRM engines | Rejected as product-core dependency by owner; do not fork/copy code without license review |

- No new paid tools, APIs, subscriptions or infrastructure were provisioned for this source.
- First-party ownership of original plugin copyright and branding is not a waiver of WordPress/GPL compliance, third-party dependency terms, partner API terms, privacy requirements or customer rights. Seek legal review before white-label commercial launch.
- Source code, plugin ZIP, staging validation, independently accepted release and live installation are **different evidence states**.

## 8. Formal build and governance sequence (future, not authorization)

**Gate 0 — brief freeze (THIS DOCUMENT):** Preserve original owner requirement, scope/negative constraints, source links and explicit no-go. Owner may revise by versioned change request.

**Gate 1 — development environment certification:** Dell Dev Tool Yard workspace and controls, PHP CLI or controlled PHP container, isolated WordPress, source-lock/lease, test artifacts, runtime and negative cross-project access verification. Do not silently route development through unrelated Shaadi or another venture.

**Gate 2 — foundation validation:** Real WordPress activation/migration, ID and privilege tests, REST and nonce checks, denial tests, retention/export/erase specification, database rollback.

**Gate 3 — self-sufficient CRM modules:** Contacts/identity reconciliation, conversations/inbox, staff ownership, lead pipeline, tasks, offline/no-AI workflows and mobile UX; capture screenshots and functional tests.

**Gate 4 — reliable integrations:** Versioned adapters for Engagement Core/StayCore/Booking Core, transactional outbox, per-destination receipts, idempotency, privacy/conflict rules, DLQ and bounded retries; synthetic identities only.

**Gate 5 — external AI:** Provider-neutral BYO configuration; scoped REST/Abilities actions, per-install and per-tenant policy, human approvals, redacted prompts and AI-off fallback.

**Gate 6 — independent QA and commercial release:** Security/tenancy and media tests, WP compatibility/multisite decision, load, restoration, SBOM/GPL review, reproducible signed ZIP, update/rollback tests, owner acceptance. Production deploy only via separately authorized change.

**Required quality states:** `PROPOSED`, `SOURCE_ONLY`, `OFFLINE_TESTED`, `STAGING_VERIFIED`, `INDEPENDENT_QA_PASSED`, `OWNER_ACCEPTED`, `RELEASE_AUTHORIZED`, `PRODUCTION_VERIFIED`. Never substitute one for another.

## 9. Checkpoints and next-step control

- **Current PR:** [#73 — draft](https://github.com/karanzing1992/engagement-core/pull/73), unmerged, development branch `feat/eccrm-wp-native-foundation-20261025`.
- **Detailed build plan:** [ENGAGEMENT_CORE_CRM_BUILD_PLAN_20261025.md](https://github.com/karanzing1992/engagement-core/blob/feat/eccrm-wp-native-foundation-20261025/docs/ENGAGEMENT_CORE_CRM_BUILD_PLAN_20261025.md).
- **Offline QA receipts:** [ENGAGEMENT_CORE_CRM_OFFLINE_QA_20261025.md](https://github.com/karanzing1992/engagement-core/blob/feat/eccrm-wp-native-foundation-20261025/docs/ENGAGEMENT_CORE_CRM_OFFLINE_QA_20261025.md).
- **Historical WACRM:** [ENGAGEMENT_CORE_WA_CRM_LATEST_UPDATE.md](https://github.com/karanzing1992/engagement-core/blob/main/docs/ENGAGEMENT_CORE_WA_CRM_LATEST_UPDATE.md).

**At this checkpoint: document and freeze.** Do not proceed with plugin code changes, installation, running on production, Git merge, service activation, AI access, Meta onboarding or customer data migrations under this instruction. The deterministic next action, only upon the next owner development instruction, is independent WordPress staging validation through the approved Dell Dev Tool Yard, followed by the conversation/inbox module.

**Reporting:** This is a documentation-only source update, **not** a verified new platform/channel integration; do not claim a released capability or a Master event publication. The existing WACRM and Ashwakaal separation remains binding.
