#!/usr/bin/env python3
"""MAD V7 automatic soundtrack decision, reusing V5/V6 cleared audio.

Openverse/Wikimedia is the V5 discovery source. This selector is deliberately
limited to recordings already admitted to the owner's private V6 reviewed-music
vault; Openverse search metadata is NEVER approval or downloadable render media.
AI chooses a SHA from the eligible catalog, not an external URL or FFmpeg command.
"""
from __future__ import annotations

import json
import re

SHA = re.compile(r"^[a-f0-9]{64}$")
MIMES = frozenset(("audio/mpeg", "audio/wav", "audio/ogg", "audio/flac", "audio/mp4"))
LICENSES = frozenset(("cc0", "pdm", "by"))
MAX_TRACKS = 24
MAX_BYTES = 4 * 1024 * 1024


def eligible(records: object) -> list[dict]:
    """Bound the owner-private list; require reviewer evidence, not catalog claims."""
    if not isinstance(records, list):
        return []
    approved = {}
    for item in records[:MAX_TRACKS]:
        if not isinstance(item, dict):
            continue
        track = item.get("track")
        evidence = item.get("evidence")
        digest = item.get("sha256")
        if not isinstance(track, dict) or not isinstance(evidence, dict):
            continue
        if (not isinstance(digest, str) or not SHA.fullmatch(digest)
            or type(item.get("bytes")) is not int
            or not 1024 <= item["bytes"] <= MAX_BYTES
            or item.get("mime") not in MIMES
            or track.get("source") != "Openverse"
            or track.get("license") not in LICENSES
            or track.get("id") != evidence.get("track_id")
            or track.get("original_source_page") != evidence.get("original_source_page")
            or track.get("license_url") != evidence.get("license_url")
            or evidence.get("reviewer_confirmed_rights") is not True
            or not str(evidence.get("source_license_proof_url") or "").startswith("https://")
            or not str(evidence.get("reviewed_by") or "").strip()
            or not str(evidence.get("reviewed_on") or "").strip()
            or (track.get("license") == "by" and evidence.get("attribution_approved") is not True)):
            continue
        approved[digest] = item
    return list(approved.values())


def rank(candidates: list[dict], brief: str, hook: str) -> list[dict]:
    """Deterministic backup only; the primary creative decision uses Groq 120B."""
    query = set(re.findall(r"[a-z]{3,}", ((brief or "") + " " + (hook or "")).lower()))
    scores = []
    for item in candidates:
        track = item["track"]
        words = set(re.findall(r"[a-z]{3,}", str(track.get("title", ""))[:200].lower()))
        tags = track.get("tags") or []
        if isinstance(tags, list):
            words.update(w for t in tags[:10] for w in re.findall(r"[a-z]{3,}", str(t)[:45].lower()))
        score = len(words & query)
        scores.append((-score, str(track.get("title", "")), item["sha256"], item))
    return [x[3] for x in sorted(scores)]


def choose(records: object, brief: str, hook: str, groq_call, *, guidance: str = "") -> tuple[list[dict], dict]:
    """AI must return an exact eligible SHA; invalid output cannot inject media."""
    candidates = eligible(records)
    if not candidates:
        return [], {"state": "no_reviewed_tracks", "selection": "none", "candidates": 0}
    default = rank(candidates, brief, hook)
    choices = [{
        "sha256": t["sha256"],
        "title": str(t["track"].get("title", ""))[:120],
        "creator": str(t["track"].get("creator", ""))[:90],
        "license": t["track"]["license"],
        "tags": t["track"].get("tags", [])[:8] if isinstance(t["track"].get("tags"), list) else [],
    } for t in default]
    prompt = (
        "You are a cinematic soundtrack curator. Select ONE existing, HUMAN-CREATED "
        "pre-cleared soundtrack that fits the footage and editorial pacing. "
        "Reply ONLY with JSON of the form {\"sha256\": \"exact-listed-sha\"}. "
        "Never invent a track, imply new rights approval, or request a download. "
        "If the brief involves spoken interviews, choose gentle, non-intrusive music. "
        "No music composition or synthetic audio. "
        "Owner brief: " + (brief or "")[:650] +
        " Approved edit hook: " + (hook or "")[:100] +
        " ALLOWLIST: " + json.dumps(choices, ensure_ascii=True, separators=(",", ":"))
    )
    # Strict schema constrains model output to already-reviewed private SHA IDs;
    # the model cannot invent a media URL or self-grant an external license.
    response_format = {"type": "json_schema", "json_schema": {
        "name": "mad_v7_reviewed_music_choice", "strict": True,
        "schema": {"type": "object", "properties": {
            "sha256": {"type": "string", "enum": [c["sha256"] for c in choices]}},
            "required": ["sha256"], "additionalProperties": False}}}
    try:
        result = groq_call("openai/gpt-oss-120b", prompt, temperature=0.1,
                           max_tokens=640, response_format=response_format)
        chosen = result.get("sha256") if isinstance(result, dict) else None
        if isinstance(chosen, str):
            for item in candidates:
                if item["sha256"] == chosen:
                    return [item] + [v for v in default if v["sha256"] != chosen], {
                        "state": "reviewed_track_selected", "selection": "groq_120b",
                        "candidates": len(candidates), "sha256": chosen
                    }
    except Exception:
        # Previously admitted recordings remain safe for deterministic fallback;
        # never bypass the prior independent rights evidence gate.
        pass
    return default, {"state": "reviewed_track_selected", "selection": "deterministic_fallback",
                     "candidates": len(candidates), "sha256": default[0]["sha256"]}
