#!/usr/bin/env python3
"""Controlled install of two extra worker lanes; preserves existing operations service.
Requires existing authenticated host, approved gateway v1.2.0, root execution and locally verified release artifacts.
Default is read-only preflight; --apply is required to write.
"""
import argparse, hashlib, json, os, shutil, stat, subprocess, sys, tempfile, urllib.request
from pathlib import Path

ROOT = Path("/opt/generic-linux-automator/worker.py")
CONFIG = Path("/etc/generic-linux-automator/host.json")
UNIT = Path("/etc/systemd/system/generic-linux-automator-lane@.service")
BACKUP = Path("/opt/generic-linux-automator/worker.py.pre-three-lanes-20261021")
GATEWAY = "https://saczglesalubroyaucqe.supabase.co/functions/v1/generic-linux-automator/health"
LANES = ("control", "development")

def die(msg):
    raise SystemExit("BLOCKED: " + msg)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def atomic(path, data, mode, uid, gid):
    fd, temp = tempfile.mkstemp(prefix=".lane-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp, mode)
        os.chown(temp, uid, gid)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate-worker", required=True)
    p.add_argument("--unit-template", required=True)
    p.add_argument("--sha256", required=True, help="Verified release worker SHA256")
    p.add_argument("--apply", action="store_true", help="Authorize on-host write after preflight")
    args = p.parse_args()
    candidate, template = Path(args.candidate_worker), Path(args.unit_template)
    if os.geteuid() != 0: die("run as root; no changes made")
    for f in (ROOT, CONFIG, candidate, template):
        if f.is_symlink() or not f.is_file(): die("missing or symlink input: " + str(f))
    if sha(candidate) != args.sha256.lower(): die("candidate checksum mismatch")
    if b'cfg.get("lane", "operations")' not in candidate.read_bytes(): die("missing lane validation")
    if b'"lane":cfg.get("lane", "operations")' not in candidate.read_bytes(): die("missing tagged poll")
    if b'NoNewPrivileges=yes' not in template.read_bytes() or b'ProtectSystem=strict' not in template.read_bytes():
        die("service hardening incomplete")
    subprocess.run([sys.executable, "-m", "py_compile", str(candidate)], check=True)
    active = subprocess.run(["systemctl", "is-active", "--quiet", "generic-linux-automator.service"])
    if active.returncode: die("operations worker not active")
    with urllib.request.urlopen(GATEWAY, timeout=8) as r:
        if json.load(r).get("version") != "1.2.0": die("gateway not yet upgraded to v1.2.0")
    original_hash = "45f4e1770d5a70ecc724808cf6d9fff3ec1f5584741037a18bd923ec20102b43"
    existing = sha(ROOT)
    if existing != original_hash and existing != args.sha256.lower(): die("unrecognized existing worker; protect local changes")
    conf_stat = CONFIG.stat()
    if conf_stat.st_uid != 0 or conf_stat.st_mode & 0o022: die("unsafe original host config")
    cfg = json.loads(CONFIG.read_text())
    if cfg.get("host_id") not in ("dell-linux","mac-linux"): die("unexpected host")
    if cfg.get("journal") != "/var/lib/generic-linux-automator/journal.sqlite3": die("unexpected journal")
    for lane in LANES:
        path = CONFIG.with_name(lane + ".json")
        new = dict(cfg, lane=lane, journal="/var/lib/generic-linux-automator/journal-" + lane + ".sqlite3")
        if path.exists():
            if path.is_symlink() or json.loads(path.read_text()) != new: die("preexisting conflicting lane config")
    if UNIT.exists() and (UNIT.is_symlink() or UNIT.read_bytes() != template.read_bytes()):
        die("existing unit has different content")
    print("PASS: " + cfg["host_id"] + ", existing worker=" + existing + ", candidate=" + args.sha256.lower())
    if not args.apply:
        print("PREFLIGHT ONLY. No files/services modified.")
        return
    if existing == original_hash:
        if BACKUP.exists(): die("backup name already occupied; manual review needed")
        shutil.copy2(ROOT, BACKUP)
        if sha(BACKUP) != original_hash: die("backup verification failed")
        st = ROOT.stat()
        atomic(ROOT, candidate.read_bytes(), stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid)
    if sha(ROOT) != args.sha256.lower(): die("worker verification failed")
    for lane in LANES:
        path = CONFIG.with_name(lane + ".json")
        new = dict(cfg, lane=lane, journal="/var/lib/generic-linux-automator/journal-" + lane + ".sqlite3")
        if not path.exists():
            atomic(path, (json.dumps(new, sort_keys=True, indent=2) + "\n").encode(), stat.S_IMODE(conf_stat.st_mode), conf_stat.st_uid, conf_stat.st_gid)
    if not UNIT.exists():
        atomic(UNIT, template.read_bytes(), 0o644, 0, 0)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    for lane in LANES:
        subprocess.run(["systemctl", "enable", "--now", "generic-linux-automator-lane@" + lane + ".service"], check=True)
    print("ENABLED: control and development; existing operations service not restarted")

if __name__ == "__main__":
    main()
