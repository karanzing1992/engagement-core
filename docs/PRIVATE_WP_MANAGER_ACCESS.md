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


## Git theme-package sync: native capability exposure (source proposal, 17 Oct 2026)

**STATUS: WordPress + MCP gateway deployed and independently checked 17 October 2026; new client-side tool discovery still PENDING until the private WP Manager connection refreshes.** WP Control already registers `wp-control/package-list` and `wp-control/package-sync` as private WordPress abilities. The owner's private MCP connection initially omitted these tools, and WordPress's paired `/wp-control/v1/bridge` action switch omitted their routes, so exposing only the MCP tool would fail with `wp_control_action_not_allowed`.

The scoped code reuses the existing WordPress admin/site pairing and Deployer for Git allowlist. The gateway exposes `list_git_packages(site_id)` (read-only repo/branch/slug discovery) and `sync_git_package(site_id,type,package,expected_repo_url,expected_branch,confirm:true)`. The WordPress bridge independently validates exact configuration, requires an actual boolean confirmation, and refuses to sync a different theme from the active stylesheet. No arbitrary URL, credentials, API secret, PHP file write, plugin installation or unconfigured package is accepted.

**Never issue sync merely because the tool becomes callable.** First verify a fresh, independently restorable theme backup, compare the configured `repo_url` and `branch` with the approved default-branch Git commit, review the code change and obtain live release approval. The legacy WPVibe draft is not the live Git theme. Run existing CI across PHP 7.4/8.1/8.3 and validate the remote type/schema. WordPress source must be installed through the existing cryptographically signed Engagement Core updater (new immutable manifest, checksum, dry-run, health/rollback). The Supabase WP Manager gateway requires a separate reviewed rollout and OAuth MCP client tool refresh before invoking new tool names. Until both sides are independently live, record `SOURCE_ONLY`. Do not call `package-sync` through raw unauthenticated REST or direct Deployer API secret. A successful WordPress package-sync response requires real public HTML/theme readback before marking the SEO theme `VERIFIED_LIVE`.

Rollback strategy: for the **gateway**, redeploy the previous exact Edge Function version with existing files/settings; for **Engagement Core**, use the signed updater's stored previous version only if health-verified, not a fabricated local backup. For **Moksha theme**, restore a separate verified theme snapshot or re-sync previous approved default-branch content; the old committed SHA by itself is not an immediate filesystem restoration.

### Verified release receipts (17 October 2026)
- WordPress Engagement Core live `0.9.16` installed using **existing Ed25519 signed updater**, immutable source commit `842199dbc524c17b7e867befb3c3cc7bec355bbc` built from previously installed 0.9.15 commit `627c8d738d38cbadcffbb3590e9813f22babb8fb`. Exact immutable ZIP SHA-256 `c07f33de08a16121bb7e53c8c39bde1d6690fde106a0fc33cbf99d21e9e1c2ce` from [CI run 39050305370](https://github.com/karanzing1992/engagement-core/actions/runs/39050305370). CI verified **only** `engagement-core.php` and `src/class-grec-wp-control.php` changed relative to prior release. Signature verification and `engine_update(dry_run:true)` passed. Actual updater returned `updated:true, health_verified:true, rollback_ready:true`. Independent `engine_status` confirms 0.9.16 and rollback 0.9.15.
- Supabase owner OAuth `wpcontrol-mcp` Edge function **v47** ACTIVE, changed only existing `lib/server.ts` in a three-file deployment, retaining OAuth and JWT setting. Added typed read-only `list_git_packages` and destructive `sync_git_package`; advertised server version `0.2.3`. Existing `get_profile`, `site_overview`, `gsc_status`, `telegram_status` readbacks successful after rollout. **Current ChatGPT session's preloaded tool catalog has not refreshed** and does not expose the two new tool names; do not assert a completed end-to-end package sync.
- Existing registered `wp-control/package-sync` WordPress ability (direct Abilities API) unchanged; the new paired bridge dispatch has a *separate* explicit boolean confirm and exact configured repo URL, branch and active stylesheet lock. No WordPress theme, Woo booking, orders, media or paid tooling was modified as part of this capability rollout.
- The canonical GitHub `engagement-core` main repository is **not** a signed WordPress installation archive merely because this source PR merges. WordPress 0.9.16 installed from the immutable **minimal release** commit above. Future installer/signing must advance to a new version, use a reviewed release delta and preserve rollback. Do not point release manifests at the evolving main tree without comparing to the deployed immutable baseline.
