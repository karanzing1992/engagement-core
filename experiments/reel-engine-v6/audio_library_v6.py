#!/usr/bin/env python3
"""V6 reusable open-audio library: licensed original recordings -> FilmCraft only.

Reuses V5 Openverse/Wikimedia metadata discovery and evidence checks, but NEVER
calls its legacy ffmpeg/ffprobe mix/ingest functions. Discovery != legal approval.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "reel-engine-v5" / "music_provider.py"
SHA256 = re.compile(r"^[a-f0-9]{64}$")
AUDIO_EXT = {".wav", ".flac", ".mp3", ".ogg", ".m4a", ".opus"}


class AudioBlocked(ValueError):
    pass


def library():
    if not LEGACY.is_file():
        raise AudioBlocked("Existing open-license audio discovery library missing")
    spec = importlib.util.spec_from_file_location("mad_v6_reused_openverse", LEGACY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover(query: str, *, limit: int = 6, provider: str = "auto") -> dict:
    """Only metadata and candidate links; no media downloads or rights assertion."""
    base = library()
    try:
        found = base.search(query, limit=limit, provider=provider)
    except (base.LicenseError, ValueError, OSError) as exc:
        raise AudioBlocked("Audio catalog search unavailable") from exc
    return {"source": "existing_v5_open_library", "provider": found["provider"],
            "candidates": found["candidates"], "rights_verified": False,
            "music_downloaded": False, "editor": "FilmCraft"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def admit(track: dict, evidence: dict, audio_path: Path, expected_sha256: str) -> dict:
    """Use only an independently reviewed track and a locally supplied audio file.

    Duration/codec must subsequently pass FilmCraft native mediaBrowser.probe;
    no secondary media editor or shell probe is allowed.
    """
    base = library()
    if not isinstance(track, dict) or not isinstance(evidence, dict):
        raise AudioBlocked("Track and independent license record required")
    if track.get("source") != "Openverse":
        raise AudioBlocked("Track must come from existing approved discovery adapter")
    if track.get("license") not in {"by", "cc0", "pdm"}:
        raise AudioBlocked("Commercial redistribution/editing license unverified")
    if not isinstance(expected_sha256, str) or not SHA256.fullmatch(expected_sha256):
        raise AudioBlocked("Approved music SHA256 required")
    path = Path(audio_path)
    if (not path.is_file() or path.is_symlink() or path.suffix.lower() not in AUDIO_EXT
            or not 1024 <= path.stat().st_size <= 60 * 1024 * 1024):
        raise AudioBlocked("Approved local soundtrack asset missing or outside size/type limits")
    if file_sha256(path) != expected_sha256:
        raise AudioBlocked("Music SHA256 differs from reviewed source")
    try:
        # V5 library contains reusable metadata/evidence checks only.
        base.read_evidence_record = None  # No legacy media editing or network calls.
        # read_evidence expects an evidence JSON file, so we check equivalent fields here.
        if evidence.get("reviewer_confirmed_rights") is not True:
            raise AudioBlocked("Independent reviewer must approve recording")
        for source_key, evidence_key in (
            ("id", "track_id"),
            ("original_source_page", "original_source_page"),
            ("license_url", "license_url"),
        ):
            if track.get(source_key) != evidence.get(evidence_key):
                raise AudioBlocked("Music provenance does not match reviewed catalog item")
        if not base.is_https(evidence.get("source_license_proof_url", "")):
            raise AudioBlocked("Original source license proof URL missing")
        if not isinstance(evidence.get("reviewed_by"), str) or len(evidence["reviewed_by"]) < 2:
            raise AudioBlocked("Reviewer identity required")
        if not isinstance(evidence.get("reviewed_on"), str) or len(evidence["reviewed_on"]) < 10:
            raise AudioBlocked("Review date required")
        if track["license"] == "by" and evidence.get("attribution_approved") is not True:
            raise AudioBlocked("CC BY track requires approved attribution")
        if not (base.is_https(track.get("original_source_page", ""))
                and base.is_https(track.get("license_url", ""))):
            raise AudioBlocked("Original source URLs invalid")
    except (TypeError, KeyError) as exc:
        raise AudioBlocked("Incomplete independent music clearance") from exc
    label = {"by": "CC BY", "cc0": "CC0", "pdm": "PDM"}[track["license"]]
    return {
        "mode": "licensed_original_recording",
        "audio_file": str(path.resolve()),
        "audio_sha256": expected_sha256,
        "filmcraft_rights": {
            "human_verified": True, "license": label,
            "creator": track["original_source_page"],
            "creator_name": track.get("creator", ""),
            "original_source_url": track["original_source_page"],
            "original_license_url": track["license_url"],
            "verified_on": evidence["reviewed_on"],
            "verified_by": evidence["reviewed_by"],
        },
        "credits": {
            "title": track.get("title"), "creator": track.get("creator"),
            "original_source": track["original_source_page"],
            "license": track["license_url"],
            "attribution_required": track["license"] == "by",
        },
        "filmcraft_native_audio_probe_required": True,
        "filmcraft_native_audio_mix_required": True,
        "ffmpeg_fallback": False,
        "license_verified": True,
        "published": False,
    }


def resolve_audio(mode: str, *, track=None, evidence=None, audio_path=None, sha256=None):
    if mode == "source_ambience_only":
        return {"mode": mode, "licensed_track": False, "music_required": False}
    if mode != "licensed_music":
        raise AudioBlocked("Unsupported audio mode; music cannot be silently omitted")
    if not all(x is not None for x in (track, evidence, audio_path, sha256)):
        raise AudioBlocked("Requested soundtrack needs approved file, provenance and SHA")
    result = admit(track, evidence, Path(audio_path), sha256)
    result["music_required"] = True
    return result


if __name__ == "__main__":
    print(json.dumps({"component": "openverse_wikimedia_reuse", "editor": "FilmCraft",
                      "license_gate": "enforced", "downloads": False, "mix_called": False}))
