# META CORE Phase 1-E — Tokenless Broker Response Contract

Date: 2026-11-10 (Asia/Kolkata)  
Owning lane: `karanzing1992/engagement-core`  
Dependency: [Phase 1-D PR #215](https://github.com/karanzing1992/engagement-core/pull/215) and WACRM [PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134)  
State: **SOURCE_ONLY / REVIEW_REQUIRED / NOT DEPLOYED**

## Scope completed in this additive branch

The new `createContractEnforcedWacrmBrokerAdapter` composes the existing
`createWacrmCentralBrokerReadAdapter`. It adds a **second fail-closed response
boundary** without modifying or replacing the existing draft implementation.

- Only existing `whatsapp_list_templates` and `whatsapp_get_template` are exposed.
- On success, require the exact Graph v26 WACRM Central template schema:
  `{id,name,language,status,category?}`; list page `{data:[...],after?}`.
- Reject unknown fields at all levels, including nested bearer/access token,
  debugging URLs, arbitrary Graph attributes, malformed IDs and out-of-bounds
  pagination. There is no generic Graph pass-through.
- Match the get-template response ID to the approved requested template ID.
- Copy only allowed primitive fields into frozen returned objects.
- Keep the existing principal authorization, strict tenant/activation/WABA/phone
  route, HTTPS pinning, server-side signing, nonces, bounded response and
  upstream-error semantics unchanged.
- No webhook ownership, message transport, phone lifecycle, Media API,
  remote OAuth issuer, credential store or new vendor permission added.

**Important:** This factory is an **additive candidate**, not automatically
substituted into existing PR #215 call sites. The previous constructor still
exists. The release integration must intentionally select this guarded
constructor, complete cross-language schema tests and obtain code-owner review
before anyone may claim the response guard is deployed.

## Reference / reuse / cost gate

1. **First-party owned:** WACRM Central
   `inc/wacrm-central-meta-read-broker.php`, specifically
   `select_template`, `template_page`, `graph_read`; owns token custody
   and sanitizes responses in [WACRM PR #134](https://github.com/karanzing1992/moksha_wordpress/pull/134).
2. **First-party owned:** current
   `src/wacrm-central-read-broker.mjs`; owns authorization, HMAC request,
   replay transport contract and read-only tool allowlist.
3. **Upstream reused (not duplicated):**
   [DojoCodingLabs/whatsapp-adapter](https://github.com/DojoCodingLabs/whatsapp-adapter)
   SDK 0.10.0 and MCP 0.5.0 (MIT per Phase 1-D review); the existing adapter
   still has an explicit Zod 4 compatibility risk. This change uses only
   built-in Node.js APIs and no new dependencies. No license additions or
   hosting/model purchases.
4. **Custom glue:** exact response-shape validation at the Node trust
   boundary, deliberately separate from the existing broker until independently
   reviewed. It is a narrowly scoped defense-in-depth adapter, not a new
   Meta client, webhook receiver or CRM.
5. **Cost:** no paid SaaS, Graph traffic, billable messaging or new runtime
   infrastructure for synthetic tests.

## Verification and release gates

Source test file: `test/phase1e-response-contract.test.mjs`.

Positive cases: A/B synthetic tenant template lists, pagination, one
WABA-scoped template detail and empty page. Negative cases: cross-tenant
principal, blocked send, mismatched template ID, unknown fields, nested
credential leakage, malformed list/template data, prototype pollution,
overlong cursor and field bounds. All requests target a fake local transport;
they cannot send to Meta. The parent Phase 1-D suite and npm audit remain
mandatory and must run on the exact candidate SHA in GitHub Actions.

**Not claimed:** real Meta application scopes, phone coexistence, token
rotation, owner-operated WACRM staging, Central Auth OAuth grant enforcement,
SDK Zod compatibility outside the tested read methods, approved send scopes,
or production deployment. Central Auth release is owned separately by
DeluluTech [PR #57](https://github.com/aarondash5-star/delulutech/pull/57)
and META CORE [issue #254](https://github.com/karanzing1992/engagement-core/issues/254).

### Required follow-up

1. Independent Node/CI review and actual WACRM PHP-to-Node output parity tests
   using the exact source heads, with no real Meta credentials or customers.
2. Wire this factory at the explicitly authorized staging server integration
   point; keep old and new constructors from being silently mixed.
3. Complete dedicated WACRM staging with encrypted crypto, protected HMAC
   secret, synthetic tenant and rollback, plus token audience/grant checks from
   the independently certified Central OAuth issuer.
4. Read-only approved Meta sandbox call, scope and coexistence verification
   under a separate owner release gate, then security sign-off.
5. Do **not** merge, deploy, turn on resource grants, send messages or change
   WhatsApp phone registration during this source sprint.

Rollback: abandon this additive branch/PR; no database migrations, flags,
secrets, customers, production endpoints or current draft files were changed.
Ashwakaal — Support Channels remains a separate workstream. No
`VERIFIED_LIVE` Master event is justified by this source-only increment.
