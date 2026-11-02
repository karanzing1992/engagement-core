#!/usr/bin/env python3
"""V5 synthetic-only GitHub execution: bounded V5 plan -> owned FFmpeg renderer.

This module never accepts user media, arbitrary URLs/paths, or publish requests.
A synthetic technical pass is NOT real-footage, sound-rights or artistic certification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "services" / "reel-engine"))
from multi_renderer import render_multiple  # noqa: E402
from v5_orchestrator import (Rejected, build_director_prompt, call_groq,
    load_system, plan_operations, read_json, required_clearance,
    validate_plan, validate_source)  # noqa: E402

COLORS = ("#2A5D86", "#395C39", "#916C47", "#B09A4E", "#224C49")


def run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE, text=True, timeout=180)


def fixture_plan():
    return {"versions": [{"id": "T1", "name": "Synthetic diagnostic only",
        "hook": "Technical integration", "narrative": "Not Moksha imagery",
        "emotional_arc": "not artistically reviewed",
        "segments": [
            {"shot_id": sid, "offset_seconds": 0, "duration_seconds": 2,
             "caption": "", "proposed_operations": []}
            for sid in ("S1", "S2", "S3")]}]}


def compile_edl(segments, ids):
    """No silent removal of model-suggested operations or timeline truncation."""
    if not 1 <= len(segments) <= 16:
        raise Rejected("Existing multi_renderer only supports 1-16 cuts")
    index = {sid: i for i, sid in enumerate(ids)}
    result = []
    for segment in segments:
        if segment.get("proposed_operations"):
            raise Rejected("Uncertified proposed effect may not be silently dropped")
        if segment["shot_id"] not in index:
            raise Rejected("Unknown source shot")
        result.append({"source_index": index[segment["shot_id"]],
                       "start": segment["offset_seconds"],
                       "seconds": segment["duration_seconds"], "loop": False})
    return result


def create_synthetic_sources(folder, shots):
    paths = []
    for i, shot in enumerate(shots.values()):
        path = folder / ("synthetic-%02d.mp4" % i)
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", "color=c=%s:s=320x180:r=15" % COLORS[i % len(COLORS)],
             "-t", str(shot["duration_seconds"]), "-c:v", "libx264",
             "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", str(path)])
        paths.append(path)
    return paths


def verify_video(path, width, height, fps):
    raw = subprocess.check_output(["ffprobe", "-v", "error",
        "-show_format", "-show_streams", "-of", "json", str(path)], text=True, timeout=30)
    parsed = json.loads(raw)
    video = next(s for s in parsed["streams"] if s.get("codec_type") == "video")
    audio = next((s for s in parsed["streams"] if s.get("codec_type") == "audio"), None)
    if (video.get("codec_name"), video.get("pix_fmt"), video.get("width"),
            video.get("height")) != ("h264", "yuv420p", width, height):
        raise Rejected("Synthetic technical output profile mismatch")
    if not audio or audio.get("codec_name") != "aac":
        raise Rejected("AAC stream missing from private synthetic test")
    numerator, denominator = (int(x) for x in video.get("avg_frame_rate", "0/1").split("/"))
    if not denominator or abs(numerator / denominator - fps) > 0.05:
        raise Rejected("Frame-rate mismatch")
    run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"])
    return {"dimensions": [width, height], "fps": fps, "codec": "h264",
            "audio_codec": "aac", "decoded": True, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sound": "silent diagnostic audio, NOT music or cleared soundtrack"}


def execute(mode, destination, profile):
    if mode not in ("fixture", "live") or profile not in ("synthetic_test", "instagram_reel"):
        raise Rejected("Only bounded synthetic certification jobs are accepted")
    manifest = read_json(HERE / "synthetic_shots.json")
    if manifest.get("content_origin") != "GENERATED TEXT FIXTURE ONLY - ZERO CUSTOMER FOOTAGE":
        raise Rejected("Source identity must be the synthetic-only public fixture")
    cfg, registry = load_system(HERE / "v5_config.json", HERE / "capability_registry.json")
    shots = validate_source(manifest, cfg)
    if mode == "live":
        required_clearance(manifest, external=True)
        prompt = build_director_prompt(cfg, shots,
            (HERE / "fixture_brand.txt").read_text(encoding="utf-8"),
            "One synthetic-only edit of 3 short segments; do not propose unsupported tools.",
            1, profile)
        proposal = call_groq(cfg, prompt, os.environ.get("GROQ_API_KEY", ""))
    else:
        proposal = fixture_plan()
    plans = validate_plan(proposal, shots, 1, cfg)
    ops = plan_operations(plans, registry)
    cuts = compile_edl(plans[0]["segments"], list(shots))
    duration = sum(c["seconds"] for c in cuts)
    if duration < 3 or duration > 120:
        raise Rejected("Existing renderer duration limit")
    width, height = cfg["profiles"][profile]["dimensions"]
    fps = cfg["profiles"][profile]["fps"]
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="v5-synthetic-") as name:
        tmp = Path(name)
        originals = create_synthetic_sources(tmp, shots)
        output = destination / "v5-synthetic-diagnostic.mp4"
        render = render_multiple(originals, output, {
            "target_seconds": duration, "width": width, "height": height,
            "fps": fps, "clip_plan": cuts}, tmp / "segments")
        video = verify_video(output, width, height, fps)
    report = {"engine": "MAD Reel Engine", "version": "5.0.0",
        "status": "SYNTHETIC_TECHNICAL_CERTIFICATION_ONLY",
        "mode": mode, "profile": profile, "model_inference": mode == "live",
        "director_planning_validated": True,
        "deferred_operations": ops["deferred_operations"],
        "render_engine": "services/reel-engine/multi_renderer.py",
        "segments": render["sections"], "duration_seconds": render["duration"],
        "real_footage_certified": False, "artistic_quality_certified": False,
        "music_licensed": False, "private_media_uploaded": False,
        "published": False, "publishing_enabled": False, "video": video}
    (destination / "v5-technical-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    p.add_argument("--profile", choices=("synthetic_test", "instagram_reel"),
                   default="synthetic_test")
    p.add_argument("--out-dir", type=Path, required=True)
    opts = p.parse_args()
    result = execute(opts.mode, opts.out_dir, opts.profile)
    print(json.dumps({"status": result["status"],
        "sha256": result["video"]["sha256"], "bytes": result["video"]["bytes"]}))


if __name__ == "__main__":
    main()
