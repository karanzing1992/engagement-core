# META CORE Lane A — Consolidated Engineering Handover (10 Nov 2026)

**Owning project:** META CORE WhatsApp Business official API → MCP, repository \`karanzing1992/engagement-core\`.  
**Workstream boundary:** **Lane A** owns WhatsApp MCP catalog, source adapters and synthetic/contract certification. **Lane B** is a separate chat/workstream responsible for DeluluTech Unified Login/OAuth, WACRM Central credentials and outbox/inbox, dedicated integrated staging, approved Meta WABA and vendor integration evidence. Never share cross-tenant authorizations, credentials or customer data. Ashwakaal — Support Channels is a separate workstream.  
**Checkpoint date:** 2026-11-10 (Asia/Kolkata). **Classification:** \`SOURCE_ONLY / SECURITY_FIX_CI_PASS / INDEPENDENT_REVIEW_PENDING / NO_MERGE / NO_DEPLOY\`.

> This document records verified development, not an assertion of live WhatsApp API availability or production approval. Preserve historical evidence SHAs even though this documentation commit moves the PR head.

## 1. Release candidate and exact source proof

- **Selected candidate:** [PR #261](https://github.com/karanzing1992/engagement-core/pull/261), source SHA \`54bc4623a67b96600465ef355eb9f2f854454acd\`, **open, not draft, not merged**.
- **Security remediation stacked on #261:** [PR #262](https://github.com/karanzing1992/engagement-core/pull/262), **last code-tested SHA** \`25cf7f1b37107773f3ebd61ecb38d9f9dc0c906d\`. Open, review requested, not merged. Documentation-only commits following this SHA do not change the underlying tested production code; re-run exact-head checks on the final integration commit before merging.
- **Original #261 source CI:** [GitHub Actions #42852289568](https://github.com/karanzing1992/engagement-core/actions/runs/42852289568): **87/87** Node tests passed; npm audit zero reported vulnerabilities. Other named exact-head CI checks: \`offline-provider-contract\`, \`synthetic-mcp\`, \`read-only-transport\` passed.
- **P1/P2 remediation CI:** [GitHub Actions #42859999564](https://github.com/karanzing1992/engagement-core/actions/runs/42859999564) at \`25cf7f1b37107773f3ebd61ecb38d9f9dc0c906d\`: **3/3** specific security regressions, **102/102 full Node tests**, **0 failed**, \`npm audit\` found **0 vulnerabilities**. Separate exact-SHA workflows also reported success.
- **Re-review status at checkpoint:** The prior Codex review on PR #262, submitted against earlier SHA \`b21d6eb...\`, found **P1 array sanitizer bypass** and **P2 template analytics nested click/cost shape**; both review threads are **outdated but unresolved**. Replies with patch evidence posted and fresh \`@codex review\` requested for \`25cf7f1b...\`. **No new independent Codex approval or signoff is verified**. A passing CI suite cannot replace this review.

## 2. Implemented functionality, strictly source-level

1. **55 versioned WhatsApp MCP tool contracts** (Meta account/phone/profile, outbound and inbound/status, templates, media, Flows, commerce/catalog, QR, analytics); **12 high-risk or conditional operations explicitly excluded**. A catalog entry or mock handler does not establish live Meta support.
2. **33 credentialless fixed Meta Graph v26 host request plans**, **17 Dojo-owned tool adapters**, **2 restricted WACRM template-broker reads**, **3 WACRM-owned inbound/status reads**, with versioned default-deny manifest.
3. Verified upstream **Dojo MCP 0.5.0, SDK 0.10.0 (MIT)** tooling; all **19 upstream Dojo handlers** exercised through in-memory fake/mock clients without real WhatsApp calls; exact input schema-derived guards for 17 Dojo-owned operations. Two template-read tools remain broker-owned.
4. Real **in-memory MCP SDK tools/list and tools/call contract tests**; no public remote MCP listener.
5. Fail-closed checks: trusted actor/tenant identity, per-operation grant, active WACRM activation/WABA/phone route, verified resource ownership, recipient opt-in, 24-hour customer-service window, approved template, billable-send/operator approval, owner-issued mutation request ID, no automatic provider retries, credential/output redaction, blocked phone lifecycle and no arbitrary Graph proxy.
6. **Original #261 fixes through #262:** immutable argument snapshot before asynchronous policy/provider calls (TOCTOU), getter/prototype-safe input handling, descriptor-only provider result access, actual Dojo \`mediaId\` upload receipt, operation-scoped aggregate analytics response handling, meaningful synthetic analytics and media fixtures.
7. **Newest Codex P1/P2 fixes in #262:** safeRead no longer invokes provider-owned \`map\`/indexed getters/iterators; only dense, bounded own-data array descriptors are reconstructed into fresh arrays. Arrays with sparse slots, overridden \`map\`, unexpected properties or credentials fail closed. Analytics-only nesting supports genuine \`clicked[]\`/\`cost[]\` with \`type\`, \`count\`, numeric \`value\`, preserving original stricter depth for other read operations. Seven new targeted cases bring total full suite from 95 to **102**.

**Primary files:** \`integrations/meta/whatsapp-mcp/src/lane-a-provider-runtime.mjs\`, \`src/lane-a-graph-v26-plans.mjs\`, \`src/lane-a-capability-catalog.mjs\`, \`src/lane-a-upstream-dojo-schemas.mjs\`, \`manifest/lane-a-whatsapp-mcp-v1.json\`; review tests \`test/lane-a-release-review-regressions.test.mjs\`, \`test/lane-a-review-codex-regressions.test.mjs\`, \`test/lane-a-review-array-hardening.test.mjs\`; CI \`.github/workflows/meta-core-lane-a-security-review.yml\`.

## 3. Open blockers and separation of ownership

### Lane A security and source release
- Obtain **fresh independent security/code review** on the final #262 source (not the superseded \`b21d6eb\` revision); inspect any new findings and leave unresolved threads open until reviewer accepts evidence.
- Review true Meta v26 Graph path, field, encoding, permission and request/response parity for conditional commerce, analytics, Flows and QR operations. Current fixed host plans are blueprints, not vendor-certified HTTP adapters.
- Verify Dojo/Zod 4 override compatibility with the owner-controlled provider host. Treat SDK installation and synthetic tests as insufficient evidence for live send parity.
- Test required checks on the **final consolidated SHA**. Do not merge with unreviewed security issues.

### Lane B only — integration and live gates
- Authenticate exact DeluluTech issuer/client/audience, tenant grant, owner WABA asset mapping and revocation in dedicated staging.
- Bind WACRM Central tokenless broker and encrypted per-tenant Meta credential custody, durable outbox/inbox and signed webhook/replay/idempotency; preserve current WhatsApp registrations and customer accounts.
- Host-level DNS SSRF/egress/redirect restrictions, 429/backoff, per-tenant quotas, opt-in/24-hour/template policy proof and explicit owner authorization for any billable send.
- Owner-approved read-only Meta sandbox/WABA/coexistence validation, rollback/restore and independent release/security acceptance before enabling real mutations.
- No Lane A claim of live WACRM, remote MCP OAuth, paid sends or vendor approval is permitted.

## 4. PR dependency order and GitHub reconciliation

**Stack (all unmerged as of this checkpoint):**

1. [#215 — Phase 1-D](https://github.com/karanzing1992/engagement-core/pull/215) → base \`main\`, **draft**; head \`a2b0147a0930ca98cb86de51511432d88d55e253\`.
2. [#257 — Phase 1-E](https://github.com/karanzing1992/engagement-core/pull/257) → base Phase 1-D branch, **draft**; head \`59f182bee33aa79b14412167e3c452ba85e6f303\`.
3. [#258 — Lane A inventory](https://github.com/karanzing1992/engagement-core/pull/258) → base Phase 1-E branch, **draft**; head \`c7e35107019ca04007d750bd71d22cf8bff018e5\`.
4. [#261 — Lane A v1](https://github.com/karanzing1992/engagement-core/pull/261) → base Lane A inventory branch, **ready for review**, head \`54bc4623a67b96600465ef355eb9f2f854454acd\`.
5. [#262 — security fix](https://github.com/karanzing1992/engagement-core/pull/262) → base #261 branch, **ready for review**, code-tested head \`25cf7f1b37107773f3ebd61ecb38d9f9dc0c906d\`.

\`main\` is not the same ancestor as this work: it has diverged substantially. The final branch was **90 commits ahead and 61 commits behind main** at the prior ancestry check. These are commit-count comparisons, not a suggested automatic merge. Inspect all competing changes, stage a coordinated non-destructive merge/rebase plan with review, preserve the existing default-branch source, and rerun all required checks after each approved integration. **No forced reset, PR retargeting, automatic merge, deploy or credentials change.** The experimental [PR #260](https://github.com/karanzing1992/engagement-core/pull/260) is not the selected candidate; do not mix it into the stack without deliberate review.

## 5. Evidence, rollback, and next handoff instruction

**Existing related documents:** 
- \`docs/META_CORE_LANE_A_MCP_SCOPE_20261110.md\`
- \`docs/META_CORE_LANE_A_FINAL_HANDOFF_20261110.md\`
- \`docs/META_CORE_LANE_A_PROVIDER_HANDOFF_20261110.md\` (separate experimental #260 branch only, not in selected stack)
- \`docs/META_CORE_LANE_A_RELEASE_GATE_REVIEW_20261110.md\`
- \`docs/META_CORE_LANE_A_P1_P2_REMEDIATION_20261110.md\`
- [Lane A tracker issue #259](https://github.com/karanzing1992/engagement-core/issues/259) and [META CORE program issue #254](https://github.com/karanzing1992/engagement-core/issues/254).

**Rollback:** Source-only; leave grants and writes disabled. Close the unmerged review PR if unacceptable; original #261/#258 branches and WACRM runtime remain unchanged. No database, real customer activity, Meta account or production deployment was modified.

**Master Stack:** Record only verifiable source progress in owning GitHub issues/PR. No \`VERIFIED_LIVE\` Supabase Master event; no claim of synced default-branch/Google Doc/plugin release for unmerged source. Ashwakaal Support Channels separate.

**Precise next-work prompt:**

> Continue META CORE WhatsApp Lane A from PR #262 on branch \`fix/meta-core-lane-a-release-review-20261110\`. Read \`docs/META_CORE_LANE_A_CONSOLIDATED_HANDOVER_20261110.md\`, verify current SHA and independent Codex review. Close any new security findings with negative tests, obtain independent acceptance of the P1/P2 array and analytics fixes, and prepare a reviewed, non-destructive PR ancestry reconciliation plan #215→#257→#258→#261→#262 against current main. Rerun all required exact-head CI checks before any source merge; do not merge, deploy, activate credentials, call live Meta, bill messages or touch Lane B until its independent owner-staging gates are certified.
