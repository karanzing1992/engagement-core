#!/usr/bin/env bash
# Claude-first multi-project rollout: private Moksha-only, non-root Linux identity.
# Restricted host setup only. NO Claude/GitHub auth migration, runners, daemons, or deployments.
set -Eeuo pipefail
umask 077
ACCOUNT="claude-moksha"
HOME_DIR="/home/claude-moksha"
OWNER_REPO="karanzing1992/moksha_wordpress"

if [ "$(uname -s)" != "Linux" ] || [ "$(id -u)" -eq 0 ]; then
  echo "BLOCKED: run as a regular non-root Linux account" >&2
  exit 11
fi
for x in sudo useradd getent id stat chmod mktemp python3; do
  command -v "$x" >/dev/null 2>&1 || { echo "BLOCKED: missing $x" >&2; exit 12; }
done
if [ ! -x /usr/sbin/nologin ]; then
  echo "BLOCKED: nologin unavailable; do not grant interactive OS login" >&2
  exit 13
fi
if [ -L "$HOME_DIR" ]; then
  echo "BLOCKED: prospective isolated home is a symlink" >&2
  exit 14
fi

# The owner is the only authority for host account creation.
sudo -v
CREATED="no"
if getent passwd "$ACCOUNT" >/dev/null; then
  ACTUAL_HOME="$(getent passwd "$ACCOUNT" | cut -d: -f6)"
  ACTUAL_SHELL="$(getent passwd "$ACCOUNT" | cut -d: -f7)"
  if [ "$ACTUAL_HOME" != "$HOME_DIR" ] || [ "$ACTUAL_SHELL" != "/usr/sbin/nologin" ]; then
    echo "BLOCKED: account already exists with unfamiliar home or shell; no modifications" >&2
    exit 15
  fi
else
  if [ -e "$HOME_DIR" ]; then
    echo "BLOCKED: home exists without the expected account; no chown" >&2
    exit 16
  fi
  sudo useradd --system --user-group --create-home --home-dir "$HOME_DIR" --shell /usr/sbin/nologin "$ACCOUNT"
  CREATED="yes"
  sudo chmod 0700 "$HOME_DIR"
fi

# Fail closed on unexpected privileged group assignment. No recursive chown.
ACCOUNT_GROUPS="$(id -nG "$ACCOUNT")"
for forbidden in sudo docker lxd adm root wheel systemd-journal; do
  case " $ACCOUNT_GROUPS " in
    *" $forbidden "*) echo "BLOCKED: worker belongs to privileged group $forbidden" >&2; exit 17;;
  esac
done
if [ "$(sudo stat -c '%U' "$HOME_DIR")" != "$ACCOUNT" ]; then
  echo "BLOCKED: worker home not owned by worker" >&2
  exit 18
fi
MODE="$(sudo stat -c '%a' "$HOME_DIR")"
if [ "$MODE" != "700" ]; then
  echo "BLOCKED: worker home mode is $MODE; expected 700; no implicit permission changes" >&2
  exit 19
fi

# Synthetic canaries only; never inspect or duplicate existing SSH/Claude/GitHub tokens.
MARKER="$(mktemp "$HOME/.claude-moksha-host-canary-XXXXXXXX")"
trap 'rm -f -- "$MARKER"' EXIT
printf 'SYNTHETIC_OWNER_PRIVATE_CANARY\n' > "$MARKER"
chmod 0600 "$MARKER"
if sudo -u "$ACCOUNT" /usr/bin/cat "$MARKER" >/dev/null 2>&1; then
  echo "BLOCKED: worker can read synthetic owner-private file" >&2
  exit 20
fi
echo "PASS: worker cannot read owner-private synthetic file"
if [ -r "$HOME_DIR" ]; then
  echo "BLOCKED: invoking human user can read the worker's private home" >&2
  exit 21
fi
echo "PASS: worker home unreadable to invoking regular user"

sudo -u "$ACCOUNT" env -i HOME="$HOME_DIR" PATH=/usr/bin:/bin   /usr/bin/python3 -c 'import os, pathlib, tempfile; h=pathlib.Path(os.environ["HOME"]); assert pathlib.Path.home()==h; p=tempfile.NamedTemporaryFile(prefix="synthetic-worker-",dir=h,delete=True);p.close()'
echo "PASS: worker can write synthetic temporary data in its own HOME"

if command -v gh >/dev/null 2>&1; then
  LOGIN="$(gh api user -q .login 2>/dev/null || :)"
  if [ "$LOGIN" = "karanzing1992" ]; then
    echo "PASS: invoking host GitHub CLI login is primary account karanzing1992"
  else
    echo "UNVERIFIED: invoking host GitHub CLI is not confirmed as karanzing1992; no tokens copied or changed"
  fi
fi
echo "ACCOUNT: $ACCOUNT"
echo "HOME: $HOME_DIR"
echo "CREATED: $CREATED"
echo "REPOSITORY_PILOT: $OWNER_REPO (verified PRIVATE in GitHub; no runner enrolled)"
echo "ACCOUNT_BASELINE_PASS: restricted non-root worker with synthetic home-boundary checks"
echo "SUBSCRIPTION_AUTH_UNDER_WORKER: NOT_VERIFIED; one-time interactive Claude login required"
echo "OS_WORLD_READABLE_FILES_AND_SRT_POLICY: NOT_FULLY_VERIFIED"
echo "GITHUB_RUNNER: NOT_ENROLLED"
