# Generic Linux SSH — independent control / operations / development lanes

**Date:** 2026-10-21 (IST)  
**Owner lane:** Automation / shared `karanzing1992/engagement-core`; NOT Business House Matrix or Ashwakaal support data  
**Governance:** Golden Rule 0, no root/network/auth changes, no unreviewed overwrite, no duplicated bridges.

## Change status and evidence

- Existing live: Dell `dell-linux` and Mac `mac-linux`, each one active outbound systemd worker, paired, shell allowed. Source checksum on both prior to changes `45f4e1770d5a70ecc724808cf6d9fff3ec1f5584741037a18bd923ec20102b43`. `sudo -n /usr/bin/id -u` returned `0` for the existing execution account on each device. Preserve this; do not change sudo or owner policy.
- Verified live Supabase schema migration: `generic_ssh_three_lanes_20261021` **APPLIED** in `saczglesalubroyaucqe`. `generic_auto_jobs.lane` NOT NULL default `operations`, CHECK allowlist `control|operations|development`, per-lane queue index, per-host lane heartbeat timestamp columns. Existing queue jobs safely default operations.
- GitHub implementation source: `feat/generic-ssh-three-lanes-20261021`. Changes to existing worker, existing gateway, additive migration, hardened systemd instance template and preflight installer. These are **SOURCE ONLY** until activated on a specific host.
- Supabase Edge `generic-linux-automator` remains **LIVE VERSION 5 / service 1.1.0**. Attempted service 1.2.0 deployment via connected Supabase was blocked by runtime safety review. Do not claim completed lane rollout.
- No new host daemon, no device re-pairing, no new worker token, no SSH key, sudo grant, network port or permissions changed in this staged phase.

## Open Source / Reuse / Cost Gate

- Reuse already deployed Python 3 worker (PSF license) with stdlib SQLite crash journal, SSH client (OpenSSH portable BSD-style license), existing PostgreSQL queue (PostgreSQL license), systemd native template instances (LGPL-2.1-or-later), Supabase Edge and existing owner MCP OAuth.
- References: https://www.freedesktop.org/software/systemd/man/latest/systemd.unit and https://www.postgresql.org/docs/current/sql-select.html . Systemd templated units are standard multi-instance facility. Existing row claim predicate `status=queued AND claim IS NULL` preserves at-most-once job claims per ID; independent journal files avoid cross-lane lock collisions. For greater scale, PostgreSQL `SKIP LOCKED` in an atomic SQL claim is an optional future enhancement, **not** deployed.
- No additional product, paid API, host, open inbound SSH or dependency. No new service architecture; only two instances of the existing daemon per host. Cost: existing capacity/network requests only. No attribution obligations beyond upstream licenses of existing tools.

## Runtime behavior after reviewed cutover

- `operations` remains the legacy existing `generic-linux-automator.service` and all existing `linux_ssh_run`/probe calls default there.
- `control` is `generic-linux-automator-lane@control.service`, distinct journal `journal-control.sqlite3`; routed via `linux_control_run` or `linux_ssh_run(lane=control)`.
- `development` is `generic-linux-automator-lane@development.service`, distinct journal `journal-development.sqlite3`; routed via `linux_development_run` or `linux_ssh_run(lane=development)`.
- Backend separates the queue using the per-job `lane`; worker poll tags the lane; selected-lane heartbeat must be fresh before admission. Operations jobs already in queue still work. All 3 workers on a host reuse the SAME previously authorized local loopback-only SSH account/worker identity; they do not gain privileges and cannot access a different tenant.
- Each lane runs at most one foreground command per host and keeps crash/uncertain-outcome journal semantics. Three independent command lanes per host, six across Dell/Mac. Long-running command on one lane does not wait on another lane's worker loop.

## Deployment gate (NOT YET PASSED)

1. Confirm source diff and branch ownership; review Edge authentication, queue admission, idempotency, lane heartbeat and local sudo policy. Securely retain Edge v5 for rollback.
2. Confirm migration in database and original `operations` probe on both hosts succeeds.
3. Deploy modified Edge from branch through the authorized owner deployment route; **do not** circumvent blocked safety checks. Require Edge v6 / health service `1.2.0` and a new owner-authenticated MCP handshake. Existing `linux_ssh_run` still must work before adding workers.
4. On each host separately, transfer the reviewed `worker.py`, `generic-linux-automator-lane@.service`, and `setup-lanes.py` from that exact reviewed commit. Compare candidate worker `sha256sum` against independently reviewed checksum. Run `sudo python3 setup-lanes.py --candidate-worker <file> --unit-template <file> --sha256 <verified_hash>` (dry-run) then with `--apply` only after preflight passes. Installer preserves the existing unit, file ownership, SSH and worker token; backs up original worker and installs independent journals and hardened services.
5. Verify both additional systemd units ACTIVE and enabled, lane heartbeats less than 60 seconds old, and no worker-identity leakage. Existing operations worker should remain online.
6. Test 12-second inert development job while concurrently queuing 1-second inert control job, and a separate operations probe on the same host. Compare queued/started/completed terminal receipts to verify overlap and no starvation. Repeat on other host. Retry a request with same idempotency key and assert one execution only.
7. Confirm host reboot auto-start, transient connectivity recovery, per-lane journal crash-recovery semantics, no duplicate command replay, disabled lane fails closed, no thermal guard or sudo changes, and app MCP tool discovery refreshed.
8. Update canonical Master via platform event with verified scope/version and mark consumer acknowledgement only on actual successful re-read.

## Rollback

- First stop submitting lane-specific jobs, inspect queued/running lane receipts and avoid replaying unknown outcomes.
- Disable `generic-linux-automator-lane@control` and `@development` after drain. Legacy `generic-linux-automator.service` stays active.
- Return Edge to stored v5 and preserve additive schema (default operations is backward-compatible). If safe, restore backed-up worker file only after draining/reviewing existing operations job; do not overwrite unknown local changes.
- Never rotate host credentials, revoke sudo/root or change server pairing as a rollback shortcut. Never auto-requeue an uncertain remote operation.

**Stack change classification:** `DB_VERIFIED / EDGE_PENDING / HOSTS_PENDING / USER_TOOLS_PENDING`. Do not claim FULLY_SYNCED or production three-lane coverage before all smoke tests and Master readback succeed.

## 21 Oct supplementary validation

Read-only download/syntax validation of the pinned branch source succeeded separately on Dell and Mac. Worker SHA-256 `fa87f35fccfe2b3c7f66baae3d5d3d0ad3e075b0115e7fa4d57fd92ed278df9b`, installer `9b4a872883a40e9b658c0f5a8837d53342e7248affb87314d3787c92a3384eda`, and service template `c98ca73da5a659c1591af6a70ca2e2654b9a7b971753f942d8df3be11ae67a05` matched on both hosts. Live gateway health independently returned `1.1.0`. Existing original worker checksum remained unchanged and both services active, sudo identity 0. No additional lanes activated. Supabase Master inbox event #130 is pending review, not published.

## Inactive host staging checkpoint

Verified on **both Dell and Mac**: the three reviewed artifacts from pinned commit `118968fbd18e682d71a944fa425684cc09a84225` were installed **inertly** under `/opt/generic-linux-automator/releases/three-lanes-20261021/` (worker, installer, hardened systemd template). Each staged artifact matches the SHA-256 values in the supplementary validation section. Original operations unit remained ACTIVE; no additional systemd instances were running (count 0) on either host. Original live worker files were not overwritten and existing root/sudo authority was not modified. These staged files are NOT an activated three-lane bridge. Gate remains Edge 1.2.0 owner-authorized deployment followed by on-host installer preflight, activation and concurrency tests. No extra polling service may be enabled until gateway version is verified.
