# Telegram User API — Moksha contact invites

This is a **local-only** Telegram user-account connector. It complements the existing Engagement Core Bot API publisher.

Why this exists:
- Telegram bots cannot start private conversations with arbitrary users.
- The Telegram user API can access the signed-in account's contacts.
- `contacts.importContacts` can match phone contacts to Telegram users.
- Invite sending is preview-first, mutual-contact-only, deduplicated and throttled.

## Security

The Telegram API ID/hash and user session remain on the local Mac.

Never commit:
- `.env`
- `*.session`
- `*.session-journal`
- `telegram-invite-ledger.json`

Default local files:
- session: `~/.moksha/telegram-user.session`
- invite ledger: `~/.moksha/telegram-invite-ledger.json`

## 1. Create Telegram API credentials

Open:
https://my.telegram.org/apps

Create an app and copy its:
- API ID
- API Hash

Do not paste the API hash into GitHub or chat.

## 2. Install

```bash
cd tools/telegram-user-agent
chmod +x bootstrap-mac.sh
./bootstrap-mac.sh
```

Edit `.env` locally and fill:

```
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_PHONE=+91...
MOKSHA_GROUP=@mokshasauna
MOKSHA_INVITE_LINK=https://t.me/mokshasauna
```

## 3. Login

```bash
.venv/bin/python agent.py login
```

Telegram sends the login code to your Telegram account/device. If 2FA is enabled, Telethon asks for the password locally.

## 4. Check status

```bash
.venv/bin/python agent.py status
```

## 5. Preview invite recipients

No messages are sent:

```bash
.venv/bin/python agent.py preview --limit 50
```

Only **mutual Telegram contacts** who:
- are not bots/deleted accounts,
- are not already members of `@mokshasauna`,
- and have not already been invited by this agent

are eligible.

## 6. Send a conservative Russian invite batch

```bash
.venv/bin/python agent.py invite --limit 20 --language ru --send --confirm MOKSHA
```

Default throttle is a random 5–9 seconds between sends. A Telegram anti-flood signal stops the run.

English:

```bash
.venv/bin/python agent.py invite --limit 20 --language en --send --confirm MOKSHA
```

## Import phone contacts from CSV

CSV fields supported:
- `phone`
- `first_name` / `name`
- `last_name`

```bash
.venv/bin/python agent.py import-csv contacts.csv
```

Importing **does not send any messages**. Telegram may not expose every phone contact as a user because privacy settings apply. After import, run `preview`.

## Important

Telegram can restrict accounts that send unwanted messages or unwanted group invitations. This connector intentionally does not cold-message non-mutual contacts. Use WhatsApp or another consented channel for contacts who are not mutual Telegram contacts.
