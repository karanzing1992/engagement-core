#!/usr/bin/env bash
# Claude Dev host stage 1: install pinned upstream SRT in user space and test fake-file isolation.
# No sudo, runner registration, GitHub auth changes, code execution from task issues, or production modifications.
set -Eeuo pipefail
umask 077

SRT_VERSION="0.0.79"
PREFIX="${HOME}/.local/share/claude-dev-srt"
BIN_DIR="${HOME}/.local/bin"
SRT="${PREFIX}/node_modules/.bin/srt"

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'MISSING_DEPENDENCY: %s\n' "$1" >&2
    return 1
  fi
}

for name in node npm bwrap socat rg python3; do
  need "$name" || {
    printf 'BLOCKED: host is missing a required prerequisite. For Debian/Ubuntu: sudo apt-get install socat ripgrep\n' >&2
    exit 20
  }
done
if [ "$(uname -s)" != "Linux" ] || [ "$(id -u)" = "0" ]; then
  echo 'BLOCKED: install using a regular Linux user' >&2
  exit 21
fi
printf 'INSTALL: upstream @anthropic-ai/sandbox-runtime@%s into a private user prefix\n' "$SRT_VERSION"
mkdir -p "$PREFIX" "$BIN_DIR"
npm install --prefix "$PREFIX" --save-exact --ignore-scripts --no-audit --no-fund "@anthropic-ai/sandbox-runtime@${SRT_VERSION}"
if [ ! -x "$SRT" ]; then
  echo 'BLOCKED: srt CLI was not installed at the expected location' >&2
  exit 22
fi
if [ -e "$BIN_DIR/srt" ] || [ -L "$BIN_DIR/srt" ]; then
  if [ "$(readlink -f "$BIN_DIR/srt")" != "$(readlink -f "$SRT")" ]; then
    echo 'BLOCKED: ~/.local/bin/srt already exists; will not replace it' >&2
    exit 23
  fi
else
  ln -s "$SRT" "$BIN_DIR/srt"
fi

# Everything below is a disposable fake-data canary. Never test on real credentials.
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/claude-dev-srt-canary-XXXXXXXX")"
WORKSPACE="$TMP_ROOT/workspace"
PRIVATE_DIR="$TMP_ROOT/private"
trap 'rm -rf -- "$TMP_ROOT"' EXIT
mkdir -p "$WORKSPACE" "$PRIVATE_DIR"
printf 'WORKSPACE_OK\n' > "$WORKSPACE/allowed.txt"
printf 'FAKE_SECRET_DO_NOT_DISCLOSE\n' > "$PRIVATE_DIR/secret.txt"
ln -s "$PRIVATE_DIR/secret.txt" "$WORKSPACE/escape-link"
python3 - "$TMP_ROOT/srt.json" "$WORKSPACE" "$PRIVATE_DIR" <<'PY'
import json,sys
cfg = {
    'network': {'allowedDomains': [], 'deniedDomains': [], 'allowUnixSockets': [], 'allowLocalBinding': False},
    'filesystem': {
        'denyRead': ['/home', '/root', '/mnt', '/media', '/run/user', sys.argv[3]],
        'allowRead': [sys.argv[2]],
        'allowWrite': [sys.argv[2]],
        'denyWrite': [sys.argv[3]],
    },
    'enableWeakerNestedSandbox': False,
}
with open(sys.argv[1], 'w', encoding='utf-8') as f:
    json.dump(cfg, f)
PY
printf 'CANARY: invoking real SRT+bubblewrap with synthetic test data\n'
export PATH="$BIN_DIR:$PATH"
if ! "$SRT" --settings "$TMP_ROOT/srt.json" /bin/cat "$WORKSPACE/allowed.txt" > "$TMP_ROOT/read.log" 2>&1 || \
    ! grep -q 'WORKSPACE_OK' "$TMP_ROOT/read.log"; then
  echo 'CANARY_FAIL: permitted workspace read failed' >&2
  sed -n '1,6p' "$TMP_ROOT/read.log" >&2
  exit 24
fi
if "$SRT" --settings "$TMP_ROOT/srt.json" /bin/cat "$PRIVATE_DIR/secret.txt" > "$TMP_ROOT/blocked-read.log" 2>&1 || \
    grep -q 'FAKE_SECRET_DO_NOT_DISCLOSE' "$TMP_ROOT/blocked-read.log"; then
  echo 'CANARY_FAIL: private file was readable' >&2
  exit 25
fi
if "$SRT" --settings "$TMP_ROOT/srt.json" /bin/cat "$WORKSPACE/escape-link" > "$TMP_ROOT/blocked-link.log" 2>&1 || \
    grep -q 'FAKE_SECRET_DO_NOT_DISCLOSE' "$TMP_ROOT/blocked-link.log"; then
  echo 'CANARY_FAIL: symlink escaped workspace' >&2
  exit 26
fi
if "$SRT" --settings "$TMP_ROOT/srt.json" /usr/bin/touch "$PRIVATE_DIR/unexpected.txt" > "$TMP_ROOT/blocked-write.log" 2>&1 || \
    [ -e "$PRIVATE_DIR/unexpected.txt" ]; then
  echo 'CANARY_FAIL: private directory was writable' >&2
  exit 27
fi
if ! "$SRT" --settings "$TMP_ROOT/srt.json" /usr/bin/touch "$WORKSPACE/allowed-write.txt" > "$TMP_ROOT/allowed-write.log" 2>&1 || \
    [ ! -f "$WORKSPACE/allowed-write.txt" ]; then
  echo 'CANARY_FAIL: permitted workspace write failed' >&2
  exit 28
fi
printf 'SRT_VERSION_PIN: %s\n' "$SRT_VERSION"
printf 'SRT_BINARY: %s\n' "$SRT"
printf 'CANARY_PASS: permitted workspace read/write\n'
printf 'CANARY_PASS: blocked private read/write and symlink escape\n'
printf 'STATUS: BASIC_SANDBOX_CANARY_PASS; host identity, subscription-in-sandbox, sockets and network enforcement UNVERIFIED\n'
printf 'CROSS_PROJECT_RUNNER: NOT_ENROLLED (no new GitHub runner or project tokens configured)\n'
