# Private Telegram Task Notification Relay — Reusable Integration Contract

**Version:** 1.0 candidate · **Prepared:** 2026-10-23 · **Owner:** Engagement Core · **State:** source implemented; production WordPress relay awaits the administrator's explicit activation.

## Purpose and boundaries

A reusable *event-triggered*, owner-private notification transport for Dev Matrix, Marketing Matrix, Pine Engineer, Andaz and future separately enrolled projects. It sends completion, failure, stalled-job, resumed-job, approval and escalation notices; it does **not** provide remote task execution, an AI chat inbound webhook, or periodic ChatGPT reminders.

The destination is **the already-verified private Moksha paid-booking DM**, from live WordPress option `grec_booking_private_telegram_chat`; it is not the `primary`, `moksha`, `andaz` or `exclusiv` publishing destination. Do **not** reuse `GREC_Telegram::send_post` with empty filters: it can broadcast to groups. Never hardcode or export the private chat ID or decrypted bot token.

Evidence: Moksha's original active WPCode snippet #13126 uses `GREC_Telegram::credentials()` and private chat pairing; an administrator-run synthetic test via snippet #13355 succeeded **23 October 2026 at 13:42:26 IST**, Telegram message ID **11**, with user confirmation. The earlier publishing test incorrectly went to the `Primary` group (message ID 1785); that group is explicitly disallowed for this workflow.

## Components

| Component | Source | Scope |
| --- | --- | --- |
| WordPress fixed-function bridge | `integrations/private-notifications/bhm-telegram-relay.php` in this repo | Validates event signature and payload, uses same paired private DM as paid bookings |
| Durable worker outbox | `brain/automation/task_events.py` in `aarondash5-star/business-house-matrix` | Register/heartbeat/failure/approval/stall events in private SQLite, no network |
| Signed delivery client | `brain/automation/private_telegram_sender.py` in Business House Matrix | One event at a time; authenticated POST and Telegram message receipt validation |
| Receipt import | `brain/automation/receipt_bridge.py` in Business House Matrix | Converts bounded trusted local completion receipts to deduplicated events |
| User-unit templates | `deploy/systemd/user/bhm-*telegram-*` and `bhm-task-watchdog.*` | Event-driven service plus internal stall detection, no user-facing reminder |
| Regression suite | `tests/test_private_telegram_sender.py` in Business House Matrix | Authentication, replay, missing auth, wrong recipient, no-retry cases |

## Transport and authentication

- **POST** `https://mokshagoa.com/wp-json/bhm-private-events/v1/notify`.
- The request is signed by the worker using an Ed25519 private key in a **0600** file under its own `~/.local/state/business-house-matrix`. WordPress stores **only** the public key (safe, published source), not the private key or any new bot token. The first signer is the existing Dell worker. Fingerprint of its public key (SHA-256): `98f4720c9120314af70584aa8320c2b8d4a83c01fbf11bb6a6183d08930c1d59`.
- Required headers: `X-Matrix-Event-ID` (64 lowercase hex), `X-Matrix-Timestamp` (Unix seconds, ±300 s), `X-Matrix-Signature` (Base64 Ed25519 64-byte detached signature). Optional audited `X-Matrix-Key-ID` identifies the signer in receipts.
- Exact signed byte string: `bhm-private-relay-v1\n<timestamp>\n<event_id>\n<raw canonical JSON body>`. No model may generate signatures or change keys/permissions.
- Payload max 2400 bytes; allowlisted kinds only; task/run identifiers must match strict alphanumeric punctuation; summary length 4–420 with secrets/HTML blocked; optional HTTPS evidence URL ≤700 chars. No guest info, passwords, payment details, chat IDs, group targets, shell commands, or arbitrary HTML.
- A unique WordPress option keyed by event ID is reserved *before* the send. Duplicate/uncertain requests are not replayed silently. WordPress checks both Telegram `ok=true` and recipient `result.chat.id` against the paired private chat before returning `status=delivered` and `message_id`; the client marks its SQLite event `sent=1` only after matching the signed event ID, delivery status, recipient marker and message ID.
- **Delivery network timeout is indeterminate**, never automatically retried (SQLite `sent=2` and WP `uncertain`). Manual receipt reconciliation is required. No broad bot token or raw developer credentials flow through GitHub.

## Reuse across projects

Emit through the same library using independent `run_id` / `task_id` namespaces:
- `dev-matrix:andaz-website` with code/QA evidence URL
- `marketing-matrix:moksha-research` with cited report/QA link
- `pine-engineer:beta-qa` with test receipt/owner decision
- Additional enrolled projects may use the existing Dell worker event outbox with distinct run IDs. A different Mac/device requires its own reviewed signer public key and permission gate; never copy Dell's private signing key to other machines.

Workflow: `register` once → `heartbeat` as progress occurs → `completed`, `failed`, `blocked`, or `approval_required` with evidence → event-driven dispatch. Internal watchdog checks for genuinely stale heartbeats after an explicit threshold (300–86400 s), creates one `stalled` and one later `escalation` event, and avoids repeated user reminders.

## Rollout and rollback gates

1. Administrator explicitly approves and **activates** the WordPress fixed-function PHP snippet. WPCode's editor reviews source/fatal errors; do not silently activate or alter the live paid-booking snippet #13126.
2. Read back active WPCode status and the newly registered `/bhm-private-events/v1/notify` route.
3. Send one signed synthetic Dev Matrix event with a unique ID and no real bookings; verify private DM receive, matching WordPress/Telegram delivery receipt and idempotency. Send no group broadcasts.
4. Only after successful authenticated canary, enable user-unit dispatch and event heartbeat watchers on the approved worker. Keep `BHM_PRIVATE_TELEGRAM_ENABLE` OFF until this verification.
5. Rollback: disable *only* the new notification snippet and stop the user units; do not modify or disable Engagement Core, the bot, paired private booking DM, WooCommerce payments, or original booking alerts.

**Current rollout status:** Source and Dell simulator are prepared. Creating the PHP snippet requires WordPress approval and subsequent user activation. Until both happen and the signed canary succeeds, automatic event delivery is NOT LIVE.
