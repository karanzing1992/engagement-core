# META CORE Lane A — External Security Report Remediation and Provider Contract

**Date:** 11 November 2026 (Asia/Kolkata)  
**Owner:** META CORE Lane A, `karanzing1992/engagement-core`  
**Input assessment:** owner-uploaded six-page PDF `META CORE Lane A Security Review Report.pdf`, reviewer source SHA `25acc4dd4f4577356fb335ad7ec105c19446c076`.  
**Work branch:** `fix/meta-core-lane-a-report-remediation-20261111` branched from the frozen candidate; **review-only original** [#264](https://github.com/karanzing1992/engagement-core/pull/264) remains frozen and unmerged.  
**Finding tracker:** [#265](https://github.com/karanzing1992/engagement-core/issues/265); **formal security gate:** [#263](https://github.com/karanzing1992/engagement-core/issues/263).  
**Release classification:** `SOURCE_ONLY / REVIEW_REMEDIATION / NO_MERGE / NO_LIVE_BINDING`.

## Report findings: treatment and acceptance tests

| Report finding | Implementation | Validation |
| --- | --- | --- |
| P2-1: shared object references / DAGs | **Intentionally retain fail-closed tree-only boundary**, no cycles, no repeated object identity anywhere in a request or provider result. Documented as a mandatory provider contract; do not silently expand aliases into massive JSON. | New tests reject repeated input and output objects, cycles and ensure no policy/provider bypass. |
| P2-2: globally allowed `phone` key | Restrict raw key `phone` to **one pinned Dojo contact path**: `whatsapp_send_contacts` > `contacts[]` > `phones[]` > `phone`. Update catalog contact representation to the pinned Dojo 0.5.0 shape (`name.formatted_name`, `phones[].phone`). All non-contact and alternate nested `phone` keys fail before `readPolicy`. Outbound provider responses containing raw `phone` still fail-closed, while public `display_phone_number` stays supported. | One authentic offline Dojo contact-send success, non-contact/nested phone denial and safe response-shape tests; all 55 synthetic provider tools run. |
| P3-1: cumulative input UTF-8 budget | Keep per-string 32 KiB bound and 1,024-node/depth bounds, **add cumulative 65,536 UTF-8 value bytes** for immutable input snapshots before policy. | Aggregate over-budget and many-small-string negatives, 64 KiB inclusive boundary, plus Unicode UTF-8 test. |
| P3-2: implicit CodeQL SARIF path | Use **the official pinned CodeQL analyze Action `output` input** set to a workspace-relative target (`${{ github.workspace }}/security-evidence` or `${{ github.workspace }}/audit-evidence`). Read SARIF directly there, keep `CODEQL_FINDING_COUNT` fail-closed, upload evidence with 3-day retention. No parent-directory `../results` assumption remains. | Independent branch workflow and original CodeQL review workflow both rerun with SARIF count and upload receipt. |

### Fixed trusted-provider contract

1. The MCP source never accepts model-supplied principal, tenant grants, WABA activation or provider token. Only a verified host identity can enter argument validation; trusted tenant and tool-policy callbacks gate any provider dispatch.
2. **Provider responses must be JSON-tree-shaped**, with own data descriptors only; no getters, functions, Proxy nodes, cycles, sparse arrays, custom array methods, or shared object identities. Reused object identities in distinct siblings are rejected deliberately even without a cycle. The provider must materialize independent plain JSON objects before return. A `phone` key in a provider response is fatal by design rather than silently leaked; upstream integrations must explicitly map approved public display fields.
3. Contact phone fields are accepted only in the installed pinned Dojo contract shape. Other resources and message tools must use their own `to` E.164 recipient field, not arbitrary `phone` keys.
4. Aggregate argument bytes count UTF-8 string **values**, not property keys; other existing node/key/dense-array and schema bounds stay active. WACRM must separately enforce transport/request-size and rate limits.
5. Provider root objects and thenables are **trusted host code**. The ECMAScript Promise resolution procedure can inspect a root `.then` before any Lane A `sanitize()` call; nested provider data is independently checked. This limitation cannot be removed by sanitizing the already-await-resolved value. WACRM host adapters must ensure no untrusted root Proxy or thenable is passed through. The provider-binding gate remains `NOT_CLEARED` until tested in Lane B.
6. The `whatsapp_upload_media_from_url` helper is only an **offline URL syntax policy** in Lane A. **Real SSRF and network egress controls are not certified by this work**. Lane B must independently enforce DNS resolution and revalidation, IPv4/IPv6 private, loopback/link-local and cloud metadata ranges, DNS rebinding prevention, redirect rechecks, TLS certificate validation and outbound firewall/allowlist policies **before an HTTP request**; test each with a disposable staging transport. No live provider is bound here.

## Verification discipline

- Existing source-only 55 tool contracts, WACRM HMAC/route tests and older P1/P2 regressions must pass unchanged.
- Source-only manifest must continue to enforce `defaultGrants=[]`, `writeEnabled=false`, `liveProviderBound=false`, `productionEnabled=false`.
- No real tenant/customer data, Meta Graph, active WABA credentials or billable sends are used by these tests.
- Run pinned npm dependencies with `npm ci --ignore-scripts`; run the full Node test suite, security negatives and `npm audit --omit=dev --audit-level=high`; run scoped CodeQL `security-extended` with its SARIF findings count verified.
- A passing local/CI suite is **not** an external approval. Publish a fresh isolated review PR with all code/doc/CI changes, and require an independent review by the named reviewer on the exact SHA. Reviewer must explicitly accept the documented tree-only and trusted-provider boundaries or request changes.
- Do not merge or deploy the original #262 / the audit #264 / new remediation stack without subsequent owner release approval and stacked ancestry reconciliation.

## Open Source / Reuse / Cost Gate

Existing internal META CORE harness, pinned Dojo MCP/SDK and Zod validation are reused. Node's built-in `node:util` Proxy detection, Node test runner, and pinned GitHub CodeQL Action are used; no additional third-party dependency, hosted AI model, paid inference, provider requests, or new persistent service is introduced. Pinning remains unchanged; verify upstream licenses and output portability during external review.

**Master reporting:** Source-only branch/PR/issue can be documented in the owner repo; it is NOT `VERIFIED_LIVE` for the Supabase Master event inbox. Lane B remains separately owned and Ashwakaal — Support Channels separately governed.
