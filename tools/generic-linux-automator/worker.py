#!/usr/bin/env python3
"""Outbound localhost-SSH worker, independent of all project-specific bridges."""
from __future__ import annotations
import argparse
import fcntl
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
import tempfile
import resource
import socket
import random
import re
from urllib import request, error
from urllib.parse import urlsplit

HOSTS = {"dell-linux", "mac-linux"}
PROBE = "id -un && uname -s && hostname"

class Blocked(Exception):
    pass

def get_config(filename: str) -> dict:
    cfgpath = Path(filename)
    if cfgpath.is_symlink():
        raise Blocked("Symlink configuration forbidden")
    st = cfgpath.stat()
    if st.st_uid != 0 or st.st_mode & 0o022:
        raise Blocked("Root-owned non-writable host configuration required")
    cfg = json.loads(cfgpath.read_text(encoding="utf-8"))
    if cfg["host_id"] not in HOSTS:
        raise Blocked("Invalid host lane")
    if cfg.get("lane", "operations") not in ("control", "operations", "development"):
        raise Blocked("Invalid execution lane")
    url = urlsplit(cfg["gateway"])
    if (url.scheme != "https" or url.hostname != "saczglesalubroyaucqe.supabase.co" or
        url.path.rstrip("/") != "/functions/v1/generic-linux-automator" or
        url.username or url.password or url.query or url.fragment):
        raise Blocked("Dedicated HTTPS gateway required")
    if type(cfg.get("ssh_port")) is not int or cfg["ssh_port"] != 22222:
        raise Blocked("Dedicated loopback SSH port must be 22222")
    if cfg["ssh_user"] != "generic-auto-exec":
        raise Blocked("Dedicated nonroot local SSH user required")
    if cfg.get("shell_enabled", False) not in (True, False):
        raise Blocked("Bad local policy")
    for key in ("ssh_key", "known_hosts"):
        path = Path(cfg[key])
        if path.is_symlink() or not path.is_file():
            raise Blocked("Missing or linked SSH trust material")
        st = path.stat()
        if st.st_uid != os.geteuid() or st.st_mode & (0o077 if key == "ssh_key" else 0o022):
            raise Blocked("Insecure SSH private key or known_hosts ownership/mode")
    return cfg

def store_secret(path: Path, secret: str):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.write(fd, (secret + "\n").encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)

def load_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.geteuid() or path.stat().st_mode & 0o077:
        raise Blocked("Private local worker token missing or unsafe")
    token = path.read_text("ascii").strip()
    if not 40 <= len(token) <= 256:
        raise Blocked("Invalid worker token")
    return token

def rpc(cfg: dict, endpoint: str, payload: dict, secret: str = "") -> dict:
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf8")
    if len(encoded) > 100000:
        raise Blocked("Payload too large")
    headers = {"content-type": "application/json", "accept": "application/json"}
    if secret:
        headers["authorization"] = "Bearer " + secret
    url = cfg["gateway"].rstrip("/") + endpoint
    req = request.Request(url, data=encoded, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=25) as resp:
            result = resp.read(100001)
    except error.HTTPError as ex:
        raise Blocked("Gateway refused HTTP " + str(ex.code)) from None
    except (error.URLError, TimeoutError, OSError):
        raise Blocked("Gateway unavailable; job state retained") from None
    if len(result) > 100000:
        raise Blocked("Oversized response")
    try:
        output = json.loads(result)
    except ValueError:
        raise Blocked("Invalid gateway response") from None
    if not isinstance(output, dict) or output.get("ok") is not True:
        raise Blocked("Gateway returned unsuccessful status")
    return output

def pair(cfg: dict):
    path = Path(cfg["token_file"])
    if path.exists():
        raise Blocked("Worker token already exists; never silently re-pair")
    code = getpass.getpass("Enter owner one-time pairing code: ").strip()
    if not 40 <= len(code) <= 160:
        raise Blocked("Invalid pairing format")
    token = secrets.token_urlsafe(48)
    # Durable secret written before a potentially ambiguous enrollment POST.
    store_secret(path, token)
    try:
        reply = rpc(cfg, "/worker/enroll", {"host_id": cfg["host_id"], "pair_code": code,
            "worker_hash": hashlib.sha256(token.encode("ascii")).hexdigest()})
    except Blocked as ex:
        if str(ex) == "Gateway refused HTTP 403":
            # The gateway guarantees invalid/expired codes are not consumed or enrolled.
            path.unlink()
            raise Blocked("Invalid or expired pairing code; local candidate token discarded") from None
        raise
    if reply.get("host_id") != cfg["host_id"]:
        raise Blocked("Enrollment host mismatch, local token preserved for recovery")
    print("PAIRED:", cfg["host_id"])

def db_open(filename: str):
    path = Path(filename)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or path.parent.stat().st_mode & 0o077 or path.parent.stat().st_uid != os.geteuid():
        raise Blocked("Journal directory is not private and worker-owned")
    if path.exists() and (path.stat().st_mode & 0o077 or path.stat().st_uid != os.geteuid()):
        raise Blocked("Journal must be 0600 and worker-owned")
    db = sqlite3.connect(str(path), timeout=10)
    os.chmod(path, 0o600)
    db.execute("""CREATE TABLE IF NOT EXISTS journal(
      id TEXT PRIMARY KEY, claim TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN ('claimed','result')),
      result TEXT)""")
    db.commit()
    return db

def redact(text: str) -> str:
    # Defense in depth: never store obvious credentials in receipts/journal.
    text = re.sub(r"(?i)(Bearer[ \t]+)[^\s]+", r"\1[REDACTED]", text)
    return re.sub(r"(?im)\b((?:api[_-]?key|password|passwd|access[_-]?token|refresh[_-]?token|secret)[ \t]*[:=][ \t]*)[^\s]+",
                  r"\1[REDACTED]", text)

def capture_limit():
    # The SSH child cannot write more than 256 KiB to each redirected output file.
    resource.setrlimit(resource.RLIMIT_FSIZE, (262144, 262144))

def ssh(cfg: dict, command: str, limit: int) -> dict:
    argv = ["/usr/bin/ssh", "-F", "/dev/null", "-T", "-p", str(cfg["ssh_port"]),
        "-i", cfg["ssh_key"], "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=yes", "-o", "UserKnownHostsFile=" + cfg["known_hosts"],
        "-o", "GlobalKnownHostsFile=/dev/null", "-o", "ForwardAgent=no",
        "-o", "ClearAllForwardings=yes", "-o", "PermitLocalCommand=no",
        "-o", "ProxyCommand=none", "-o", "ProxyJump=none",
        "-o", "ConnectTimeout=5", "-o", "CanonicalizeHostname=no",
        "-l", cfg["ssh_user"], "127.0.0.1",
        "/bin/sh -c " + shlex.quote(command)]
    try:
        # TemporaryFile is disk backed: no stdout/stderr pipe buffering in RAM.
        with tempfile.TemporaryFile() as out_file, tempfile.TemporaryFile() as err_file:
            done = subprocess.run(argv, stdout=out_file, stderr=err_file,
                check=False, timeout=limit+8, env={"PATH":"/usr/bin:/bin","LC_ALL":"C"},
                preexec_fn=capture_limit, start_new_session=True)
            out_file.seek(0); err_file.seek(0)
            out = redact(out_file.read(20000).decode("utf-8", "replace").replace("\x00","\ufffd"))
            err = redact(err_file.read(20000).decode("utf-8", "replace").replace("\x00","\ufffd"))
            rc = done.returncode
    except subprocess.TimeoutExpired:
        rc, out, err = None, "", "SSH timeout; remote outcome uncertain"
    except OSError:
        rc, out, err = None, "", "Local SSH executable unavailable"
    return {"status":"completed" if rc == 0 else "failed", "exit_code":rc,
            "stdout":out,"stderr":err}

def flush(cfg, db, token):
    for id, claim, state, result in db.execute("SELECT id,claim,state,result FROM journal ORDER BY rowid").fetchall():
        if state == "claimed":
            # Crash after remote command claim: cannot know whether it completed.
            result = json.dumps({"status":"failed","exit_code":None,"stdout":"",
                "stderr":"Interrupted before result journal; execution outcome uncertain"})
            db.execute("UPDATE journal SET state='result',result=? WHERE id=?", (result,id))
            db.commit()
        rpc(cfg, "/worker/result", {"host_id":cfg["host_id"],"id":id,"claim":claim,**json.loads(result)}, token)
        db.execute("DELETE FROM journal WHERE id=?",(id,))
        db.commit()

def tick(cfg, db, token):
    flush(cfg,db,token)
    b = rpc(cfg, "/worker/poll", {"host_id":cfg["host_id"],
        "lane":cfg.get("lane", "operations")}, token)
    job = b.get("job")
    if job is None:
        return
    if not isinstance(job,dict):
        raise Blocked("Malformed job")
    id, claim, kind, limit = (job.get(k) for k in ("id","claim","kind","timeout_seconds"))
    if (not isinstance(id,str) or not isinstance(claim,str) or
        kind not in ("probe","shell") or type(limit) is not int or not 5<=limit<=120):
        raise Blocked("Malformed job identity")
    db.execute("INSERT INTO journal(id,claim,state) VALUES (?,?,'claimed')",(id,claim))
    db.commit()
    if kind=="probe":
        result=ssh(cfg,PROBE,limit)
    elif cfg.get("shell_enabled") is not True:
        result={"status":"failed","exit_code":None,"stdout":"","stderr":"Local shell gate disabled"}
    elif not isinstance(job.get("command"),str) or not 1<=len(job["command"])<=8192:
        result={"status":"failed","exit_code":None,"stdout":"","stderr":"Bad remote command"}
    else:
        result=ssh(cfg,job["command"],limit)
    db.execute("UPDATE journal SET state='result',result=? WHERE id=?",(json.dumps(result),id))
    db.commit()
    flush(cfg,db,token)

def sd_notify(message: str):
    target = os.environ.get("NOTIFY_SOCKET")
    if not target:
        return
    if target.startswith("@"):
        target = "\x00" + target[1:]
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as sock:
            sock.connect(target)
            sock.sendall(message.encode("ascii"))
    except OSError:
        pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("action", choices=("pair","once","run"))
    args=ap.parse_args()
    try:
        if os.geteuid() == 0:
            raise Blocked("Worker must never run as root")
        cfg=get_config(args.config)
        if args.action=="pair":
            pair(cfg)
            return 0
        token=load_secret(Path(cfg["token_file"]))
        lockfd=os.open(cfg["journal"]+".lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(lockfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked("Another worker is already active") from None
        with db_open(cfg["journal"]) as db:
            if args.action=="once":
                tick(cfg,db,token)
            else:
                errors = 0
                sd_notify("READY=1")
                while True:
                    try:
                        tick(cfg,db,token)
                        errors = 0
                        sd_notify("WATCHDOG=1")
                        time.sleep(5)
                    except Blocked as ex:
                        errors = min(errors + 1, 6)
                        print("TRANSIENT: "+str(ex),file=sys.stderr)
                        sd_notify("WATCHDOG=1")
                        time.sleep(min(60,5 * (2 ** min(errors-1,4))) + random.random()*2)
        return 0
    except (Blocked, OSError, ValueError, KeyError, sqlite3.Error) as ex:
        print("WORKER_BLOCKED: "+str(ex),file=sys.stderr)
        return 3

if __name__ == "__main__":
    sys.exit(main())
