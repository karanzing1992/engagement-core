# Engagement Core CRM — 0.1.0-dev

**Status:** review-only developer foundation, NOT production ready. Own WordPress-hosted data, optional external AI, no third-party CRM dependency.

## What's actually implemented
- WordPress-native installable plugin; isolated custom tables `eccrm_contacts`, `eccrm_identities`, `eccrm_events`.
- Admin-only contact dashboard with nonce-protected add form and 25 recent records.
- Authenticated REST API: GET/POST `/wp-json/eccrm/v1/contacts`; GET/PATCH `/wp-json/eccrm/v1/contacts/{id}`.
- Only users with `manage_eccrm` capability can read/write; the role is granted only to WP administrators on activation.
- Source-bound external IDs cannot be edited through the generic PATCH path. Unique nullable source/external identity index for deduplication.
- Local audit-event metadata with no raw customer PII duplication or outbound dispatch.
- Optional WordPress Abilities API read-only, internal-only ability (not exposed via REST).

## Staging installation
1. Review the exact source and use a *disposable test WordPress site*, WordPress >=6.9, PHP >=8.1.
2. Back up the site; install the ZIP as an ordinary WP plugin, activate, inspect all three SQL tables and the Engagement CRM admin menu.
3. Use synthetic records only. Test no-capability user denial for REST and admin form; test invalid names and duplicates.
4. Deactivate to disable API/dashboard. Tables remain intentionally so activation and rollback do not delete customer records.

## Nonfeatures / hard blockers
**NO** actual inbox, contact identity linking UI, messages, deal pipeline, staff roles, privacy export/delete, consent management, durable remote event delivery, retry workers, AI provider connectivity, channel send actions or cross-product writes. Database table presence is not functionality. All messages and live provider connects are disabled by omission.

## REST examples (use authenticated staging context)
`GET /wp-json/eccrm/v1/contacts?limit=25`
`POST /wp-json/eccrm/v1/contacts` with JSON `{ "display_name":"Synthetic Test", "source":"manual" }`
`PATCH /wp-json/eccrm/v1/contacts/1` with JSON `{ "lifecycle":"qualified" }`

No anonymous endpoint. WordPress cookie+nonce or a narrowly scoped account credential is required by WP for REST authentication; capability checks occur regardless.

## Source ownership / rollback
This is an **independent plugin** inside `engagement-core/packages/engagement-core-crm/`, not a replacement for Engagement Core v0.9.15, WACRM Central/Consumer, StayCore or Booking Core. Do not turn WACRM live / move any WhatsApp number. Deactivation keeps local data. Removal/export/erase is deliberately out of scope and is a production blocker.

See `docs/ENGAGEMENT_CORE_CRM_BUILD_PLAN_20261025.md` for the approved architecture, gates and tests.
