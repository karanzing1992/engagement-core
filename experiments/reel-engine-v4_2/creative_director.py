#!/usr/bin/env python3
"""Reel Engine V4.2: Groq 120B creative direction -> Groq 20B edit compiler.

Consumes *attested shot metadata*, not raw video. Generates safe JSON EDL only.
Does not render, publish, execute shell model output, upload or alter media.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

CREATIVE_MODEL = "openai/gpt-oss-120b"
EXEC_MODEL = "openai/gpt-oss-20b"
VALID_TRANSITIONS = {"cut", "dissolve", "fade"}


class ContractError(ValueError):
    pass


def require_shots(data):
    if data.get("provenance") not in {"human_reviewed", "gemini_human_reviewed"}:
        raise ContractError("Shot manifest requires explicit human review attestation")
    shots = data.get("shots")
    if not isinstance(shots, list) or not 2 <= len(shots) <= 60:
        raise ContractError("Need between 2 and 60 verified source shots")
    result = {}
    for s in shots:
        if not isinstance(s, dict):
            raise ContractError("Invalid source shot")
        sid = s.get("id")
        if not isinstance(sid, str) or not (1 <= len(sid) <= 32) or sid in result:
            raise ContractError("Shot IDs missing, duplicate, or malformed")
        start, length = s.get("start_seconds"), s.get("duration_seconds")
        if not isinstance(start, (int, float)) or not isinstance(length, (int, float)):
            raise ContractError("Source timing missing")
        if not (0 <= start < 3600 and 0.75 <= length <= 100 and start + length <= 3600):
            raise ContractError("Source timing out of bounds")
        desc = s.get("visible_description")
        if not isinstance(desc, str) or not 4 <= len(desc) <= 320:
            raise ContractError("Visible description missing")
        result[sid] = {"id": sid, "start": float(start),
                       "duration": float(length), "visible": desc}
    return result


def check_concepts(plan, shots):
    versions = plan.get("versions")
    if not isinstance(versions, list) or len(versions) != 3:
        raise ContractError("Director must produce exactly A/B/C treatments")
    out = []
    for expected, version in zip("ABC", versions):
        if version.get("id") != expected:
            raise ContractError("Concept IDs must be A,B,C")
        segments = version.get("segments")
        if not isinstance(segments, list) or not 5 <= len(segments) <= 15:
            raise ContractError("Every treatment needs 5..15 segments")
        duration = 0
        for clip in segments:
            sid, d = clip.get("shot_id"), clip.get("duration_seconds")
            if sid not in shots or not isinstance(d, (int, float)):
                raise ContractError("Unknown shot or clip duration")
            if not 0.75 <= d <= min(shots[sid]["duration"], 6.0):
                raise ContractError("Clip exceeds grounded shot")
            if len(str(clip.get("caption", ""))) > 55:
                raise ContractError("On-screen text too long")
            duration += d
        if not 14 <= duration <= 40:
            raise ContractError("Reel duration out of bounds")
        out.append({"id": expected, "name": str(version.get("name", ""))[:60],
                    "narrative": str(version.get("narrative", ""))[:500],
                    "hook": str(version.get("hook", ""))[:180],
                    "segments": segments, "duration_seconds": round(duration, 2)})
    return out


def compile_edl(concepts, shots):
    """Deterministic fail-safe EDL while the optional 20B compiler is not trusted."""
    result = []
    for v in concepts:
        timeline = []
        cursor = 0.0
        for c in v["segments"]:
            s = shots[c["shot_id"]]
            dur = float(c["duration_seconds"])
            timeline.append({"op": "place", "shot_id": s["id"],
                             "timeline_start_seconds": round(cursor, 3),
                             "source_start_seconds": s["start"],
                             "duration_seconds": dur,
                             "caption": c.get("caption", ""),
                             "transition": "cut"})
            cursor += dur
        result.append({"id": v["id"], "duration_seconds": round(cursor, 2),
                       "commands": timeline})
    return result


def _call_groq(client, model, prompt, temperature, tokens=4500):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content":
                   "You are a brilliant creative director and accurate video-edit planner. "
                   "Respect footage truth, consent, brand identity and exact JSON contract."},
                  {"role": "user", "content": prompt}],
        temperature=temperature, response_format={"type": "json_object"},
        max_completion_tokens=tokens)
    raw = response.choices[0].message.content
    if not raw:
        raise ContractError("Model returned empty response")
    return json.loads(raw)


def run_director(shots, brand, brief, key, *, client=None):
    if not key:
        raise ContractError("Groq key missing")
    if client is None:
        from groq import Groq
        client = Groq(api_key=key, timeout=65, max_retries=0)
    source = [{"id":s["id"],"start_seconds":s["start"],
               "duration_seconds":s["duration"],"visible":s["visible"]}
              for s in shots.values()]
    prompt = (
        "Produce EXACTLY 3 substantially different original 15-35 second Instagram "
        "Reel directions A,B,C grounded ONLY in the following verified shots. "
        "Use 5-15 segments per treatment. Every segment is "
        "{shot_id: string, duration_seconds: 0.75..6, caption: <=55 chars}. "
        "Duration can never exceed source shot duration. Use no facts/people/places "
        "not actually present. Each version {id,name,narrative,hook,segments}. "
        "Output JSON object {versions:[...]} in ABC order. No sales claim, no fake "
        "logo or endorsements, and no copyrighted soundtrack. The brand constrains "
        "style, not physical ownership of scenery. Distinguish concepts by order, "
        "hook and narrative, not just overlay text.\nBRAND:\n"
        + brand[:5000] + "\nBRIEF:\n" + brief[:1200] +
        "\nVERIFIED SHOTS:\n" + json.dumps(source, ensure_ascii=False))
    plan = _call_groq(client, CREATIVE_MODEL, prompt, temperature=0.88)
    accepted = check_concepts(plan, shots)
    edl = compile_edl(accepted, shots)
    return {"version": "4.2-candidate", "director_model": CREATIVE_MODEL,
            "editor_model_target": EXEC_MODEL,
            "editor_mode": "deterministic_guarded_compiler",
            "gemini_input": "source-attested shot descriptions",
            "versions": accepted, "edl": edl, "not_rendered": True,
            "not_published": True}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--shots", required=True)
    p.add_argument("--brand", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--live-groq", action="store_true")
    p.add_argument("--authorize-external-shot-metadata", action="store_true")
    args = p.parse_args(argv)
    try:
        shots_path = Path(args.shots)
        brand = Path(args.brand).read_text()
        manifest = json.loads(shots_path.read_text())
        shots = require_shots(manifest)
        if not args.live_groq:
            result = {"version": "4.2-candidate", "preflight": "PASS",
                      "shot_count": len(shots), "media_uploaded": False,
                      "external_requests": 0, "gemini_live_connected": False}
        else:
            if not args.authorize_external_shot_metadata:
                raise ContractError("External source metadata requires owner authorization")
            result = run_director(shots, brand, args.brief, os.environ.get("GROQ_API_KEY", ""))
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
        print(json.dumps({"status": "PASS", "output": str(out),
                          "mode": "groq120" if args.live_groq else "offline",
                          "published": False}))
        return 0
    except (ContractError, ValueError, OSError) as ex:
        print(json.dumps({"status": "BLOCKED", "reason": str(ex)[:180]}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
