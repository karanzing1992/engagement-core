#!/usr/bin/env python3
"""Resumable, SHA-checked uploader for Moksha private Reel Engine.

Usage:
    REEL_ENGINE_TOKEN=... python private_upload_client.py \
      --url https://<private-worker-host> /path/to/video.mp4

Never print or persist the bearer token. Uses ordinary HTTPS (urllib) and chunks
up to 8 MiB, so a 231 MB video needs about 28 bounded-memory requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def sha_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def call(base: str, path: str, token: str, *, method: str = "GET",
         data: bytes | None = None, chunk_hash: str | None = None,
         retries: int = 4) -> dict:
    url = base.rstrip("/") + path
    if urlsplit(url).scheme != "https":
        raise RuntimeError("Uploads require HTTPS")
    headers = {"Authorization": "Bearer " + token}
    if method == "POST":
        headers["Content-Type"] = "application/json"
    if chunk_hash:
        headers["X-Chunk-SHA256"] = chunk_hash
        headers["Content-Type"] = "application/octet-stream"
    for attempt in range(retries):
        try:
            request = Request(url, headers=headers, data=data, method=method)
            with urlopen(request, timeout=110, context=ssl.create_default_context()) as result:
                return json.load(result)
        except HTTPError as error:
            if error.code < 500 and error.code not in (408, 429):
                raise RuntimeError(f"Upload request denied: HTTP {error.code}") from error
            if attempt == retries - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        time.sleep(2 ** attempt)
    raise RuntimeError("Upload exhausted retries")


def upload_video(base: str, path: Path, token: str) -> dict:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Local path must be a file")
    if path.suffix.lower() not in (".mp4", ".mov", ".mkv", ".webm"):
        raise ValueError("Unsupported video container")
    digest = sha_file(path)
    metadata = {"name": path.name, "size": path.stat().st_size, "sha256": digest,
                "mime_type": {".mp4": "video/mp4", ".mov": "video/quicktime",
                              ".mkv": "video/x-matroska", ".webm": "video/webm"}[path.suffix.lower()]}
    state_path = path.with_name("." + path.name + ".reel-upload.json")
    state = None
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
            if state.get("sha256") != digest or state.get("base") != base:
                state = None
        except (ValueError, OSError):
            state = None
    if state:
        try:
            info = call(base, "/v1/uploads/" + state["id"], token)
        except Exception:
            state = None
    if not state:
        info = call(base, "/v1/uploads", token, method="POST",
                    data=json.dumps(metadata).encode())
        state = {"id": info["id"], "sha256": digest, "base": base}
        state_path.write_text(json.dumps(state))
        os.chmod(state_path, 0o600)
    received = set(info["received_chunks"])
    with path.open("rb") as media:
        for i in range(info["total_chunks"]):
            if i in received:
                continue
            media.seek(i * info["chunk_bytes"])
            part = media.read(info["chunk_bytes"])
            call(base, f"/v1/uploads/{info['id']}/chunks/{i}", token,
                 method="PUT", data=part, chunk_hash=hashlib.sha256(part).hexdigest())
            print(f"Verified chunk {i+1}/{info['total_chunks']}", flush=True)
    completed = call(base, f"/v1/uploads/{info['id']}/complete", token,
                     method="POST", data=b"{}")
    if completed["sha256"] != digest or completed["size"] != metadata["size"]:
        raise RuntimeError("Upload verification mismatch")
    state_path.unlink(missing_ok=True)
    return completed


def main():
    parser = argparse.ArgumentParser(description="Resumable private Reel Engine uploader")
    parser.add_argument("--url", required=True, help="HTTPS base of authenticated Reel Engine")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    key = os.environ.get("REEL_ENGINE_TOKEN", "")
    if len(key) < 32:
        parser.error("REEL_ENGINE_TOKEN environment variable must be configured privately")
    print(json.dumps(upload_video(args.url, args.file, key), indent=2))


if __name__ == "__main__":
    main()