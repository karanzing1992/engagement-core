# META CORE Lane A — Consolidated external assessment P3 hardening, 11 November 2026

**Workstream:** META CORE WhatsApp MCP source, `karanzing1992/engagement-core`.  
**Reported source revision:** `ef82ec3bcbd950342701d4c69c00717c4b0d1c89` ([draft integration PR #270](https://github.com/karanzing1992/engagement-core/pull/270)).  
**Source of findings:** second owner-provided `META CORE Lane A — Consolidated Source Security Assessment` (five-page PDF; 108-patch review) and [triage issue #271](https://github.com/karanzing1992/engagement-core/issues/271).  
**Remediation branch:** `fix/meta-core-lane-a-consolidated-p3-20261111`; exclusively synthetic/source-only; do **not** merge to `main` or bind live providers.  
**Approval:** Existing independent reviewer [#267 APPROVED](https://github.com/karanzing1992/engagement-core/pull/267#pullrequestreview-5848178296) is for an earlier SHA. The new isolated candidate must receive a fresh exact-SHA review after tests.

## Second report: new P3 findings and treatment

### P3-1 — Legacy standalone Proxy trap parity

Harden `src/adapter.mjs`, `src/dojo-v26.mjs`, `src/wacrm-central-read-broker.mjs`, and `src/wacrm-broker-response-contract.mjs` using Node built-in `util.types.isProxy()`, **before** reflecting on request envelopes, arguments or returned data.

- Reject root Proxy request objects without destructuring, getters or trap execution. Authenticate and resolve connections only after clean arguments pass.
- Legacy WBMCP takes a bounded descriptor-only **deep argument snapshot before any host await**, rejecting nested Proxy nodes, accessors, cycles, shared object references and malformed arrays; preserved existing synthetic read/dry-run semantics. Dojo's early scanner rejects nested Proxy values and malformed array elements without invoking object-owned iterators, and snapshots arguments before asynchronous authorizer/SDK construction.
- Broker cleansers and standalone response validators deny Proxy objects without touching traps, reject accessor-backed data, and reconstruct dense arrays from data descriptors.
- Negative tests assert **zero user-owned Proxy traps invoked**, no authorization/transport/SDK callback on denied inputs, and no response leak. All existing tenant and tool capabilities must still pass their offline contracts.

### P3-2 — Immutable supply-chain action references

Pin `.github/workflows/meta-core-phase1d-certify.yml` to the same verified immutable SHAs already used in the newer security workflows:
- `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`
- `actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1`

Keep `persist-credentials: false` and `npm ci --ignore-scripts`; do not add runners, secret grants, or live deployments. Negative test asserts no floating checkout/setup-node tags.

### P3-3 — Argument path collision and offline URL nuance

- `inputSnapshot()` now carries a **typed structural path** (property string or `null` array marker) rather than concatenating arbitrary caller-owned key strings. A `phone` key is allowed *only* under genuine `whatsapp_send_contacts > contacts[] > phones[]` with the pinned Dojo schema. Object keys permit only `^[A-Za-z0-9_]{1,128}$` (and still deny dangerous prototype/credential keys). Synthetic dotted/bracketed keys cannot impersonate a structural array segment before policy.
- Preserve `new URL()` normalization of integer, hexadecimal and octal IPv4 literals, and reject known wildcard-DNS-to-loopback hostnames with suffixes `nip.io`, `sslip.io`, `localtest.me`, `lvh.me` in *both* static URL preflight helpers. Existing private-IP literal checks remain.
- **This is NOT full SSRF safety.** Arbitrary publicly named hosts can resolve to private IPv4/IPv6 endpoints or change on DNS rebinding. Lane B's transport must independently enforce DNS lookup/revalidation, redirect-chain checks, TLS, private/reserved IPv4/IPv6 and cloud metadata deny, connect-to-validated-address binding and outbound firewall/egress limits before live media fetches. Trust of root thenables/Promises remains a separately blocking Lane B provider requirement.

## Required verification before external re-review

1. Run all 55-tool offline contracts and existing P1/P2 regression fixtures; retain **121/121 prior baseline** and add the new P3 tests, no reductions.
2. Run explicit `test/lane-a-consolidated-p3-negative.test.mjs` adversarial cases and all focused negatives in pinned independent review workflow. Tests are fixture-only and do not call Meta or a live WACRM instance.
3. Run `npm audit --omit=dev --audit-level=high`, JS CodeQL `security-extended` with zero-finding SARIF gate, and every PR check at the **final candidate SHA**. Do not claim PASSED before verifying finished Action run IDs.
4. Review diff against [integration draft #270](https://github.com/karanzing1992/engagement-core/pull/270), check no existing production, feature grants, tenant tokens or secrets changed.
5. Obtain explicit independent `APPROVED` / `REQUEST_CHANGES` review at new exact SHA, reconcile findings [#271](https://github.com/karanzing1992/engagement-core/issues/271), and obtain separate owner merge permission. The old review approval and a green CI do not authorize integration into `main`.

## Reuse and cost

Reuse existing audited Lane A code, Node's standard-library Proxy detection and test runner, pinned Dojo/Zod dependencies and pinned GitHub CodeQL Actions. No new package dependency, API key, paid model, hosted runner tier or live billable message is introduced. Source-only classification, not `VERIFIED_LIVE` in the Master Registry. Ashwakaal — Support Channels remains a separate account/workstream.
