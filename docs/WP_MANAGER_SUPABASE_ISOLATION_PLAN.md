# Private WP Manager — Dedicated Supabase Isolation Plan
**Decision status:** PROPOSED / NOT DEPLOYED
**Recorded:** 12 October 2026
**Workstream:** Moksha WordPress private WP Manager

## Purpose and present state
The first-party WP Manager ChatGPT plugin communicates through the existing authenticated `wpcontrol-mcp` Supabase Edge Function in **existing multi-use Supabase project `saczglesalubroyaucqe`**, with paired site-owned WordPress Engagement Core API. This existing service is actively used. Private Supabase functions and keys in that multi-use project also serve unrelated workflows, so account/permission isolation is a future hardening measure, **not an automatically authorized migration**.

**No dedicated WP Manager Supabase project has been created or verified as part of this plan.** Do not conflate it with the separate Andaz PMS Backup Vault or place shared management credentials in that vault.

## Proposed target (requires owner approval and testing)
- A dedicated Supabase project for the private WordPress control gateway with independent authenticated user identities, scoped service keys, isolated Edge Secrets, least-privilege RLS and detailed redacted audit logs.
- Migrate only the verified WP Manager gateway implementation and explicitly approved site pairings; do not copy the constituency application database, Andaz bookings, unrelated customer records, analytics histories or other tenant secrets.
- Verify OAuth redirect URLs and per-site owners end-to-end before any production cutover; preserve old gateway until new path passes scoped read operations and controlled dry runs.
- Record explicit rollback: restore prior paired gateway URL and tokens using an owner-audited cutover, with no guest impact. Never assume that sharing a public URL means a credential can be reused.
- Independently review cost, permitted plan quotas, maintenance, incident response, registry reporting and restore credentials before approving deployment.
- Do not create any project, move secrets, revoke authorizations, disable a gateway or change production URLs merely because this proposal was registered.

## Current status for cross-project reporting
**Architecture proposal only.** The existing Supabase gateway has been observed as `ACTIVE` (Edge Function `wpcontrol-mcp` v30 during the 12 October audit). This observation does not mean the separate project exists or that the migration is approved. If a later production deployment is authorized, report it as a separate source-backed release/Route B event with its own exact evidence and audited migration record.

**References:** https://github.com/karanzing1992/engagement-core/blob/main/docs/PRIVATE_WP_MANAGER_ACCESS.md and https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_HEALTH_RUNBOOK.md
