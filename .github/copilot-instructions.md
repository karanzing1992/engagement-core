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


## Cross-project master-stack event reporting (active 11 October 2026)
Every material capability, integration, security fix, breaking API/dependency change or verified deployment must be reported to **MOKSHA MASTER**. Documentation only; it does not authorize any production change.

Preferred in an authorized ChatGPT Project: call the connected Supabase `public.submit_master_stack_change` function in project `saczglesalubroyaucqe` with a stable event key, repository/project, source HTTPS URL, change type, title, concise evidence-backed summary, source kind and version. No service credentials in Git. The private event inbox is synchronized into the Google master registry after source verification.

If using GitHub Copilot without the Supabase connector: add a `STACK CHANGE` block to the commit or PR description with type, scope, source version, deployed version only if verified, summary, evidence and rollback. A separate daily monitor checks the approved repositories for newly committed material changes.

Protocol: https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md
Master: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

Never include customer records, account data, credentials, private chat excerpts or security keys. Do not claim newly written Git code is live. Review and approve deployment separately.
