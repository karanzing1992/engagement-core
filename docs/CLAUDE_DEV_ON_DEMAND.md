# Claude Dev — shared, owner-invoked development capability
**Status:** shared invocation contract, 15 October 2026. **Execution:** Shaadi repo verified only. Other repositories are **NOT** enrolled or remotely executable by this document alone.

## Intent
Any participating ChatGPT Project may use the owner's existing Linux-hosted Claude Code capability **only when the owner explicitly asks** (e.g. "Use Claude Dev on this"). Reuse the verified Shaadi GitHub Issues → self-hosted Actions runner → local subscription-authenticated Claude CLI → tests → review PR pattern. Do **not** build a second model infrastructure, share API keys, install another paid service, or silently start background work.

## Verified source system (separate GitHub identity)
- Host CLI bridge: [KaranZi/shaadi-aunty-dodge scripts/shaadi_actions_bridge.py](https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/scripts/shaadi_actions_bridge.py).
- Owner-only event entry: [shaadi-direct.yml](https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/.github/workflows/shaadi-direct.yml). The actual trigger is a newly opened `[SHAADI-CODE]` issue **in that repository**, authored by GitHub user ID `11679700`, with `SHAADI_TASKS_ENABLED=true` and an online `shaadi-local` runner. Not a general cross-repository gateway.
- Highest subscription-included model was tested on the owner's local Linux host as `--model opus` → `claude-opus-5-5`. See [Shaadi PR #32](https://github.com/KaranZi/shaadi-aunty-dodge/pull/32). **The explicit model-selector change remains an unmerged draft PR** as of 15 October 2026. Do not assert that it is active on `main`.
- The `--model best` alias required additional usage credits in that test; do **not** choose it or add Anthropic API-key billing. Prefer subscription CLI auth, `--model opus` once properly adopted, and `CLAUDE_CODE_SUBAGENT_MODEL=inherit`, with account-reality verified per invocation.
- Review-only result: branch, validation and a PR, no auto-merge, production deployment or cross-repo write.

## On-demand request/dispatch contract
1. **Explicit owner invocation required.** Gather task from conversation, identify the exact ChatGPT Project and repo, requested paths, requirements, tests, resource cap, and allowed operations. Silence/routine status/installation is not consent to run.
2. **Source & approval gate:** read Moksha Master Golden Rule 0, check internal components and maintained upstream licensed foundations. Confirm correct linked GitHub identity and authorization. Never infer that `karanzing1992` is `KaranZi`, or vice versa.
3. **Capability gate:** inspect this repo's verified native runner, event trigger, owner restrictions, repo-scoped token, permitted paths, Claude CLI auth/model, test command and PR workflow. If **not enrolled**, create a non-executable review-ready onboarding plan or a scoped source PR and say `NOT ENROLLED`; do not send a fake task or claim execution.
4. **Dispatch only through the inspected, owner-approved repository entrypoint.** For currently verified Shaadi route: create a new `[SHAADI-CODE]` issue only for actual authorized Shaadi game changes within `godot/` and `docs/REUSE_LOG.md`. Do not submit unrelated project tasks to Shaadi or broaden its allowlist. Never treat task text as shell commands.
5. **Local Claude security:** use existing CLI installed on Linux, no paid API credentials; least-privilege tool allowlist, isolated workspace/worktree, scoped branch and file write allowlist, restricted system commands, secret redaction, resource and timeout limits; do not edit unknown or dirty checkout. Runner identity, credentials and customer data remain separate. Do not clone other projects using the Shaadi token.
6. **Completion:** log actual runner/CLI/model evidence and real test results, source reuse/license decisions, changed files, blocker classification, PR URL and rollback. No merging, deployment, publishing, live transactions, booking restoration, trading, posting or messaging unless a separately authorized project-specific release route is approved.
7. **On demand** means no polling/chat automations and no cross-chat remote agent capability is assumed. The Moksha Master reporting worker is only a change registry and **not a Claude task dispatcher**.

## Request template (issue/task description, not executable code)
- Origin ChatGPT Project:
- GitHub owner/repository and authorized account:
- Goal, acceptance criteria and test command:
- Allowed paths / excluded paths:
- Existing internal source and open-source upstream/licence checks:
- Credential/data/privacy constraints, runtime/tool restrictions:
- Needed branch / expected PR; no auto-merge/deploy:
- Actual runner enrollment: `VERIFIED` / `NOT ENROLLED`.

## Expansion / enrollment of a different repository
Prefer a reviewed adaptation of Shaadi's existing bridge, **not a new general-purpose remote shell**. For each new repo: read exact default branch and existing CI; verify private-repo policy; create a scoped owner-only event workflow and approved self-hosted runner registration; use repo-specific trusted checkout, secrets and file allowlist; confirm dry-run no-change canary, allowed edit/test/PR canary, unauthorized user/repo/path negative cases; log rollback. Because personal/repository-scoped runners do not magically span accounts, separately enroll each repo or introduce an explicitly owner-approved GitHub organization runner group with selected private repos. Do not auto-enroll all nine monitored master repos; reporting allowlist and Claude execution allowlist are **independent**.

## Controls and upstream references
- [Moksha Master protocol](https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md).
- [GitHub self-hosted runner model](https://docs.github.com/en/actions/concepts/runners/self-hosted-runners?platform=linux) and [runner access isolation](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).
- [Anthropic Claude Code CLI](https://code.claude.com/docs/en/cli-reference).

This file is a **documented shared capability policy**, not a declaration of a multi-project runtime deployment. Per-project status must be verified before each actual dispatch.

## Isolation and routing audit — 15 October 2026 (source inspection, not a host penetration test)

**Audit scope:** SHAADI `main` workflow [shaadi-direct.yml](https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/.github/workflows/shaadi-direct.yml), source bridge [shaadi_actions_bridge.py](https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/scripts/shaadi_actions_bridge.py), owner personal plugin v1.2.0 and loaded skill. **Live runner heartbeat, `SHAADI_TASKS_ENABLED` value, host process isolation, per-project installations and remote execution not independently verified.**

| Gate | Observed state | Verdict |
|---|---|---|
| Source repository and account separation | Private `KaranZi/shaadi-aunty-dodge` is distinct from public `karanzing1992/engagement-core`; correct GitHub connection must be chosen for each | PASS — source identities |
| Trigger routing | `issues: opened`; workflow matches owner numeric user ID `11679700`, `[SHAADI-CODE]` title prefix, and `vars.SHAADI_TASKS_ENABLED == 'true'`; bridge independently checks issue, repo and owner ID | PASS — code gate; enabled status UNKNOWN |
| Queuing/worker | `runs-on: [self-hosted, Linux, X64, shaadi-local]`; max 25 min; fixed concurrency group; no general cross-project dispatch entrypoint | PASS — declared route; online worker UNKNOWN |
| Path restriction | Claude has `Read,Write,Edit,Glob,Grep` and `acceptEdits`; code checks `git status` AFTER Claude, permitting commits only from `godot/` and `docs/REUSE_LOG.md` | **FAIL for pre-execution filesystem containment:** post-hoc Git checks do not prevent unauthorized reads, writes, symlink escape or modifications to untracked non-Git paths |
| Credentials and data | Code removes selected API and GitHub token environment variables before Claude and checks `claude.ai` login; same host runner/Unix user can have access to other local credentials and workspaces | PARTIAL; **OS/process isolation unverified**. Env filtering is not a sandbox |
| Billing/model | CLI `--model opus` on owner machine previously reported Opus 5.5 with subscription; main bridge currently does not pass that flag; [draft PR #32](https://github.com/KaranZi/shaadi-aunty-dodge/pull/32) contains proposal | PARTIAL; do not assert main always selects highest included model |
| Release rights | Bridge creates isolated branch and review PR; no automatic merge or deploy in inspected code | PASS — current code |
| Cross-project availability | Personal private plugin source contains skill; in-session `skills__list` exposes it. Plugin Management separately reported app `plugins_6acd2050739081918cbd975f2e23409c` as `not_installed` | PARTIAL; account-wide installation/other Project access NOT VERIFIED |

**Actionable hardening and enrollment requirement:**
1. **Never use the current Shaadi process as a multi-project runner or promise full isolation.** For any other repository return `NOT ENROLLED` until verified scoped entrypoint exists. Do not route other repos' tasks through `[SHAADI-CODE]`.
2. **Require preventive isolation before generalization**, not merely a prompt or post-hoc `git status`: a dedicated unprivileged execution identity/container/VM with only the target repo mounted, deny access to other home directories and Unix sockets, prevent symlink traversal, bound network/process permissions, per-job disposable workspace, no shared SSH/GitHub/cloud credentials, and no broad project filesystem bind mounts. Validate actual enforcement with negative tests before calling it secure. Prefer reviewed existing open-source sandboxing rather than inventing a custom jail.
3. Keep owner-only repo-specific authorization, stable source checkout, narrow token scopes; separate account/tenant runner and credential stores. Safeguard other GitHub accounts. Underlying self-hosted runners are not automatically clean or isolated. See [GitHub self-hosted security](https://docs.github.com/en/actions/reference/security/secure-use) and [ephemeral runner reference](https://docs.github.com/en/actions/reference/runners/self-hosted-runners).
4. Test **unauthorized user, wrong repo, disallowed path, symlink outside workspace, credentials access, repeated dispatch, dirty checkout, offline runner, unavailable subscription model and failure after validation**. Evidence must be observed in actual isolated runtime; source review does not prove these negative cases.
5. Only then enroll an individual private repository via an owner-reviewed adapter, run a read-only canary and bounded change→test→PR canary. **No global rollout, broad Shell tool, auto-merge, auto-deploy or paid API key.**
6. Plugin visibility and execution are separate: after private plugin updates, inspect installed skill catalog and plugin installation state. If the plugin is not installed for a Project/account, provide its private plugin URL and obtain the user's installation action; do not imply the skill or CLI has account-wide execution permissions.

**Risk verdict:** The private Skill's **guidance** is safe to distribute as an on-demand policy. Shaadi's **configured repository gate** is narrow. Claude's **host-side filesystem containment** is *not verified and not enforced by the inspected source*. Shared autonomous PC coding for other projects remains **NOT ENROLLED**.

## Secure router v1 source publication — 15 October 2026

- **Published source:** [tools/claude-dev-router](https://github.com/karanzing1992/engagement-core/tree/main/tools/claude-dev-router) on default branch; reviewed and merged from [PR #52](https://github.com/karanzing1992/engagement-core/pull/52) at commit `b2bf899330bd03d0c6746a6a6c0bb3226e85b6da`.
- **Quality:** 13 offline local authorization/path tests PASS; independent GitHub-hosted source QA run [38706210384](https://github.com/karanzing1992/engagement-core/actions/runs/38706210384) completed successfully. These tests did **not** run Claude or prove Linux host isolation.
- **Private skill:** existing personal Moksha Master plugin `moksha-master-stack-reinforced` v1.3.0 bundles identical router support sources and a fail-closed runbook. No separate plugin or duplicate polling worker.
- **Environment:** repository sample policy `enabled:false`; sample workflow is NOT installed into an executable private repository; no other project is enrolled and no PC runner service or host jail was deployed. `SRT` / `bubblewrap` on the actual owner PC, dedicated Unix identity/authentication, negative host canaries, and isolated project-specific runner registration remain unverified. **Do not report infrastructure as live.**
- **Operator path:** first verify dedicated host isolation, run test cases against real SRT/bwrap and separate Claude subscription account context; only then copy template into a private repository, adjust exact owner/repo/runner IDs, review boundaries, explicitly enable it, and verify an actual issue→Claude→tests→PR canary. No public repository self-hosted workflow.
