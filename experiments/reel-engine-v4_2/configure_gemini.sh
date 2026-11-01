#!/usr/bin/env bash
# Local secret enrollment, never prints or commits the API key.
set -euo pipefail
umask 077
dest="$HOME/.config/mad-yard/secrets/gemini-api-key"
mkdir -p -- "$(dirname "$dest")"
chmod 700 -- "$(dirname "$dest")"
if [ ! -t 0 ]; then echo "Run in your private interactive terminal, not ChatGPT." >&2; exit 2; fi
printf "Enter your Gemini API key (hidden input): " >&2
IFS= read -r -s secret
printf '\n' >&2
if [ "$(printf %s "$secret" | wc -c)" -lt 12 ]; then echo "Missing/invalid key; nothing stored" >&2; exit 2; fi
printf "%s" "$secret" > "$dest.tmp"
unset secret
chmod 600 -- "$dest.tmp"
mv -f -- "$dest.tmp" "$dest"
chmod 600 -- "$dest"
echo "Saved secure key outside Git with permissions 0600."
echo 'export GEMINI_API_KEY_FILE="$HOME/.config/mad-yard/secrets/gemini-api-key"'
