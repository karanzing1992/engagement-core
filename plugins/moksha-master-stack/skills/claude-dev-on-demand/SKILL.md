---
name: claude-dev-on-demand
description: Use when the owner explicitly asks any ChatGPT Project to use Claude Code, the PC-based Claude developer, Claude CLI, parallel code agents, or the existing GitHub-to-local Claude development bridge. Verify a repository-scoped execution route before dispatch; otherwise prepare a safe onboarding.
---

# Shared Claude Dev — deliberate, owner-invoked only

**Canonical contract:** https://github.com/karanzing1992/engagement-core/blob/main/docs/CLAUDE_DEV_ON_DEMAND.md

Read the linked contract and the current [Moksha Master protocol](https://github.com/karanzing1992/engagement-core/blob/main/docs/MASTER_STACK_UPDATE_PROTOCOL.md) on each material task. This installed Skill grants **no remote shell, runner, GitHub or Claude account permissions**. Never claim a task executed merely because a Skill or GitHub issue exists.

## When owner says “use Claude Dev”
1. Treat this as explicit permission to prepare and issue a **scoped development task** for the current Project, but not permission to relax repository policies, spend extra credits, merge, deploy, publish, trade, message users, modify live data or restore databases.
2. Determine the originating Project, exact repository/owner and verified GitHub connection (important: `KaranZi` and `karanzing1992` are distinct). Identify success criteria, allowed directories, test commands and environment boundaries from that Project's evidence. Do not invent unknown scopes.
3. First examine **existing internal tools**, upstream public licensed solutions and the project's actual development/runner policy. Reuse the existing Shaadi implementation as a reference, not as a general-purpose executable for unrelated repos.
4. **Execution gate:** verify an installed, enabled, owner-restricted task trigger for *this exact repository*, plus associated self-hosted runner, local Claude CLI subscription auth, approved tool/path restrictions, test+PR workflow and credential scope. If not verifiable, return `NOT ENROLLED` and prepare a safe scoped onboarding PR/issue; never pretend to have run Claude.
5. **Known working pattern:** `KaranZi/shaadi-aunty-dodge` has `.github/workflows/shaadi-direct.yml` and `scripts/shaadi_actions_bridge.py`, owner ID 11679700, `[SHAADI-CODE]` issue entry, repo-specific enable flag `SHAADI_TASKS_ENABLED=true`, runner `shaadi-local`. Use **only** for authorized Shaadi game work in permitted paths. Creating a task issue is not proof that the flag is enabled or runner online. Inspect completion logs and issue/PR evidence.
6. **Model/billing:** A PC test verified Claude Code CLI `--model opus` used `claude-opus-5-5` with the user's Claude subscription. The `best` alias required extra credits. Shaadi model configuration is proposed in [draft PR #32](https://github.com/KaranZi/shaadi-aunty-dodge/pull/32), not confirmed merged. Prefer the subscription-available Opus alias after verified rollout, keep subagents inheriting, do not set paid API keys or silently change global login.
7. **Isolation and safety:** each job uses its own repository credentials, scoped checkout/worktree/branch, path allowlist, least-privilege tools, timeout and resource cap; owner-only triggers and no arbitrary issue-text shell execution. For other repositories, use a *separately reviewed* adapted workflow; do not share the Shaadi runner token or assume a master reporting allowlist grants development access.
8. **Closeout:** report `QUEUED`, `RUNNING`, `BLOCKED`, or `VERIFIED COMPLETED` only with direct evidence. Record actual model, tests, modified files and reviewable PR, plus limitations; no automatic merge or live deployment. Report material verified changes using the existing Master Stack sync, never through a new poller.

## Cross-project request syntax (user-facing)
“Use Claude Dev for [feature/fix] in this project. Research existing open-source implementations, run the repository tests, and prepare a pull request. Don't merge or deploy.”

## Status boundary
- **Available as shared ChatGPT guidance:** once this Skill is installed/enabled for the requesting Project.
- **PC execution:** only for explicitly enrolled and verified repositories; Shaadi is the currently documented implementation.
- **Not automatic:** a ChatGPT Project's instruction setting, GitHub account permission, self-hosted runner registration, and local auth are independent. The Master Stack registry is NOT the Claude dispatcher.
