# META CORE Lane A — External Security Re-review Package (11 Nov 2026)

## Frozen review identity

- **Review-only branch:** `audit/meta-core-lane-a-resubmit-20261111`.
- **Updated immutable application source:** `24a9c9ef508d16275b8e62e7b8bd9858338cd1ec`, produced on isolated [remediation PR #266](https://github.com/karanzing1992/engagement-core/pull/266).
- **Full original security series:** [PR #262](https://github.com/karanzing1992/engagement-core/pull/262), original source SHA `25acc4dd4f4577356fb335ad7ec105c19446c076`.
- **Previous preserved review branch/PR:** [#264](https://github.com/karanzing1992/engagement-core/pull/264), retained without changes.
- **Compare base for resubmission:** `feat/meta-core-lane-a-final-provider-20261110` so the reviewer sees all security changes, not only the 11 Nov remediation.
- **Formal approval gate:** [#263](https://github.com/karanzing1992/engagement-core/issues/263); [report findings tracker #265](https://github.com/karanzing1992/engagement-core/issues/265).
- **Source-only. No deployment, merge, live token, WACRM operation or billable WhatsApp sends.**

This review branch was copied from the tested remediation source commit. The extra review-only commit adds only this markdown handoff, with **zero application-code or workflow differences** from the immutable source revision above. Verify this using GitHub's compare API or Git diff before issuing any approval.

## External assessor's 6-page report — 4 observations disposition

| Finding | Corrective action | Required review judgment |
| --- | --- | --- |
| P2: shared object references rejected | Explicitly **retain tree-only, fail-closed** payload contract. Reused object identity and cycles denied, protecting from alias expansion. Added separate negative caller/provider tests. | Review acceptance of a documented JSON-tree-only integration contract, not a new DAG-support feature. |
| P2: global `phone` exemption / output asymmetry | Restrict phone to pinned Dojo `whatsapp_send_contacts > contacts[] > phones[] > phone`. Align catalog and verify full 55-tool E2E. Output raw `phone` remains fail-closed; `display_phone_number` remains public. | Inspect no unintended phone data reaches readPolicy on unrelated tools, and user-visible profile fields remain intact. |
| P3: missing aggregate UTF-8 budget | Aggregate 65,536-byte input value cap, alongside per-string 32,768-byte/node/depth bounds, plus UTF-8 and many-small-string tests. | Test exact boundary and pathological payload rejection before policy or host provider. |
| P3: CodeQL `../results` path dependency | Both CI workflows use pinned CodeQL Action's documented `output` input, SARIF inside `github.workspace`; zero-finding gate and 3-day artifact confirmed. | Validate workflow YAML and exact run artifact; ensure future runner portability. |

See [full change rationale and required provider trust/egress contract](META_CORE_LANE_A_EXTERNAL_SECURITY_REMEDIATION_20261111.md).

## Verified source CI evidence, before adding this review-only documentation

- **[Isolated independent CI #42884217367](https://github.com/karanzing1992/engagement-core/actions/runs/42884217367)** at exact application source SHA `24a9c9ef508d16275b8e62e7b8bd9858338cd1ec`: 29/29 focused security checks, 121/121 complete Node tests, npm audit reports 0 vulnerabilities, CodeQL `security-extended` success, SARIF `CODEQL_FINDING_COUNT=0`.
- **[CodeQL SARIF artifact #13793819580](https://github.com/karanzing1992/engagement-core/actions/runs/42884217367/artifacts/13793819580)** (3-day retention; reviewer should preserve a copy).
- At source SHA, three source CI checks `codeql-lane-a`, `Independent JavaScript CodeQL security-extended`, and `Node security and contract tests` were successful.
- This branch's independent workflow will run again on the audit head. Confirm those exact-head results after the doc-only commit.

## External review instructions

1. Compare full PR diff against `feat/meta-core-lane-a-final-provider-20261110`; validate frozen source diff and that the audit branch has no extra application-code changes.
2. Independently assess P1 previously remediated array/Proxy/TOCTOU leakage, and the four findings above; read source, tests, new catalog contact shape, and CodeQL log plus SARIF.
3. **Do not equate a green CI/SARIF with independent approval.** The reviewer must supply any novel findings, reproduction and exact commit.
4. Explicitly evaluate the two **non-Lane-A** limitations: root trusted provider Promise/thenable assimilation before `sanitize()`, and real DNS/redirect/TLS/IPv4/IPv6/egress SSRF controls on `whatsapp_upload_media_from_url`—both must stay blocked until Lane B certifies its host integration. Lane A rejects private URL literals but cannot certify live host egress.
5. Provide `APPROVED` or `REQUEST_CHANGES` from the reviewer's own independent GitHub account, referencing the immutable application SHA, audit PR SHA, each accepted residual risk and exact CI evidence. An external PDF without verifiable reviewer identity is assessment input, not formal approval; do not silently mark Issue #263 accepted.
6. Owner separately checks reviewer independence/rights and records source-security acceptance/no-go in #263. An audit PR is **NEVER MERGED**; source integration and eventual production remain separate approval gates.

## Free/open-first and isolation

The implementation reuses existing Lane A/MCP/Dojo code, Node built-in modules and pinned GitHub CodeQL Action, without new paid services or runtime dependencies. WACRM Central and Meta credentials/data remain outside this review, Lane B separately owned; Ashwakaal — Support Channels independently governed. **Source-only reviews do not qualify as VERIFIED_LIVE Supabase Master events.**
