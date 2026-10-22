# Dell secure browser keyboard repair — 23 October 2026 IST

Status: VERIFIED_LIVE frontend release; real owner key enrollment still pending.

## Problem and fix
Owner could see the Dell desktop but could not reliably type. Production depended on an invisible one-pixel textarea activated by clicking the screenshot; frame refresh immediately overwrote the keyboard-active status. A synthetic desktop browser could exercise that old handler, so this audit does not claim the owner's exact browser failure was reproduced.

Add visible Activate keyboard, masked Private text to Dell, Send private text, Enter, Tab and Backspace controls. Native masked entry avoids depending on screenshot keyboard focus. Text uses the same P-256 ECDH/AES-GCM send implementation and owner-authenticated API. Clear the field immediately on send and on hide/logout; reject empty/multiline/over-300 input. Keep private input status separate from frame refresh. Accepted means relay acceptance, not independently verified keystroke execution.

No auth/PIN/device/owner controls, relay backend, browser profiles, v6 controller, model policy, host permissions, dependencies or paid services changed.

## Source and verification
Source: integrations/dell-private-login-ui/src/index.html, code commit 39052af4d05156be627a757c1631ae3526d06d3b. Test harness preserved in integrations/dell-private-login-ui/tests/keyboard-regression.cjs. It uses the existing Dell Playwright installation and staged source directory; adapt these two path constants before use on another host.

Dell isolated candidate: ~/dell-ai-operator/keyboard-fix-20261023. Existing remote-ui files untouched because they differ from current production.

- Terminal receipt ae74408d-15b5-48ce-8c67-e1c6eaaba160, completed exit 0: 10 checks PASS: masked native field, real browser ECDH/AES-GCM encryption to a synthetic recipient, no plaintext in captured request, clear after send, explicit Enter, empty rejection, clear on hidden, synthetic 401 fail-closed, keyboard activation/typing, mobile overflow/page errors. No real credentials or live owner auth used. Checks are grouped in the emitted ten-item list.
- Node ESM syntax check PASS locally. Production file is the same tested source (ignoring only final newline in local scratch copy).
- Source SHA256 e5b2b416ac4ca284387f181592457406a16a0add5cf5b9181692ccdefd84f6a3. SHA1 deb03af9316b45bcad65fffab284835773761cbd.
- Preview dpl_FmJ7UGPAQyBaqXF1gx5Nz45h9V62 READY. Vercel file tree src/index.html matches SHA1.
- Production dpl_9dZMqYPvwrtvtfuk9To8akALSgEa READY; exact existing project prj_tVBQSoZ2c8LR9U4czF0BN07NMjEH, permanent domain https://dell-private-login-ui.vercel.app/.
- Independent Dell HTTP readback receipt bfc89076-098a-423c-82f2-b275abe8d3ba, completed exit 0: SHA256 matches and visible private input present. Key existence metadata: false at this point, so no credential activation/inference claimed.

## Vercel routing and rollback
Explicit teamId returned 403. The canonical 21 Oct incident already documents this connector scope-routing issue. Used the same authenticated connection's documented default scope, verified immutable project and deployment IDs and source tree before release; no alternate credentials, account, team or new frontend. Prior deployment dpl_7wF7mrwcUFCa7wdP1YA6vw3iZhx3 remains the rollback.

## Enrollment handoff
The first 15-minute enrollment window expired and was not replayed. After confirming the key file was absent, started one new owner-terminal session matrix-groq-owner-enroll-v2-20261023.service, RuntimeMaxSec=1800, NoNewPrivileges=yes, same private display and existing router enroll CLI. Owner explicitly instructed assistant to enter FREE; new session goes straight to masked API key entry with that confirmed plan flag. No secret passed in commands/logs.

Owner refreshes/unlocks original hosted page, pastes key only into masked Private text to Dell, presses Send private text, waits for accepted message, then presses Enter. Do not paste key into chat. Subsequent verification must inspect metadata/authenticated provider response only. Model activation/free-billing/license/QA gates remain separate.

Existing control-lane read-only receipts 86cdfadd-8430-4bea-bb6f-e03ecdd59d03 and ba51a7ac-4408-4b4e-bee3-931ae06402ed showed delayed terminal delivery; do not describe them as successful or replay mutations. Operations-lane release readback completed. No bridge restart or configuration changes used.

STACK CHANGE: VERIFIED_LIVE secure input UI release; source remains on isolated fix branch, no main merge or FULLY_SYNCED registry/consumer claim. Business House Matrix remains independent from Moksha Master.
