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
