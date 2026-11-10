# META CORE Lane A — host read response + legacy Dojo snapshot P2 remediation

**Date:** 2026-11-11 (Asia/Kolkata)  
**Source repository:** `karanzing1992/engagement-core`  
**Scope:** isolated synthetic-only WhatsApp MCP Lane A; no credentials, customer data, live Graph or deployment.  
**Frozen source base:** `dba775286e8df6ea032cc09074b20054d6fe701a`, [full-diff audit #278](https://github.com/karanzing1992/engagement-core/pull/278).  
**New work branch:** `fix/meta-core-lane-a-host-reads-dojo-p2-20261111`. Previous reviewed source and audit PR must remain unchanged.  
**Review origin:** two new P2 Codex threads on PR #278; earlier [issue #274](https://github.com/karanzing1992/engagement-core/issues/274) covers two prior P2 findings, not a substitute for new review.

## P2-A — Host Graph read field parity and response integrity

**Finding:** Graph request blueprints explicitly request `timezone_id,message_template_namespace` for `whatsapp_get_business_account`, but the generic output allowlist dropped them; `whatsapp_list_qr_codes` could turn `data:[{code,prefilled_message,deep_link}]` into `data:[{}]` while claiming success. Generic `{id,name}` mock fixtures did not exercise the real read contract.

**Fix:** `src/lane-a-provider-runtime.mjs` retains its global credential-deny and basic `copyKeys` allowlist. A new **per-tool scoped map** allows only documented Graph read fields at the authorized response object or a `data[]` record. Scoped operations include business-account, QR listing, flow/flow assets/metrics, and subscription reads. A metric `value` is permitted solely under its declared metric-values path; it remains denied elsewhere. Blank QR-list rows are rejected rather than returned as apparently successful empty objects. Caller-owned Proxies, getters, aliases, confidential keys and unsafe arrays continue to fail closed.

**Required examples:**
- `whatsapp_get_business_account`: `id,name,timezone_id,message_template_namespace` preserved.
- `whatsapp_list_qr_codes`: `code,prefilled_message,deep_link` and `qr_image_url` preserved inside `data[]`.
- `whatsapp_get_flow`: `preview,data_channel_uri,whatsapp_business_account` preserved.
- `whatsapp_get_flow_assets`: `asset_type,download_url` preserved.
- `whatsapp_get_flow_metrics`: nested `metric.values[].value` preserved only within that tool.
- `whatsapp_get_subscription_status`: `subscribed_fields,override_callback_uri` preserved.
- Unrelated `whatsapp_get_phone_number` must not leak scoped business-account/QR fields.

## P2-B — Dojo legacy source must not invoke attacker-owned serialization hooks

**Finding:** `src/dojo-v26.mjs` previously inspected own descriptors in `boundedArgs(args)` but then ran `JSON.stringify(args)` on the **original caller-owned graph**. A custom nested array prototype could define an inherited `toJSON` getter/method, which ran before tenant authorization and could replace the validated representation.

**Fix:** Replace the boolean scanner with a **bounded, descriptor-only recursive deep copy** that does not call `JSON.stringify` on caller-owned inputs. Proxies, inherited/custom array prototypes, own accessors, sparse arrays, cycles/shared references, invalid primitive types and forbidden prototype-pollution keys are rejected before any authorization, token resolution, SDK construction or network path. Existing 256-node, depth-8, max-128-array-item limits are preserved, along with per-string length and a cumulative UTF-8 budget. Plain arrays/objects are reconstructed from own *data* descriptors and passed as independent `safeArgs` to the trusted Dojo dispatcher; later mutation of original args cannot affect dispatch.

**Required tests:** zero inherited `toJSON` getter invocation, no host callbacks on rejected inputs, no own getter invocation, valid bounded nested arrays, and TOCTOU mutation of input during async authorization not reflected in the SDK arguments.

## Testing and approval

New test file: `integrations/meta/whatsapp-mcp/test/lane-a-host-reads-dojo-snapshot-p2.test.mjs` (8 cases), added to the independent focused review workflow; all prior P1/P2/P3 suites preserved.

**Exact-head certification required after documentation:** >=144 full Node tests and >=52 focused tests, npm production dependency audit with zero high/critical vulnerabilities, two pinned scoped CodeQL security-extended scans with `CODEQL_FINDING_COUNT=0`, required synthetic/transport/manifest checks, and no unapproved paths or secrets. Check full tool fixture coverage; passing CI is source-only evidence.

**External human review:** Full-diff audit of the *new* exact SHA, not earlier #273/#278 approvals. Request new `APPROVED` or `REQUEST_CHANGES` and reconcile new review comments; do not silently resolve previous threads. Owner source-merge permission and tested main compatibility remain separately required.

**Strict NO-GO:** No original PR merged, no production, no live Meta/WACRM, no OAuth resource grants, no credential custody enabled, no outbound WhatsApp sends or billing. Lane B still requires host Promise/thenable trust, DNS rebinding, private IPv4/IPv6 and metadata blocks, redirect/TLS/egress enforcement, encrypted credentials, customer consent and durable outbox/idempotency. Preserve Ashwakaal — Support Channels separately and do not publish source-only evidence as `VERIFIED_LIVE` in Supabase Master.

**Cost/reuse:** existing Node built-ins, pinned GitHub workflow/CodeQL, Dojo/Zod and synthetic fixtures only; no new dependency or paid service.
