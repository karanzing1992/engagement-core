# Engagement Core CRM v0.2.0 mobile-first Tabler UI — QA/Handover (2026-10-25)

**Stage:** Isolated Dell WordPress staging / browser QA verified; **USER ACCEPTANCE PENDING**, NOT production certified.
**Code branch:** `feat/eccrm-tabler-ux-20261025` → base `feat/eccrm-wp-native-foundation-20261025` (unmerged).
**Authority:** Customer and CRM records hosted only in the self-contained WordPress plugin. External AI remains optional and unconnected.
**Rejected predecessor:** The stock WP admin form from v0.1.0 is retained via the base branch for rollback; user explicitly rejected its visual UX.

## Software reuse
- Tabler `@tabler/core@1.7.0` MIT dashboard kit. Pinned NPM tarball SHA-256: `9de5840569dbb946989b4870f4bf02f3570369cccb5ecbfa34c76477d29a16fa`.
- Built into the Dell stage at `assets/css/tabler.min.css` and loaded via local WP `wp_enqueue_style`. The upstream asset is **not** a first-party authored source; run `sh scripts/build-tabler.sh` before packaging/installing outside Dell. Bundle this generated CSS in customer ZIP; the raw GitHub source tree by itself requires this build step.
- Full MIT notice in `assets/TABLER-LICENSE-NOTICE.txt`. No CDN, ApexCharts, premium Tabler widgets, non-permissive component imports, or paid subscriptions.
- CRM UI runtime `assets/js/workspace.js` is original code connected to WordPress REST with logged-in operator and `X-WP-Nonce`.

## Actual implemented UI
- Tabler-based custom CRM workspace with mobile bottom navigation and desktop sidebar, working Overview / Contacts / Activity views (three real views, not placeholders).
- Overview counts pulled from SQL: total contacts, qualified leads, customers. Recent real contacts and local event metadata.
- Contact creation, read, update, search (name/email/phone), lifecycle filters, bounded pagination and result refresh.
- Secure native dialog: mobile bottom sheet and tablet/desktop modal, with inline errors.
- Existing per-site `manage_eccrm` permission. Unauthenticated API requests denied; no broadcast or external AI actions.
- A scope notice explicitly discloses unbuilt omnichannel messaging, external AI, StayCore and Booking Core adapters.

## Browser QA evidence
- Dell isolated WordPress 7.1.3 / PHP 8.2.35 / MariaDB with synthetic contacts only.
- Playwright with system Chrome **27/27 end-to-end assertions passed** after correcting an API query-string path bug and the contact-modal post-save refresh timing.
- End-to-end cases: WordPress login, CRM page HTTP 200, live summary counts, mobile bottom navigation, contact listing, search, modal open, create, prefill/read, lifecycle edit, lifecycle filter, real activity view, drawer open/close, JavaScript exception check, responsive UI.
- Vertical mobile baseline: 390 x 844 and 360 x 800. Supplementary no-horizontal-overflow checks: 320, 375, 414, 768, 800, 1024 and 1440px.
- Screenshots: `screens/tabler-ux/390-overview.png`, `390-contacts.png`, `390-editor.png`, `390-activity.png`, `360-overview.png`, `768-overview.png`, `1440-overview.png` saved on Dell under `/var/lib/generic-linux-automator-exec/eccrm-wordpress-qa-20261025/`; screenshots are **QA artifacts, not committed to product source**.
- UI scope tests are not independent security certification, full accessibility audit, performance/load benchmark or evidence the unbuilt CRM modules function.

## Release gates
- The owner requested **mobile-first UI/UX and personal user test before any further feature development**. Hold this gate strictly.
- No public production deployment or import of real customer data. Live WACRM, Engagement Core, StayCore, Booking Core and Ashwakaal remain unchanged.
- Synthetic test WordPress user-test link is temporary, disposable and access-controlled. Never distribute the test WordPress administrator password. Reviewer permission limited to `manage_eccrm`.
- Full CRM scope (omnichannel unified inbox, AI provider connectors, booking synchronization, automation, campaigns) remains unimplemented and should NOT be implied by this UI rebuild.
- No merging until independent QA, explicit owner acceptance, and rollback evidence.

**Quality states:** DEV_SOURCE_DONE / STAGING_BROWSER_QA_PASSED / USER_TEST_PENDING / PRODUCTION_NO_GO.
