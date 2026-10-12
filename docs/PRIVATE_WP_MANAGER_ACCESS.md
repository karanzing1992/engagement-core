# Moksha private WP Manager — first-party access, signed updates and Search Console

**Evidence date:** 12 October 2026. **Classification:** verified operational runbook, not a new authorization grant.
**Scope:** Moksha Wellness WordPress `https://mokshagoa.com/` and the private connected **WP Manager** ChatGPT plugin backed by **Engagement Core**. Do not conflate this with a third-party "WordPress manager" provider or assume the plugin appears in every ChatGPT Project or account.

## Canonical control architecture

```text
User-authorized ChatGPT session / private WP Manager plugin
  -> Supabase wpcontrol-mcp (owner-scoped OAuth/MCP gateway, currently Edge v16)
  -> POST https://mokshagoa.com/wp-json/wp-control/v1/bridge
     (bearer identity verified by WordPress, paired site ID and local admin rechecked)
  -> Engagement Core native WP Control action
  -> typed WordPress operation or independent first-party Search Console adapter
```

**Prefer this existing first-party path** for supported WordPress inspection, SEO, products, publishing, diagnostics and signed updater operations. It is separate from the **source-code lane**, which uses the monitored `karanzing1992/engagement-core` GitHub repository, and the **browser/UI lane**, which uses the authorized local Opera agent where necessary. Do not invent WP Control capabilities; discover currently connected tools. Third-party WPVibe is not required for WP Manager-native operations and its free-tier quota may independently fail.

Verified in a connected session: `list_sites` resolved **Moksha Wellness Goa**, active and paired at `https://mokshagoa.com`; `engine_status`, `engine_check`, `engine_update`, `list_plugins` and `site_overview` use the private WP Manager connector. Not all tools advertised by source necessarily become visible until the MCP gateway and ChatGPT plugin reconnect/refresh. Never infer a live credential, grant or connection from GitHub code, documentation or the connector name alone.

## Native signed updater — required operating sequence

1. **Discover** the user-authorized site with `list_sites`; pass the returned ID unmodified. Never guess a site UUID.
2. **Inspect** `site_overview`, `list_plugins` and `engine_status`. Confirm the intended installed version, active status, WordPress and PHP compatibility, signature readiness, current rollback state and any current failure.
3. **Verify release:** `engine_check` must report the expected newer version with **valid Ed25519 signature** and the intended immutable GitHub commit and SHA-256. Release service: `engagement-core-release` Edge Function, managed separately from the private MCP gateway.
4. **Dry-run:** `engine_update({site_id, dry_run:true})` must succeed. A dry-run is only a signature/version preflight, **not** proof that a live upload or filesystem swap will succeed.
5. **Install** via `engine_update({site_id})` only with user-authorized upgrade intent, matching verified signed version and no outstanding blocker. Do not bypass the native checks, force older releases with `allow_reinstall`, toggle plugin security or upload arbitrary zip/FTP in response to an error.
6. **Verify independently**: updater result `updated:true`, `health_verified:true`, `rollback_ready:true`; then re-read `engine_status` and `list_plugins`, public `/wp-json/engagement-core/v1/health` and `/wp-json/wp-control/v1/status`, plus any relevant guest page and unaffected integrations. Keep rollback ready and preserve WooCommerce/guest data.

**12 October 2026 verified production result:** Engagement Core **0.9.14 → 0.9.15** via this private native updater; updater reported signature valid, verified health and rollback to **0.9.14**. WordPress **7.1.2**, PHP **8.2.34**. Google Site Kit **1.187.0** remained active; Telegram remained connected; Mud Bath page remained reachable. Signed release `engagement-core-release` Edge **v8**, private `wpcontrol-mcp` Edge **v16**. Source commit `627c8d738d38cbadcffbb3590e9813f22babb8fb`; release ZIP SHA-256 `b9eb6eb60dab33522a3000a71f33258efa4332e45eea24367094456cac39352d`. Those are point-in-time observations, **not** immutable future version claims.

## Important HTTP 403 learning

- `engine_status`, `engine_check` and signed `dry_run` succeeded while some **actual installation** requests intermittently returned **HTTP 403** with no useful WordPress error code. The first failed request left the active plugin at 0.9.14; a subsequent normal, authenticated, signed installation succeeded.
- **Root cause was not conclusively determined.** It might be upstream or application policy; do **not** assert a firewall, ModSecurity, expired OAuth or WP permissions as confirmed.
- Safely distinguish response origin: WordPress REST `code`, numeric HTTP status and coarse response class (JSON vs HTML/non-JSON/none). Do not log/raw-return response bodies, bearer tokens, authorization headers, secrets or guest data.
- Check the live plugin and audit records **after every failed update** before retrying. Intermittent 403 is not license to turn off WAF, loosen ACLs, bypass site pairing/ownership, or install arbitrary software.
- Source diagnostic improvements: `engagement-core` squash commits `e7b846d0f9c89c0e838100fe520d1068a4c02fb2` and `450f02fd94ed54e86abfd7937ef928724976a92e`; Edge v16 supports safe response classification. Successful installation **does not prove the upstream error is permanently fixed**.

## Search Console status and OAuth boundary

- Native **read-only** Google Search Console tools are source-implemented and the Engagement Core **0.9.15** plugin and MCP gateway were deployed. The named tools are `gsc_status`, `gsc_search`, `gsc_inspect`, `gsc_sitemaps` (where exposed by the current private ChatGPT connection).
- **Google consent is separate and pending.** Admin opens `https://mokshagoa.com/wp-admin/admin.php?page=grec-search-console` and completes the independent Google OAuth read-only authorization. Do not borrow Site Kit, Windsor.ai, or GSC Wizard tokens or infer the new OAuth is connected because Google Site Kit is active.
- Google's URL Inspection API can return indexing/canonical state but **does not request indexing** for ordinary pages. Never claim it triggers a recrawl.
- Do not expose Client ID secret, refresh token, admin passwords, or any external tenant's personal data in GPT chats, GitHub or the master registry.

## Master Registry and cross-project boundaries

- **GitHub source changes:** merge a verified `STACK CHANGE:` final commit to the allowlisted `engagement-core` default branch and let the independent Apps Script Route A publish a unique marker. This runbook is operational evidence; source-only changes must not be reported as live deployment.
- **Live platform-only changes:** when supported by independent readback, submit one idempotent Route B event to `public.submit_master_stack_change` via the authorized Supabase connector. The separate inbox synchronizer publishes those events; read the Master Google Doc before claiming completion. Do not manually duplicate GitHub entries.
- Never assume the private WP Manager plugin is installed, enabled, authorized, or visible in another ChatGPT Project, account or device. Discover active connectors and use the owner-approved connection only. Connecting or installing remains an explicit user action.
- Tenant boundaries remain: Moksha and **Andaz Vibe Stay - Arambol, Goa** (including PMS/backup), Ashwakaal support channels and other ventures keep separate credentials, audience/customer data and approvals. No silent cross-tenant reads or writes.

**Authoritative evidence:** 
- Source: https://github.com/karanzing1992/engagement-core/commit/627c8d738d38cbadcffbb3590e9813f22babb8fb
- Gateway diagnostics: https://github.com/karanzing1992/engagement-core/commit/450f02fd94ed54e86abfd7937ef928724976a92e
- Public health: https://mokshagoa.com/wp-json/engagement-core/v1/health
- Live pairing status (not a login grant): https://mokshagoa.com/wp-json/wp-control/v1/status
- Master Registry: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit
