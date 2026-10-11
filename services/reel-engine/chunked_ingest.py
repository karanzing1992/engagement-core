"""Private, authenticated, resumable chunked uploads for user-owned Reel media.

Only the API boundary accepts bytes. This store itself is network-independent and
uses size/checksum checks, atomic renames and advisory Linux file locks. Session
files live outside public /outputs and are not reachable by URL without auth.
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import time
import uuid

CHUNK_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_UPLOAD_SESSIONS = 24
SESSION_LIFETIME = 48 * 3600
ID = re.compile(r"^[0-9a-f]{32}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
MEDIA_TYPES = {"video/mp4", "video/quicktime", "video/x-matroska", "video/webm"}
EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}


class UploadError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def _save_json(path: Path, metadata: dict) -> None:
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


class UploadStore:
    def __init__(self, root: Path, *, max_file_bytes: int = MAX_FILE_BYTES,
                 chunk_bytes: int = CHUNK_BYTES):
        self.root = Path(root)
        self.sessions = self.root / "sessions"
        self.assets = self.root / "private-assets"
        self.sessions.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.assets.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.max_file_bytes = max_file_bytes
        self.chunk_bytes = chunk_bytes

    def _dir(self, session_id: str) -> Path:
        if not ID.fullmatch(session_id):
            raise UploadError("Invalid upload session", 404)
        folder = self.sessions / session_id
        if not folder.is_dir():
            raise UploadError("Unknown upload session", 404)
        return folder

    @contextlib.contextmanager
    def _locked(self, folder: Path):
        with (folder / ".lock").open("a+b") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _metadata(self, folder: Path) -> dict:
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        if time.time() > meta["created_at"] + SESSION_LIFETIME:
            raise UploadError("Upload session expired", 410)
        return meta

    def begin(self, *, name: str, size: int, sha256: str, mime_type: str) -> dict:
        if not isinstance(name, str) or len(name) > 180 or not name or "\x00" in name:
            raise UploadError("Invalid upload filename")
        # Strict basename avoids path traversal and arbitrary file writes.
        if name != Path(name).name or "\\" in name or name in {".", ".."}:
            raise UploadError("Upload filename must not contain paths")
        if Path(name).suffix.lower() not in EXTENSIONS or mime_type not in MEDIA_TYPES:
            raise UploadError("Unsupported video extension or media type")
        if type(size) is not int or size < 1 or size > self.max_file_bytes:
            raise UploadError(f"File must be between 1 and {self.max_file_bytes} bytes", 413)
        if not isinstance(sha256, str) or not SHA.fullmatch(sha256):
            raise UploadError("A 64-character SHA-256 is required")
        active = 0
        for folder in self.sessions.iterdir():
            if folder.is_dir() and (folder / "metadata.json").exists():
                try:
                    m = json.loads((folder / "metadata.json").read_text())
                    if time.time() < m["created_at"] + SESSION_LIFETIME and not m.get("complete"):
                        active += 1
                except (ValueError, OSError, KeyError):
                    active += 1
        if active >= MAX_UPLOAD_SESSIONS:
            raise UploadError("Too many incomplete uploads; retry later", 429)
        session_id = uuid.uuid4().hex
        folder = self.sessions / session_id
        folder.mkdir(mode=0o700)
        metadata = {
            "id": session_id, "name": name, "size": size, "sha256": sha256,
            "mime_type": mime_type, "chunk_bytes": self.chunk_bytes,
            "chunks": math.ceil(size / self.chunk_bytes), "created_at": time.time(),
            "complete": False,
        }
        _save_json(folder / "metadata.json", metadata)
        return self.status(session_id)

    def status(self, session_id: str) -> dict:
        folder = self._dir(session_id)
        with self._locked(folder):
            m = self._metadata(folder)
            received = [i for i in range(m["chunks"]) if (folder / f"{i:07d}.chunk").is_file()]
            return {"id": session_id, "size": m["size"], "sha256": m["sha256"],
                    "chunk_bytes": self.chunk_bytes, "total_chunks": m["chunks"],
                    "received_chunks": received, "complete": bool(m["complete"]),
                    "asset_id": m.get("asset_id")}

    def accept_chunk(self, session_id: str, index: int, incoming: Path,
                     sha256: str | None = None) -> dict:
        folder = self._dir(session_id)
        try:
            with self._locked(folder):
                m = self._metadata(folder)
                if m["complete"]:
                    raise UploadError("Session already completed", 409)
                if type(index) is not int or not 0 <= index < m["chunks"]:
                    raise UploadError("Chunk index outside upload range")
                expected = min(self.chunk_bytes, m["size"] - index * self.chunk_bytes)
                if incoming.stat().st_size != expected:
                    raise UploadError(f"Chunk {index} expected {expected} bytes", 422)
                hasher = hashlib.sha256()
                with incoming.open("rb") as reader:
                    for block in iter(lambda: reader.read(1024 * 1024), b""):
                        hasher.update(block)
                digest = hasher.hexdigest()
                if sha256 and (not SHA.fullmatch(sha256) or digest != sha256):
                    raise UploadError("Chunk SHA-256 mismatch", 422)
                target = folder / f"{index:07d}.chunk"
                if target.is_file():
                    with target.open("rb") as reader:
                        existing = hashlib.file_digest(reader, "sha256").hexdigest()
                    if existing != digest:
                        raise UploadError("Conflicting chunk retry", 409)
                    return {"ok": True, "chunk": index, "sha256": digest, "already_received": True}
                os.replace(incoming, target)
                return {"ok": True, "chunk": index, "sha256": digest, "already_received": False}
        finally:
            incoming.unlink(missing_ok=True)

    def complete(self, session_id: str) -> dict:
        folder = self._dir(session_id)
        with self._locked(folder):
            m = self._metadata(folder)
            if m["complete"]:
                return {"ok": True, "id": session_id, "asset_id": m["asset_id"],
                        "sha256": m["sha256"], "size": m["size"], "already_complete": True}
            missing = [i for i in range(m["chunks"]) if not (folder / f"{i:07d}.chunk").is_file()]
            if missing:
                raise UploadError(f"Upload incomplete: missing chunks {missing[:12]}", 409)
            target = self.assets / f"{session_id}{Path(m['name']).suffix.lower()}"
            partial = self.assets / f".{session_id}.partial"
            digest = hashlib.sha256()
            size = 0
            try:
                with partial.open("wb") as output:
                    for i in range(m["chunks"]):
                        with (folder / f"{i:07d}.chunk").open("rb") as reader:
                            for block in iter(lambda: reader.read(1024 * 1024), b""):
                                output.write(block)
                                digest.update(block)
                                size += len(block)
                    output.flush()
                    os.fsync(output.fileno())
                if digest.hexdigest() != m["sha256"] or size != m["size"]:
                    raise UploadError("Final file size or SHA-256 mismatch", 422)
                os.replace(partial, target)
                m["complete"] = True
                m["asset_id"] = session_id
                _save_json(folder / "metadata.json", m)
            finally:
                partial.unlink(missing_ok=True)
            for i in range(m["chunks"]):
                (folder / f"{i:07d}.chunk").unlink(missing_ok=True)
            return {"ok": True, "id": session_id, "asset_id": session_id,
                    "sha256": m["sha256"], "size": size, "already_complete": False}

    def resolve(self, asset_id: str) -> Path:
        folder = self._dir(asset_id)
        with self._locked(folder):
            meta = self._metadata(folder)
            if not meta["complete"]:
                raise UploadError("Asset upload is incomplete", 409)
            path = self.assets / f"{asset_id}{Path(meta['name']).suffix.lower()}"
            if not path.is_file() or path.stat().st_size != meta["size"]:
                raise UploadError("Committed upload data missing or corrupt", 500)
            return path

    def clean_expired(self) -> dict:
        now = time.time()
        count = 0
        for folder in self.sessions.iterdir():
            if not folder.is_dir() or not ID.fullmatch(folder.name):
                continue
            with self._locked(folder):
                try:
                    m = json.loads((folder / "metadata.json").read_text())
                except (OSError, ValueError):
                    continue
                if now - m.get("created_at", now) < SESSION_LIFETIME:
                    continue
                path = self.assets / f"{folder.name}{Path(m['name']).suffix.lower()}"
                path.unlink(missing_ok=True)
                count += 1
            shutil.rmtree(folder, ignore_errors=True)
        return {"expired_sessions_removed": count}