# Generic Linux SSH v7 compatibility hotfix — 22 October 2026

## Problem and verified diagnosis
The original ChatGPT App-backed plugin `generic ssh linux` (app ID `asdk_app_6ad65c4697b481918d93a18735d4aa7e`, plugin `plugin_asdk_app_6ad65c4697b481918d93a18735d4aa7e`, release v1.0.1) advertises a frozen five-tool snapshot. Its `linux_ssh_run` input supports only `host_id,command,timeout_seconds` and omits the `lane` input. Supabase gateway v6/service 1.2.0 already registered seven MCP tools including `linux_control_run` and `linux_development_run`. Reconnecting did not refresh the App's tool snapshot.

A **second** personal plugin `generic-linux-ssh-mcp` (`plugins_6ad64adab5e481918832cd516e779009`, release v0.1.20) is a direct MCP plugin pointing to the same protected gateway URL. The two entries do **not** represent two worker fleets or independent credentials. Never uninstall either automatically. Prefer the canonical direct MCP plugin after its tool exposure is independently verified.

## Code fix
Source commit: `832de82d2a94b4b0f1119def70eb155aa6c2d800`
Deployed: existing Supabase project `saczglesalubroyaucqe`, function `generic-linux-automator` Edge version **7**, service version **1.2.1**. Existing identities, permissions, auth, worker URLs, Postgres jobs, and all six worker instances are unchanged.

A backward-compatible lane selector was added to `linux_ssh_run` *only* for legacy five-tool clients whose schema cannot accept the optional `lane` parameter. The marker must occupy the first line exactly:

```text
# generic-ssh-lane:control
uname -sr
```

Allowed values: `control`, `operations`, `development`. If the marker is absent, `linux_ssh_run` continues to default to `operations`; official clients with the `lane` parameter continue to work unchanged. Malformed, conflicting, or empty routing commands are rejected. The header is stripped **before** insertion into the same owner-scoped job queue; all established host pairing, OAuth owner authorization, `allow_shell`, lane heartbeat, idempotency and receipt rules still apply. Never use the marker as a privilege or authorization bypass. No background job is considered complete until `linux_task_status` returns `completed` and `exit_code=0`.

## Verified production receipts
All six commands were dispatched from the **five-tool ChatGPT client** using the backward-compatible routing header (or the default operations lane); all six terminal receipts show the intended per-host lane, completed, exit 0, empty stderr and no uncertain outcome.

| Host | Lane | Receipt | Started UTC | Finished UTC |
|---|---|---|---|---|
| Dell | Development | `7837cf31-ce82-496a-976a-55e88bfd74a0` | 19:57:10.670 | 19:57:24.864 |
| Dell | Control | `5a7e8933-2aae-469b-910e-59efae9231ae` | 19:57:15.503 | 19:57:16.846 |
| Dell | Operations | `80aaaf89-20ee-46d6-ae29-cabfa3a9d860` | 19:57:19.006 | 19:57:20.472 |
| Mac | Development | `806c3411-5a50-4300-883b-c813e5b2498c` | 19:57:14.878 | 19:57:27.814 |
| Mac | Control | `2ea6a278-50dd-4232-b9c4-97a2bd7692ad` | 19:57:20.019 | 19:57:20.975 |
| Mac | Operations | `3ded74bd-fb76-408f-9b0e-3baded07245c` | 19:57:20.599 | 19:57:21.560 |

Control and operations overlapped the running development job on **each** host. The development commands used only a bounded `sleep 12` with `date`/shell builtins; no configuration or privilege modification was performed.

## Remaining presentation issue
The ChatGPT App client still **exposes five tool names**, not seven, even though six-lane execution is operational and the live backend registers seven. Only an admin/developer refresh and approval of the App's registered MCP tools can make the two dedicated tool names available in the App's frozen client snapshot. Editing skills, GitHub source or publishing another plugin release cannot directly force that frozen snapshot to update. The two plugins should not be consolidated by deleting one before direct MCP capability and OAuth access are confirmed.

## Safety / rollback
- Preserve owner-approved sudo policy; never change Dell/Mac root permissions without fresh host-specific approval.
- No credential copies, worker-key bypasses, unscoped SQL queue injection, public inbound SSH, or forced re-pairing.
- If necessary and approved, roll back the Edge Function to v6 after reconciling any in-flight jobs. The compatibility marker is otherwise inert to standard calls.
