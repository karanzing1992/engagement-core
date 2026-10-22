# GOLDEN RULE AW-1 — Always-visible automation identity tag

**Effective 2026-10-22 | Owner directive | DEFAULT for all automation projects and workers.**

**Rule:** Every **automation-controlled** browser window, browser tab, desktop application, remote GUI session and terminal window **must display a persistent, human-readable identification tag whenever an automated task is attached or capable of acting.** Ordinary owner/user windows **must not be tagged, captured or modified** merely because the automation extension is installed. The automation tag identifies who controls a window; it is **not proof of authorization**.

## Required visual format

`AUTOMATION | <PROJECT> | <WORKER> | <TASK-ID> | <MODE> | <STATE>`

Example (identifiers are illustrative, not active sessions):

`AUTOMATION | PINE-QA | MANBIR | P3QA-014 | READ-ONLY | RUNNING`

- **PROJECT:** stable bounded project/tenant identifier, never a customer name, user credential or secret.
- **WORKER:** Dell, Mac, Pine-Manbir or approved worker ID.
- **TASK-ID:** unique stable task/lease ID, preferably short (e.g. last 8 safe characters), correlated with a full immutable terminal receipt. Never use a fabricated identifier.
- **MODE:** `READ-ONLY`, `EDIT-QA`, `STAGING` or explicitly permitted scope; never say `WRITE` if the task only has read permission. `LIVE TRADING` must never be shown or enabled for Pine Engineer.
- **STATE:** `READY`, `RUNNING`, `PAUSED`, `BLOCKED` or `FINISHED`; match the actual task ledger, do not infer completion.
- Label must be high contrast, legible at 320px width, not obscured by app content, and visually distinctive without using color alone. Prefer compact two-line text at narrow widths, top edge in automation-owned windows with accessible label. Never cover consent dialogs, secure keyboard inputs, site navigation required for safety or critical chart controls.
- On web surfaces, render in an extension-controlled overlay with `pointer-events:none` on the label and `role=status` for accessibility; apply only after verifying the tab's automation ownership. For native windows/terminals, use the safe window title/header/banner or a controller-owned always-on-top panel where permitted. **Do not** inject browser tag elements into manual/personal browsing sessions.

## Enforcement contract — default ON, fail closed

1. Before the **first automated GUI interaction**, verify **window ownership**, exact task ID, intended project and host, allowed origin/chart and whether the session has a sole writer/valid lease. No arbitrary active-tab fallback; never tag or act on an unknown user window.
2. Create/update the tag before any click, fill, scroll, navigation, screenshot, script edit, keyboard input or pointer movement. Use the current task's immutable receipt metadata and **least-privilege mode**.
3. Ensure the tag survives page navigation, popup/new-tab handling, browser recovery and reconnect. Every automation-controlled child window must have its own explicit tag or remain unacted upon until verified; don't assume inherited trust.
4. Before a high-impact action, verify tag remains visible **and** identity/mode matches authoritative task and authorization. Record a redacted screenshot or UI inspection, the tag text, source version and full immutable task receipt. A tag alone never authorizes writes.
5. If the tag is missing, illegible, mismatched, stale or disappears: set `BLOCKED:UNLABELED_WINDOW`, stop **new GUI mutations** and reacquire the verified owned window/lease. Read-only recovery/diagnostics may continue through established safe routes. Never use untagged fallback mouse coordinates to proceed.
6. When the task finishes, leave a `FINISHED` tag visible while the automation window remains open, or close only the **owned disposable** window under existing approvals. Do not remove a label to hide automation ownership. On session handoff update the owner/lease tag atomically after single-writer transfer.
7. No raw passwords, PINs, OAuth tokens, cookies, client IDs, customer PII, private strategy code, financial metrics or secret URLs in tags, screenshots or logs. Keep fixed-width short IDs and redaction in receipts.
8. Policy rollout is mandatory for **all newly created or modified automation GUI runtimes** and future releases; apply to legacy running workers **only through source-hash/backup/owner-approved deployment, paired device tests, screenshot evidence and rollback**. Documentation commits do **not** install a visible tag into currently running Mac, Dell or Windows browsers.

## Minimum acceptance tests

- Tagged automation-owned tab visible on mobile and desktop at 320px, 390px, 768px; label survives reload/navigation and a newly authorized popup.
- Manual tab and unrelated user-owned window have **no** automation overlay.
- Wrong project/task/mode/window owner rejected; missing tag pauses before clicks; two writer contenders do not create duplicate agent ownership.
- Tag is screenshot-visible and does not interfere with clicks, password dialogs or TradingView Pine Editor.
- Reconnect and save/reload preserve ownership; stale/ended task reflects `BLOCKED` or `FINISHED` without implying task success.
- Rollback to verified backup works, before production enablement.

## Project adoption and precedence

This is a **shared visible-operation golden rule** and complements the existing Master Golden Rule 0, narrow tenant privileges, browser single-writer restrictions and protected-chart prohibitions. It does not override native TradingView evidence or Phase 3 certification gates; owner PIN is never printed in the tag.

Applies to: **Moksha/Andaz Dell browser operator, Mac Opera native browser control, generic SSH GUI sessions, Pine Manbir TradingView controller and Matrix/Pine web-app automation.** Text-only non-GUI jobs don't require an on-screen tag, but must retain a named task/lease and terminal receipt. Agent/skill instructions must link this document; adapters must implement and verify the tag independently.

**Source versus runtime:** ADOPTED as default policy immediately; a given runtime earns `VISUAL_TAG_VERIFIED` only after a **fresh on-device screenshot plus fail-closed negative test**. The older isolated UI previews and the Vercel PIN app are not by themselves automation-controlled browser windows.

## Implementation and native QA checkpoint — 2026-10-22

- **Source merged:** Matrix PR [#10](https://github.com/aarondash5-star/business-house-matrix/pull/10), commit `cd764b750ae3fb25d5c30e52b645634cfece8f2a`; 13/13 tag/denial unit tests pass. Native test harness and receipt from PR [#11](https://github.com/aarondash5-star/business-house-matrix/pull/11), commit `a58e9373eb179904d4c3fec42c19c645d25ff62d`, merged with CI PASS.
- **Native display verified for disposable QA only:** 320/390/768/1440 Chromium screenshots on Dell all pass. A separate QA Chrome window was CLI-raised and focused at **1280×800** on Dell's **private Xvfb display `:99`**, with readable label, full desktop PNG SHA-256 `d1fbd74a1c4db123eb5aba8db518e3b8e051731ef291cd020945e7e046a04852`; the final read-only CLI focus recheck passed. **Dell physical display `:0` was not changed.**
- **Live controller gate remains OPEN:** This proof does not certify tag enforcement inside the existing Dell Let's Goa operator, Mac Opera controller or Pine Manbir TradingView Controller. Each still requires a source/lease-matched installation, native action refusal when hidden or mismatched, screenshot, reload and rollback. Do not mark fleetwide compliance.
- **Full cross-project handover and exact receipts:** [AW-1 Pine Engineer handover](https://github.com/karanzing1992/gpt-pine-engineer/blob/main/docs/handoffs/AW1_AUTOMATION_WINDOW_TAG_HANDOVER_2026-10-22.md). [Matrix deployment tracker #9](https://github.com/aarondash5-star/business-house-matrix/issues/9).
