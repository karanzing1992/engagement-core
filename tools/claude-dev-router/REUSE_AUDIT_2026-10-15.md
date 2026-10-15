# Claude Dev — Golden Rule 0 reuse audit and rollout hold
**Date:** 15 October 2026
**Status:** Architecture audit, **no execution or credential changes**.
**Canonical authority:** [MASTER_STACK_UPDATE_PROTOCOL.md](../../docs/MASTER_STACK_UPDATE_PROTOCOL.md) → Golden Rule 0; [CLAUDE_DEV_ON_DEMAND.md](../../docs/CLAUDE_DEV_ON_DEMAND.md).

## Finding

The recently added custom `router.py`, installers, host canaries, `claude-moksha` user bootstrap, and disabled Moksha validation-only workflow were source-tested and, in the case of SRT synthetic filesystem and network/socket tests, tested on the owner's PC. **However, their combined architecture was assembled before a documented options comparison with the official upstream Claude GitHub Action.** That is a Golden Rule 0 process miss, irrespective of whether each custom security test was useful. Do not describe any of this as a completed cross-project service.

## Existing systems checked and reuse decision

| Candidate | Verifiable source / licence | Fit and cost constraints | Decision |
|---|---|---|---|
| Existing `KaranZi/shaadi-aunty-dodge` private Actions-to-CLI bridge | `scripts/shaadi_actions_bridge.py`, `.github/workflows/shaadi-direct.yml` in owner's separate private account; internal reusable pattern | Live owner-gated Shaadi task #42 reached `SHAADI_TASK_NO_CHANGES`. Does not isolate other tenant/repo data by merely checking final Git paths; cannot become cross-project dispatcher without fresh authorization | **Retain unchanged for Shaadi only.** Reuse its tested requirements/QA/review pattern, not its credentials or runner |
| **Official `anthropics/claude-code-action@v1`** | [GitHub source](https://github.com/anthropics/claude-code-action), **MIT**; [setup](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md), [usage](https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md), [security](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md) | GitHub-native issue/PR automation. Documents `CLAUDE_CODE_OAUTH_TOKEN` for eligible Pro/Max users, created via `claude setup-token`, or separate metered `ANTHROPIC_API_KEY`. Requires explicit repository app/secret permissions; use minimum-scoped private repo and avoid uncontrolled triggers. Subscription entitlement, usage policy, GitHub Actions minutes, availability of correct account login and any charge **have not been verified**. OAuth must NOT be pasted into chat, committed or shared between account owners. | **Evaluate FIRST for each new private repo** before creating any custom runner. No activation until owner approves and authentication/cost/security checks pass |
| Upstream `@anthropic-ai/sandbox-runtime` with Linux bubblewrap | [Anthropic SRT](https://github.com/anthropics/sandbox-runtime), **Apache-2.0**, beta | Protect local process files and network if on-device execution remains necessary. Owner-host PASS on six synthetic filesystem assertions and later localhost/socket/env canary. Not a container security guarantee or subscription under separate identity proof | **Reuse upstream unchanged when local execution is essential**; no custom replacement |
| Official GitHub `actions/runner` | [Runner source](https://github.com/actions/runner), GitHub-maintained. [Ephemeral runner documentation](https://docs.github.com/en/actions/reference/runners/self-hosted-runners), [security](https://docs.github.com/en/actions/reference/security/secure-use) | Private repo only; persistent runners can be compromised and leak credentials. Repo-scoped ephemeral runners are preferable if local host is required. Installation, patching and isolation remain operator overhead | **Fallback**, not default infrastructure |
| Owner's `engagement-core` shared reporting worker, Supabase cron/Node-RED/Opera bridges | Canonical Master registry/automation architecture | These are reporting or separately enrolled device-control systems, **not** a grant for arbitrary code execution or cross-tenant shell access | **Do not repurpose or duplicate them** |

## Compliance correction and no-new-build gate

1. **Freeze original multi-repository execution expansion** and `setup-moksha-isolated-user.sh` rollout. The owner has NOT run the new identity bootstrap. Do not ask them to run it while upstream option is unevaluated.
2. The `karanzing1992/moksha_wordpress` pilot ([PR #117](https://github.com/karanzing1992/moksha_wordpress/pull/117)) is already merged but **intentionally OFF**: policy `enabled:false`, repo variable gate, validation-only workflow, no new runner. Do not enable those controls or reinterpret source-only CI as live Claude execution.
3. Do not remove or change the already working Shaadi runner/Claude login, or migrate tokens from `KaranZi` to `karanzing1992`.
4. For next private-repo pilot, assess **official Claude Code GitHub Action** with the owner's current subscription route before touching the Linux PC. Document credential scope, privacy, project permissions, model, subscription-cost reality, GitHub minutes, triggers, tests and rollback. Alternatives must be compared explicitly.
5. If the official Action is unsuitable (documented, verifiable reason), prefer GitHub's official ephemeral runner plus existing SRT, per-repo isolation and minimal glue. A custom central scheduler/dispatcher remains prohibited without documented no-viable-reuse exception and explicit owner approval.
6. Gate every new coding task with a **Reference / Reuse Decision** including upstream repo/version, licence, security/maintenance/cost check, what is reused, narrowly necessary custom changes, host/runtime evidence and rollback. Source-only code must not be labelled deployed.
7. Continue to require explicit user consent before enabling live workflows, new credentials, GitHub Apps, project integrations, remote execution or paid services.

**Specific process noncompliance acknowledged:** custom scripts had individual implementation tests but lacked this required pre-implementation reference comparison. This memo documents the miss and corrective selection, not a retroactive claim that the earlier work was compliant.

**Next status:** `PAUSED FOR UPSTREAM REUSE DECISION`. No further host setup commands should be issued solely to advance the abandoned custom route.
