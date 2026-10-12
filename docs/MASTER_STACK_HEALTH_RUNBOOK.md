# MOKSHA MASTER — Operations Health and Recovery Standard
**Effective:** 12 October 2026. **Workstream:** shared reporting, not production deployment.
**Canonical protocol:** [MASTER_STACK_UPDATE_PROTOCOL.md](./MASTER_STACK_UPDATE_PROTOCOL.md)
**Registry:** https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

## Publishing architecture: exactly two independent routes

1. **Route A — monitored GitHub default-branch commit:** installed owner-managed **Google Apps Script** enumerates exactly nine allowlisted repositories and appends unique `[MASTER-GITHUB-CHANGE:repo:SHA]` markers to the Google Doc. Its private per-repository cursors live in Google Apps Script Script Properties, **not** `public.master_stack_repo_cursors`. Repo changes do not automatically update installed Apps Script code. A fresh Google Doc entry proves publication for that source; it does not by itself prove the time-driven trigger is configured.
2. **Route B — verified service/platform change:** Supabase project `saczglesalubroyaucqe` stores source-backed events in `public.master_stack_change_events`. The existing ChatGPT automation **Master Inbox Sync** (task `6acb14e2f848819195dc354327ddf2ca`) is enabled with an hourly condition-watch schedule. It verifies sources, appends unique `[MASTER-STACK-EVENT:ID]` markers, reads the Doc back, and only then updates review state and published timestamp. It MUST NOT duplicate Route A's GitHub source markers or scan GitHub commits independently.

**Critical isolation:** Supabase `cron.job` `moksha-master-external-task-dispatcher` running every 15 minutes checks backlog, stale repo cursors and Opera heartbeat. A successful cron run proves the *health check* executed, **not** that the Docs inbox publisher or Mac agent succeeded. Supabase Edge Function `master-stack-worker` is a separately deployed service; `ACTIVE` status or `verify_jwt:true` is not evidence of invocation or successful publishing.

## Health gates and escalation

| Component | PASS | WARN/FAIL |
|---|---|---|
| Connected apps & registry | Google Docs read succeeds; Source/Skill/DB reachable | Any required access denied, stale installed Skill compared with GitHub |
| Apps Script Route A | Owner shows successful **time-driven** execution within expected window, or confirmed recent monitored material commit marker | Trigger never verified, repeated script errors, new tagged commit absent after 2 expected windows |
| Route B automation | Task **enabled**, recent completion; pending events reviewed promptly; each published row's unique document marker exists | Disabled task, any `verified` older than 2 h, any `pending_review` older than 24 h, missing marker or failed update |
| Supabase dispatcher | Enabled cron, recent successful executions | Cron error/stopped, stale `master_external_schedules.last_run_at` |
| Device automation (separate) | Opera recent verified heartbeat | Last heartbeat over 30 min old; do not claim Mac is online from a passing dispatcher |
| Deduplication | Exactly one event/source marker per published change | Duplicate markers, conflicting source URL or mismatched event title and commit |
| Security | All privileged credentials stay in their own connectors/secret stores | Tokens in Git/Google Doc, public service role permissions, cross-tenant account access |

## Read-only SQL diagnostics
Run against Supabase project `saczglesalubroyaucqe` using an authorized connected app. No mutations in diagnostic phase.

```sql
select review_status,count(*) as n,min(created_at) as oldest,max(created_at) as newest
from public.master_stack_change_events group by review_status order by review_status;

select id,origin_project,source_kind,source_url,title,review_status,created_at,
       published_at,review_note,publish_error
from public.master_stack_change_events
where review_status in ('verified','pending_review','needs_info')
order by created_at;

select jobid,jobname,schedule,active from cron.job
where jobname='moksha-master-external-task-dispatcher';

select jobid,status,start_time,end_time,return_message
from cron.job_run_details where jobid in
(select jobid from cron.job where jobname='moksha-master-external-task-dispatcher')
order by start_time desc limit 10;

select task_key,enabled,last_run_at,next_run_at from public.master_external_schedules order by task_key;
select task_key,started_at,outcome,details from public.master_external_schedule_runs
order by started_at desc limit 12;

select repo_full_name,last_checked_at,last_error from public.master_stack_repo_cursors;
select started_at,finished_at,outcome from public.master_stack_worker_runs order by started_at desc limit 10;
```

The Supabase repo cursor timestamps might remain old while Route A is fully active: the owner-installed Google Apps Script has **separate** checkpoints. Never backfill or mutate those Supabase cursors to manufacture health.

## Reconciliation without duplicate or false claims

1. First inspect the Google Doc for both `[MASTER-STACK-EVENT:ID]` and any matching `[MASTER-GITHUB-CHANGE:repo:SHA]`. Check that a marker occurs exactly once and links to the correct source.
2. Validate the actual source, current evidence and *scope*. A GitHub source commit is **not** evidence of a live WP/Mac/Supabase deployment. Cloud Console or private WordPress admin URLs require authenticated access; unreachable pages should remain pending, not invented as verified.
3. If the matching source marker already exists, reconcile the Supabase row without writing a duplicate.
4. Otherwise for `verified` rows, append a factual dated, source-linked note with the unique `[MASTER-STACK-EVENT:ID]` marker. Reread the Google Doc to check marker and source before updating to `published`.
5. For `pending_review` rows, independently inspect platform/source evidence. If the supplied source URL is for a **different change**, set `needs_info` and explain the exact mismatch in `review_note`. Do not replace an inaccurate source silently.
6. Use scoped compare-and-set status writes (e.g. `WHERE id=? AND review_status='verified'`); never update booking/customer records, provider permissions, live user messages, production sites or GitHub Actions as a side effect of registry reconciliation.

## Incident: 12 October 2026

**Detected:** Master Inbox Sync was **disabled**; 15 inbox events: 1 published, 6 verified waiting, 8 pending. Supabase cron was healthy and **warning** about the backlog. The independent GitHub→Doc flow had 75 unique source markers, with a recent 12 October entry. Mac Opera had not heartbeated for approximately 2 hours. The installed `master-stack-sync` Skill lacked newer Ashwakaal/Automation policy even though GitHub contained it.

**Remediation:** Reactivated the existing Master Inbox Sync task. Six previously verified entries were subsequently published and read back in the master Google Doc as events `[MASTER-STACK-EVENT:2]` … `[MASTER-STACK-EVENT:7]`. The remaining platform claims were reviewed separately. Entries #9 (claimed GSC read-only gateway tools, source commit actually updater diagnostics) and #12 (claimed separate Supabase-project plan, source commit actually basic-auth gateway support) were set `needs_info` with precise mismatches, not published.

**Observed restrictions:** WPVibe account reached a 24-hour free-plan tool quota and connected GSC Wizard reports `payment_required`; these block direct live platform verification here. Never bypass billing/authorization or treat previously captured operator screenshots as proof of current status. Unattended Apps Script trigger status needs owner-side Executions inspection. Mac Opera heartbeat issues belong to its separate automation workstream and must not prompt cross-brand credential changes.

## Master Skill release discipline

GitHub `plugins/moksha-master-stack/skills/` is the canonical **Skill source**, not a guarantee the installed ChatGPT plugin has that release. Audit skill content via `skills__read` and compare against current GitHub source. Refresh the actual plugin only through the creator/authorized installed plugin editor. Do not claim account-wide installation from source updates. The skill must explicitly include Ashwakaal isolation, verified Automation & Systems multi-repo mapping, Route A default-branch caveat and Route B approval controls.

## Keep scope proportional

Avoid a second GitHub poller, duplicate ChatGPT task or needless paid GitHub Actions. The existing hourly task can recover platform-only events; dispatcher warnings and this runbook provide independent detection. Alert on repeated failures/age, not every no-change polling cycle. This runbook registers controls but doesn't prove them operational until observed in live provider telemetry.


## Closure audit — 12 October 2026

**Result: all previously held reporting events reconciled with source evidence.** The four remaining Google events were independently corroborated against the authenticated, completed Opera agent *historical* browser jobs already stored in existing Supabase `public.automation_jobs`. This did not require new Google sign-in, credentials, or customer data.

- Event **#13**: API/client/scope screenshots/snapshots from jobs `976`, `978`, `981`, `983`, `985`, `989`. Supports Google Web Application OAuth client and read-only scope on 12 October; does not expose client secrets or claim current future grant status.
- Event **#14**: job `1021`, dated **2026-10-12 14:26 UTC**, showed WordPress admin “Search Console connected with read-only permission” and “Connected (read only)”. Confirmed as historical, not perpetual OAuth health.
- Event **#15**: jobs `1009` and `1011`, dated **2026-10-12 14:15 UTC**, showed accessible `https://mokshagoa.com/` Google Search Console property and a historical performance report. Metrics are dated to that snapshot, never automatically current.
- Event **#16**: Site Kit jobs `1033`–`1036` showed Advanced data breakdowns UI and a save action, and GTM jobs `1055`, `1059` showed the newly created container ID. This is **not** evidence that the Tag Manager container is deployed/published or that event tracking is live. The advanced toggle itself was not independently visible in the last post-save snapshot.

Each event received an accurately qualified, owner-readable source URL and one unique canonical Google Doc marker. Following readback, events were transitioned `needs_info → verified → published`; the database was never advanced ahead of document verification. No previous duplicate publication marker was added.

**Skill adoption:** Private owner plugin [moksha-master-stack-reinforced v1.1.0](https://chatgpt.com/plugins/plugins_6acd2050739081918cbd975f2e23409c) exists and `skills://plugins/moksha-master-stack-reinforced/master-stack-sync/skill.md` was successfully enumerated and loaded on 12 October 2026. Its source includes Ashwakaal tenant separation, multi-repo Automation mapping, Route A/Route B idempotency and health runbook controls. The legacy `skills://plugins/moksha-master-stack/master-stack-sync` URI is still available: Project-specific persistent Instructions are not centrally editable here, and should prefer the reinforced Skill if both appear. Do not mistake creating a new private plugin for overwriting the legacy one.

**Apps Script runtime evidence (indirect only):** Google Drive native Master Registry revisions at `2026-10-12T09:31:49Z`, `10:31:46Z`, `11:31:48Z`, `12:32:01Z` include successive additions of unique `[MASTER-GITHUB-CHANGE:...]` entries, consistent with automatic hourly GitHub→Docs publishing. Independent Apps Script execution-list and configured trigger inspection **were not granted through these tools**, so a literal owner-visible Apps Script execution record is still UNVERIFIED. These observed publications nevertheless establish repeated functioning Route A output, not merely source-code configuration. Avoid marking individual trigger execution logs as inspected.

**Remaining operational distinction:** This is a clean reporting/backlog state; it is **not** a fresh live OAuth/GA4/GTM functional end-to-end test. When a future task requires current authentication, a live provider API/status read must be performed through an authorized connection. Retain snapshots with timestamps and read-only provenance. Never reuse guest or cross-brand credentials.
