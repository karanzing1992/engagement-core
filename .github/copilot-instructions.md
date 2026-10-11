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
