# Engagement Core CRM — 0.2.0 development UI

**Status:** Mobile-first native WordPress CRM UI / Dell isolated staging, **owner visual acceptance pending**. Not a production CRM release. All data for CRM contacts stays in WordPress.

## Functional, verified UI
- Tabler 1.7.0 MIT-based responsive shell (desktop sidebar, mobile bottom navigation).
- Overview with real WordPress contact counts, recent contacts, real local audit events.
- Contacts: authenticated list, bounded search, lifecycle filtering, create, detail editing and lifecycle updates.
- Activity: actual local event ledger, not fabricated interactions.
- Contact edits use WordPress REST requests with WordPress nonce and `manage_eccrm` authorization.
- Mobile modal operates as a bottom-sheet, with labeled inputs and inline validation.

## Building a standalone installable WordPress ZIP
1. Clone the source from `feat/eccrm-tabler-ux-20261025` or the eventual approved release ref.
2. Run `sh packages/engagement-core-crm/scripts/build-tabler.sh` from the repository root (requires npm/internet at **build time only**). This fetches a pinned Tabler 1.7.0 MIT stylesheet; the script refuses an altered SHA-256 tarball.
3. Confirm `packages/engagement-core-crm/assets/css/tabler.min.css` exists. Package the **whole** `engagement-core-crm` folder in the ZIP. The shipped plugin uses local assets and needs no UI CDN or npm runtime.
4. Install into an **isolated disposable WordPress** >=6.9, PHP >=8.1. Confirm activation/schema/capability before testing synthetic contacts. Do **not** install this branch on production.
5. Preserve the bundled `assets/TABLER-LICENSE-NOTICE.txt`. Tabler's third-party extra widget/plugin libraries are NOT included.

```sh
sh packages/engagement-core-crm/scripts/build-tabler.sh
cd packages
zip -q -r engagement-core-crm-mobile-QA-STAGING-ONLY.zip engagement-core-crm -x 'engagement-core-crm/tests/*' 'engagement-core-crm/scripts/*'
```

## Local API
`GET /wp-json/eccrm/v1/overview`, `GET /wp-json/eccrm/v1/activity`, `GET/POST /wp-json/eccrm/v1/contacts`, `GET/PATCH /wp-json/eccrm/v1/contacts/{id}`. On plain-permalink WordPress sites, REST URLs may be query-string form. REST authentication and capabilities are always enforced.

## Explicit nonfeatures
**NOT BUILT:** unified WhatsApp/Instagram/email inbox, channel publishing/replies, AI model adapters, StayCore/Booking Core transactional adapters, sales pipelines, team-specific ACL, retention/export/erase lifecycle, production backup/restore workflows. No live customer data, outbound sends or external AI are authorized.

## QA
[Mobile-first real-browser QA handover](../../docs/ENGAGEMENT_CORE_CRM_TABLER_MOBILE_UX_QA_20261025.md). Dell isolated WordPress and Chrome 27/27 functional E2E assertions passed, including browser create/edit. Browser checks do not constitute independent security/accessibility or production certification.

**Next gate:** owner user test. Keep this draft PR unmerged; do not start additional CRM modules until explicit acceptance.
