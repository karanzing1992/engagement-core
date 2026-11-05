#!/usr/bin/env python3
"""MAD Reel Engine V6 source-only contracts.

Model results are proposals, not evidence that a FilmCraft effect was executed.
This module never edits media, sends inference, publishes, or changes V5 routing.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHOT_ID = re.compile(r"^[A-Za-z0-9_-]{1,48}$")


class V6Blocked(ValueError):
    """Fail closed on unsafe or unverified creative work."""


def read_config(path: Path = HERE / "v6_config.json") -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    check_config(data)
    return data


def check_config(c: dict) -> None:
    if c.get("version") != "6.0.0-dev" or c.get("release_status") != "source_only_no_production_switch":
        raise V6Blocked("V6 must remain isolated from V5 production until certified")
    p, roles, editor, delivery = (c.get(k, {}) for k in
                                  ("provider_policy", "model_roles", "editor", "delivery"))
    if p.get("mode") != "gemini_plus_groq" or p.get("gemini_auth") != "GEMINI_API_KEY":
        raise V6Blocked("Gemini-first API key routing missing")
    if p.get("gemini_model_selection") != "highest_available_pro_generateContent_from_live_model_list":
        raise V6Blocked("Gemini Pro must be selected from the actual key's available models")
    if p.get("groq_auth") != "REEL_ENGINE_KEY" or p.get("allow_paid_inference") is not False:
        raise V6Blocked("Existing server-side Groq key and no-paid-inference rules required")
    if p.get("external_media_requires_explicit_owner_consent") is not True:
        raise V6Blocked("External source consent mandatory")
    if p.get("cross_provider_fallback") is not False:
        raise V6Blocked("Unapproved cross-provider fallback forbidden")
    expected = {
        "research": ("gemini", "discover_pro_model_at_runtime"),
        "creative_director": ("groq", "openai/gpt-oss-120b"),
        "editor_feasibility_reviewer": ("groq", "openai/gpt-oss-20b"),
    }
    for role, (provider, model) in expected.items():
        r = roles.get(role, {})
        if (r.get("provider"), r.get("model")) != (provider, model):
            raise V6Blocked("Required model role order/provider changed: " + role)
    if roles["research"].get("allow_flash_fallback") is not False:
        raise V6Blocked("Do not silently downgrade Gemini Pro")
    if editor.get("provider") != "FilmCraft" or editor.get("version") != "0.16.0":
        raise V6Blocked("Pinned FilmCraft editor required")
    if not SHA256.fullmatch(editor.get("linux_x86_64_archive_sha256", "")):
        raise V6Blocked("FilmCraft archive integrity pin missing")
    for flag in ("no_ffmpeg_or_ffprobe", "no_alternative_render_fallback",
                 "effect_receipts_required", "zero_silent_effect_omissions"):
        if editor.get(flag) is not True:
            raise V6Blocked("Editor-only guarantee absent: " + flag)
    if (delivery.get("private_only") is not True or
            delivery.get("publish_automatically") is not False or
            delivery.get("default_runtime_version") != "v5" or
            delivery.get("source_consent_required") is not True or
            delivery.get("music_mode") != "verified_existing_recordings_only" or
            delivery.get("output_profile") != {"width": 1080, "height": 1920}):
        raise V6Blocked("Private preview, source rights, music or V5 rollback changed")


def pro_models(list_models_response: dict) -> list[str]:
    """Discover supported Pro generation models. This does not verify billing."""
    models = []
    if not isinstance(list_models_response, dict):
        raise V6Blocked("Gemini model-list response malformed")
    for item in list_models_response.get("models", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        methods = item.get("supportedGenerationMethods", [])
        if (isinstance(name, str) and name.startswith("models/gemini-") and
                "-pro" in name.lower() and isinstance(methods, list) and
                "generateContent" in methods):
            models.append(name.removeprefix("models/"))
    # Prefer higher numeric family/version; previews remain candidates, not certified.
    def sortkey(model: str):
        numeric = tuple(int(x) for x in re.findall(r"\d+", model)[:3])
        # Prefer general-purpose Pro over specialized customtools/image/audio models.
        specialized = any(s in model for s in
                          ("customtools", "image", "audio", "tts", "robotics", "embedding"))
        return (not specialized, numeric, "preview" not in model, model)
    return sorted(set(models), key=sortkey, reverse=True)


def select_pro_model(list_models_response: dict, *, approved_model: str | None = None) -> str:
    candidates = pro_models(list_models_response)
    if approved_model:
        if approved_model not in candidates:
            raise V6Blocked("Owner-selected Pro model not available on this API key")
        return approved_model
    if not candidates:
        raise V6Blocked("No Pro generateContent model found; no silent Flash downgrade")
    return candidates[0]


def validate_source_manifest(manifest: dict, *, external_gemini_frames: bool) -> dict:
    if not isinstance(manifest, dict):
        raise V6Blocked("Source manifest required")
    digest = manifest.get("source_sha256", "")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise V6Blocked("Private source hash missing")
    if manifest.get("human_reviewed") is not True:
        raise V6Blocked("Human reviewed source required")
    if manifest.get("rights_and_consent_cleared") is not True:
        raise V6Blocked("Footage and people rights gate has not passed")
    if external_gemini_frames and manifest.get("external_ai_processing_consent") is not True:
        raise V6Blocked("Explicit external AI image processing consent required")
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not 1 <= len(shots) <= 64:
        raise V6Blocked("One to sixty-four verified source shots required")
    seen = set()
    for shot in shots:
        if not isinstance(shot, dict):
            raise V6Blocked("Malformed source shot")
        sid = shot.get("id")
        if not isinstance(sid, str) or not SHOT_ID.fullmatch(sid) or sid in seen:
            raise V6Blocked("Duplicate/invalid shot ID")
        seen.add(sid)
        start, duration = shot.get("start_seconds"), shot.get("duration_seconds")
        if type(start) not in (int, float) or type(duration) not in (int, float):
            raise V6Blocked("Actual source timestamps required")
        if not (0 <= start <= 3600 and 0.4 <= duration <= 120 and start + duration <= 3600):
            raise V6Blocked("Source shot out of bounds")
        if not isinstance(shot.get("visible"), str) or len(shot["visible"].strip()) < 5:
            raise V6Blocked("Grounded shot observation required")
    return manifest


def validate_effect_receipts(requested: list[dict], executed: list[dict]) -> dict:
    """Require a unique native-command receipt AND independent output check per op.

    Command receipts alone do not prove that a user-visible effect was rendered.
    Caller must populate output_verified only after inspecting resulting frames/audio.
    """
    if not isinstance(requested, list) or not isinstance(executed, list):
        raise V6Blocked("Effect ledgers must be lists")
    if not 0 <= len(requested) <= 128:
        raise V6Blocked("Effect count exceeds admitted job scope")
    requested_ids = [r.get("id") for r in requested if isinstance(r, dict)]
    if len(requested_ids) != len(requested) or any(
            not isinstance(x, str) or not SHOT_ID.fullmatch(x) for x in requested_ids):
        raise V6Blocked("Malformed creative effect IDs")
    if len(set(requested_ids)) != len(requested_ids):
        raise V6Blocked("Duplicate effect request ID")
    if len(executed) != len(requested):
        raise V6Blocked("Missing or extra effect receipts")
    by_id = {}
    for receipt in executed:
        if not isinstance(receipt, dict) or receipt.get("id") in by_id:
            raise V6Blocked("Duplicate/malformed native effect receipt")
        by_id[receipt.get("id")] = receipt
    if set(by_id) != set(requested_ids):
        raise V6Blocked("Effects were omitted or substituted")
    incomplete = []
    for effect_id in requested_ids:
        receipt = by_id[effect_id]
        if (receipt.get("status") != "applied" or
                not isinstance(receipt.get("filmcraft_command"), str) or
                not receipt["filmcraft_command"].strip() or
                receipt.get("native_command_ok") is not True or
                receipt.get("output_verified") is not True):
            incomplete.append(effect_id)
    if incomplete:
        raise V6Blocked("Creative completeness unverified: " + ", ".join(incomplete[:10]))
    return {"requested": len(requested_ids), "verified_applied": len(requested_ids),
            "omitted": 0, "creative_complete": True,
            "technical_only": True, "owner_artistic_approval": False}


if __name__ == "__main__":
    c = read_config()
    print(json.dumps({"version": c["version"], "configuration": "PASS",
                      "production_modified": False, "provider_policy": c["provider_policy"]["mode"],
                      "editor": c["editor"]["provider"],
                      "live_api_checked": False}))
