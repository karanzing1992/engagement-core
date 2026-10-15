#!/usr/bin/env bash
# Claude Dev / SRT: repair *only* the synthetic sandbox canary's read-only helper allowlist.
# No sudo; no npm operations; no runner changes; no credential access; no real project files.
set -Eeuo pipefail
umask 077

SRT_ROOT="$HOME/.local/share/claude-dev-srt"
SRT="$SRT_ROOT/node_modules/.bin/srt"
HELPER_DIR="$SRT_ROOT/node_modules/@anthropic-ai/sandbox-runtime/vendor/seccomp/x64"
HELPER="$HELPER_DIR/apply-seccomp"
if [ ! -x "$SRT" ]; then
  echo 'BLOCKED: srt not installed at expected per-user location' >&2
  exit 11
fi
if [ ! -f "$HELPER" ]; then
  echo 'BLOCKED: vendor/seccomp/x64/apply-seccomp is genuinely absent on the host' >&2
  echo 'Inspect npm package contents; do NOT disable seccomp, Unix socket protections or path denies.' >&2
  exit 12
fi
if [ ! -x "$HELPER" ] || [ -L "$HELPER" ] || [ -L "$HELPER_DIR" ]; then
  echo 'BLOCKED: seccomp helper is not a regular executable or has unexpected symlink' >&2
  exit 13
fi
for tool in python3 bwrap cat touch grep; do
  command -v "$tool" >/dev/null || { echo "BLOCKED: missing $tool" >&2; exit 14; }
done
# Parent /home remains inaccessible, except this exact, read-only SRT helper directory.
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/claude-dev-srt-retest-XXXXXXXX")"
trap 'rm -rf -- "$ROOT"' EXIT
WORKSPACE="$ROOT/workspace"
FAKE_PRIVATE="$ROOT/fake-private"
mkdir -p "$WORKSPACE" "$FAKE_PRIVATE"
printf 'CANARY_WORKSPACE_OK\n' > "$WORKSPACE/allowed.txt"
printf 'CANARY_FAKE_SECRET\n' > "$FAKE_PRIVATE/secret.txt"
ln -s "$FAKE_PRIVATE/secret.txt" "$WORKSPACE/escape-link"
python3 - "$ROOT/settings.json" "$WORKSPACE" "$FAKE_PRIVATE" "$HELPER_DIR" <<'PY'
import json, pathlib, sys
config = {
    "network": {"allowedDomains": [], "deniedDomains": [],
                "allowUnixSockets": [], "allowLocalBinding": False},
    "filesystem": {
        "denyRead": ["/home", "/root", "/mnt", "/media", "/run/user", sys.argv[3]],
        "allowRead": [sys.argv[2], sys.argv[4]],
        "allowWrite": [sys.argv[2]],
        "denyWrite": [sys.argv[3], sys.argv[4]],
    },
    "enableWeakerNestedSandbox": False,
}
pathlib.Path(sys.argv[1]).write_text(json.dumps(config))
PY
run() { "$SRT" --settings "$ROOT/settings.json" "$@"; }
if ! run /bin/cat "$WORKSPACE/allowed.txt" > "$ROOT/allow.log" 2>&1 ||
   ! grep -q 'CANARY_WORKSPACE_OK' "$ROOT/allow.log"; then
  echo 'FAIL: workspace access or SRT/seccomp startup failed' >&2
  sed -n '1,8p' "$ROOT/allow.log" >&2
  exit 20
fi
echo 'PASS: SRT+seccomp starts, workspace read allowed'
if run /bin/cat "$FAKE_PRIVATE/secret.txt" > "$ROOT/deny-read.log" 2>&1 ||
   grep -q 'CANARY_FAKE_SECRET' "$ROOT/deny-read.log"; then
  echo 'FAIL: fake private file readable' >&2; exit 21
fi
echo 'PASS: fake private file unreadable'
if run /bin/cat "$WORKSPACE/escape-link" > "$ROOT/deny-symlink.log" 2>&1 ||
   grep -q 'CANARY_FAKE_SECRET' "$ROOT/deny-symlink.log"; then
  echo 'FAIL: symlink escaped the sandbox' >&2; exit 22
fi
echo 'PASS: symlink escape refused'
# Linux SRT denyRead uses a tmpfs mount for directories. Writes there may
# return success, but must NEVER create or modify files on the real host.
if run /usr/bin/touch "$FAKE_PRIVATE/forbidden.txt" > "$ROOT/deny-write.log" 2>&1; then
  echo 'INFO: sandbox wrote to disposable denyRead tmpfs (not necessarily the host)'
fi
if [ -e "$FAKE_PRIVATE/forbidden.txt" ] ||
   ! grep -qx 'CANARY_FAKE_SECRET' "$FAKE_PRIVATE/secret.txt"; then
  echo 'FAIL: a private file was created or modified on the host' >&2; exit 23
fi
echo 'PASS: denyRead tmpfs writes did not modify host private files'

# A separate read-visible directory outside allowWrite must reject writes
# outright. Unlike denyRead tmpfs, this path has no overlay.
READABLE_ONLY="$ROOT/readable-only"
mkdir -p "$READABLE_ONLY"
if run /usr/bin/touch "$READABLE_ONLY/forbidden.txt" > "$ROOT/outside-write.log" 2>&1 ||
   [ -e "$READABLE_ONLY/forbidden.txt" ]; then
  echo 'FAIL: write outside allowWrite was not blocked' >&2
  exit 25
fi
echo 'PASS: read-visible path outside allowWrite refused writes'
if ! run /usr/bin/touch "$WORKSPACE/permitted.txt" > "$ROOT/allow-write.log" 2>&1 ||
   [ ! -f "$WORKSPACE/permitted.txt" ]; then
  echo 'FAIL: sandbox workspace not writable' >&2
  sed -n '1,8p' "$ROOT/allow-write.log" >&2
  exit 24
fi
echo 'PASS: workspace write allowed'
echo 'SRT_HOST_FILESYSTEM_CANARY_PASS (synthetic paths; no real secrets tested)'
echo 'HOST_IDENTITY, NETWORK, SOCKETS, CLAUDE_SUBSCRIPTION_IN_SANDBOX: NOT YET VERIFIED'
echo 'CROSS_PROJECT_RUNNERS: NOT_ENROLLED'
