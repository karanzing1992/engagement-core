# Generic Linux SSH — resilience release (21 Oct 2026)

## Implementation status: VERIFIED_LIVE
- Supabase project: `saczglesalubroyaucqe` (shared owned Automation lane; Ashwakaal support remains separate).
- Gateway: `generic-linux-automator` Edge **v5**, service **1.1.0**; previous Edge v4/service 1.0.1 available for rollback.
- Source: `product/gateway/supabase/functions/generic-linux-automator/index.ts`.
- Worker on both `dell-linux` and `mac-linux`: root-owned `/opt/generic-linux-automator/worker.py`; SHA-256 `45f4e1770d5a70ecc724808cf6d9fff3ec1f5584741037a18bd923ec20102b43`.
- Worker release source: `tools/generic-linux-automator/worker.py`. Host backup `/opt/generic-linux-automator/worker.py.pre-hardening-20261021` on BOTH hosts.
- Worker service drop-in: `/etc/systemd/system/generic-linux-automator.service.d/20-watchdog.conf` with `Type=notify`, `NotifyAccess=main`, `WatchdogSec=300s`; verified active five-minute watchdog on both.
- Shell account `generic-auto-exec`: removed NOPASSWD ALL on BOTH; replaced ONLY with `sudo systemctl restart generic-linux-automator.service` (plus unrelated Linux Mint distro commands). Backup root-only `/root/generic-auto-sudoers.pre-hardening-20261021`. **This deliberately removes general root-admin via ChatGPT SSH.** Restore only through an independently authorized system administrator.

## Threat model and safeguards
1. ChatGPT OAuth access can expire. Supabase Auth is source of trust; never mint replacement owner tokens via worker secrets or four-digit PIN. 401 invalid_token prompts owner reconnection; Auth upstream 503, 429 and timeouts are transient 503 Retry-After.
2. Gateway jobs admit 12 active valid queued/running per host, support optional 8–96-character `idempotency_key` unique to `owner_id,host_id`, with canonical same-command same-timeout retry handling and collision rejection. Current ChatGPT plugin tool schema may not expose optional key until tool schema reload; DB uniqueness was tested using synthetic expired job and then deleted.
3. Queue maintenance by native Supabase pg_cron `generic-auto-queue-reconciliation` every five minutes, id 2. Unclaimed overdue queued records -> `expired`; claimed overdue -> `outcome_unknown`. The worker may later submit matching original claim receipt to resolve uncertainty. **No automatic re-execution or false success.**
4. Worker stdout/stderr temporarily spooled to disk with RLIMIT_FSIZE 256KiB per stream in SSH child; only first 20,000 characters persisted or transmitted. Protects memory from unbounded PIPE capture; child errors on excessive output. Best-effort redaction of obvious Bearer, password, secret and API token literals BEFORE SQLite storage. Do not run credential-dumping commands; arbitrary values may still evade redaction.
5. Durable SQLite journal persists `claimed` and `result` before sending; on restart an uncertain interrupted command is recorded as failed with NULL exit instead of replayed. Worker lock prevents two conflicting pollers. Exponential backoff with jitter and systemd watchdog detect hangs.
6. `generic_auto_health_events` RLS enabled, anon/authenticated grants revoked; status events stored at most 60 days. A separate ChatGPT hourly condition-watch `Linux Bridge Outage Watch` notifies on material outages; it is NOT 5-minute paging and actual future notification delivery is not yet independently verified.
7. Existing host pairing, per-owner identity, shell dual gate and localhost SSH host-key pinning remain. No credentials/keys are stored in public source.

## Runtime QA performed
- Dell + Mac heartbeat fresh, worker active, root-owned production SHA identical, `WatchdogUSec=5min`.
- Both latest `linux_probe` records completed exit code 0 after worker restarts.
- Restricted sudo test on BOTH returned `BLOCKED` for arbitrary root command, and sample strings `Bearer TESTTOKEN password=SECRET123 api_key=ABCDEFGHIJK` were redacted in cloud receipts.
- Gateway version readback via `/health` 1.1.0; owner tools still return host status; no-token and invalid-token checks passed on Edge 1.0.1 before upgrade, owner-auth checks passed after 1.1.0 deployment.
- Database unique idempotency index exists and duplicate synthetic expired-job insert produced exactly one row, then deletion.
- Supabase migrations: `generic_auto_resilience_queue_idempotency_and_health` (20261021080116) and `generic_auto_reconcile_and_health_events` (20261021080555).
- Historical stale jobs safely reconciled: one Dell claimed record -> `outcome_unknown`; Dell one plus Mac three unclaimed -> `expired`. Do not replay.
- Explicit end-to-end simultaneous duplicate MCP requests with idempotency key: **NOT YET TESTED**, because this ChatGPT session's published tool schema still lacks the optional field. New-session MCP schema refresh is required.
- Simulated provider 503 branch and deliberately frozen worker were **NOT** induced in production; no unsafe outage testing performed.

## Recovery/rollback
- Host error with MCP 401 while workers online: owner reconnects existing plugin. Do not rotate pairing or reboot machines.
- Host worker stuck: use independent owner-admin access to inspect journal/systemd; the restricted bridge may restart ONLY `generic-linux-automator.service`, and only when no uncertain running task.
- Edge rollback: redeploy verified previous v4/service 1.0.1 from prior immutable PR #62 commit, preserve `verify_jwt=false` (because Edge itself authenticates owners and workers). Never disable authentication.
- Worker rollback requires independent admin rights, not generic-auto-exec: compare expected backup SHA `b76def38da04038441c8163ee03a3e226de072f862650727db426b0010c76beb`, restore backup atomically, remove watchdog drop-in if reverting sd_notify support, reload daemon and restart; verify both hosts.
- Cron rollback: `select cron.unschedule('generic-auto-queue-reconciliation');` only with owner authorization. Do not rollback status constraint while historical `expired`/ `outcome_unknown` rows exist.
- General-root sudo restriction is intentional and should not be rolled back for convenience.

## Golden Rule 0 / costs
Existing OSI-open-source Python standard library, systemd, SQLite, GitHub, Supabase tools, and owned worker/source were reused. No new paid service, external browser vendor, token store or extra hosting introduced. Supabase free-plan scheduling use must remain within resource limits.

STACK CHANGE: Existing automation bridge with hardened worker, queue, cron and owner auth. Live machine deployment and repo source are separate until merge/consumer readback.
