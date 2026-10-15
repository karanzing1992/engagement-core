# Shared Claude Dev — Secure Router v1 (candidate; disabled by default)

**State:** source implementation and offline tests; **not deployed to a PC, not enrolled in any other repository.**

This reuses the private `KaranZi/shaadi-aunty-dodge` source-only design (owner-authored issue → local runner → Claude Code → tests → review PR). It does **not** repurpose that game's runner for other brands. A copy of this small router must live in a separately approved **private** execution repository, with its own GitHub account/runner/credential scope, before that repository can execute.

The infrastructure consists of:

- `router.py`: fail-closed event/policy validation, and opt-in wrapper for an existing Claude CLI using Anthropic's maintained [Sandbox Runtime (SRT)](https://github.com/anthropics/sandbox-runtime) and Linux [bubblewrap](https://github.com/containers/bubblewrap). SRT is beta; do not rely on a source-only claim of containment.
- `repo-policy.EXAMPLE.json`: explicit owner ID, exact repository, `enabled:false` default, model and source path allowlist. A **GitHub issue is not an authorization token**. Each runner must have its own repo-local policy, owner-only workflow and verified identity.
- `tests/test_router.py`: offline negative/positive cases for routing, malicious paths, symlinks, paid-model selection and sandbox config shape.
- `workflow.PRIVATE-REPO-EXAMPLE.yml`: **template only**, not runnable from the public master repository. Must be reviewed in the intended PRIVATE repo with matching numeric owner ID and exact registered self-hosted runner labels. **Do not** enable on a public repo or on the old Shaadi runner without separating the OS execution boundary.

## Deployment gates

1. **Target is a private repository:** review its GitHub account and branch, app permissions, unique repo-scoped runner registration and operator-controlled workflow. Never reuse `KaranZi` write tokens for `karanzing1992` or vice versa. Do not register one shared persistent runner across untrusted repos.
2. **Host isolation first:** Use a dedicated least-privilege Unix account or an ephemeral VM/container, dedicated `HOME` containing only that project's *own* Claude subscription login, and SRT with read-deny `/home`, workspace/auth-only read carveouts, repo-only writes and no direct GitHub network. No access to host SSH, Docker socket, GitHub CLI auth, Supabase keys, Andaz guest data or other project folders. SRT's auth-directory access remains sensitive: use a dedicated login, monitor abuse, and never claim it makes session credentials invisible to code running under the same identity.
3. **Negative host tests are mandatory:** deny read/write of another project and private config, deny symlink escape, deny Unix sockets and GitHub outbound networking; verify no host env secrets. Test with the **actual** installed SRT+bwrap and account. Documentation and offline unit tests are NOT substitutes.
4. **Runner + subscription:** verify local Claude Code login under dedicated identity and `--model opus` without paid API keys. In the private repo, install GitHub Actions runner with a unique repo-specific label and no broad org group. Check that `CLAUDE_DEV_ISOLATED_IDENTITY=verified`, `CLAUDE_DEV_NEGATIVE_CANARIES_PASS=yes`, and `CLAUDE_DEV_EXECUTION_ALLOWED=true` are managed by owner-reviewed host configuration **only after** evidence, not supplied by task text. A mere env variable is not a security guarantee.
5. **Trusted release lane:** Model gets no `Bash` tool, GitHub token or push rights. A separate human-reviewed/project-specific trusted lane inspects the `git status --porcelain -z`, verifies allowed paths/symlink boundaries, runs known tests in containment, creates a PR with a narrowly scoped token and **never auto-merges/deploys**. The current `router.py` emits `CLAUDE_COMPLETED_UNREVIEWED` for precisely this reason; it deliberately **does not** push or merge.
6. **Pilot:** run one deny-case canary, one harmless read-only owner-authored issue, and one disposable edit→test→review-PR canary; read job logs and report observed results. Per-repo enrollment remains `NOT ENROLLED` until all gates pass. Each other project requires its own enrollment.

## Offline test

```bash
python3 -m unittest discover -s tests -v
```

### Routed request (only after private per-repository setup)

```bash
python3 router.py --policy ./repo-policy.json --event "$GITHUB_EVENT_PATH" \
  --actor "$GITHUB_ACTOR" --repository "$GITHUB_REPOSITORY"
# validation only; no Claude started

# Production path is deliberately a separate operator gate after host isolation:
python3 router.py --policy ./repo-policy.json --event "$GITHUB_EVENT_PATH" \
  --actor "$GITHUB_ACTOR" --repository "$GITHUB_REPOSITORY" \
  --workspace "$GITHUB_WORKSPACE" --auth-home "$CLAUDE_DEV_AUTH_HOME" --execute
```

**Sources / reuse log:**

- Source local bridge: https://github.com/KaranZi/shaadi-aunty-dodge/blob/main/scripts/shaadi_actions_bridge.py (private, accessed through authorized account).
- Official CLI: https://code.claude.com/docs/en/cli-reference ; use established `--model opus` to avoid API credit charges, availability still dependent on owner plan.
- Anthropic sandbox runtime (beta): https://github.com/anthropics/sandbox-runtime ; Linux uses bubblewrap and a proxy; `denyRead`, `allowRead`, `allowWrite`, `denyWrite`, `allowedDomains` must be tested against the installed version.
- GitHub self-hosted runner security: https://docs.github.com/en/actions/reference/security/secure-use — repo-scoped runner, never trust persistent shared runner for unrelated projects.
- Canonical Master: https://github.com/karanzing1992/engagement-core/blob/main/docs/CLAUDE_DEV_ON_DEMAND.md . The master reporting worker does **not** authorize execution.

**No extra paid service, credentials, host execution, production GitHub app installation, or automatic changes to project accounts are included.**
