# GOLDEN RULE AW-1 — Manbir-only visible automation identity tag

**Scope correction: 2026-10-22 IST — owner's latest instruction supersedes the fleetwide wording of the original rule.**

**AW-1 applies ONLY to Pine Manbir's authorized Windows TradingView automation controller and its automation-owned GUI windows.** It is **not** a default or required deployment for Dell, Mac, Moksha/Andaz browser operators, generic SSH GUI sessions, Matrix automation, or other applications. No Dell/Mac rollout or certification is required under AW-1. Existing standalone test fixtures and merged libraries can be retained for reuse but are not a mandate to install anything outside Pine Manbir. Any future scope expansion requires a fresh explicit owner instruction.

## Required visible label (Manbir only)

`AUTOMATION | <PROJECT> | MANBIR | <TASK-ID> | <MODE> | <STATE>`

Example (not an active task): `AUTOMATION | PINE-QA | MANBIR | P3QA-014 | READ-ONLY | RUNNING`.

- Show a persistent, legible, high-contrast label only in **automation-owned**, specifically authorized disposable Manbir TradingView/browser/desktop windows; never tag the owner's personal or unknown windows. Never display PINs, keys, cookies, private scripts, chart content or other secrets.
- Derive project, worker, task ID, lease, mode and state from a verified controller receipt; the visible tag never authorizes additional actions or changes. Modes must represent true permissions (e.g. READ-ONLY or EDIT-QA); live trading remains OFF.
- Display before the first automated GUI interaction and after navigation/reload/reconnect, including newly authorized child windows. Do not use unknown active-tab fallbacks.
- If the tag is hidden, missing, mismatched, stale or illegible, refuse new GUI actions and set `BLOCKED:UNLABELED_WINDOW`. Permit only approved, read-only diagnosis/recovery until exact identity/lease and a visible tag are restored.
- Require one GUI writer, valid task lease and exact permitted origin/chart. Preserve all personal windows, the protected TradingView chart `/chart/JvxzE0Bg/`, unknown Pine buffers, source backups and rollback. No publication, production alerts, broker connections, orders or live trading.
- A finished task must indicate FINISHED while the owned window remains open, or close only that explicitly owned disposable window by established authorization. Redact all receipts.

## Manbir-only deployment and QA process

1. Read [AW-1 handover](https://github.com/karanzing1992/gpt-pine-engineer/blob/main/docs/handoffs/AW1_AUTOMATION_WINDOW_TAG_HANDOVER_2026-10-22.md), [Pine AGENTS.md](https://github.com/karanzing1992/gpt-pine-engineer/blob/main/AGENTS.md), and the [current Manbir connection runbook](https://github.com/karanzing1992/gpt-pine-engineer/blob/main/docs/lanes/manbirs-connection-current.md).
2. Use only the existing Pine Manbir SSH to query live host/controller identity and task journal. Reconcile unresolved/queued work and verify the sole controller writer before any native action.
3. Read the installed TradingView Controller path, immutable current source hash, owned window/profile/tab/lease and rollback snapshot; do not assume merged GitHub code is installed. Never overwrite an unknown local source buffer or change manual charts.
4. Adapt the existing merged reusable AW-1 guard only to this verified Manbir controller and one authorized disposable QA window. No second writer, new fleetwide service, unrelated app changes, or broad process termination.
5. Native QA must record task IDs, before/after source hashes, process/window/lease identity, labeled screenshots at useful desktop and narrow widths, reload/navigation/popup persistence, explicit manual-window noninterference, forced missing/wrong/stale-tag action refusal, reconnect behavior, one-writer contention, and verified restore/rollback. No production chart mutations.
6. Grade each gate PASS, FAIL, PENDING, BLOCKED or INCONCLUSIVE with immutable receipts. AW-1 on Manbir is NOT CERTIFIED until native evidence proves each gate and rollback. Keep [Matrix tracker #9](https://github.com/aarondash5-star/business-house-matrix/issues/9) open until Manbir certification.

## Historical implementation evidence (not production deployment)

- Existing reusable Matrix source: [PR #10](https://github.com/aarondash5-star/business-house-matrix/pull/10) with 13/13 unit tests, and [PR #11](https://github.com/aarondash5-star/business-house-matrix/pull/11) with native fixture harness.
- Disposable Dell Chromium screenshots at 320/390/768/1440 and isolated fullscreen capture on **private Xvfb display `:99`** previously passed. Fullscreen image SHA-256 `d1fbd74a1c4db123eb5aba8db518e3b8e051731ef291cd020945e7e046a04852`. These remain valid historical *test fixture* records, NOT certification for the Dell operator and NOT a current AW-1 deployment requirement.
- Mac Node 13/13 tests likewise demonstrate only portable code behavior, not Mac Opera installation.
- Actual Manbir controller has no proven native AW-1 tagged screenshot, missing-tag refusal, reconnect or verified rollback as of this correction. Pine Gold M5 Phase 3 remains NOT CERTIFIED.

**Precedence:** this owner-scoped correction overrides all earlier statements describing AW-1 as mandatory for Dell, Mac, every worker, every project or all automation windows. It does not weaken independent pre-existing security policies on other controllers.
