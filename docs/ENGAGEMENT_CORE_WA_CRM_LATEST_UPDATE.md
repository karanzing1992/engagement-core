# Engagement Core — WhatsApp CRM (WACRM): Latest Update

**Audit date:** 2026-10-25 (Asia/Kolkata)  
**Status:** **NO-GO — production CRM / live-number coexistence / commercial rollout**  
**Permitted:** Existing isolated development and sandbox workflows; read-only operational review.  
**Document class:** Source-verified status snapshot, not a deployment approval or live Meta authorization.  
**Owning implementation:** Private `karanzing1992/moksha_wordpress` (WACRM Central + Consumer).  
**Shared-status index:** Public `karanzing1992/engagement-core` (this file).

> **Scope boundary:** Engagement Core WordPress publishing v0.9.x and WhatsApp Status publishing are **not** the WACRM product. The WACRM implementation lives in `moksha_wordpress`; this document is the cross-project status/index. Do not infer WACRM readiness from Engagement Core plugin version.

## 1. Executive decision

The WACRM technical foundation exists: Central licensing/monitoring and an official WhatsApp Business App Coexistence broker, a customer-hosted signed relay receiver, encrypted connection settings, event/contact tables, a restricted event inbox, and a separate Meta sandbox send/template console. **This is not yet a production two-way customer CRM.** The consumer is unconnected to a production phone, history/media and staff workflow are incomplete, the 0.1.1 launch-safety candidate is still draft/unmerged, and Meta production approval has not been independently verified.

**GO:** isolated development, existing test-only sandbox, read-only verification.  
**NO-GO:** live pilot with a real Business-app number, existing production-number onboarding, customer campaigns, general commercial rollout.  
**Non-negotiable:** preserve the existing WhatsApp Business mobile app; no phone registration, migration, deregistration or re-pairing without a separate explicit owner-approved change window and verified official Coexistence eligibility.

## 2. Observed production state (verified 2026-10-25)

| Check | Readback | Meaning |
| --- | --- | --- |
| Moksha WordPress platform | WP 7.1.3; PHP 8.2.34; active `moksha-sanctuary-git` theme | Reachable pilot host (not CRM signoff) |
| Central Meta health | `ok=true`; `configured=true`; Graph `v26.0`; `coexistence=true`; raw challenge enabled | Configuration present; not proof of Meta approval or live subscription |
| WACRM Consumer health | Version `0.1.0`; `relay_ready=false`; `connection_mode=unconnected`; schema `0.1.0` | **Live consumer not connected** |
| Central monitoring health | `ok=true`; free-key registration and aggregate telemetry advertised; content collection disabled | Route operational; commercial licensing lifecycle untested |
| Test-console health | `ok=true`, `mode=test_only`, configured, test token stored | Sandbox configured; current token validity and delivery not re-tested in audit |
| WordPress WACRM tables | 0 WACRM events, 0 WACRM contacts, 0 WACRM Meta routes (read-only counts) | No evidence of real pilot traffic flowing into WACRM |
| Launch-readiness REST route | `GET /wacrm/v1/readiness` returned HTTP 404 (`rest_no_route`) | New v0.1.1 readiness tooling **not live** |
| Current 0.1.1 candidate | PR #52 open, draft, unmerged; head `8988b25a4a63a2f350d3fa1c4b76f9976628b5cf` | Not release-certified or production-deployed |
| Candidate relationship to `main` | 9 commits ahead, 104 behind (comparison at audit) | Requires careful reconciliation; no blind merge |
| Candidate CI evidence | No commit status checks or PR-triggered workflow runs returned for PR #52 head | **No verified runtime test of candidate** |

The `moksha_wordpress` `main` branch was documented as the live Hostinger theme release lane on 2026-10-05. That historical note is not a substitute for runtime checks. The WACRM Consumer currently loads through the theme's `functions.php`, not as an independently managed customer-installable release. Central's local loader and Consumer's pilot boot path exist in source.

**Confidence labels:** LIVE = directly observed authenticated runtime state; SOURCE = inspected repository code; CI = retrieved past GitHub Actions run; HISTORY = prior dated documentation/PR description, requiring re-verification for a current provider decision.

## 3. Verified engineering foundations

- **SOURCE / LIVE:** Central Meta Embedded Signup/coexistence support, webhook challenge handler and configured health. The source checks the provider's `is_on_biz_app` attribute and rejects Cloud API-only fallback.
- **SOURCE:** Consumer uses signed HMAC-SHA256 `timestamp.raw_json` relay envelopes, a five-minute time window, 1 MiB payload ceiling, explicit relay version, WABA/phone isolation and AES-256-GCM encryption for relay credentials.
- **SOURCE:** Consumer provides idempotent event inserts, contact upserts, capture of raw history/echo/status/sync references, private administrator-only inbox and read-only health.
- **SOURCE / LIVE:** Separate administrator-only test console with independently stored sandbox credentials and test/send/template facilities; it does not register or migrate a phone.
- **CI:** Consumer security/parser regression run [#37907639192](https://github.com/karanzing1992/moksha_wordpress/actions/runs/37907639192) passed for PHP 7.4, 8.1, 8.3. Coexistence safety run [#37902217500](https://github.com/karanzing1992/moksha_wordpress/actions/runs/37902217500) passed. These were **earlier-code tests**, not 0.1.1 launch certification.
- **HISTORY:** The 2026-10-09 readiness playbook records a Meta sandbox message accepted/delivered and template creation demonstrated; App Review was **Review in progress**, not approved, on that date. Current Meta status was not independently fetched on 2026-10-25.

## 4. Production release gates

| Priority | Gate | Audit result | Acceptance evidence |
| --- | --- | --- | --- |
| P0 | Current Meta App Review, Advanced Access, applicable provider verification | **BLOCKED / unverified** | Direct current Meta approval readback for messaging/management and any required additional qualifications |
| P0 | Explicit controlled-trial owner approval and official mobile-app Coexistence | **BLOCKED** | Approved change window; exact phone `is_on_biz_app=true` confirmed by Meta; never Cloud-only fallback |
| P0 | Connected Consumer and authenticated relay path | **BLOCKED** | Signed delivery to correctly isolated test tenant; receipt readback; fail-closed unsigned/replay/wrong-tenant tests |
| P0 | End-to-end two-way CRM | **BLOCKED** | Agent can see normalized conversation, reply, observe message state, and avoid duplicates with authorized test identity |
| P0 | Reliable multi-tenant delivery | **BLOCKED** | Retry on any downstream failure, durable per-tenant queue/dead-letter handling, reconciliation, alerting and replay/idempotency tests |
| P0 | Contact opt-in, retention, deletion/export and data isolation | **BLOCKED** | Signed-off privacy/consent implementation, access policy and delete/export exercise with test data |
| P0 | Staff roles and support workflow | **BLOCKED** | Least-privilege support roles, assignment, audit trail and denied-access tests; admin-only event viewer is insufficient |
| P0 | Media/history normalization | **BLOCKED** | Inbound/outbound history, echoes, text, media and attachment retention paths verified with test data |
| P0 | Release 0.1.1 integration | **BLOCKED** | Reconcile draft against `main`, review diff/security, run PHP lint and regression suites and build reproducible ZIP |
| P0 | Production operational rollback | **VERIFY** | Proven site backup/restore, token rotation/revocation, relay disablement and on-call incident runbook without phone deregistration |
| P1 | Monitoring and rate/backpressure controls | **VERIFY** | Delivery/error metrics, alert tests, retry queue visibility, log redaction, credential expiry exercise |
| P1 | Customer packaging, licensing and update channel | **BLOCKED** | Independently installable/upgradable Consumer build, licensing test, version compatibility and rollback install |
| P1 | Commercial rules and template operations | **VERIFY** | Verified business billing, WhatsApp template approval, opt-in, messaging window, support escalation, error handling |

**Interpretation:** A passing health endpoint or old CI run is not sufficient evidence for customer traffic. The 0.1.1 safeguards must be reviewed and exercised; authorization constants/flags are operator attestations, not independent confirmation of Meta approval.

## 5. Code-review priorities / defects to resolve

1. **Partial delivery acknowledgment:** In live Central source, an incoming Meta batch can be acknowledged when some tenant relays succeeded and others failed. This risks not receiving upstream retries for failed tenants. PR #52 changes the behavior to retryable HTTP 503 when *any* tenant fails, but still lacks a persistent per-tenant retry/dead-letter mechanism.
2. **Coexistence binding authority:** Central validates a Meta response indicating Business-app coexistence; Consumer's administrator connection endpoint separately accepts an `is_on_biz_app` boolean. Review trust boundaries and require a verified signed/provisioned attestation for production binding rather than treating the caller-provided boolean as proof.
3. **Functional MVP gap:** Current Consumer is an event receiver and restricted event viewer, **not** a complete production chat/reply interface. Normalized conversation state, agent replies/permissions, opt-in and history/media lifecycle must be implemented and tested.
4. **Data lifecycle:** Raw event JSON persists locally. Implement configured retention, deletion/export, consent auditing, encrypted/backed-up storage and documented recovery.
5. **Release hygiene:** Draft PR #52 is substantially behind main. Reconcile deliberately, run static security review, PHP compatibility + regression tests, build/inspect Consumer ZIP, stage deployment and verify rollback without touching production Meta assets.

These are audit findings and release requirements; this document does not assert a newly proven exploit, successful production message, or active Meta permission.

## 6. Release plan and exit criteria

1. **Recovery / isolation:** Bring PR #52 up to date against current `main` in a development branch, preserve unrelated site changes and make a reviewed diff. No owner production number or Meta live flag changes.
2. **Test candidate:** Run offline `php -l` on Central/Consumer/readiness/test-console and `tests/wacrm-launch-readiness-smoke.php`, `tests/wacrm-consumer-relay-smoke.php`, `tests/wacrm-coexistence-safety-smoke.php`, and `tests/wacrm-test-console-smoke.php`. Save exact output and commit SHA. Verify reproducible package and installation without theme duplicate boot.
3. **Complete product-critical functionality:** Two-way reply and conversation UI, granular agents, contact consent/retention, media/history, durable tenant retries with dead-letter/alerts, backups and data export/deletion.
4. **Verify provider approvals:** Confirm status directly in Meta and required access/provider qualifications. Screenshots and review submissions are not approvals; sandbox success is not production eligibility.
5. **Separate safe trial:** With explicit consent, exercise a noncritical, separate WhatsApp Business-app number under official Coexistence. Verify mobile app still works, receive/send, statuses, echoes, history/media, opt-in, duplicate/outage recovery, operator workflow and rollback.
6. **Dedicated production decision:** Only after evidence signoff, schedule separate owner-approved activation for the existing production account. Keep outbound automations disabled until consent, billing and review gates pass.

### Explicit go/no-go matrix

| Stage | Decision as of 2026-10-25 |
| --- | --- |
| Source development and isolated sandbox | **GO** (within existing test-only scope) |
| QA/staging evaluation | **GO** (candidate still must pass its new tests) |
| Real-number controlled pilot | **NO-GO** |
| Existing business production number | **NO-GO** |
| Commercial multi-customer launch | **NO-GO** |

## 7. Canonical evidence / navigation

- [WACRM source repository — private](https://github.com/karanzing1992/moksha_wordpress)
- [Consumer v0.1.0 README](https://github.com/karanzing1992/moksha_wordpress/blob/main/packages/wacrm-consumer/README.md)
- [Central + Consumer deployment notes](https://github.com/karanzing1992/moksha_wordpress/blob/main/DEPLOYMENT.md)
- [PR #50 — signed Consumer relay (merged)](https://github.com/karanzing1992/moksha_wordpress/pull/50)
- [PR #51 — sandbox send/template console (merged)](https://github.com/karanzing1992/moksha_wordpress/pull/51)
- [PR #52 — candidate 0.1.1 safety preflight (draft, unmerged)](https://github.com/karanzing1992/moksha_wordpress/pull/52)
- [0.1.1 review-pending production readiness playbook](https://github.com/karanzing1992/moksha_wordpress/blob/feature/wacrm-launch-safety-preflight/docs/WACRM_PRODUCTION_READINESS.md)
- [Historical passing Consumer CI](https://github.com/karanzing1992/moksha_wordpress/actions/runs/37907639192)
- [Historical passing coexistence CI](https://github.com/karanzing1992/moksha_wordpress/actions/runs/37902217500)
- [Engagement Core caption/WhatsApp Status separation](https://github.com/karanzing1992/engagement-core/blob/main/docs/moksha-platform-caption-publishing-standard.md)

## 8. Revalidation and scope protection

This status is **time-bound**: repeat Meta approval, GitHub PR/CI, customer-site health, rollback, and end-to-end checks before upgrading any NO-GO result. Do not mistake a source commit, release package, configured credential, submitted App Review or 200 health response for production authorization.

**Security/privacy:** No WhatsApp messages, customer records, live number identifiers, bearer tokens, webhook signing secrets, tenant credentials or private database exports are included in this public shared-status document. Keep operational credentials and customer records separated by brand/customer. Ashwakaal Support Channels is a distinct workstream and is not part of this WACRM pilot.

**Change classification:** Documentation-only baseline as of 2026-10-25; **no software changes, plugin publication, Meta enrollment or production deployment** are asserted.
