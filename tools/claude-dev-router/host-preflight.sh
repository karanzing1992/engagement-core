#!/usr/bin/env bash
# Read-only Claude Dev host assessment. No installs, secrets, network, or config changes.
set -u
export PATH="$HOME/.local/bin:$PATH"
have() { command -v "$1" >/dev/null 2>&1 && printf 'yes' || printf 'no'; }
report() { printf '%-28s %s\n' "$1" "$2"; }
report "platform" "$(uname -s 2>/dev/null || echo unknown)"
report "uid_root" "$([ "$(id -u)" -eq 0 ] && echo yes || echo no)"
report "git_cli" "$(have git)"
report "gh_cli" "$(have gh)"
report "claude_cli" "$(have claude)"
report "node_cli" "$(have node)"
report "npm_cli" "$(have npm)"
report "bwrap_cli" "$(have bwrap)"
report "srt_cli" "$(have srt)"
report "python3_cli" "$(have python3)"
if command -v claude >/dev/null 2>&1; then
  ver=$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || :)
  report "claude_version" "${ver:-unverified}"
else
  report "claude_version" "missing"
fi
if command -v claude >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  result=$(env -u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u ANTHROPIC_BASE_URL \
    -u CLAUDE_CODE_USE_BEDROCK -u CLAUDE_CODE_USE_VERTEX -u CLAUDE_CODE_USE_FOUNDRY \
    claude auth status 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print("yes" if d.get("loggedIn") is True and d.get("authMethod")=="claude.ai" else "no")' 2>/dev/null || true)
  report "claude_subscription_auth" "${result:-unverified}"
else
  report "claude_subscription_auth" "unverified"
fi
if command -v bwrap >/dev/null 2>&1; then
  if timeout 8 bwrap --ro-bind / / --proc /proc --dev /dev --unshare-all --share-net /bin/true >/dev/null 2>&1; then
    report "bwrap_kernel_sandbox" "yes"
  else
    report "bwrap_kernel_sandbox" "no"
  fi
else
  report "bwrap_kernel_sandbox" "unverified"
fi
report "cross_project_isolation" "UNVERIFIED (requires dedicated identity and negative tests)"
report "multi_repo_runner" "UNVERIFIED (requires private repo enrollment and live run)"
report "recommended_status" "NOT_ENROLLED until host isolation and scoped route confirmed"
