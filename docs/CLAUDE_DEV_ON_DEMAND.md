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
