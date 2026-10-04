from __future__ import annotations

import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import librosa
import numpy as np

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
ALLOWED_LICENSES = {
    "owned",
    "original",
    "cc0",
    "public-domain",
    "royalty-free-commercial",
    "licensed-commercial",
}


def _safe_id(name: str) -> str:
    stem = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    return "-".join(filter(None, stem.split("-")))[:72] or "track"


def _track_id(path: Path) -> str:
    digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:10]
    return f"{_safe_id(path.stem)}-{digest}"


def _analyze_audio(path: Path) -> dict:
    y, sr = librosa.load(path, sr=22050, mono=True, duration=120)
    if y.size == 0:
        raise ValueError("Audio file contains no decodable samples")

    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, _ = librosa.beat.beat_track(onset_envelope=onset, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0

    rms = float(np.mean(librosa.feature.rms(y=y)))
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))

    # Relative features are intentionally coarse: metadata tags remain authoritative.
    energy = min(1.0, max(0.0, rms * 8.0))
    brightness = min(1.0, max(0.0, centroid / 5000.0))
    rhythmic = min(1.0, max(0.0, zcr * 8.0))

    inferred: list[str] = []
    if energy < 0.28:
        inferred += ["calm", "serene", "ambient"]
    elif energy < 0.52:
        inferred += ["warm", "organic", "balanced"]
    else:
        inferred += ["energetic", "upbeat"]

    if brightness < 0.42:
        inferred += ["soft", "earthy"]
    elif brightness > 0.68:
        inferred += ["bright", "fresh"]

    if 82 <= bpm <= 118 and energy < 0.55:
        inferred += ["wellness", "premium", "cinematic"]
    if 96 <= bpm <= 126 and rhythmic > 0.25:
        inferred += ["reels", "social"]

    return {
        "bpm": round(bpm, 3),
        "duration": round(float(librosa.get_duration(y=y, sr=sr)), 3),
        "energy": round(energy, 4),
        "brightness": round(brightness, 4),
        "rhythmic": round(rhythmic, 4),
        "inferred_tags": sorted(set(inferred)),
    }


def _license_ok(meta: dict, platform: str | None = None) -> bool:
    if not meta.get("commercial_use", False):
        return False
    if str(meta.get("license", "")).strip().lower() not in ALLOWED_LICENSES:
        return False

    expires = meta.get("license_expires")
    if expires:
        try:
            exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                return False
        except ValueError:
            return False

    allowed_platforms = meta.get("platforms") or ["all"]
    allowed_platforms = {str(x).lower() for x in allowed_platforms}
    if platform and "all" not in allowed_platforms and platform.lower() not in allowed_platforms:
        return False
    return True


def ingest_track(
    source_path: Path,
    library_root: Path,
    metadata: dict,
) -> dict:
    library_root.mkdir(parents=True, exist_ok=True)

    license_name = str(metadata.get("license", "")).strip().lower()
    if license_name not in ALLOWED_LICENSES:
        raise ValueError(
            "Track must declare an allowed license: "
            + ", ".join(sorted(ALLOWED_LICENSES))
        )
    if not metadata.get("commercial_use", False):
        raise ValueError("commercial_use must be true for automatic Reel selection")

    track_id = metadata.get("id") or _track_id(source_path)
    suffix = source_path.suffix.lower()
    if suffix not in AUDIO_EXTS:
        raise ValueError(f"Unsupported audio extension: {suffix}")

    target = library_root / f"{track_id}{suffix}"
    shutil.copyfile(source_path, target)

    analysis = _analyze_audio(target)
    merged = {
        "id": track_id,
        "file": target.name,
        "title": metadata.get("title") or source_path.stem,
        "artist": metadata.get("artist") or "",
        "license": license_name,
        "commercial_use": True,
        "platforms": metadata.get("platforms") or ["all"],
        "attribution": metadata.get("attribution") or "",
        "license_source": metadata.get("license_source") or "",
        "license_expires": metadata.get("license_expires"),
        "tags": sorted(set(str(x).lower() for x in metadata.get("tags", []))),
        **analysis,
    }
    (library_root / f"{track_id}.json").write_text(
        json.dumps(merged, indent=2),
        encoding="utf-8",
    )
    return merged


def list_tracks(library_root: Path, platform: str | None = None) -> list[dict]:
    library_root.mkdir(parents=True, exist_ok=True)
    tracks: list[dict] = []
    for meta_path in sorted(library_root.glob("*.json")):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            audio_path = library_root / str(meta["file"])
            if not audio_path.exists():
                continue
            if platform and not _license_ok(meta, platform):
                continue
            tracks.append(meta)
        except (ValueError, KeyError, json.JSONDecodeError):
            continue
    return tracks


def rank_tracks(
    library_root: Path,
    *,
    moods: list[str] | None = None,
    target_bpm: float | None = None,
    bpm_min: float | None = None,
    bpm_max: float | None = None,
    platform: str = "instagram",
    limit: int = 5,
) -> list[dict]:
    desired = {str(x).lower() for x in (moods or [])}
    ranked: list[dict] = []

    for meta in list_tracks(library_root, platform=platform):
        bpm = float(meta.get("bpm") or 0.0)
        if bpm_min is not None and bpm < bpm_min:
            continue
        if bpm_max is not None and bpm > bpm_max:
            continue

        tags = {
            *[str(x).lower() for x in meta.get("tags", [])],
            *[str(x).lower() for x in meta.get("inferred_tags", [])],
        }
        overlap = len(desired & tags)

        score = 0.0
        score += overlap * 2.2
        if desired:
            score += (overlap / len(desired)) * 3.0

        if target_bpm and bpm > 0:
            bpm_distance = abs(bpm - target_bpm)
            score += max(0.0, 3.0 - bpm_distance / 8.0)

        # Wellness reels default toward moderate energy if no explicit mood data exists.
        energy = float(meta.get("energy") or 0.0)
        score += max(0.0, 1.5 - abs(energy - 0.34) * 3.0)

        item = dict(meta)
        item["score"] = round(score, 4)
        item["matched_moods"] = sorted(desired & tags)
        item["path"] = str(library_root / str(meta["file"]))
        ranked.append(item)

    ranked.sort(key=lambda x: (-float(x["score"]), x.get("title", "")))
    return ranked[: max(1, int(limit))]


def select_track(library_root: Path, selector: dict) -> dict | None:
    ranked = rank_tracks(
        library_root,
        moods=list(selector.get("moods") or []),
        target_bpm=selector.get("target_bpm"),
        bpm_min=selector.get("bpm_min"),
        bpm_max=selector.get("bpm_max"),
        platform=str(selector.get("platform", "instagram")),
        limit=1,
    )
    return ranked[0] if ranked else None
