# META CORE Lane A — P1/P2 release review remediation

**Date:** 2026-11-10 | **Repository:** `karanzing1992/engagement-core`  
**Selected Lane A release candidate:** [PR #261](https://github.com/karanzing1992/engagement-core/pull/261), source SHA `54bc4623a67b96600465ef355eb9f2f854454acd`.  
**Isolated security remediation:** [PR #262](https://github.com/karanzing1992/engagement-core/pull/262), branch `fix/meta-core-lane-a-release-review-20261110`.  
**Security classification:** `SOURCE_ONLY / NO_LIVE_PROVIDER`. Do **not** mark independently security-approved until a fresh external review accepts the exact head.

## Re-review scope

The first Codex review on #262 identified two unresolved findings:

1. **P1: Untrusted array execution and data leakage.** The former `safeRead` invoked untrusted `value.map`, allowing an attacker-controlled array override to bypass sanitation and allowing accessor-backed indices to execute.
2. **P2: Real click/cost metric shape.** Template analytics can contain `clicked[]` and `cost[]` entries with nested `type`, `count` and/or numeric `value` fields, exceeding the old nesting limit and losing `value`. Source shape reference: [360dialog template analytics](https://docs.360dialog.com/docs/resources/templates/template-analytics), [Meta template insights](https://whatsappbusiness.com/wp-content/uploads/2026/04/Best-Practices-for-Marketing-Messages-on-WhatsApp-.pdf). 360dialog is an **external schema reference**, not a substitute for owner-verified Meta v26 provider acceptance.

### Implementation

- `src/lane-a-provider-runtime.mjs`: replace response-array method calls with descriptor-only handling of dense canonical arrays. Enforce `Array.prototype`, numeric own index keys, bounded size, no sparse entries, no own `map` override, no indexed getters and no extra symbol or string properties; allocate a fresh clean array and recursively inspect only own data descriptors.
- Preserve original non-analytics result nesting bound at depth 7. For the two specifically authorized Graph analytics tools only, allow up to depth 12. Shared bounded object graph budget is 1,024 nodes and each array has at most 100 elements; downstream sanitized response byte size remains limited.
- Allow aggregate analytic numeric `value` only inside the analytics result contract; block credential-like fields at any nesting level and drop unrelated phone or customer records. Preserve genuine `clicked[]`/`cost[]` metric aggregates.
- `test/lane-a-review-array-hardening.test.mjs`: 7 negative/positive cases: array index getters do not execute; own `map` methods cannot leak; extra/sparse arrays denied; nested credentials denied; clicked/cost arrays preserve aggregate types/counts/values; oversized arrays fail; analytics excluded from unrelated tools.
- Existing releases’ 95 test cases and previous security fixes must keep passing. New suite target: **102 total Node tests**, zero vulnerabilities and independently reviewed exact head.

## Release boundaries and rollback

- The security patch remains **stacked** on PR #261 and does not modify the selected candidate or ancestor branches in place. PR ancestry: #215 → #257 → #258 → #261 → #262.
- Do not resolve Codex review threads merely because tests pass. Request independent re-review of this new head, then follow owner-controlled ancestor reconciliation and exact-head retesting before merge.
- No remote MCP listener, Graph transport, real WACRM broker binding, secrets, permissions, customer data, outbound messages, phone migration, payment or production changes. Host DNS/SSRF/egress, owner-approved persistent outbox/429 retry, Meta app scope and vendor payload acceptance, OAuth resource grants and dedicated WACRM staging are **Lane B/release-gate responsibilities**.
- If rejection occurs, close/revert the unmerged security PR; no running service or customer state is affected. Ashwakaal — Support Channels remains isolated.
- **No Supabase Master VERIFIED_LIVE event is authorized** for source-only changes. Master default-branch sync is required only after an actually reviewed/default-branch source merge with verified acknowledgements.
