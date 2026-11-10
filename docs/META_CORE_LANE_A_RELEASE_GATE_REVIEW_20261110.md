# META CORE Lane A — Independent release-gate review and isolated remediation

**Date:** 2026-11-10 | **Owning source:** `karanzing1992/engagement-core` | **Security-fix PR:** [#262](https://github.com/karanzing1992/engagement-core/pull/262)  
**Release candidate reviewed:** [#261](https://github.com/karanzing1992/engagement-core/pull/261) at `54bc4623a67b96600465ef355eb9f2f854454acd`. Source base preserved, no in-place overwrite.  
**Classification:** `SOURCE_ONLY / SECURITY_REVIEW_IN_PROGRESS` (not externally deployed, not customer-data/Meta-connected).

## Reproduced defects

1. **Async TOCTOU of MCP arguments (security, release blocker).** Validated `args` were discarded after the ingress gate; later provider dispatch rebuilt the arguments from the original caller-owned object. Asynchronous host policy/route callbacks could mutate previously approved send data. A separate regression fixture mutates the send body after authorization, verifying the exact originally approved body must reach the synthetic provider. The original PR #261 reproduced failing checks in the new isolated CI ([run #42856051832](https://github.com/karanzing1992/engagement-core/actions/runs/42856051832)).
2. **Input accessor execution before policy (security).** The runtime passed raw untrusted model input to `readPolicy` before ingress validation. The patch takes a descriptor-only deep immutable plain-object snapshot synchronously before any `await`, rejecting accessors, unusual prototypes, prototype-polluting keys, credential and tenant fields, size excess, cycles, and non-JSON values. Whitelisted contact card `phone` fields remain permitted and are subsequently validated against upstream Dojo schemas.
3. **Provider response getter execution (security).** `JSON.stringify` of raw provider output preceded field-level sanitization and could invoke getters. The patch inspects own data descriptors first, applies recursive allowlist sanitation, then sizes the safe copy.
4. **Dojo media-upload receipt lost (Codex independent review, P2).** The deployed Dojo's successful `whatsapp_upload_media_from_url` MCP result includes `structuredContent.mediaId`. The candidate omitted the media ID during sanitization and rejected it as lacking an accepted receipt. Patch retains bounded numeric/live IDs and in-memory Dojo mock IDs; ensures mediaUpload is the only alternate non-read receipt shape.
5. **Business and template analytics data stripped (Codex independent review, P2).** The candidate discarded `analytics` and `template_analytics` metrics, producing empty results. The patch uses an **operation-specific** allowlist for analytic buckets and template click/aggregate values, excluding raw business phone arrays; it requires the expected report field for the requested analytics operation. Fake-provider fixtures now return realistic metrics instead of generic `id,name`.

Independent Codex review on #261 recorded two unresolved review threads for items 4 and 5. PR #262 is submitted for their review; threads must not be marked resolved before reviewer acceptance and proper source integration.

## Required exact-head acceptance

- New async/auth/accessor negative tests pass.
- New media-upload/analytics production-shape mock fixtures pass, including nested secret denial and no analytics spillover to unrelated tool outputs.
- Full inherited synthetic Node suite and dependency audit pass on the **same immutable final SHA**.
- External Codex/independent code reviewer performs a new review; author cannot self-certify its release.
- Preserve default-deny tool grants and no live Graph, account registration, credentials, billable sends, local web listener, WACRM customer records or production deployments.
- Confirm ancestry `#215 → #257 → #258 → #261 → #262` and recognize direct `main` reconciliation still requires owner-reviewed coordinated rebase/merge and fresh CI after any merge.

## Additional current blockers

- **Vendor endpoint parity:** Graph v26 analytics, commerce and conditional Flows operations remain **request blueprints**, not accepted live Meta API calls. Verify actual approved WABA provider contracts and scope requirements; do not enable conditional tools on plan tests alone. [Meta official Cloud API collection](https://www.postman.com/meta/whatsapp-business-platform/collection/wlk6lh4/whatsapp-cloud-api) is the primary API reference.
- **Lane B:** Verified issuer/audience/actor grants and dedicated WACRM Central staging, encrypted credential custody, owner-owned outbox and inbox, webhook signature/replay, exact Meta WABA activation and read-only sandbox certification.
- **Host security:** DNS-aware SSRF and egress restrictions, durable send idempotency, rate-limit/429 backoff, recipient consent and cost policy, code-owner signoff.
- **Ancestry:** PR #261 targets draft #258, itself stacked on drafts #257 and #215. `main` has diverged; do not merge #261 directly or pretend it has been promoted.

## Open-source / cost / rollback

Reuse the existing first-party WACRM Central broker/outbox architecture, MIT [Dojo WhatsApp SDK/MCP](https://github.com/DojoCodingLabs/whatsapp-adapter), and built-in Node primitives. **No new paid tooling, packages, Meta traffic, credentials or vendor authorization** used. Rollback is to close the review-only PR; no running services or database migration changed. The existing #261 code was not rewritten. Ashwakaal — Support Channels remains a separate venture. A source-only PR is **not a VERIFIED_LIVE Supabase Master event**.
