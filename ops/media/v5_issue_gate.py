#!/usr/bin/env python3
"""Owner-only GitHub Issue control-plane gate for V5 synthetic certification.

Issues and public CI cannot carry guest footage, credentials, access tokens or
signed private-media identifiers. Real footage remains in the existing sealed
WordPress queue, outside this GitHub issue interface.
"""
import argparse
import json
import re
from pathlib import Path
import sys
from reel_engine_router import load_policy, route_job

PROJECT_RE = re.compile(r"^[a-z0-9_]{3,48}$")
ALLOWED_KEYS = {"schema_version", "operation", "project_id", "job_type", "mode", "profile"}
ALLOWED_TYPES = {"instagram_reel", "social_video", "youtube_short", "brand_video"}

class GateRejected(ValueError):
    pass

def authorize(event):
    repository = event.get("repository") or {}
    owner = (repository.get("owner") or {}).get("login")
    issue = event.get("issue") or {}
    author = (issue.get("user") or {}).get("login")
    if not owner or author != owner:
        raise GateRejected("Only the repository owner may submit a render job")
    if issue.get("state") != "open":
        raise GateRejected("Only open issues are eligible")
    if not str(issue.get("title", "")).startswith("[MAD-V5] "):
        raise GateRejected("Missing dedicated V5 job title")
    if not any(x.get("name") == "reel-v5-run" for x in issue.get("labels", [])):
        raise GateRejected("Explicit reel-v5-run label required")
    body = issue.get("body") or ""
    if not isinstance(body, str) or len(body) > 1200:
        raise GateRejected("Job control JSON must be short and public-safe")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError) as exc:
        raise GateRejected("Issue body must be exact JSON") from exc
    if not isinstance(payload, dict) or set(payload) - ALLOWED_KEYS:
        raise GateRejected("Unknown or unsafe job input field")
    if payload.get("schema_version") != 1 or payload.get("operation") != "synthetic_certification":
        raise GateRejected("Only bounded synthetic certification is available")
    project = payload.get("project_id")
    if not isinstance(project, str) or not PROJECT_RE.fullmatch(project):
        raise GateRejected("Invalid project")
    if payload.get("job_type") not in ALLOWED_TYPES:
        raise GateRejected("Unsupported video job type")
    if payload.get("mode") not in {"fixture", "live"}:
        raise GateRejected("Unsupported inference mode")
    if payload.get("profile") not in {"synthetic_test", "instagram_reel"}:
        raise GateRejected("Unsupported export profile")
    selected = route_job(payload, load_policy())
    if selected["status"] != "V5_SELECTED_FOR_NEW_JOB":
        raise GateRejected("V5 project routing was not accepted")
    return {"status": "ACCEPTED_SYNTHETIC_ONLY", "project_id": project,
            "mode": payload["mode"], "profile": payload["profile"],
            "issue_number": issue["number"], "engine": "reel-engine-v5",
            "version": "5.0.0", "private_media": False, "publishing": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = authorize(json.loads(args.event.read_text()))
    except (GateRejected, ValueError, OSError, KeyError, TypeError) as exc:
        print("V5_ISSUE_GATE_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print("V5_OWNER_ISSUE_GATE_ACCEPTED", record["issue_number"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
