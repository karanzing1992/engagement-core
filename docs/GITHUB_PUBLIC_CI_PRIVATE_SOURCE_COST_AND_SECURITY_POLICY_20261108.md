# Cross-project GitHub CI cost optimization — public runner, private source

**Version:** 2026-11-08 / v1 documentation. **Status:** reusable, evidence-backed **OPTION**, not automatic platform migration or global release authorization.
**Policy owner:** Moksha Master Stack / Automation. **Applies to:** separately approved GitHub CI for Moksha, DeluluTech, Andaz, MAD, CRM, Meta Core, Nokia and other owner-operated repositories **only after per-repo enrollment**. **Separate:** Ashwakaal — Support Channels, KaranZi/Shaadi and other ventures with their own permissions and customer data.
**Golden Rule 0:** open-source/free-first without weakening confidentiality or production safeguards.

## 1. Why and exactly when it saves money

GitHub documents that **standard GitHub-hosted runners for public repositories** do not consume the private-repository hosted compute allowance, whereas GitHub-hosted jobs in **private repositories** consume plan-included compute and may incur charges after the allowance is exhausted. See:

- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://github.com/resources/insights/2026-pricing-changes-for-github-actions

**Not all public Actions usage is free.** Larger runners, extra cache/artifact storage, third-party paid calls, external providers, and other metered products may still cost money. Rerun the billing check before broad deployment; do not hardcode old monthly-minute quotas. Review the GitHub Additional Product Terms; this pattern must be legitimate CI for an authorized project, not an unrelated general compute farm. GitHub says reusable-workflow billing attaches to the **caller** repository, not necessarily the repository containing the reusable workflow; merely storing YAML publicly without moving the calling job does NOT shift charges.

**Decision priority:** (1) eliminate unnecessary/redundant private jobs and cache/storage; (2) use regular existing included private minutes for restricted/sensitive work; (3) use public standard-runner **for safe isolated CI**, after risk review; (4) use a separately approved isolated/self-hosted runner when appropriate and current terms allow; (5) request owner cost approval before billable runners/services. Never publish a private repo to obtain public pricing.

## 2. Certified concrete reference — 8 Nov 2026

| Field | Verified state |
|---|---|
| Private source | `aarondash5-star/delulutech`, source candidate SHA `4bff39c2acb868fad212d82c42ef4bd252041bea` |
| Existing public CI host | `aarondash5-star/business-house-matrix`, draft PR #45, dedicated branch `ci/dlt-wpmanager-public-runner-20261108` |
| Source workflow | `.github/workflows/dlt-main-private-source-cert.yml` in the public CI host |
| Configured GitHub Environment | `DELULUTECH_SOURCE_READ_TOKEN` (Environment *name*) |
| Effective secret *name* | `DELULU_PRIVATE_TOKEN` (Environment secret, not its value) |
| Auth scope | Source-owner fine-grained private repository **Contents: Read-only**, required for pinned source checkout |
| Verified execution | https://github.com/aarondash5-star/business-house-matrix/actions/runs/42462288388 |
| Production test suite | PASS — job `128673963110`: private checkout, exact SHA, PHP lint, native connector build, npm tests, platform/auth regression tests, both Cloudflare candidate bundles |
| OAuth isolation suite | PASS — job `128673963407`: selected consent/access-boundary tests |
| Private source / customer data published | **No** source mirror, no public build artifacts, no cache; private checkout temporary and cleaned. Public logs use summary-only test verdicts |
| Deploy, merge, production authentication | **None** |
| Certification boundary | Does **not** prove 1:1 coverage of original `WP Manager 2.0 OAuth Consent QA` or set source-repository required checks to green. Original private-source PR #57 still draft. Production release remains NO-GO |
| Owner security exception | GitHub Environment has **no branch restrictions by explicit owner directive**. Only workflow-level owner/repository/branch/event guards exist. This is a known residual risk and **must not** be copied as the default |

The first runs failed because (a) a token secret was absent/wrong name, (b) a token lacked read access to the private source, and (c) an owner-created new Environment was not the one referenced in the workflow. The successful fix was **selecting the actual Environment plus the actual Environment secret name** and verifying repository access. The words `Environment` and `secret` are distinct concepts even when the user gives them identical names.

## 3. Enrollment and data-isolation gate — MUST pass per repo/account

1. Record owning venture, GitHub identity, **private source repository**, public CI host, verified ownership/permission, branch, reviewed source commit SHA, permitted tests, data classification, dependencies and destination of sanitized results. Do not equate `aarondash5-star`, `karanzing1992`, and `KaranZi` accounts.
2. Confirm CI requires **no real customer records, API service-role credentials, admin credentials, OAuth refresh tokens, Meta/WhatsApp tokens, live account access or write grants**. If tests need these, keep the relevant job in private isolated CI (or use synthetic fixtures), not this public-runner pattern.
3. Do not copy a private repository into the public Git tree, issue, PR, cache, artifact, Actions summary, website or log. Never export private source as a public artifact. A **temporary checkout on a public-repo CI runner is still a trust exposure**: decide whether the sensitivity of the private source warrants it before opting in.
4. Approve a **dedicated least-privileged source-read** fine-grained PAT or short-lived GitHub App installation token: select the authorized source repository, Contents Read-only, short expiry and rotation. **Do not use** generic all-repositories write-capable tokens, account passwords, customer credentials, another venture's PAT, or install an unknown public GitHub App. The owner must create the token in the authorized source account or supply a collaboration-scoped token with *verified effective read access*.
5. Require a separate public CI host and approved owner-specific branch (prefer dedicated minimal CI repo; sharing a busy public business repo is only a pilot exception). The source repo **remains private** and owns reviews, branch protections and release decisions.
6. Before each migration, inspect current runner pricing, artifact/cache quota, project Terms and existing CI; state estimated cost difference as **free standard public hosted minutes vs. private plan usage**, not a guaranteed monetary savings figure without billing usage data.
7. Owner signs off sensitive project exclusions individually. **Never bulk-enable all projects or automatically migrate all jobs**. Development/QA lanes remain separate; support-channel systems including Ashwakaal remain separate until expressly enrolled.

## 4. Standard secure execution contract (reference recipe)

**Recommended baseline:** separate dedicated public CI runner repo with limited writers, protected reviewed branch, GitHub Environment branch allowlist + optional reviewers, pinned GitHub Actions SHA, immutable **private source commit SHA**, no untrusted PR input, `GITHUB_TOKEN` read-only, secret only on checkout steps, no deployment and cleanup. An owner-controlled unrestricted Environment was tolerated in the pilot but **not** the standard for other repos.

Example workflow skeleton: adapt `SOURCE_REPO`, `PINNED_SHA`, branch and exact test commands only after per-repo review.

```yaml
name: Private-source QA (public host)
on:
  push:
    branches: [ci/approved-private-source]
    paths: [.github/workflows/private-source-qa.yml]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  isolated-tests:
    if: github.repository == 'EXAMPLE_OWNER/ci-public' && github.ref == 'refs/heads/ci/approved-private-source' && github.actor == 'EXAMPLE_OWNER'
    runs-on: ubuntu-latest # standard, not a larger runner
    environment: approved-source-read # restrict environment to approved branch
    timeout-minutes: 15
    steps:
      - name: Validate source token can read pinned commit
        env:
          SOURCE_TOKEN: ${{ secrets.SOURCE_READ_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail; set +x
          test -n "$SOURCE_TOKEN"
          GH_TOKEN="$SOURCE_TOKEN" gh api repos/SOURCE_OWNER/private-source/commits/PINNED_SHA --jq '.sha' >/dev/null
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
        with:
          repository: SOURCE_OWNER/private-source
          ref: PINNED_SHA
          path: private-source
          token: ${{ secrets.SOURCE_READ_TOKEN }}
          persist-credentials: false
      - name: QA and sanitized receipt
        shell: bash
        run: |
          set -euo pipefail
          test "$(git -C private-source rev-parse HEAD)" = 'PINNED_SHA'
          # Replace with reviewed project-specific tests. Suppress private output:
          if (cd private-source && ./ci/test-synthetic.sh) > "$RUNNER_TEMP/private-test.log" 2>&1; then
            echo 'PRIVATE_SOURCE_QA=PASS' >> "$GITHUB_STEP_SUMMARY"
          else
            echo 'PRIVATE_SOURCE_QA=FAIL' >> "$GITHUB_STEP_SUMMARY"
            exit 1
          fi
      - name: Cleanup ephemeral working directory
        if: always()
        shell: bash
        run: |
          rm -rf private-source "$RUNNER_TEMP/private-test.log"
```

**Note:** This skeleton is a specification, not tested as-is and not configured on any repository. The real certified implementation is the referenced WP Manager workflow, which also performs syntactic checks and explicit source-token authorization. Do not place arbitrary bash commands from PR descriptions into privileged jobs.

**Security controls (non-negotiable for other projects):**

- No `pull_request_target` / `workflow_run` privileged trigger to run untrusted PR code; no dynamic `github.event.pull_request.head.sha` checkout with secrets. Public PRs must not execute secret-bearing jobs. See https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target .
- Only owner-approved **pinned source SHA**, pinned action SHAs, locked/pinned deps and exact test entrypoints. No `@main` / `latest` source checkout, no command string injection via labels or workflow inputs.
- A public repo contributor with **write** access may change workflows and compromise Environment secrets (code-level `if` guards can be changed by a writer). Require branch protection/PR review and separate Environment branch allowlist/review where possible. Disabling Environment restrictions requires explicit documented owner risk acceptance and is NOT reusable default. Rotate credentials after any exposure.
- Do **not** upload `actions/upload-artifact` output of private builds, `actions/cache` of private source/dependencies, `actions/upload-pages-artifact`, coverage source maps, logs, screenshots, databases or test reports containing proprietary details. No git push from runner. Keep only redacted PASS/FAIL, source hash, dates and run URL; inspect logs for leaks.
- Set job timeout, minimal `permissions: contents: read`, minimize network access and token availability, ensure `persist-credentials:false`, clean ephemeral workspace, and reserve original source-repo approval and branch protections.
- The public Action host itself is public: workflow YAML, check names, public job summaries and some metadata are discoverable. Avoid revealing project-specific confidential naming/architecture if it is sensitive. Do not claim the public workflow has the same privacy as a private repository.

## 5. Migration phases and quality gates

**M0 — inventory:** audit source repo CI minutes, current failing workflows, pricing, which jobs are independently testable, private-data/secret dependencies, target host account, source owner. Record owner approval.

**M1 — establish public host:** choose an approved existing public repo or separate minimal public CI repo; put reviewed workflow on a distinct branch + draft PR. Run a synthetic, public-only canary with no private checkout. Confirm standard runner and audit results.

**M2 — source authorization:** create source-owner read-only credential, attach **only** to the intended Environment, verify exact Environment *name* and secret *name*, verify `gh api repos/OWNER/PRIVATE` and the exact source commit. Never print a token. Fail before checkout if read denied.

**M3 — isolated certification:** run pinned checkout and scoped synthetic tests, suppress source logs, validate compiled bundle where relevant, check commit SHA, ensure source deletion and no uploaded artifacts/cache. Capture exact GitHub run/job URLs, final status and specific tests included/excluded.

**M4 — parity/independent review:** compare every original private CI test, PHP/Node/browser/device/integration/security stage against external jobs. Missing stages remain pending, not 'certified'. Preserve unchanged release gates in source repo; external pass is **not** source required-check status. If needed, configure independently reviewed official status integration rather than forge check contexts or weaken protections.

**M5 — controlled adoption:** only after security + owner + reviewer approval; apply a per-repo documented route and monitor costs. Keep a rollback path to original private CI. Do not silently disable source workflows while parity, approvals or production deployment are outstanding.

## 6. Required per-repository receipt

```text
venture / GitHub owner / source repo + branch:
public CI host + account + workflow branch + owner:
source SHA and tests included / excluded:
source sensitivity and privacy decision:
credential owner / selected repo / permission / expiry (never value):
GitHub Environment name / secret name / protection/exception:
runner standard or larger / billing baseline and estimated change:
canary URL, full CI run URL, job conclusions, log-leak review:
source PR required-check context parity / missing checks:
security review + owner approval / risk exceptions:
rollback / original private runner route:
Master Registry reference and consumer acknowledgement:
state = DRAFT | READY | TESTED | SOURCE_ONLY | NO_GO | VERIFIED_CI | RELEASED
```

Do not reuse credential values or customer data across accounts or ventures. One cross-project *policy* does **not** mean one universal runnable token, public CI host or shared account.

## 7. Existing repositories / workstreams and adoption rule

- `aarondash5-star/delulutech` (private) → `aarondash5-star/business-house-matrix` (public) is a **certified CI pilot**, not released production; links above.
- `karanzing1992/Matrix-House` (private) hosted an independent Central OAuth source mirror; its private runner **does not itself provide public-runner free-minute savings**. Keep its own credentials and draft status; do not mix with Aaron's token.
- `karanzing1992/engagement-core` (public) is the **canonical documentation** host. Its own public-source CI can use standard public-hosted runner without private checkout where tests are safe.
- Other owner repos (Moksha WordPress, CRM, Meta Core, MAD, Android Nokia, Andaz, StayCore, Trading/Pine, etc.) should **review this policy** whenever CI spend is material, but preserve their source owner, GitHub permissions, releases and deployment controls. No automatic account-wide enrollment.
- `KaranZi` Shaadi/game code, other client repos, and **Ashwakaal Support Channels** are **independent**: never install shared source tokens or transfer customer data to a DeluluTech or Moksha runner unless separately authorized and audited.

## 8. Maintenance and synchronization

Version this policy under `karanzing1992/engagement-core`; link it from participating repo READMEs or `docs/ci/` during each **owner-approved adoption**. A draft PR is not published policy until merged/accepted. Report verified new platform capability via the authorized Supabase Master event inbox where required; Master Doc publication, skill release and consumer ACK must be independently verified. Retest billing policy each quarter or when GitHub announces a change.

**Evidence links:** GitHub's public-runner billing and security docs above; actual [CI success #42462288388](https://github.com/aarondash5-star/business-house-matrix/actions/runs/42462288388), [public draft PR #45](https://github.com/aarondash5-star/business-house-matrix/pull/45) and [private source draft PR #57](https://github.com/aarondash5-star/delulutech/pull/57).
