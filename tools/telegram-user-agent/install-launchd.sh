#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$HERE/.venv/bin/python"
WORKER="$HERE/worker.py"
PLIST="$HOME/Library/LaunchAgents/com.moksha.telegram-user-agent.plist"
LOGDIR="$HOME/.moksha"

if [ ! -x "$PYTHON" ]; then
  echo "Missing virtualenv. Run: bash $HERE/bootstrap-mac.sh" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$LOGDIR"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.moksha.telegram-user-agent</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON</string>
    <string>$WORKER</string>
  </array>
  <key>WorkingDirectory</key><string>$HERE</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>15</integer>
  <key>StandardOutPath</key><string>$LOGDIR/telegram-user-worker.log</string>
  <key>StandardErrorPath</key><string>$LOGDIR/telegram-user-worker.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"
echo "Installed and started Telegram user-agent worker."
echo "Logs: $LOGDIR/telegram-user-worker.log"
