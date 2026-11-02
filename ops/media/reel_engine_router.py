#!/usr/bin/env python3
"""Reel Engine V5 cross-project job intake. No video/API operation is performed.

A source of truth for new jobs. Never silently routes to an older renderer,
publishes, transfers private media, or bypasses existing owner/manager gates.
"""
import argparse
import json
from pathlib import Path
import sys

DEFAULT = Path(__file__).with_name("reel-engine-routing.json")


class RoutingError(ValueError):
    pass


def load_policy(path=DEFAULT):
    policy=json.loads(Path(path).read_text(encoding="utf-8"))
    if policy.get("default_engine")!="reel-engine-v5" or policy.get("version")!="5.0.0":
        raise RoutingError("V5 is not configured as the default engine")
    if policy.get("music",{}).get("composition_allowed") is not False:
        raise RoutingError("Music policy must use verified existing recordings")
    if policy.get("replay_and_legacy",{}).get("silent_fallback") is not False:
        raise RoutingError("Silent legacy fallback prohibited")
    for p in policy["projects"]:
        if not (p.get("id") and p.get("brand") and p.get("owner_gate")):
            raise RoutingError("Projects need individual brands and owner gates")
    return policy


def route_job(job, policy):
    if not isinstance(job,dict):
        raise RoutingError("Job request must be an object")
    typ=job.get("job_type")
    if typ in policy.get("not_for",[]):
        return {"status":"OUT_OF_SCOPE","job_type":typ,
                "reason":"Handled by its project engine, not Reel Engine V5",
                "no_media_operation":True}
    if typ not in policy.get("default_for",[]):
        return {"status":"UNKNOWN_JOB_TYPE","job_type":typ,
                "reason":"Requires owner-approved type registration",
                "no_media_operation":True}
    project=job.get("project_id")
    projects={x["id"]:x for x in policy["projects"]}
    if project not in projects:
        raise RoutingError("Unknown project identifier or brand")
    if job.get("existing_inflight") is True:
        return {"status":"EXISTING_JOB_UNCHANGED",
                "reason":"Version migration of in-flight jobs forbidden",
                "no_media_operation":True}
    if job.get("engine_override") and job.get("engine_override")!="reel-engine-v5":
        return {"status":"REQUIRES_OWNER_OVERRIDE_APPROVAL",
                "reason":"Legacy engine exception requires explicit project owner approval",
                "no_media_operation":True}
    p=projects[project]
    result={"status":"V5_SELECTED_FOR_NEW_JOB","project_id":project,
            "job_type":typ,"engine":"reel-engine-v5","version":"5.0.0",
            "brand_reference":p["brand"],"owner_release_gate":p["owner_gate"],
            "policy_id":policy["policy_id"],
            "canonical_config":policy["canonical_config"],
            "music_policy":"approved-existing-openly-licensed-recordings-only",
            "models":policy["creative_roles"],
            "media_uploaded":False,"rendered":False,"published":False,
            "real_source_v5_certified":False}
    if job.get("brand_reference"):
        result["brand_reference"]=job["brand_reference"]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--policy",default=str(DEFAULT))
    parser.add_argument("--job",required=True,help="JSON file containing job_type and project_id")
    parser.add_argument("--output",required=True)
    a=parser.parse_args(argv)
    try:
        result=route_job(json.loads(Path(a.job).read_text()),load_policy(a.policy))
        out=Path(a.output)
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({"status":result["status"],
                          "version":result.get("version"),
                          "no_render":True}))
        return 0 if result["status"] in {"V5_SELECTED_FOR_NEW_JOB","OUT_OF_SCOPE","EXISTING_JOB_UNCHANGED"} else 2
    except (RoutingError,ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)[:180]}),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
