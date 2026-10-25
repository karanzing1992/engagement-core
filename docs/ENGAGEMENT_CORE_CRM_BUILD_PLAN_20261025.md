# Engagement Core CRM — source of truth and v0.1 development ledger
**Owner brief (25 Oct 2026):** “Crm inside wp ai any from outside” followed by “Document and start building.”
**Code owner:** `karanzing1992/engagement-core`; dedicated package `packages/engagement-core-crm`. Branch: `feat/eccrm-wp-native-foundation-20261025`.
**Stage:** SOURCE_ONLY / OFFLINE_TESTED; **NOT** WordPress staging installed or production certified. No merge, provider credentials, customer data or release authorized.

## Non-negotiable contract
- All core CRM contacts, conversations, identities, tasks, workflows, permissions, event/audit history and administration **inside WordPress**, stored in custom site-prefixed WordPress tables. No external CRM service/database as an authoritative record.
- External AI is entirely optional and interchangeable (provider-neutral adapter; scoped WordPress REST/Abilities interface). CRM must remain manually operational offline.
- Bidirectional, authorized adapters for Engagement Core, StayCore, Booking Core, WhatsApp, email, social, website and external webhook/API consumers. Ownership stays with authoritative systems: StayCore reservations, Booking Core bookings, Engagement Core campaigns.
- No unauthorized outbound messages, live WhatsApp Business-number migration, transaction mutations, campaign publication or external AI data sharing.
- Standalone commercially redistributable WordPress plugin and own product identity. GPL-compatible WordPress package; independent AI services may be separately licensed. Verify third-party redistribution/trademark/privacy obligations before release.
- Prevent cross-customer credential/record sharing, minimize PII, define export/erase/retention and consent gates before real customer records.

## Requirement → evidence (RTM)
| ID | Requirement | Acceptance gate | State at v0.1 |
|---|---|---|---|
| CRM-01 | Complete self-sufficient WordPress CRM | Local contacts, inbox, pipelines, tasks, workflows available without AI | **PARTIAL** contacts and local storage only |
| CRM-02 | AI from any outside provider | Provider-neutral tool adapters with explicit per-action authorization; disabled gracefully | **PARTIAL** internal-only WordPress ability; no providers connected |
| CRM-03 | Multichannel inbound/outbound | Each authorized provider has reliable receipts, opt-in and negative tests | NOT STARTED |
| CRM-04 | Engagement, Stay and Booking Core | Versioned adapters, distinct authority, tenant identity reconciliation | **PARTIAL** identity schema only |
| CRM-05 | Multiple internal/external destinations | Transactional outbox, idempotency, backoff, dead letters, alerts and recovery | **PARTIAL** local-only event ledger, no dispatch |
| CRM-06 | Native independent product | Installable ZIP, isolated schema, upgrades, license inventory, rollback | **PARTIAL** developer ZIP/smoke only; no WordPress staging installation |
| CRM-07 | Security, privacy, commercial rights | Least privilege, verified deletion/export, consent, backups and notice | **PARTIAL** admin capability/nonce and no live external sends |
| CRM-08 | Phone-first modern UI | Real viewport, accessibility, mobile interaction tests | NOT STARTED; initial WP-native admin |
| CRM-09 | Dell Dev Tool Yard release governance | Protected branch/worktree, separate QA, owner approval, deploy receipt | **PARTIAL** source branch and offline tests; full governor QA not certified |

## Reuse and open-source/cost gate (Golden Rule 0)
- **Reuse first-party** [WACRM Consumer v0.1.0](https://github.com/karanzing1992/moksha_wordpress/blob/main/packages/wacrm-consumer/wacrm-consumer.php) signed relay and safety principles *through an adapter*, without altering live Meta configuration. Existing Consumer is **not** a finished two-way inbox.
- **Reuse first-party** [Engagement Core v0.9.15](https://github.com/karanzing1992/engagement-core/blob/main/engagement-core.php) social/publishing/secrets/scheduling adapters without touching the live plugin.
- **Reuse upstream** [WordPress Plugin/REST API](https://developer.wordpress.org/plugins/) and [Abilities API](https://developer.wordpress.org/apis/abilities-api/) (WordPress GPLv2+, WP >= 6.9) for authentication, capabilities, hooks and discoverable tools.
- Future background worker: evaluate [Action Scheduler](https://github.com/woocommerce/action-scheduler) (GPL-3.0-or-later, pin/review before inclusion), server cron, retries and DLQ; **none bundled or activated yet**.
- Alternatives considered: Groundhogg (GPLv3+, commercial core fork would obligate derivative redistribution); FluentCRM (edition/premium feature constraints); existing WACRM (messaging adapter only). User expressly selected new first-party WordPress CRM, not a vendor fork; custom code limited to missing CRM domain glue.
- **Added paid services/licenses:** none. Source construction uses existing tools; compute/hosting/AI costs are not automatically zero.

## What v0.1.0-dev implements
`packages/engagement-core-crm/` standalone plugin with admin menu/nonce form, three custom WordPress tables (contacts, external identities and local-only event metadata), contact validation, source-bound deduplication, contact list/get/create/update REST APIs requiring `manage_eccrm`, internal-only permission-gated contacts-list ability, no outbound delivery, and synthetic PHP smoke tests.

**Offline evidence:** PHP 8.4.24 lint passed for all PHP files; 16 synthetic smoke assertions passed. This is not a WordPress/DB E2E result. Package ZIP and its SHA must be recorded separately and compared with committed sources.

## Mandatory next gates
1. Independent code review of schema, REST/abilities exposure, GDPR-like export/delete/retention, capabilities, concurrent identity update, WP deactivation and audit durability.
2. Disposable isolated WordPress >=6.9 / PHP >=8.1 installation, table integrity, CRUD under authenticated/unauthenticated roles, denied nonce, repeated activations, migration, data persistence, mobile viewport.
3. Complete conversation/inbox UI, pipeline, tasks and event processing. Implement persistent queue and idempotent multi-destination delivery before any webhook or outbound channels.
4. Verify WACRM official Meta Business App Coexistence separately; no production phone changes; preserve existing pilot safety gates. Integrate Engagement Core/StayCore/Booking Core with no data ownership breach.
5. Provider-neutral external AI adapters with least-privilege tools, configurable human approval, safe fallback when AI offline.
6. Commercial license/SBOM/privacy/pentest/backup-restore/rollback, independent QA and explicit owner go/no-go prior to public ZIP release or deployment.

## Rollback and separation
Initial ZIP is **staging only**. Plugin deactivation removes routes and UI, **retains tables** intentionally. No code is being merged or installed on Moksha, Andaz, StayCore or Booking Core. Ashwakaal — Support Channels remains a distinct workstream with separate accounts/credentials/customer records.

**Truth labels:** DOC_VERIFIED and SOURCE_ONLY do not imply QA_CERTIFIED, OWNER_ACCEPTED, MASTER_SYNCED, STAGING_VERIFIED or PRODUCTION_GO.
