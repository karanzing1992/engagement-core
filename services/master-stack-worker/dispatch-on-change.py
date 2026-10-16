#!/usr/bin/env python3
"""Demand-trigger the existing owner Apps Script publisher; no polling or new runner.

Usage: MASTER_SYNC_WEBAPP_URL=... MASTER_EVENT_HMAC_SECRET=... \
  python3 services/master-stack-worker/dispatch-on-change.py REPO SHA

Only use after the installed Web App and script properties are verified.
The current request never includes the HMAC secret, and no secrets are logged.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.request

ALLOWLIST = frozenset((
    "moksha_wordpress", "android_gpt_bridge", "engagement-core",
    "mokshasitemap", "andaz-vibe-stay", "staycore-pms",
    "synergistica-website", "constituency-ops-v1", "gpt-pine-engineer",
))


def build_event(repo, sha, secret, timestamp=None, nonce=None):
    if repo not in ALLOWLIST or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Invalid allowlisted repo or complete commit SHA")
    if len(secret) < 32:
        raise ValueError("HMAC secret must be at least 32 characters")
    epoch = int(time.time()) if timestamp is None else int(timestamp)
    nonce = secrets.token_urlsafe(18) if nonce is None else nonce
    if not re.fullmatch(r"[A-Za-z0-9_-]{12,80}", nonce):
        raise ValueError("Invalid nonce")
    parts = ("1", "github", repo, sha, str(epoch), nonce)
    payload = "\n".join(parts).encode("utf-8")
    return {
        "version": 1, "kind": "github", "repo": repo, "sha": sha,
        "timestamp": epoch, "nonce": nonce,
        "signature": hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest(),
    }


def deliver(url, event):
    if not url.startswith("https://script.google.com/macros/s/") or not url.endswith("/exec"):
        raise ValueError("Expected the verified Google Apps Script Web App /exec URL")
    req = urllib.request.Request(url, json.dumps(event).encode("utf-8"),
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=90) as response:
        result = json.load(response)
    marker = f"[MASTER-GITHUB-CHANGE:{event['repo']}:{event['sha']}]"
    if result.get("ok") is not True or result.get("marker") != marker or result.get("status") not in ("published", "already_published"):
        raise RuntimeError("Publisher did not confirm verified document readback: " + str(result.get("status", "unknown")))
    return result["status"]


def main(argv):
    if len(argv) != 3:
        print("Usage: dispatch-on-change.py REPO COMPLETE_SHA", file=sys.stderr)
        return 2
    url = os.environ.get("MASTER_SYNC_WEBAPP_URL", "")
    secret = os.environ.get("MASTER_EVENT_HMAC_SECRET", "")
    if not url or not secret:
        print("Event publisher not configured: no request sent", file=sys.stderr)
        return 2
    try:
        event = build_event(argv[1], argv[2], secret)
        status = deliver(url, event)
        print("MASTER_SYNC " + status + " " + argv[1] + " " + argv[2])
        return 0
    except (ValueError, RuntimeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        print("MASTER_SYNC FAIL " + type(error).__name__ + " (retain task for safe retry)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
