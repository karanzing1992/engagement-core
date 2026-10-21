# Generic Linux SSH v1.2.0 — seven-tool schema, six execution lanes, plugin rollout

**Effective:** 22 October 2026 IST  
**Ownership:** Automation / Generic Linux SSH; project `saczglesalubroyaucqe`  
**Source of truth:** existing `generic-linux-automator` Supabase Edge Function, `engagement-core` release commit `6168a7a3fd6b6bd3e7933188dd2161086667d3db` and [production rollout](./GENERIC_SSH_THREE_LANES_ROLLOUT_20261021.md).  
**New schema reference:** [mcp-tool-input-schema-v1.2.0.json](../product/gateway/supabase/functions/generic-linux-automator/mcp-tool-input-schema-v1.2.0.json).

## Verified production and ownership

- Live Edge **v6/service 1.2.0** advertises seven MCP tools, verified from deployed source.
- `dell-linux` and `mac-linux` each run **three** independently polling workers: control, operations, development. Six of six harmless lane commands completed with exit 0; the control and operations jobs overlapped each host's running development job.
- Existing operations service remained in place. All six workers were active/enabled; independent new worker restart smoke tests completed and fresh heartbeats returned; no host reboot or forced WAN outage was performed.
- Local `generic-auto` worker is nonroot; SSH command account `generic-auto-exec` retains owner-approved passwordless sudo on Dell/Mac. **Never change root grants without fresh host-specific explicit owner approval**. Keep credential, key, pairing, project, user and customer-data isolation.
- Master verification: `[MASTER-STACK-EVENT:132]`, `[MASTER-GITHUB-CHANGE:engagement-core:6168a7a3fd6b6bd3e7933188dd2161086667d3db]`; Supabase platform event #132 published.

## Seven MCP tool definitions (source verified)

| Tool | Request fields | Lane/return behavior |
|---|---|---|
| `linux_host_status` | `host_id` | Host heartbeat, `lanes.control/operations/development` timestamps, freshness and shell permission |
| `linux_pair_host` | `host_id` | Single-use enrollment code only for separately authorized unpaired host; never auto-repair |
| `linux_probe` | `host_id`, optional `idempotency_key` | Fixed read-only SSH probe in `operations` |
| `linux_ssh_run` | `host_id`, `command`, optional `lane`, `timeout_seconds`, `idempotency_key` | Defaults to `operations`; accepts control/operations/development |
| `linux_control_run` | `host_id`, `command`, optional timeout/key | Fixed `control` lane, no lane argument |
| `linux_development_run` | `host_id`, `command`, optional timeout/key | Fixed `development` lane, no lane argument |
| `linux_task_status` | `host_id`, `id` (UUID) | Terminal and interim receipt, per-job lane/status/output/exit code; never treat queued as done |

`host_id`: `dell-linux` or `mac-linux`. `command`: string 1–8192 characters. `timeout_seconds`: integer 5–120 (default 30 for shell). `idempotency_key`: optional 8–96 characters matching `^[A-Za-z0-9_.:-]{8,96}$`. A given key may be reused **only** for the identical host, lane, command, and timeout. Queue accepts up to twelve active jobs per host/lane; workers poll independent SQLite journals. Never auto-requeue `outcome_unknown`, `stale_running` or expired jobs.

**Example:** `linux_ssh_run({host_id:"dell-linux", lane:"development", command:"uname -s", timeout_seconds:20, idempotency_key:"linux-dev-uname-20261022"})`. The tool enqueues a job; poll `linux_task_status` for `completed` and exit code 0.

## Published plugin releases

- Reusable source/skills/MCP plugin **`generic-linux-ssh-mcp` v0.1.20**; plugin ID `plugins_6ad64adab5e481918832cd516e779009`, current release ID `pluginrel_6ad90aabda648191bfc39bce418dee4c`. Added canonical onboarding skill `skills/generic-linux-ssh-mcp/SKILL.md` and `schemas/generic-linux-ssh-tools-v1.2.0.json`. Original `.mcp.json` endpoint and unrelated skills preserved.
- The separately installed App-backed Generic SSH entry `plugin_asdk_app_6ad65c4697b481918d93a18735d4aa7e` is now **v1.0.1**, release ID `pluginrel_6ad90b297ebc8191bcb7493f03d21cde`. Added `skills/generic-linux-six-lanes/SKILL.md` as onboarding skill while preserving `.app.json` and its existing App ID and presentation; no new App, identity, auth grants or shell-permission changes.
- Verified each release with `get_plugin_files` readback. The *live server MCP schema* is seven tools. **The current old ChatGPT session may still expose cached five tools**; plugin files do not hot-reload a session's App tool definitions. Fresh-session reconnect and inspection is required before claiming UI/consumer schema acknowledgement. No manual proxy token or service-role bypass is allowed.

## Practical lane selection and safe recovery

Reserve `control` for quick diagnostics and bounded recovery, `operations` for normal SSH and browser orchestration (legacy default), and `development` for compiles/tests/build jobs. Parallel lanes do not provide separate user accounts, isolated files, extra resource quotas or lock-free browser profiles; protect shared files and CPU/thermal limits. For errors: check fresh per-lane `linux_host_status`, queue+terminal `linux_task_status`, the named instance's `systemctl` status and logs, and preserve local journal state. A stale authenticated plugin OAuth token is a **client authorization** issue; owner reconnects in Plugins, not worker-key repair.

Rollback: inspect all in-flight/uncertain receipts; stop extra `@control`/`@development` services, restore Edge v5 if authorized, retain operations and verified original worker backups. Do not change sudoers, rotate tokens, modify keys or open public SSH as part of rollback. Systemd enablement and restart were tested; full reboot/WAN interruption remain acceptance tests, not published claims.

**Open-source/reuse gate:** reused already deployed Python standard library/SQLite, OpenSSH, systemd, PostgreSQL and Supabase; no new paid dependency or service. Reference upstream: https://www.freedesktop.org/software/systemd/man/latest/systemd.unit and https://www.postgresql.org/docs/current/explicit-locking.html.

**Stack change:** Source and published plugins now document verified six-lane capability. Consumer tool-schema refresh is `PENDING` until a fresh ChatGPT session sees the seven live tools.
