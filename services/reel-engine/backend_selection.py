"""Moksha/MAD FFmpeg-only backend admission (non-destructive migration gate).

This policy has no network access, does not mutate production, and preserves
historical renderer implementations for read-only archaeology/rollback.
"""
from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
POLICY_FILE = HERE / "backend_policy.json"


class UnsupportedRenderer(ValueError):
    """An unsupported, retired or ambiguous renderer was requested."""


def load_policy(path: Path = POLICY_FILE) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("policy_version") != "1.0" or data.get("default_renderer") != "ffmpeg":
        raise UnsupportedRenderer("FFMPEG_POLICY_MISSING_OR_INVALID")
    if data.get("renderer_mode") != "exclusive":
        raise UnsupportedRenderer("FFMPEG_EXCLUSIVE_MODE_REQUIRED")
    if data.get("automatic_publish") is not False:
        raise UnsupportedRenderer("PUBLISH_PERMISSION_NOT_GRANTED")
    retired = data.get("deprecated_renderers")
    if not isinstance(retired, list) or not {"filmcraft", "gstreamer", "mlt", "frei0r"}.issubset(set(retired)):
        raise UnsupportedRenderer("DEPRECATED_RENDERER_LIST_INCOMPLETE")
    return data


def select_renderer(requested: str | None = None, *, policy: dict | None = None) -> dict:
    """Refuse legacy renderers, even when a caller supplies an alias/override."""
    p = load_policy() if policy is None else policy
    if p.get("default_renderer") != "ffmpeg" or p.get("renderer_mode") != "exclusive":
        raise UnsupportedRenderer("FFMPEG_POLICY_MISSING_OR_INVALID")
    if p.get("automatic_publish") is not False:
        raise UnsupportedRenderer("PUBLISH_PERMISSION_NOT_GRANTED")
    chosen = (requested or p["default_renderer"]).lower().strip()
    if chosen not in ("ffmpeg", "ffmpeg-cli"):
        raise UnsupportedRenderer("RENDERER_DEPRECATED_OR_NOT_SUPPORTED")
    return {"engine": "ffmpeg", "probe": "ffprobe", "automatic_publish": False,
            "ffmpeg_required": True, "legacy_editor_fallback": False}


def validate_receipt(receipt: dict, *, policy: dict | None = None) -> dict:
    p = load_policy() if policy is None else policy
    chosen = select_renderer(receipt.get("engine"), policy=p)
    if receipt.get("video_stream_verified") is not True:
        raise UnsupportedRenderer("VIDEO_STREAM_NOT_VERIFIED")
    if receipt.get("audio_stream_verified") is not True:
        raise UnsupportedRenderer("AUDIO_STREAM_NOT_VERIFIED")
    if receipt.get("full_decode_passed") is not True:
        raise UnsupportedRenderer("OUTPUT_DECODE_NOT_VERIFIED")
    if receipt.get("published") is not False:
        raise UnsupportedRenderer("UNAUTHORIZED_PUBLICATION")
    return {**chosen, "media_technically_verified": True}
