#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, PeerFloodError, RPCError, UserPrivacyRestrictedError

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / ".env")

API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
PHONE = os.getenv("TELEGRAM_PHONE", "").strip()
GROUP = os.getenv("MOKSHA_GROUP", "@mokshasauna").strip()
INVITE_LINK = os.getenv("MOKSHA_INVITE_LINK", "https://t.me/mokshasauna").strip()
SESSION = os.path.expanduser(os.getenv("TELEGRAM_SESSION_PATH", "~/.moksha/telegram-user"))

DEFAULT_MESSAGE_RU = """Привет! 🌿

Мы развиваем небольшое wellness-сообщество Moksha в Арамболе — сауна, восстановление, общие сессии и полезные локальные обновления.

Если тебе это близко, присоединяйся к нашей Telegram-группе:
{invite_link}

Будем рады видеть тебя в сообществе 🤍"""

DEFAULT_MESSAGE_EN = """Hi! 🌿

We’re building a small Moksha wellness community in Arambol — sauna, recovery, community sessions and useful local updates.

If that sounds like your kind of space, you’re welcome to join:
{invite_link}

Would be lovely to have you with us 🤍"""


@dataclass
class ContactRow:
    user_id: int
    first_name: str
    last_name: str
    username: str
    phone: str
    mutual: bool
    existing_member: bool = False

    @property
    def display_name(self) -> str:
        name = " ".join(x for x in [self.first_name, self.last_name] if x).strip()
        return name or self.username or str(self.user_id)


def require_credentials() -> None:
    if not API_ID or not API_HASH:
        raise SystemExit(
            "Missing TELEGRAM_API_ID / TELEGRAM_API_HASH in tools/telegram-user-agent/.env. "
            "Create them at https://my.telegram.org/apps and keep them local."
        )


def client() -> TelegramClient:
    require_credentials()
    Path(SESSION).expanduser().parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(SESSION, API_ID, API_HASH)


async def ensure_login(c: TelegramClient) -> None:
    await c.connect()
    if await c.is_user_authorized():
        return
    if not PHONE:
        raise SystemExit("TELEGRAM_PHONE is missing in .env.")
    await c.start(phone=PHONE)


async def get_contacts(c: TelegramClient) -> list[types.User]:
    result = await c(functions.contacts.GetContactsRequest(hash=0))
    users = []
    for user in getattr(result, "users", []):
        if not isinstance(user, types.User):
            continue
        if user.bot or user.deleted or user.is_self:
            continue
        users.append(user)
    return users


async def get_existing_member_ids(c: TelegramClient) -> set[int]:
    try:
        entity = await c.get_entity(GROUP)
        participants = await c.get_participants(entity)
        return {p.id for p in participants if getattr(p, "id", None)}
    except Exception as exc:
        print(f"Warning: could not enumerate current {GROUP} members: {exc}", file=sys.stderr)
        return set()


async def contact_rows(c: TelegramClient) -> list[ContactRow]:
    contacts = await get_contacts(c)
    members = await get_existing_member_ids(c)
    rows = []
    for user in contacts:
        rows.append(
            ContactRow(
                user_id=user.id,
                first_name=user.first_name or "",
                last_name=user.last_name or "",
                username=user.username or "",
                phone=user.phone or "",
                mutual=bool(getattr(user, "mutual_contact", False)),
                existing_member=user.id in members,
            )
        )
    return rows


def eligible(rows: Iterable[ContactRow], include_non_mutual: bool = False) -> list[ContactRow]:
    selected = []
    for row in rows:
        if row.existing_member:
            continue
        if not include_non_mutual and not row.mutual:
            continue
        selected.append(row)
    return selected


def print_preview(rows: list[ContactRow], limit: int | None = None) -> None:
    rows = rows[:limit] if limit else rows
    print(
        json.dumps(
            [
                {
                    "user_id": row.user_id,
                    "name": row.display_name,
                    "username": row.username,
                    "phone": row.phone,
                    "mutual": row.mutual,
                    "existing_member": row.existing_member,
                }
                for row in rows
            ],
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"\nEligible contacts shown: {len(rows)}")


async def cmd_login(_: argparse.Namespace) -> None:
    c = client()
    try:
        await ensure_login(c)
        me = await c.get_me()
        print(
            json.dumps(
                {
                    "ok": True,
                    "user_id": me.id,
                    "name": " ".join(x for x in [me.first_name, me.last_name] if x),
                    "username": me.username,
                    "group": GROUP,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await c.disconnect()


async def cmd_status(_: argparse.Namespace) -> None:
    c = client()
    try:
        await c.connect()
        if not await c.is_user_authorized():
            print(json.dumps({"ok": False, "authorized": False}, indent=2))
            return
        me = await c.get_me()
        rows = await contact_rows(c)
        print(
            json.dumps(
                {
                    "ok": True,
                    "authorized": True,
                    "user_id": me.id,
                    "username": me.username,
                    "contacts": len(rows),
                    "mutual_contacts": sum(1 for row in rows if row.mutual),
                    "already_in_group": sum(1 for row in rows if row.existing_member),
                    "eligible_mutual": len(eligible(rows)),
                    "group": GROUP,
                    "invite_link": INVITE_LINK,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await c.disconnect()


async def cmd_preview(args: argparse.Namespace) -> None:
    c = client()
    try:
        await ensure_login(c)
        rows = eligible(await contact_rows(c), include_non_mutual=args.include_non_mutual)
        print_preview(rows, args.limit)
    finally:
        await c.disconnect()


def render_message(language: str) -> str:
    template = DEFAULT_MESSAGE_RU if language == "ru" else DEFAULT_MESSAGE_EN
    return template.format(invite_link=INVITE_LINK)


async def cmd_invite(args: argparse.Namespace) -> None:
    if not args.send or args.confirm != "MOKSHA":
        raise SystemExit(
            "Invite sending is protected. Re-run with --send --confirm MOKSHA after reviewing 'preview'."
        )

    c = client()
    try:
        await ensure_login(c)
        rows = eligible(await contact_rows(c), include_non_mutual=args.include_non_mutual)
        if args.limit:
            rows = rows[: args.limit]

        message = render_message(args.language)
        sent = []
        skipped = []
        failed = []

        for index, row in enumerate(rows, start=1):
            try:
                user = await c.get_input_entity(row.user_id)
                await c.send_message(user, message, link_preview=True)
                sent.append({"user_id": row.user_id, "name": row.display_name})
                print(f"[{index}/{len(rows)}] sent -> {row.display_name}")
            except (UserPrivacyRestrictedError, PeerFloodError) as exc:
                skipped.append(
                    {"user_id": row.user_id, "name": row.display_name, "error": type(exc).__name__}
                )
                print(
                    f"[{index}/{len(rows)}] skipped -> {row.display_name}: {type(exc).__name__}",
                    file=sys.stderr,
                )
                if isinstance(exc, PeerFloodError):
                    print(
                        "Telegram signaled anti-spam/flood protection. Stopping this run.",
                        file=sys.stderr,
                    )
                    break
            except FloodWaitError as exc:
                failed.append(
                    {
                        "user_id": row.user_id,
                        "name": row.display_name,
                        "error": f"FloodWait {exc.seconds}s",
                    }
                )
                print(f"Flood wait {exc.seconds}s. Stopping this run.", file=sys.stderr)
                break
            except RPCError as exc:
                failed.append(
                    {"user_id": row.user_id, "name": row.display_name, "error": type(exc).__name__}
                )
                print(
                    f"[{index}/{len(rows)}] failed -> {row.display_name}: {exc}",
                    file=sys.stderr,
                )

            if index < len(rows):
                await asyncio.sleep(random.uniform(args.delay_min, args.delay_max))

        print(
            json.dumps(
                {
                    "ok": len(failed) == 0,
                    "attempted": len(sent) + len(skipped) + len(failed),
                    "sent_count": len(sent),
                    "skipped_count": len(skipped),
                    "failed_count": len(failed),
                    "sent": sent,
                    "skipped": skipped,
                    "failed": failed,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await c.disconnect()


async def cmd_import_csv(args: argparse.Namespace) -> None:
    path = Path(args.csv).expanduser()
    if not path.exists():
        raise SystemExit(f"CSV not found: {path}")

    contacts = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=1):
            phone = (row.get("phone") or row.get("Phone") or "").strip()
            if not phone:
                continue
            first = (
                row.get("first_name")
                or row.get("First Name")
                or row.get("name")
                or "Contact"
            ).strip()
            last = (row.get("last_name") or row.get("Last Name") or "").strip()
            contacts.append(
                types.InputPhoneContact(
                    client_id=index,
                    phone=phone,
                    first_name=first or "Contact",
                    last_name=last,
                )
            )

    c = client()
    try:
        await ensure_login(c)
        result = await c(functions.contacts.ImportContactsRequest(contacts=contacts))
        print(
            json.dumps(
                {
                    "ok": True,
                    "submitted": len(contacts),
                    "imported": len(getattr(result, "imported", [])),
                    "users_returned": len(getattr(result, "users", [])),
                    "retry_contacts": list(getattr(result, "retry_contacts", [])),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await c.disconnect()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Local Telegram user-account connector for Moksha contact invitations."
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="Authenticate the Telegram user account locally.")
    sub.add_parser("status", help="Show authorization and contact/group counts.")

    preview = sub.add_parser(
        "preview", help="Preview contacts eligible for a Moksha invite. Sends nothing."
    )
    preview.add_argument("--limit", type=int, default=50)
    preview.add_argument("--include-non-mutual", action="store_true")

    invite = sub.add_parser(
        "invite", help="Send the Moksha invite link to eligible Telegram contacts."
    )
    invite.add_argument("--limit", type=int, default=20, help="Maximum contacts in one run.")
    invite.add_argument("--language", choices=["ru", "en"], default="ru")
    invite.add_argument("--delay-min", type=float, default=5.0)
    invite.add_argument("--delay-max", type=float, default=9.0)
    invite.add_argument("--include-non-mutual", action="store_true")
    invite.add_argument("--send", action="store_true")
    invite.add_argument("--confirm", default="")

    imported = sub.add_parser(
        "import-csv", help="Import phone contacts from CSV using Telegram user API. Sends nothing."
    )
    imported.add_argument("csv")

    return p


async def main() -> None:
    args = parser().parse_args()
    handlers = {
        "login": cmd_login,
        "status": cmd_status,
        "preview": cmd_preview,
        "invite": cmd_invite,
        "import-csv": cmd_import_csv,
    }
    await handlers[args.command](args)


if __name__ == "__main__":
    asyncio.run(main())
