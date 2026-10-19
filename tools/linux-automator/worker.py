#!/usr/bin/env python3
"""Outbound Linux SSH worker for the generic automator (separate from Pine/Shaadi).

Stdlib only. One host identity, one loopback-only SSH login, persisted no-replay journal.
Shell jobs disabled by default both here and at the gateway.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import sqlite3
import subprocess
import sys
import time
from urllib import request, error
from urllib.parse import urlsplit
import fcntl

HOSTS = {"dell-linux", "mac-linux"}
PROBE_COMMAND = "id -un && uname -s && hostname"
MAX_OUTPUT = 20000


class Blocked(Exception):
    pass


def secure_path(path: str, *, must_exist: bool = True) -> Path:
    p = Path(path).expanduser()
    if p.is_symlink():
        raise Blocked("Symlink path refused")
    p = p.resolve(strict=must_exist)
    return p


def load_config(path: str) -> dict:
    f = secure_path(path)
    st = f.stat()
    if st.st_mode & 0o022:
        raise Blocked("Configuration must not be group/world writable")
    obj = json.loads(f.read_text(encoding="utf-8"))
    required = {"host_id", "gateway", "ssh_user", "ssh_key", "known_hosts", "token_file", "journal"}
    if not isinstance(obj, dict) or not required.issubset(obj):
        raise Blocked("Configuration missing required fields")
    if obj["host_id"] not in HOSTS:
        raise Blocked("Unknown host lane")
    uri = urlsplit(obj["gateway"])
    if (uri.scheme != "https" or not uri.netloc or uri.username or uri.password
            or uri.query or uri.fragment
            or not uri.path.rstrip("/").endswith("/functions/v1/generic-linux-automator")):
        raise Blocked("HTTPS gateway must match the dedicated function path")
    if not isinstance(obj["ssh_user"], str) or not obj["ssh_user"].replace("-", "").replace("_", "").isalnum():
        raise Blocked("Invalid dedicated SSH login")
    obj["ssh_key"] = str(secure_path(obj["ssh_key"]))
    obj["known_hosts"] = str(secure_path(obj["known_hosts"]))
    obj["token_file"] = str(secure_path(obj["token_file"], must_exist=False))
    obj["journal"] = str(secure_path(obj["journal"], must_exist=False))
    obj["shell_enabled"] = obj.get("shell_enabled") is True
    return obj


def write_private_new(path: str, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, text.encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)


def token(cfg: dict) -> str:
    p = secure_path(cfg["token_file"])
    if p.stat().st_mode & 0o077:
        raise Blocked("Worker secret mode must be 0600")
    value = p.read_text("ascii").strip()
    if not (40 <= len(value) <= 256):
        raise Blocked("Worker token missing or invalid")
    return value


def post(cfg: dict, endpoint: str, payload: dict, bearer: str | None = None) -> dict:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(data) > 100000:
        raise Blocked("Oversized request")
    url = cfg["gateway"].rstrip("/") + endpoint
    headers = {"content-type": "application/json", "accept": "application/json"}
    if bearer:
        headers["authorization"] = "Bearer " + bearer
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=25) as response:
            raw = response.read(100001)
    except error.HTTPError as exc:
        raise Blocked("Gateway rejected request (HTTP " + str(exc.code) + ")") from None
    except (error.URLError, TimeoutError, OSError):
        raise Blocked("Gateway unreachable; retain job state without replay") from None
    if len(raw) > 100000:
        raise Blocked("Oversized gateway response")
    try:
        parsed = json.loads(raw)
    except ValueError:
        raise Blocked("Gateway returned malformed JSON") from None
    if not isinstance(parsed, dict) or parsed.get("ok") is not True:
        raise Blocked("Gateway returned an unsuccessful response")
    return parsed


def pair(cfg: dict) -> None:
    if os.path.exists(cfg["token_file"]):
        raise Blocked("Already has a token; never silently re-pair")
    code = getpass.getpass("One-time owner pairing code (not echoed): ").strip()
    if not (40 <= len(code) <= 160):
        raise Blocked("Invalid pairing-code format")
    value = secrets.token_urlsafe(48)
    write_private_new(cfg["token_file"], value + "\n")
    # Save secret first: an uncertain HTTP response cannot safely re-enroll.
    response = post(cfg, "/worker/enroll", {
        "host_id": cfg["host_id"],
        "pair_code": code,
        "worker_hash": hashlib.sha256(value.encode("ascii")).hexdigest(),
    })
    if response.get("host_id") != cfg["host_id"]:
        raise Blocked("Unexpected enrollment host; preserve token for investigation")
    print("PAIRED host=" + cfg["host_id"] + "; token stored locally only")


def database(cfg: dict) -> sqlite3.Connection:
    dbpath = Path(cfg["journal"])
    dbpath.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    conn = sqlite3.connect(str(dbpath), timeout=10)
    os.chmod(dbpath, 0o600)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("""CREATE TABLE IF NOT EXISTS journal (
        id TEXT PRIMARY KEY, claim TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('claimed','result')),
        result TEXT)""")
    conn.commit()
    return conn


def exec_ssh(cfg: dict, command: str, limit: int) -> dict:
    # ssh still verifies the pinned loopback host key. Never use StrictHostKeyChecking=no.
    argv = [
        "/usr/bin/ssh", "-T", "-p", "22",
        "-i", cfg["ssh_key"],
        "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "UserKnownHostsFile=" + cfg["known_hosts"],
        "-o", "GlobalKnownHostsFile=/dev/null",
        "-o", "ClearAllForwardings=yes", "-o", "ConnectTimeout=5",
        "-l", cfg["ssh_user"], "127.0.0.1",
        "/bin/sh", "-c", shlex.quote(command),
    ]
    try:
        run = subprocess.run(
            argv, capture_output=True, timeout=limit + 8, check=False,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )
        stdout = run.stdout.decode("utf-8", "replace").replace("\x00", "\ufffd")[:MAX_OUTPUT]
        stderr = run.stderr.decode("utf-8", "replace").replace("\x00", "\ufffd")[:MAX_OUTPUT]
        rc = run.returncode
    except subprocess.TimeoutExpired:
        stdout, stderr, rc = "", "SSH timeout; remote completion uncertain", None
    except OSError:
        stdout, stderr, rc = "", "SSH process unavailable", None
    return {"status": "completed" if rc == 0 else "failed",
            "exit_code": rc, "stdout": stdout, "stderr": stderr}


def flush_results(cfg: dict, conn: sqlite3.Connection, secret: str) -> None:
    rows = conn.execute("SELECT id,claim,state,result FROM journal ORDER BY rowid").fetchall()
    for jid, claim, state, result in rows:
        if state == "claimed":
            # Host/process died before durable result. Never replay an uncertain command.
            result = json.dumps({"status": "failed", "exit_code": None,
                                 "stdout": "", "stderr": "Interrupted; execution outcome uncertain"})
            conn.execute("UPDATE journal SET state='result',result=? WHERE id=?", (result, jid))
            conn.commit()
        payload = {"host_id": cfg["host_id"], "id": jid, "claim": claim, **json.loads(result)}
        post(cfg, "/worker/result", payload, secret)
        conn.execute("DELETE FROM journal WHERE id=?", (jid,))
        conn.commit()


def once(cfg: dict, conn: sqlite3.Connection, secret: str) -> None:
    flush_results(cfg, conn, secret)
    r = post(cfg, "/worker/poll", {"host_id": cfg["host_id"]}, secret)
    job = r.get("job")
    if job is None:
        return
    if not isinstance(job, dict):
        raise Blocked("Malformed job")
    jid, claim, kind = job.get("id"), job.get("claim"), job.get("kind")
    if not isinstance(jid, str) or not isinstance(claim, str) or kind not in ("probe", "shell"):
        raise Blocked("Malformed job identity")
    limit = job.get("timeout_seconds")
    if type(limit) is not int or not (5 <= limit <= 120):
        raise Blocked("Invalid timeout")
    # Claim recorded *before* any possible SSH execution.
    conn.execute("INSERT INTO journal (id,claim,state) VALUES (?,?,'claimed')",
                 (jid, claim))
    conn.commit()
    if kind == "probe":
        result = exec_ssh(cfg, PROBE_COMMAND, limit)
    elif not cfg["shell_enabled"]:
        result = {"status": "failed", "exit_code": None, "stdout": "",
                  "stderr": "Local shell execution disabled"}
    else:
        command = job.get("command")
        if not isinstance(command, str) or not (1 <= len(command) <= 8192):
            result = {"status": "failed", "exit_code": None, "stdout": "",
                      "stderr": "Invalid shell job"}
        else:
            result = exec_ssh(cfg, command, limit)
    conn.execute("UPDATE journal SET state='result',result=? WHERE id=?",
                 (json.dumps(result, ensure_ascii=False), jid))
    conn.commit()
    flush_results(cfg, conn, secret)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generic Linux automator worker")
    ap.add_argument("--config", required=True)
    ap.add_argument("action", choices=("pair", "once", "run"))
    args = ap.parse_args()
    try:
        cfg = load_config(args.config)
        if args.action == "pair":
            pair(cfg)
            return 0
        secret = token(cfg)
        lockfile = cfg["journal"] + ".lock"
        lockfd = os.open(lockfile, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked("Another worker process already holds this host lease") from None
        with database(cfg) as conn:
            if args.action == "once":
                once(cfg, conn, secret)
            else:
                while True:
                    try:
                        once(cfg, conn, secret)
                    except Blocked as e:
                        print("WORKER_TRANSIENT: " + str(e), file=sys.stderr)
                    time.sleep(5)
        return 0
    except (Blocked, ValueError, json.JSONDecodeError, sqlite3.Error) as exc:
        print("WORKER_BLOCKED: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
