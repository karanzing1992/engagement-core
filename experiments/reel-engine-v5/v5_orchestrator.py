#!/usr/bin/env python3
"""MAD Reel Engine V5: model/tool extensible creative planner.

Creative imagination is open; bounded, provenance-checked media edits are not
unrestricted shell access. This module plans/reports capabilities; it does not
render, import third-party footage, publish or change existing manager services.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class Rejected(ValueError):
    pass


def read_json(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(d, dict):
        raise Rejected("Expected a JSON object")
    return d


def load_system(config_path, registry_path):
    cfg, reg = read_json(config_path), read_json(registry_path)
    if cfg.get("version") != "5.0.0" or reg.get("version") != 5:
        raise Rejected("V5 configuration/registry version mismatch")
    gate=cfg.get("provider_policy",{})
    if gate.get("allowed")!=["groq"] or gate.get("fallback")!="same_provider_only":
        raise Rejected("V5 only permits the configured Groq API")
    if cfg.get("routing_revision")!="groq_only_task_routing_20261104":
        raise Rejected("Groq-only task routing revision mismatch")
    models = cfg.get("models", {})
    for role in ("creative", "vision", "execution", "critique"):
        if not models.get(role):
            raise Rejected("Missing model role " + role)
        for entry in models[role]:
            if entry.get("provider")!="groq" or not isinstance(entry.get("model"),str):
                raise Rejected("Only Groq-hosted model IDs are permitted for " + role)
            if entry.get("credential_env")!="GROQ_API_KEY":
                raise Rejected("Groq-only key mapping required for " + role)
            t = entry.get("temperature")
            if t is not None and not (0 <= t <= 2):
                raise Rejected("Model creativity temperature outside API profile")
    operations = reg.get("operations", [])
    names = [x.get("name") for x in operations]
    if len(names) != len(set(names)):
        raise Rejected("Duplicate operation registration")
    for op in operations:
        if op.get("status") not in {"candidate", "verified", "blocked"}:
            raise Rejected("Unknown operation status")
    tasks=cfg.get("task_routing")
    if not isinstance(tasks,dict) or not tasks:
        raise Rejected("Task routing is required")
    for task,route in tasks.items():
        role=route.get("role")
        if role not in models or not route.get("candidate_models"):
            raise Rejected("Invalid task route "+task)
        ids={entry["model"] for entry in models[role]}
        if any(mid not in ids for mid in route["candidate_models"]):
            raise Rejected("Task route references unavailable model "+task)
    for profile in cfg["profiles"].values():
        w, h = profile["dimensions"]
        if not (64 <= w <= 8192 and 64 <= h <= 8192):
            raise Rejected("Unsupported output size")
    if cfg["creative"]["brand_style_locked"] is not True or cfg["source"]["provenance_required"] is not True:
        raise Rejected("Cannot disable brand/source hard gates")
    if cfg["tools"]["never_execute_model_shell"] is not True:
        raise Rejected("Model shell execution forbidden")
    return cfg, reg


def models_for_role(cfg, role):
    return [dict(m) for m in cfg["models"][role]]


def select_model(cfg, role, available=None):
    """Choose first authorized Groq model, never an external provider."""
    if role not in cfg["models"]:raise Rejected("Unknown model role")
    for model in cfg["models"][role]:
        if model.get("provider")!="groq":
            raise Rejected("V5 external model fallback forbidden")
        key="groq:"+model["model"]
        if available is None or key in available:
            return model
    raise Rejected("No configured Groq model available for role " + role)


def models_for_task(cfg, task, available=None):
    """Return prioritized Groq-only candidates based on the exact task and permissions."""
    route=cfg["task_routing"].get(task)
    if not route:
        raise Rejected("Unregistered Groq task: "+str(task))
    defined={m["model"]:m for m in cfg["models"][route["role"]]}
    choices=[]
    for ident in route["candidate_models"]:
        selected=defined[ident]
        if available is None or "groq:"+ident in available:
            choices.append(dict(selected))
    if not choices:
        raise Rejected("No authorized Groq model for task "+task)
    return choices


def validate_source(data, cfg):
    if data.get("provenance") not in {"human_reviewed", "gemini_human_reviewed"}:
        raise Rejected("Human verified source manifest required")
    shots = data.get("shots")
    if not isinstance(shots, list) or not shots:
        raise Rejected("Shot manifest cannot be empty")
    if len(shots) > cfg["budget"]["max_shots_per_manifest"]:
        raise Rejected("Manifest exceeds per-job operating budget")
    by_id = {}
    for s in shots:
        sid = s.get("id")
        if not isinstance(sid, str) or not ID_RE.fullmatch(sid) or sid in by_id:
            raise Rejected("Malformed or duplicate shot id")
        start, duration = s.get("start_seconds"), s.get("duration_seconds")
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (start, duration)):
            raise Rejected("Shot timings must be numeric")
        if start < 0 or duration <= 0 or start + duration > cfg["budget"]["max_source_seconds"]:
            raise Rejected("Shot exceeds verified source/budget")
        desc = s.get("visible_description")
        if not isinstance(desc, str) or not 4 <= len(desc) <= 1500:
            raise Rejected("Grounded visual description required")
        by_id[sid] = dict(s)
    return by_id


def required_clearance(manifest, *, external=False):
    if not external:
        return
    if manifest.get("external_metadata_approved") is not True:
        raise Rejected("Source description may not leave trusted host without approval")
    if manifest.get("rights_and_consent") is not True:
        raise Rejected("Media rights and recognizable-person consent not cleared")


def validate_brief_versions(number, cfg):
    if not isinstance(number, int) or isinstance(number, bool):
        raise Rejected("Requested treatment count must be an integer")
    if number < 1:
        raise Rejected("At least one treatment is required")
    if number > cfg["budget"]["max_treatments_per_job"]:
        raise Rejected("Requested number exceeds configured operating budget, not creative style policy")
    return number


def build_director_prompt(cfg, verified_shots, brand, brief, versions, profile):
    if profile not in cfg["profiles"]:
        raise Rejected("Unknown export profile")
    if not isinstance(brand, str) or len(brand.strip()) < 6:
        raise Rejected("Approved brand description is required")
    if not isinstance(brief, str) or len(brief.strip()) < 6:
        raise Rejected("Creative brief required")
    n = validate_brief_versions(versions, cfg)
    facts = [{"id":s["id"], "start_seconds":s["start_seconds"],
              "duration_seconds":s["duration_seconds"],
              "visible":s["visible_description"]} for s in verified_shots.values()]
    schema = {
      "versions":[{"id":"T1","name":"your concept name","narrative":"original narrative",
                   "emotional_arc":"from feeling to feeling","hook":"first-frame hook",
                   "segments":[{"shot_id":"a verified ID","offset_seconds":0.0,
                                "duration_seconds":1.0,"caption":"",
                                "proposed_operations":[{"name":"color_grade","parameters":{"creative_look":"subtle warm"}}]}]}]
    }
    return (
        "You are an autonomous independent cinematic creative director. "
        "Exercise maximum ORIGINAL CREATIVE EXPRESSION inside strict source truth "
        "and verified brand requirements. You decide genre, structure, hook, pace, "
        "visual style, editing rhythm, typography, sound design, visual treatment "
        "and storytelling. No default restrictions on shots, length, transitions "
        "or template, except the requested export profile and project resource budget. "
        "You may propose new creative operations, even if the local tool registry "
        "does not implement them yet: mark them as proposed, never invent successful "
        "execution. Every segment must reference ONLY observed source shots and "
        "valid offsets/durations. Do not invent shots, people, venue, actions, "
        "music rights or credentials. No unapproved publishing. "
        "Return a JSON object with exactly " + str(n) + " *structurally diverse* "
        "treatments. Use distinct IDs T1..T" + str(n) + ". "
        "No fixed number of segments; use only what serves the story. "
        "Each segment has shot_id, offset_seconds, duration_seconds, "
        "caption and proposed_operations list. Important: proposed_operations "
        "may not yet be renderable; our guarded compiler will flag them. "
        "You may suggest new operations/tools as creative direction. "
        "Proposed output JSON shape: " + json.dumps(schema) +
        "\nEXPORT PROFILE: " + profile + " " + json.dumps(cfg["profiles"][profile]) +
        "\nVERIFIED BRAND RULES: " + brand[:8000] +
        "\nUSER CREATIVE BRIEF: " + brief[:4000] +
        "\nVERIFIED SOURCE SHOTS: " + json.dumps(facts,ensure_ascii=False)
    )


def validate_plan(plan, shots, count, cfg):
    versions = plan.get("versions")
    if not isinstance(versions, list) or len(versions) != count:
        raise Rejected("Number of returned versions differs from requested")
    validated = []
    for i, v in enumerate(versions, 1):
        if not isinstance(v, dict):
            raise Rejected("Version must be JSON object")
        if v.get("id") != "T" + str(i):
            raise Rejected("Treatment IDs not in requested T1..TN order")
        clips = v.get("segments")
        if not isinstance(clips, list) or not clips:
            raise Rejected("Treatment has no source clips")
        total = 0.
        outclips = []
        for c in clips:
            if not isinstance(c, dict) or c.get("shot_id") not in shots:
                raise Rejected("Unknown source shot")
            source = shots[c["shot_id"]]
            offset, duration = c.get("offset_seconds", 0), c.get("duration_seconds")
            if not isinstance(offset, (int,float)) or not isinstance(duration,(int,float)):
                raise Rejected("Invalid clip timing")
            if not (offset >= 0 and duration > 0 and
                    offset + duration <= source["duration_seconds"] + 0.00001):
                raise Rejected("Clip outside actual source interval")
            if len(str(c.get("caption",""))) > 240:
                raise Rejected("Oversized text")
            proposals = c.get("proposed_operations", [])
            if not isinstance(proposals,list) or len(proposals) > 100:
                raise Rejected("Malformed operations or excessive execution cost")
            for op in proposals:
                if not isinstance(op,dict) or not isinstance(op.get("name"),str):
                    raise Rejected("Malformed proposed operation")
            total += duration
            outclips.append(dict(c,source_start_seconds=source["start_seconds"]+offset))
        if total > cfg["budget"]["max_timeline_seconds_per_treatment"]:
            raise Rejected("Duration exceeds current rendering budget")
        validated.append({"id":v["id"],"name":str(v.get("name",""))[:100],
                          "hook":str(v.get("hook",""))[:500],
                          "narrative":str(v.get("narrative",""))[:2000],
                          "emotional_arc":str(v.get("emotional_arc",""))[:600],
                          "duration_seconds":round(total,3),"segments":outclips})
    return validated


def plan_operations(validated, registry):
    """Classify proposals; never pass unverified model ops into an executor."""
    byname = {v["name"]:v for v in registry.get("operations",[])}
    accepted, deferred = [], []
    for version in validated:
        for shot in version["segments"]:
            for op in shot.get("proposed_operations", []):
                name=op["name"]
                item={"version":version["id"],"shot_id":shot["shot_id"],
                      "name":name,"parameters":op.get("parameters",{})}
                meta=byname.get(name)
                if meta and meta.get("status") == "verified":
                    if not isinstance(item["parameters"], dict):
                        raise Rejected("Tool argument type wrong")
                    # Operation-level adapter must separately validate real invocation.
                    accepted.append(item)
                else:
                    deferred.append(dict(item,reason=
                        "no_verified_adapter" if not meta else meta.get("status")))
    return {"verified_operation_proposals":accepted,"deferred_operations":deferred,
            "execution_ready":len(deferred)==0,
            "shell_commands_executed":0,"rendered":False,"published":False}


def call_groq_vision(cfg, frame_path, prompt, key, model=None, client=None):
    """Groq-only multimodal frame caption: never log images, keys or model output."""
    if not key:raise Rejected("Missing Groq key")
    m=model or models_for_task(cfg,"shot_visual_analysis")[0]
    if m.get("provider")!="groq" or m.get("model")!="qwen/qwen3.8-27b":
        raise Rejected("Unapproved Groq vision model")
    frame=Path(frame_path)
    if not frame.is_file() or not 100<=frame.stat().st_size<=250000:
        raise Rejected("Invalid or oversized private vision frame")
    if not isinstance(prompt,str) or not 10<=len(prompt)<=1500:
        raise Rejected("Invalid bounded vision prompt")
    if client is None:
        from groq import Groq
        client=Groq(api_key=key,timeout=40,max_retries=0)
    payload={
       "model":m["model"],
       "messages":[{"role":"user","content":[
          {"type":"text","text":prompt},
          {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,"+base64.b64encode(frame.read_bytes()).decode("ascii")}}
       ]}],
       "temperature":m.get("temperature",0.2),
       "max_completion_tokens":m.get("max_completion_tokens",350)
    }
    if m.get("reasoning_effort"):
        payload["reasoning_effort"]=m["reasoning_effort"]
    out=client.chat.completions.create(**payload)
    message=(out.choices[0].message.content or "").strip()
    if len(message)<8:raise Rejected("Groq vision produced no grounded description")
    return re.sub(r"[\\r\\n]+"," ",message)[:300]


def call_groq(cfg, prompt, key, model=None, client=None):
    if not key:
        raise Rejected("Missing Groq key")
    m = model or cfg["models"]["creative"][0]
    if m.get("provider") != "groq":
        raise Rejected("Live call adapter currently supports Groq only")
    if client is None:
        from groq import Groq
        client=Groq(api_key=key,timeout=70,max_retries=0)
    kwargs={
       "model":m["model"],
       "messages":[
          {"role":"system","content":"Original creative director. Ground every shot. Return valid JSON only."},
          {"role":"user","content":prompt}],
       "temperature":m.get("temperature",0.85),
       "max_completion_tokens":m.get("max_completion_tokens",4700),
       "response_format":{"type":"json_object"},
    }
    if m.get("reasoning_effort"):
        kwargs["reasoning_effort"]=m["reasoning_effort"]
    r=client.chat.completions.create(**kwargs)
    text=r.choices[0].message.content
    if not text:
        raise Rejected("Empty creative director output")
    return json.loads(text)


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",default=str(ROOT/"v5_config.json"))
    ap.add_argument("--registry",default=str(ROOT/"capability_registry.json"))
    ap.add_argument("--shots",required=True)
    ap.add_argument("--brand",required=True)
    ap.add_argument("--brief",required=True)
    ap.add_argument("--versions",type=int,default=None)
    ap.add_argument("--profile",default="private_preview")
    ap.add_argument("--output",required=True)
    ap.add_argument("--live-groq",action="store_true")
    ap.add_argument("--authorize-external-shot-metadata",action="store_true")
    args=ap.parse_args(argv)
    try:
        cfg,reg=load_system(args.config,args.registry)
        shots_manifest=read_json(args.shots)
        shots=validate_source(shots_manifest,cfg)
        count=validate_brief_versions(args.versions or cfg["creative"]["default_treatments"],cfg)
        brand=Path(args.brand).read_text(encoding="utf-8")
        prompt=build_director_prompt(cfg,shots,brand,args.brief,count,args.profile)
        result={"engine":"Reel Engine V5","status":"preflight",
                "source_provenance":shots_manifest["provenance"],
                "models":{k:[x["model"] for x in cfg["models"][k]] for k in cfg["models"]},
                "registered_tools":[a["id"] for a in reg["adapters"]],
                "requested_treatments":count,"profile":args.profile,
                "user_media_uploaded":False,"rendered":False,"published":False,"music_policy":"existing_openly_licensed_only_no_composition"}
        if args.live_groq:
            required_clearance(shots_manifest,external=True)
            if not args.authorize_external_shot_metadata:
                raise Rejected("Owner must authorize metadata leaving the trusted host")
            data=call_groq(cfg,prompt,os.environ.get("GROQ_API_KEY",""))
            validated=validate_plan(data,shots,count,cfg)
            result["status"]="planned_unrendered"
            result["concepts"]=validated
            result["operation_report"]=plan_operations(validated,reg)
            result["director_model_used"]=cfg["models"]["creative"][0]["model"]
            result["source_descriptions_sent_to_groq"]=True
        else:
            result["source_descriptions_sent_to_groq"]=False
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps({"status":result["status"],"treatments":count,
                          "output":str(output),"rendered":False,"published":False}))
        return 0
    except (Rejected,ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)[:220]}),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
