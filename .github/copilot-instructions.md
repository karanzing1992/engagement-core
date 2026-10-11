# Engagement Core — reusable WordPress connector platform

## Project governance
Keep a generic brand-neutral engagement engine with explicit brand/tenant adapters. Current source supports WordPress, OAuth-based YouTube engagement, and WooCommerce Action Scheduler with WP-Cron fallback; messaging channel availability requires individual authorization verification. Do not invent posting permissions or use unsupported social actions. Reel/media production must use properly licensed source and avoid unattended costly GitHub builds.

## Shared stack governance (11 October 2026)
This repository follows the **MOKSHA MASTER** technology stack/version policy as a shared engineering standard; it does NOT share business data, production credentials, legal identities or public branding across ventures.

Registry: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit
Automation audit: https://docs.google.com/document/d/1ybmMCLX_9gy2SUAL9_h-8HpTWBVWt_ksbTShHn1FF5w/edit

**Mandatory on every dependency, platform, security or API change:**
1. Inspect actual source/lockfile and deployed versions; verify supported stable release and official security/advisory notes. Never assume source equals production.
2. Compare compatibility, licensing, API quotas, costs, deprecations and migration implications.
3. Record dated release deltas in the canonical registry and relevant project documentation, noting current/available/approved target version, evidence, tests and rollback.
4. For urgent security issues, prepare a minimal reviewed patch quickly. For routine updates, propose a tested PR. **Never silently deploy or auto-upgrade major versions, production services, database schemas, payments, booking data or customer messaging.**
5. Prefer shared reusable core with per-brand adapter/config; audit identity and tenant boundaries. Protect secrets and private data.
6. Avoid unnecessary GitHub Actions, long-running Git polling or automatic costly tests; prefer targeted CI and existing authenticated runtime.
7. Treat this file as guidance for Copilot/agents, not authorization to mutate production.

## Cross-project master-stack event reporting — LIVE PROTOCOL (11 October 2026)
This repository participates in the shared MOKSHA MASTER technology registry. At completion of **material** features, fixes, integrations, security changes, runtime/dependency upgrades and verified deployments, use the **tested two-route synchronization method**. Treat this reporting duty as part of definition-of-done, not permission to deploy or change customer data.

**Route A — this GitHub repository (default):** Include `STACK CHANGE:` at the **start of the final commit subject** describing a real, material capability/technology change; detail verification, source vs live deployment, impacted components, versions, compatibility and rollback in the commit body. The independent Google Apps Script checks nine allowlisted repositories hourly and adds source-linked `[MASTER-GITHUB-CHANGE:repo:SHA]` entries to the master Google Doc. The script consumes **GitHub commits, not PR descriptions or ChatGPT messages**. If squash-merging, preserve the tag in the final commit message. Eligible conventional commits like `feat:` and `fix:` with changed code can also be detected. Do not label routine churn or generated output a stack change. Copilot-instruction-only changes are intentionally ignored by the collector.

**Route B — change outside GitHub:** If new verified behavior/configuration happens exclusively in WordPress, Google, Supabase or another connected service without a GitHub commit, authorized ChatGPT Projects may submit an idempotent, evidence-linked event via connected Supabase `public.submit_master_stack_change` (project `saczglesalubroyaucqe`). A **separate verified hourly Master Inbox Sync** publishes those events. Do not mistake Google Apps Script for the Supabase inbox publisher.

**Project separation & safety:** Do not include credentials, customer/guest data, private conversations or passwords. Code committed is NOT proof of production deployment; always label source-only vs verified live. Check releases/security, cost, compatibility, rollback, staging and backups before upgrades. StayCore PMS bookings require independent offsite backup and audited admin-only restore. Andaz Lifestyle Stay is an internal label; public brand is Andaz Vibe Stay - Arambol, Goa; keep tenant data separate.

**Canonical protocol:** https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md
**Worker details:** https://github.com/karanzing1992/engagement-core/blob/main/services/master-stack-worker/apps-script/README.md
**Master Doc:** https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

**ChatGPT Project distinction:** These repository instructions guide agents working in this codebase. They are not automatically installed into separate ChatGPT Projects. Add the reusable project-level paragraph in the canonical protocol to those Projects' persistent Instructions when you need chat-native compliance.
