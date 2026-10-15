#!/usr/bin/env python3
"""Read-only SRT host canary: synthetic localhost, AF_UNIX and clean environment.

Never calls Claude, never touches real secrets/repos, and never enrolls runners.
Tests actual installed @anthropic-ai/sandbox-runtime and seccomp on this Linux PC.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import tempfile

SRT_ROOT = Path.home() / ".local/share/claude-dev-srt"
SRT = SRT_ROOT / "node_modules/.bin/srt"
ARCHES = {"x86_64": "x64", "aarch64": "arm64"}
CANARY_SECRET_NAME = "MOKSHA_FAKE_TOKEN_FOR_CANARY"
SCRIPT = """
import json, os, socket, sys
host_port = int(sys.argv[1])
result = {}
result['fake_token_in_child'] = 'MOKSHA_FAKE_TOKEN_FOR_CANARY' in os.environ
result['unexpected_api_key_in_child'] = any(
    name in os.environ for name in
    ('ANTHROPIC_API_KEY', 'GH_TOKEN', 'GITHUB_TOKEN', 'AWS_SECRET_ACCESS_KEY',
     'SUPABASE_SERVICE_ROLE_KEY')
)
try:
    connection = socket.create_connection(('127.0.0.1', host_port), timeout=2)
    result['loopback_connected'] = True
    connection.close()
except OSError:
    result['loopback_connected'] = False
try:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    result['unix_socket_created'] = True
    sock.close()
except OSError:
    result['unix_socket_created'] = False
print('SANDBOX_CANARY_JSON=' + json.dumps(result, sort_keys=True))
"""

def fail(reason: str, code: int) -> None:
    print("CANARY_BLOCKED: " + reason, file=sys.stderr)
    raise SystemExit(code)

def main() -> None:
    if sys.platform != "linux" or os.geteuid() == 0:
        fail("requires non-root Linux identity", 10)
    arch = ARCHES.get(platform.machine())
    if arch is None:
        fail("unsupported native seccomp architecture", 11)
    if not SRT.is_file() or not os.access(SRT, os.X_OK):
        fail("SRT not found at pinned per-user location", 12)
    helper_dir = SRT_ROOT / "node_modules/@anthropic-ai/sandbox-runtime/vendor/seccomp" / arch
    helper = helper_dir / "apply-seccomp"
    if not helper.is_file() or not os.access(helper, os.X_OK):
        fail("native seccomp helper missing; never bypass seccomp", 13)
    if helper.is_symlink() or helper_dir.is_symlink():
        fail("native seccomp path symlinked", 14)
    if shutil.which("python3") is None or shutil.which("bwrap") is None:
        fail("python3/bwrap missing", 15)

    # A test-only localhost service; no external packets, credentials or data.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as host_listener:
        host_listener.bind(("127.0.0.1", 0))
        host_listener.listen(8)
        port = host_listener.getsockname()[1]
        with tempfile.TemporaryDirectory(prefix="claude-dev-host-net-") as td:
            root = Path(td)
            ws = root / "workspace"
            ws.mkdir()
            child = ws / "socket_probe.py"
            child.write_text(SCRIPT, encoding="utf-8")
            settings = {
                "network": {
                    "allowedDomains": [],
                    "deniedDomains": ["*"],
                    "allowUnixSockets": [],
                    "allowAllUnixSockets": False,
                    "allowLocalBinding": False,
                },
                "filesystem": {
                    "denyRead": ["/home", "/root", "/mnt", "/media", "/run/user"],
                    "allowRead": [str(ws), str(helper_dir.resolve(strict=True))],
                    "allowWrite": [str(ws)],
                    "denyWrite": [str(helper_dir.resolve(strict=True))],
                },
                "enableWeakerNestedSandbox": False,
                "enableWeakerNetworkIsolation": False,
            }
            cfg = root / "srt.json"
            cfg.write_text(json.dumps(settings), encoding="utf-8")

            # Parent contains a FAKE token; child is launched with an explicit
            # allowlist, not inherited host credentials.
            parent = os.environ.copy()
            parent[CANARY_SECRET_NAME] = "SYNTHETIC_CANARY_ONLY"
            safe_env = {
                "HOME": str(Path.home()),
                "PATH": parent.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "LANG": parent.get("LANG", "C.UTF-8"),
                "TMPDIR": str(root),
            }
            try:
                run = subprocess.run(
                    [str(SRT), "--settings", str(cfg), sys.executable,
                     str(child), str(port)],
                    cwd=ws, env=safe_env, capture_output=True, text=True,
                    timeout=35, check=False,
                )
            except subprocess.TimeoutExpired:
                fail("sandbox subprocess timeout", 16)
            if run.returncode != 0:
                fail("SRT process failed: " + (run.stderr or "").strip()[:350], 17)
            lines = [
                line.split("SANDBOX_CANARY_JSON=", 1)[1]
                for line in run.stdout.splitlines()
                if line.startswith("SANDBOX_CANARY_JSON=")
            ]
            if len(lines) != 1:
                fail("missing or ambiguous sandbox probe result", 18)
            result = json.loads(lines[0])
            if result.get("fake_token_in_child") or result.get("unexpected_api_key_in_child"):
                fail("sensitive environment variable reached child", 19)
            print("PASS: sanitized environment excludes fake token and known cloud keys")
            if result.get("loopback_connected") is not False:
                fail("sandbox connected to the live local host listener", 20)
            print("PASS: denied sandbox connection to a live localhost listener")
            if result.get("unix_socket_created") is not False:
                fail("sandbox created AF_UNIX socket; native seccomp not enforcing", 21)
            print("PASS: native seccomp blocked AF_UNIX socket creation")
            # Positive control: real host loopback still works after the denied attempt.
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=2):
                    pass
            except OSError:
                fail("host loopback control connection unexpectedly failed", 22)
            print("PASS: host local listener is reachable outside sandbox")
    print("SRT_NETWORK_SOCKET_ENV_CANARY_PASS (synthetic only)")
    print("REMAINING: dedicated Unix identity, sandboxed Claude subscription, remote egress policy and scoped private runner not verified")

if __name__ == "__main__":
    main()
