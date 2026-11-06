#!/usr/bin/env python3
"""Private V6 model planner: execute on engagement-core with existing API secrets.

NO customer video, audio, images, GitHub private-repository URLs or media
credentials are used here. Only an OIDC-authenticated request for human-reviewed
shot description and owner prompt reaches the private Cloudflare job broker.

Transport: GitHub Actions OIDC -> Cloudflare Worker -> D1 -> model APIs ->
Cloudflare Worker -> private GitHub Release using the Worker's vault binding.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from multimodel_filmcraft_bridge import run

WORKER = "https://mad-v6-owner-private-beta.karanbizweb360.workers.dev"
AUDIENCE = "mad-v6-owner-private-beta"
JOB = re.compile(r"^v6job-[a-f0-9]{32}$")
SCHEMA = "mad-v6-private-plan/1"
MAX_PAYLOAD = 40 * 1024


class PlannerBlocked(ValueError):
    pass


def require_owner_source(payload):
    if not isinstance(payload, dict):
        raise PlannerBlocked("No approved private source metadata available")
    job = payload.get("job_id")
    if not isinstance(job, str) or not JOB.fullmatch(job):
        raise PlannerBlocked("Invalid private V6 job identity")
    source = payload.get("source_sha256")
    if not isinstance(source, str) or not re.fullmatch(r"[a-f0-9]{64}", source):
        raise PlannerBlocked("Source SHA-256 is missing")
    brief = payload.get("brief")
    description = payload.get("source_description")
    duration = payload.get("source_duration_seconds")
    if not isinstance(brief, str) or not 12 <= len(brief) <= 1200:
        raise PlannerBlocked("Approved creative direction is missing")
    if not isinstance(description, str) or not 20 <= len(description) <= 1000:
        raise PlannerBlocked("Human-reviewed shot description is missing")
    if type(duration) not in (int, float) or not 3 <= duration <= 480:
        raise PlannerBlocked("Source duration is unavailable or invalid")
    if payload.get("rights_confirmed") is not True or payload.get("free_gemini_consent") is not True:
        raise PlannerBlocked("Privacy or source-rights approval missing")
    if payload.get("audio_mode") != "source_ambience_only":
        raise PlannerBlocked("Unverified third-party soundtrack is not admissible")
    if payload.get("state") != "planning":
        raise PlannerBlocked("Private job has not been exclusively admitted for planning")
    return payload


def make_manifest(source):
    return {
        "source_sha256": source["source_sha256"],
        "human_reviewed": True,
        "rights_and_consent_cleared": True,
        "external_ai_processing_consent": True,
        "shots": [{
            "id": "s1",
            "start_seconds": 0.0,
            "duration_seconds": min(120., float(source["source_duration_seconds"])),
            "visible": source["source_description"],
        }]
    }


def make_private_plan(source, creative):
    require_owner_source(source)
    if not isinstance(creative, dict) or creative.get("editor") != "FilmCraft":
        raise PlannerBlocked("FilmCraft creative plan missing")
    p = {
        "schema": SCHEMA, "job_id": source["job_id"],
        "source": source["source_sha256"],
        "editor": "FilmCraft", "audio_mode": "source_ambience_only",
        "source_rights_admitted": creative.get("source_rights_admitted"),
        "live_model_inference": creative.get("live_model_inference"),
        "published": False, "owner_approval": False,
        "model_roles": creative.get("model_roles"),
        "director_sha256": creative.get("director_sha256"),
        "review_sha256": creative.get("review_sha256"),
        "hook": creative.get("hook"),
        "cuts": creative.get("cuts"),
        "operations": creative.get("operations"),
        "requested_effects": creative.get("requested_effects"),
    }
    raw = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(raw) > MAX_PAYLOAD:
        raise PlannerBlocked("Private creative plan exceeds signed delivery limit")
    return p


def get_oidc_token():
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not url or not token:
        raise PlannerBlocked("Signed GitHub Actions OIDC is unavailable")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ("pipelines.actions.githubusercontent.com", "token.actions.githubusercontent.com"):
        raise PlannerBlocked("Unexpected GitHub OIDC minting endpoint")
    destination = url + ("&" if "?" in url else "?") + urlencode({"audience": AUDIENCE})
    req = Request(destination, headers={"Authorization": "Bearer " + token,
                                       "Accept": "application/json", "User-Agent": "mad-v6-plan-only"})
    with urlopen(req, timeout=20) as response:
        payload = json.loads(response.read(8192))
    result = payload.get("value")
    if not isinstance(result, str) or len(result) < 120:
        raise PlannerBlocked("Signed workload identity was not returned")
    return result


def broker(endpoint, oidc_token, payload=None):
    if not isinstance(endpoint, str) or not endpoint.startswith("/internal/v6/plans/"):
        raise PlannerBlocked("Invalid V6 broker endpoint")
    job = endpoint.split("/")[4]
    if not JOB.fullmatch(job):
        raise PlannerBlocked("Invalid V6 job identity")
    raw = None
    method = "GET"
    if payload is not None:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(raw) > MAX_PAYLOAD:
            raise PlannerBlocked("Creative plan too large for private handoff")
        method = "POST"
    headers = {"Authorization": "Bearer " + oidc_token, "Accept": "application/json",
               "User-Agent": "MAD-V6-Signed-Plan-Runner"}
    if raw is not None:
        headers["Content-Type"] = "application/json"
    req = Request(WORKER + endpoint, data=raw, headers=headers, method=method)
    with urlopen(req, timeout=40) as response:
        data = response.read(MAX_PAYLOAD + 1)
    if len(data) > MAX_PAYLOAD:
        raise PlannerBlocked("Private broker response exceeds size limit")
    return json.loads(data)


def execute(job_id, *, synthetic_fixture=None):
    if not JOB.fullmatch(job_id):
        raise PlannerBlocked("Invalid private V6 job identifier")
    if synthetic_fixture is None:
        if os.environ.get("GITHUB_REPOSITORY") != "karanzing1992/engagement-core" or os.environ.get("GITHUB_REF") != "refs/heads/main":
            raise PlannerBlocked("Live inference allowed only on canonical engine default branch")
        if os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED") != "true":
            raise PlannerBlocked("Free-tier Gemini API project confirmation missing")
        oidc = get_oidc_token()
        source = require_owner_source(broker("/internal/v6/plans/" + job_id + "/source", oidc))
    else:
        source = require_owner_source(synthetic_fixture)
        oidc = None
    creative = run(
        source=make_manifest(source),
        brief=source["brief"],
        brand="Moksha Wellness, Arambol Goa; cinematic nature-led wellness; no medical guarantees.",
        mode="fixture" if synthetic_fixture is not None else "live",
        audio_mode="source_ambience_only",
        approved_api_cost=synthetic_fixture is None,
    )
    plan = make_private_plan(source, creative)
    if synthetic_fixture is None:
        if plan.get("live_model_inference") is not True:
            raise PlannerBlocked("Only independently reviewed live model plans may be delivered")
        result = broker("/internal/v6/plans/" + job_id + "/commit", oidc, plan)
        if result.get("state") != "plan_committed" or result.get("job_id") != job_id:
            raise PlannerBlocked("Broker rejected private reviewed FilmCraft plan")
        print(json.dumps({"status":"SIGNED_PLAN_COMMITTED","job_id":job_id,
                          "models_used":plan["model_roles"],"published":False}))
    else:
        print(json.dumps({"status":"SYNTHETIC_CONTRACT_ONLY","job_id":job_id,
                          "models_called":False,"published":False}))
    return plan


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", required=True)
    p.add_argument("--synthetic-input", default=None)
    a = p.parse_args()
    example = json.loads(Path(a.synthetic_input).read_text()) if a.synthetic_input else None
    execute(a.job_id, synthetic_fixture=example)


if __name__ == "__main__":
    try:
        main()
    except (PlannerBlocked, OSError, ValueError, KeyError) as exc:
        print("MAD_V6_PRIVATE_PLANNER_BLOCKED:" + type(exc).__name__, file=sys.stderr)
        raise SystemExit(2)
