#!/usr/bin/env python3
"""Read-only safety audit for fixed-name Cloud Run CPU pilot buckets.

Never writes Google Cloud resources, never prints tokens/credentials.
Returns 0 only if both proposed bucket names are confirmed absent.
Existing resources must be inspected before choosing a new suffix.
"""
from __future__ import annotations
import json
import subprocess
import sys


def gcloud(*args: str) -> tuple[int, object | None, str]:
    p = subprocess.run(["gcloud", *args, "--format=json"], text=True,
                       capture_output=True, timeout=35, check=False)
    if p.returncode:
        return p.returncode, None, (p.stderr or p.stdout or "").strip()
    try:
        return 0, json.loads(p.stdout), ""
    except ValueError:
        return 1, None, "Invalid Google Cloud response"


def bucket_name(value: str) -> str:
    return value.removeprefix("gs://").rstrip("/")


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: python3 audit-cloudrun-pilot.py PROJECT_ID INPUT_BUCKET OUTPUT_BUCKET")
        return 2
    project, source, output = sys.argv[1:]
    if not project or not source or not output or source == output:
        print("ERROR: Missing project or conflicting bucket names")
        return 2

    rc, project_data, error = gcloud("projects", "describe", project)
    if rc or not isinstance(project_data, dict):
        print("BLOCKED: Project ownership metadata unavailable (read-only).")
        return 3
    number = str(project_data.get("projectNumber", ""))
    if not number:
        print("BLOCKED: Project number not returned.")
        return 3
    print("PROJECT: " + project + " (project number verified)")

    rc, bucket_list, error = gcloud("storage", "buckets", "list", "--project=" + project)
    if rc or not isinstance(bucket_list, list):
        print("BLOCKED: Cannot enumerate project-owned storage buckets.")
        return 3
    owned = {bucket_name(str(x.get("name") or "")) for x in bucket_list if isinstance(x, dict)}
    blocked = False

    for role, name in (("SOURCE", source), ("OUTPUT", output)):
        present_in_project = name in owned
        rc, info, error = gcloud("storage", "buckets", "describe", "gs://" + name)
        if present_in_project:
            blocked = True
            print(f"{role}: EXISTS IN TARGET PROJECT — REFUSE OVERWRITE/REUSE: gs://{name}")
            if isinstance(info, dict):
                print("  location: " + str(info.get("location", "unknown")) +
                      "; uniform IAM: " + str(
                          (info.get("iamConfiguration") or {})
                          .get("uniformBucketLevelAccess", {}).get("enabled", "unknown")) +
                      "; public access prevention: " + str(
                          (info.get("iamConfiguration") or {})
                          .get("publicAccessPrevention", "unknown")))
            continue

        if rc == 0:
            blocked = True
            other = str(info.get("projectNumber", "")) if isinstance(info, dict) else ""
            if other and other != number:
                print(f"{role}: NAME OWNED BY DIFFERENT PROJECT — REFUSE REUSE: gs://{name}")
            else:
                print(f"{role}: EXISTS BUT NOT IN PROJECT LIST — OWNERSHIP UNKNOWN: gs://{name}")
            continue

        lower = error.lower()
        if any(term in lower for term in ("not found", "404", "does not exist")):
            print(f"{role}: NOT FOUND (name available at audit time): gs://{name}")
        else:
            blocked = True
            print(f"{role}: UNKNOWN (permissions/API/transient error); abort without changes.")

    if blocked:
        print("BLOCKED: at least one name exists or could not be verified.")
        print("No Cloud APIs, IAM, storage, container or jobs were modified by this audit.")
        return 5
    print("PASS: both bucket names are absent at audit time.")
    print("No Cloud resources were modified by this audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
