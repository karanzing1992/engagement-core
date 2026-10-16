---
name: gpt-machine-claude-bridges
description: Operate, document, troubleshoot and audit existing GPT-to-machine MCP CLI and GPT-to-GitHub-to-Claude CLI bridges on authorized Mac/Dell Shaadi Studio hosts. Distinguish direct connection from GitHub relay, enforce evidence and stop orders.
---

# GPT machine CLI and GitHub Claude bridge — operator skill

## Routing decision (mandatory)
1. **Direct GPT → MCP CLI → host:** Only use when THIS ChatGPT session exposes an authenticated callable per-host MCP tool. Discover its exact schema and invoke a bounded allowlisted command. Local `mac_server.py` or `dell_server.py` and repository `.mcp.json` do NOT by themselves connect ChatGPT. If missing, report `DIRECT_CLI_NOT_CONNECTED`; never invent a tool, public endpoint or local shell.
2. **Fallback GPT → connected GitHub → private issue JSON → host `github_relay.py` → allowlisted Claude CLI/worker → issue comment → GPT:** Repository `KaranZi/shaadi-aunty-dodge` with GitHub identity `KaranZi` (not `karanzing1992`). This is asynchronous. Issue creation = queued request, NOT execution. Host comment must contain signed/owner-authenticated machine identity, timestamp, action, result, PID/session and relevant queue/checkpoint evidence. Treat absent or stale ACK as `PENDING`.
3. **Claude → Godot MCP:** The project's `.mcp.json` registers local Godot stdio MCP for Claude Code; it is neither bridge 1 nor ChatGPT remote CLI registration.

## Existing host registry
Mac Linux host `KARAN`: `~/shaadi-mac-bridge/`, `mac_server.py`, `github_relay.py`, `run_worker.py`, `shaadi-mac-relay.service`, roles visual/gameplay/qa. Dell Linux host `karan-Inspiron-5379`: `~/shaadi_dell_bridge/`, `dell_server.py`, `github_relay.py`, `run_worker.py`, `shaadi-dell-relay.service`, roles render/android/qa. Verify installed names and paths before changing anything; source registry is not live process evidence.

## Commands and proofs
Use documented, allowlisted JSON only. `{"action":"status"}` for overall health, `{"action":"queue_status"}` for queue; `{"action":"logs"}` for bounded sanitized tail if supported; `{"action":"stop","role":"visual"}` etc. for authorized role stop. Never issue unverified `resume`, `start`, `reset`, arbitrary shell or lease-clearing commands. For each result distinguish `requested`, `acknowledged`, `worker_running`, `terminal`, `verified_stopped`. Verify host and current UTC timestamp, task id, PID, queue and checkpoint. Preserve dirty worktrees, active work, and existing state on failure. Don't leak secrets, tokens, private logs or credentials into issue bodies.

## Critical current policy and stop state (16 Oct 2026)
Owner ordered STOP ALL tasks: Mac stop requests #362–364, Dell #365–367, control comments #209/#181; stop ACKs were pending when filed. No new work, auto-refill, retries, launches or resumed tasks until owner explicitly reauthorizes. Owner also withdrew the **single shared cross-host Claude lease policy**: intended future state allows Mac and Dell concurrent Claude sessions within legitimate provider limits, but installed relay migration is NOT verified; issue #368 tracks it. Do not bypass or forcibly clear an existing lease; audit checkpoint/holder first. A policy document change is not runtime activation.

## Diagnostics and recovery
Read actual issue comments before repeating commands; dedupe by issue ID and task ID. On missing direct tool, inspect existing ChatGPT plugin/connector exposure and supported authenticated remote transport; don't rebuild an MCP server. On GitHub fallback failure, check correct repo/account, issue body JSON, relay service health and ACK age. A stale held lease with no worker requires manual reconciliation of original job PID, token and checkpoint, not blind reset. For power/network outage preserve queue and use documented fail-closed retry/backoff. Source changes do not hot-reload local relays or ChatGPT plugins. Reuse existing bridge code; Golden Rule 0, no paid APIs, no unauthorized public listeners.

## Canonical evidence
- Direct bridge audit: https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/docs/production/DIRECT_MCP_CLI_BRIDGE_RECOVERY_20261016.md
- Live direct-exposure blocker: https://github.com/KaranZi/shaadi-aunty-dodge/issues/355
- Mac/Dell quota and recovery: https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/docs/production/MAC_SHARED_QUOTA_COMPATIBILITY_FIX_20261016.md
- Two-host control and owner policy: https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/docs/production/TWO_MACHINE_12H_20261015.md
- Owner lease-migration issue: https://github.com/KaranZi/shaadi-aunty-dodge/issues/368
- Master sync: https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md

## Master propagation
Material changes: commit verified source, immediately append/read back unique Master marker using authorized demand-based route; update SAME existing owned plugin via Plugin Creator and verify release, then verify consumer versions. GitHub skill source alone is NOT installed plugin release. If any step fails, report PARTIAL accurately.
