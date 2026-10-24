#!/usr/bin/env python3
"""Approved Dell -> Moksha WordPress Media Library handoff.

No WordPress password or bearer token is used. The signer remains on Dell.
The WordPress endpoint must be explicitly enabled and pinned to its public key.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

MAX_BYTES = 64 * 1024 * 1024
CHUNK = 4 * 1024 * 1024
SITE = "https://mokshagoa.com"
BASE = "/wp-control/v1/media-handoff"


def create_key(path: Path) -> None:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private = Ed25519PrivateKey.generate()
    blob = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(blob)
    os.chmod(path, 0o600)
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    print(json.dumps({
        "private_key_saved": str(path),
        "public_key_base64": base64.b64encode(public).decode("ascii"),
        "note": "Register only the public key in WordPress; keep PEM on Dell.",
    }))


def load_key(path: Path) -> Ed25519PrivateKey:
    st = path.stat()
    if st.st_mode & 0o077:
        raise ValueError("Private signing key has unsafe permissions")
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Expected Ed25519 private key")
    return key


def canonical(method: str, path: str, timestamp: str, nonce: str, body: bytes) -> bytes:
    return (
        f"{method}\n{path}\n{timestamp}\n{nonce}\n"
        f"{hashlib.sha256(body).hexdigest()}\nmokshagoa.com"
    ).encode("utf-8")


def call(key: Ed25519PrivateKey, route: str, body: bytes,
         content_type: str = "application/json") -> dict:
    if not route.startswith(BASE + "/"):
        raise ValueError("Route outside signed media handoff")
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    sig = key.sign(canonical("POST", route, timestamp, nonce, body))
    headers = {
        "Content-Type": content_type,
        "X-GREC-Time": timestamp,
        "X-GREC-Nonce": nonce,
        "X-GREC-Signature": base64.b64encode(sig).decode("ascii"),
    }
    req = Request(SITE + "/wp-json" + route, body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read(32768))
    except HTTPError as exc:
        # Do not print request headers, signatures, passwords or tokens.
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"WordPress HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError("WordPress network transfer failed") from exc
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError("WordPress did not acknowledge the signed action")
    return data


def send(file: Path, keyfile: Path, session: str | None, dry_run: bool) -> None:
    if not file.is_file() or file.suffix.lower() != ".mp4":
        raise ValueError("Choose an existing approved MP4")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,126}\.mp4", file.name):
        raise ValueError("Use a safe MP4 filename")
    size = file.stat().st_size
    if size < 1024 or size > MAX_BYTES:
        raise ValueError("MP4 is outside allowed size")
    h = hashlib.sha256()
    with file.open("rb") as src:
        for buf in iter(lambda: src.read(1024 * 1024), b""):
            h.update(buf)
    digest = h.hexdigest()
    if dry_run:
        print(json.dumps({"dry_run": True, "file": file.name, "size": size,
                          "sha256": digest, "parts": (size + CHUNK - 1) // CHUNK}))
        return
    key = load_key(keyfile)
    if session:
        if not re.fullmatch(r"[a-f0-9]{32}", session):
            raise ValueError("Invalid upload session ID")
        sid = session
    else:
        manifest = {"filename": file.name, "size": size, "sha256": digest,
                    "mime": "video/mp4", "brand": "moksha", "owner_approved": True}
        result = call(key, BASE + "/start",
                      json.dumps(manifest, separators=(",", ":")).encode("utf-8"))
        sid = result["id"]
        if result.get("chunk_bytes") != CHUNK:
            raise RuntimeError("Unexpected WordPress chunk size")
    print(json.dumps({"session": sid, "phase": "transferring", "parts": (size + CHUNK - 1) // CHUNK}))
    with file.open("rb") as stream:
        part = 0
        while True:
            data = stream.read(CHUNK)
            if not data:
                break
            call(key, f"{BASE}/{sid}/chunk/{part}", data,
                 content_type="application/octet-stream")
            part += 1
    result = call(key, f"{BASE}/{sid}/finish", b"{}")
    if result.get("sha256") != digest or result.get("size", size) != size:
        raise RuntimeError("WordPress receipt does not match source hash/size")
    print(json.dumps({"phase": "media_library_registered",
                      "attachment_id": result.get("attachment_id"),
                      "url": result.get("url"), "sha256": digest,
                      "note": "Media upload only; no social post has been published."}))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generate-key", type=Path)
    ap.add_argument("--file", type=Path)
    ap.add_argument("--key", type=Path)
    ap.add_argument("--resume", type=str, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.generate_key:
        if args.file or args.key or args.resume:
            ap.error("Key generation cannot be combined with upload")
        create_key(args.generate_key)
        return
    if not args.file or (not args.key and not args.dry_run):
        ap.error("--file and --key are required unless --dry-run")
    send(args.file, args.key, args.resume, args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)
