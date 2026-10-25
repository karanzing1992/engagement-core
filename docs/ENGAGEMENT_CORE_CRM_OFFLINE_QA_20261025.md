# Engagement Core CRM 0.1.0-dev — offline QA checkpoint
**Date:** 2026-10-25 · **Branch:** `feat/eccrm-wp-native-foundation-20261025` · **Scope:** Source and offline package only; no deployment.

## Evidence
- PHP CLI: **8.4.24**, sandbox; `php -l` passed for all six plugin PHP files plus synthetic test harness.
- Command: `php packages/engagement-core-crm/tests/smoke.php` — **16/16 synthetic assertions passed**. Tested malformed email/name, invalid lifecycle, array-valued field denial, REST capability denial/allow, bounded route registrations, malformed JSON, create, duplicate external identifier, immutable source identity, and no-PII local event metadata.
- ZIP: `engagement-core-crm-v0.1.0-dev-STAGING-ONLY.zip`; SHA256 `ef82995f23b63d41e928f9c2bbd32314a88f3a5d6a09c1f07e893daa4924dd93`. Zip integrity/entry verification succeeded (eight files, one `engagement-core-crm/` top directory, no extra configuration/secrets).
- GitHub source: bootstrap, six PHP files under `includes/`, `readme.txt`, `README.md` and `tests/smoke.php` had blob hashes checked against the exact local source used for the ZIP. Only files required for plugin runtime were included in ZIP; no test harness was bundled for an installed customer site.
- Dell SSH development lane: completed a read-only `git ls-remote` query for the branch with exit code 0; remote source HEAD at that check `e3bf4c4d9f274858fa9b9cc3e3b81e9b37421494`. The Dell lane has Python 3.12.3, **no PHP CLI**, so PHP execution was NOT tested on Dell.

## Limitations / independent gates
- Mock tests **are not real WordPress integration tests**. `dbDelta`, administrator role activation, REST HTTP authentication, nonce CSRF and multisite behavior remain untested in an actual WordPress instance.
- No pipeline/inbox/message send, actual AI calls, staff role model, source ownership reconciliation, event delivery/retry/dead-letter, retention/delete/export or customer data consent exists yet.
- No independent QA Brain/Dev Tool Yard governor acceptance receipt or WordPress staging/production check; this checkpoint must never be relabeled as owner acceptance, release authorization or production success.
- No live WordPress, Meta, WACRM, Engagement Core, StayCore or Booking Core state was changed.

**Next QA action:** provision an isolated, disposable WordPress test installation via the approved development yard without touching existing sites; check activation/CRUD/permissions/schema/rollback and record terminal receipts. Keep this draft PR unmerged until full QA and owner gate.
