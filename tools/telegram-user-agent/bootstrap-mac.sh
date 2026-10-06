#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="${VENV:-.venv}"

"$PYTHON_BIN" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/pip" install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo
  echo "Created $HERE/.env"
  echo "Add TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_PHONE, then run:"
  echo "  $VENV/bin/python agent.py login"
else
  chmod 600 .env || true
  echo "Existing .env kept."
fi

mkdir -p "$HOME/.moksha"
chmod 700 "$HOME/.moksha" || true

echo
echo "Telegram user-agent is installed."
