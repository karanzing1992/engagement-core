# Generic Linux Automator — Dell + Mac

Status: SOURCE CANDIDATE ONLY. Not deployed, not paired, not connected as a
ChatGPT plugin, and no Dell/Mac changes performed.

## Scope

A reusable automation transport, separate from Pine and game/project workers:

ChatGPT (new owner-authenticated private MCP plugin)
 -> Supabase OAuth MCP function "generic-linux-automator"
 -> per-host queue, owner authorization, receipts (dedicated DB tables)
 -> outbound-polling Linux systemd worker
 -> pinned local OpenSSH 127.0.0.1:22
 -> nonroot dedicated execution account on that same Linux host.

Host identities are "dell-linux" (Dell Inspiron 5379) and "mac-linux"
(Mac KARAN running Linux). Separate bearer credentials per host; worker
tokens are never shown to ChatGPT or committed. Shell execution is
disabled by default in BOTH gateway host DB and worker host config.
Only the fixed loopback probe is initially permitted.

## What is staged in this branch

- worker.py: standard-library Python agent, deterministic host IDs, outbound
  HTTPS, single-instance flock, durable SQLite no-replay receipt journal,
  token stored locally with mode 0600, SSH strict known_hosts and key-only.
- config.EXAMPLE.json: operator-supplied paths; copy outside repository,
  use the actual host ID and private gateway URL.
- systemd/generic-linux-automator.service: dedicated nonroot worker with
  systemd hardening, restart-on-failure and private writable state.
- supabase/migrations/20261019_generic_linux_automator_review.sql:
  independent tables with RLS on and no public/authenticated grants.
- supabase/functions/generic-linux-automator/index.ts:
  dedicated gateway supporting status, pairing, safe probe, disabled shell
  queue until explicitly enabled, and terminal receipts with claim tokens.
- tests/test_worker.py: offline validation and fail-closed negative cases.

## Mandatory deployment and QA gates

1. Review source/PR, correct host aliases, verify owner and approved
   Supabase project, snapshot DB and obtain authorization for migration.
   Do not copy Pine's DPAPI token, TradingView controller, account or key.
2. Apply reviewed SQL using standard migration process. Verify RLS,
   permissions, security advisor and table isolation, and bootstrap the
   VERIFIED authenticated owner UUID and the two host rows (not in Git).
   Start enabled=true, allow_shell=false on both.
3. Deploy NEW Edge function under its dedicated name, never overwrite
   pine-manbirs-mcp or other live functions. This function needs
   verify_jwt=false for non-OAuth worker routes; code validates MCP user
   with Supabase Auth and owner membership, worker routes with token hash.
   First test unauthorized, expired pair, wrong host, cross-host isolation,
   replay, output errors and status-only access.
4. On each Linux device separately, create the dedicated generic-auto
   system user, non-sudo generic-auto-exec local SSH login, unique key,
   pinned host fingerprint and private /var/lib/generic-linux-automator
   directory. Do not change any existing game bridge or Claude settings.
   Use no password SSH, no permissive host-key trust, no forwarded ports.
   The local OpenSSH listener must be independently verified.
5. Copy worker.py and service file to their reviewed host locations and
   supply /etc/generic-linux-automator/host.json based on sample, differing
   host_id per computer. Keep private token, SSH key and journal host-local.
6. Register the separate PRIVATE MCP ChatGPT plugin with OAuth for this
   endpoint; this is a separate human connection/installation action.
   Use linux_pair_host one time for each host and enter code only on that
   respective machine using worker.py --config ... pair.
7. Start service, call linux_host_status, linux_probe then read
   linux_task_status to a terminal exit-code/result on BOTH computers.
   Check service/logs, reboot independently, retest heartbeat and no replay.
8. Before shell jobs are enabled, perform negative isolation tests against
   sudo/root, unrelated home directories, sockets, SSH keys, other project
   workspaces, symlink escapes, worker concurrency and cross-host jobs.
   Explicit owner review then enables per-host allow_shell (DB) and
   shell_enabled (local config), never a global permissive default.

Offline test (within checked-out branch):
    python3 -m unittest discover -s tools/linux-automator/tests -v

Manual probe (only after host installation and pairing):
    sudo -u generic-auto python3 /opt/generic-linux-automator/worker.py --config /etc/generic-linux-automator/host.json once

A job queue ACK is not SSH execution. A heartbeat is not proof of a live
local SSH login. Never replay an interrupted unknown command; journal
stores an explicit uncertain failure result.

## Open Source / Reuse / Cost Gate

Reusable internal verified 19 Oct Pine architecture:
https://github.com/karanzing1992/gpt-pine-engineer/blob/main/docs/lanes/manbirs-connection-current.md
(the code and credentials belong to a separate private workstream).
Prior game bridge source:
https://github.com/KaranZi/shaadi-aunty-dodge
(game-only stopped pipeline, NOT reusable as a cross-project executor).
Current shared project rules:
https://github.com/karanzing1992/engagement-core/blob/main/docs/CLAUDE_CROSS_PROJECT_LANES.md

Reused maintained open source:
- OpenSSH: https://github.com/openssh/openssh-portable (BSD/ISC family).
- Python: https://www.python.org/psf/license/ (PSF).
- Supabase JS: https://github.com/supabase/supabase-js (MIT, pinned 2.75.0
  to match the existing owned gateway; update only after testing).
- MCP TypeScript SDK: https://github.com/modelcontextprotocol/typescript-sdk
  (mixed MIT/Apache 2.0 transition, pinned 1.25.3).
- systemd: https://github.com/systemd/systemd (LGPL 2.1-or-later core).

New work is limited to the Linux worker, isolated multi-host mapping,
job journal and service configuration. No new server product or paid
account was provisioned. Existing Supabase capacity might incur usage:
zero additional cost is NOT certified until assessed.

## Rollback and source synchronization

Stopping the separately named worker/systemd service and disabling the new
Edge function leaves Pine and Shaadi unchanged. Preserve logs/journals for
forensics; drop ONLY reviewed generic_auto_* tables following backup. No
force-push, no automatic merge, no production replacement.

This feature branch does not satisfy the Master default-branch monitoring
and Docs readback protocol. Source state != deployed state != plugin visible
!= host paired != remotely executable. Publish verified Master updates
only when actual release and consumer acknowledgments exist.
