#!/usr/bin/env python3
"""MAD Reel Engine V7: bounded cinematic finishing of V6 verified FFmpeg media.

Reuses first-party V6 for source hash admission, shot/titles, reviewed EDL and
licensed recording mix. Adds a second FFmpeg cinematic finishing/normalization
pass without changing V6's Cloudflare OIDC/job lifecycle.
No autonomous publication, invented media, copyrighted compositions, or
self-attested artistic acceptance.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from pathlib import Path
import sys
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v6-kv-gateway'))
import ffmpeg_v6_adapter as v6

# These are declarative presets, not arbitrary command strings from models.
# Keep them contrast-safe for documentary/guest footage.
PRESETS: dict[str, dict[str, float]] = {
    "elemental-sanctuary": {
        "contrast": 1.065, "saturation": 0.91, "brightness": 0.003,
        "vignette": 0.22, "grain": 2.5, "audio_i": -16.0
    },
    "sauna-cinema": {
        "contrast": 1.09, "saturation": 0.89, "brightness": 0.008,
        "vignette": 0.29, "grain": 2.1, "audio_i": -16.0
    },
    "guest-reflections": {
        "contrast": 1.035, "saturation": 0.98, "brightness": 0.002,
        "vignette": 0.18, "grain": 1.3, "audio_i": -16.0
    },
    "earth-rejuvenation": {
        "contrast": 1.055, "saturation": 0.94, "brightness": 0.008,
        "vignette": 0.24, "grain": 2.0, "audio_i": -16.0
    },
    "clean-editorial": {
        "contrast": 1.02, "saturation": 1.00, "brightness": 0.0,
        "vignette": 0.12, "grain": 0.0, "audio_i": -16.0
    },
}


class V7Blocked(ValueError):
    """A V7 creative/rights/capability constraint failed."""


def preset_for(brief: str) -> str:
    """Deterministic classification; brand is not inferred from unseen footage."""
    b = (brief or "").casefold()
    for keys, preset in (
        (("sauna", "banya", "steam"), "sauna-cinema"),
        (("earth rejuvenation", "mud ritual", "mud bath"), "earth-rejuvenation"),
        (("testimonial", "guest review", "interview"), "guest-reflections"),
        (("elemental", "sanctuary", "nature"), "elemental-sanctuary"),
    ):
        if any(k in b for k in keys):
            return preset
    return "clean-editorial"


def _check(spec: dict[str, Any]) -> tuple[Path, Path, dict[str, float]]:
    if not isinstance(spec, dict):
        raise V7Blocked("V7_SPEC_INVALID")
    name = spec.get("v7_preset")
    if name not in PRESETS:
        raise V7Blocked("V7_PRESET_NOT_ALLOWLISTED")
    if spec.get("published", False) is not False or spec.get("owner_approval", False) is not False:
        raise V7Blocked("V7_PUBLICATION_NOT_AUTHORIZED")
    # No untrusted FFmpeg filter strings, model-generated graph fragments or
    # imported logo assets are accepted in the finishing layer.
    for forbidden in ("ffmpeg_filter", "command", "filter_complex", "external_media_url",
                      "music_url", "generated_music", "unsafe_expression"):
        if forbidden in spec:
            raise V7Blocked("V7_UNTRUSTED_MEDIA_OR_FILTER_INPUT")
    base = Path(spec.get("output", "")).resolve()
    private = Path(spec.get("workdir", "")).resolve()
    if base.parent != private or not private.is_dir():
        raise V7Blocked("V7_PRIVATE_OUTPUT_REQUIRED")
    profile = PRESETS[name]
    return private, base, profile


def _filters(profile: dict[str, float], seconds: float) -> tuple[str, str]:
    if not 1.2 <= seconds <= 120:
        raise V7Blocked("V7_DURATION_UNSUPPORTED")
    fade = min(0.75, seconds / 8)
    fade_out = max(0, seconds - fade)
    video = [
        "eq=contrast=%.4f:saturation=%.4f:brightness=%.4f" % (
            profile["contrast"], profile["saturation"], profile["brightness"]),
        "vignette=angle=%.5f:eval=frame" % (math.pi / 2 * profile["vignette"]),
    ]
    if profile["grain"]:
        video.append("noise=alls=%d:allf=t+u" % int(round(profile["grain"])))
    video.extend(["fade=t=in:st=0:d=%.3f" % fade,
                  "fade=t=out:st=%.3f:d=%.3f" % (fade_out, fade)])
    audio = ("loudnorm=I=%.1f:TP=-1.5:LRA=11,"
             "afade=t=in:st=0:d=%.3f,afade=t=out:st=%.3f:d=%.3f"
             % (profile["audio_i"], fade, fade_out, fade))
    return ",".join(video), audio



def _audio_peak_db(path: Path) -> float:
    """Inspect decoded peak; near-silent AAC can make loudnorm output NaN/Inf."""
    result = v6._exec([
        "ffmpeg", "-hide_banner", "-loglevel", "info", "-nostats",
        "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"
    ], 90)
    # Private media names and FFmpeg diagnostics stay out of owner/job logs.
    decoded = result.stderr.decode("utf-8", errors="replace")
    m = re.search(r"max_volume:\s*(-inf|[-+]?[0-9]+(?:\.[0-9]+)?)\s*dB", decoded)
    if not m:
        raise V7Blocked("V7_AUDIO_PEAK_NOT_MEASURED")
    peak = float(m.group(1))
    if math.isnan(peak):
        raise V7Blocked("V7_AUDIO_PEAK_INVALID")
    return peak


def _scene_boundaries(source: Path, seconds: float, fps: int) -> tuple[list[float], str]:
    """Look for real edits in the owner's source; never fetch or synthesize footage."""
    if seconds < 10:
        return [], "single_short_shot"
    try:
        probe = v6._exec([
            "ffmpeg", "-hide_banner", "-loglevel", "info", "-nostats", "-i", str(source),
            "-vf", r"scale=320:-2,select=gt(scene\,0.25),showinfo",
            "-an", "-f", "null", "-"
        ], max(30, min(180, int(seconds * 3))))
        candidates = [float(value) for value in
                      re.findall(r"pts_time:\s*([0-9]+(?:\.[0-9]+)?)",
                                 probe.stderr.decode("utf8", errors="replace"))]
    except (v6.RenderBlocked, ValueError):
        candidates = []
    out = []
    for value in candidates:
        if 3.0 < value < seconds-3.0 and (not out or value-out[-1] >= 4.0):
            out.append(round(value*fps)/fps)
        if len(out) >= 5:break
    if out:
        return out, "detected_scene_boundaries"
    # Avoid returning a falsely complete "cinematic" edit from a long single
    # segment. Short editorial chapters retain every frame and continuous speech.
    if seconds >= 24:
        return [round(seconds*fraction*fps)/fps for fraction in (.33, .66)], "timed_editorial_chapters"
    return [], "no_safe_boundary"


def _protect_dialogue_timeline(spec: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Honor owner's keep-dialogue-and-runtime direction before rendering."""
    if not spec.get("dialogue_priority"):
        return spec, "not_requested"
    details = v6.probe(Path(spec["source"]))
    if details["audio"] is None:
        raise V7Blocked("V7_DIALOGUE_SOURCE_AUDIO_MISSING")
    if not spec.get("preserve_full_source"):
        return spec, "audio_only_priority"
    duration = details["duration"]
    if duration > 120:
        raise V7Blocked("V7_FULL_SOURCE_TOO_LONG")
    fps = int(spec["fps"])
    cuts = spec["cuts"]
    cursor = 0.0
    complete = len(cuts)>1
    for cut in cuts:
        if abs(float(cut["start"])-cursor)>.07:
            complete=False
        cursor=float(cut["start"])+float(cut["seconds"])
    if abs(cursor-duration)>.12:
        complete=False
    if complete:
        result=dict(spec,transition_style="dip-to-black")
        return result, "reviewed_full_length_edl"
    boundaries,method=_scene_boundaries(Path(spec["source"]),duration,fps)
    frames=[0]+[round(t*fps) for t in boundaries]+[round(duration*fps)]
    if any((right-left)/fps <.4 for left,right in zip(frames,frames[1:])):
        raise V7Blocked("V7_PROTECTED_CUT_TOO_SHORT")
    shot_cuts=[{"start":frames[i]/fps,"seconds":(frames[i+1]-frames[i])/fps}
               for i in range(len(frames)-1)]
    # Keep one reviewed instruction; do not invent dialogue or rewrite captions.
    approved_first=list(spec["operations"][0]) if spec["operations"] else []
    operations=[approved_first]+[[] for _ in shot_cuts[1:]]
    return dict(spec,cuts=shot_cuts,operations=operations,
                transition_style="dip-to-black"), method


def finish(spec: dict[str, Any]) -> dict[str, Any]:
    """V6 render -> V7 finish -> independent decode; private output only."""
    work, target, profile = _check(spec)
    spec, transition_source = _protect_dialogue_timeline(spec)
    v6.verify_backend()
    draft = work / "v7-base-private.mp4"
    if draft == target:
        raise V7Blocked("V7_DESTINATION_CONFLICT")
    base = dict(spec, output=str(draft))
    try:
        baseline = v6.render(base)
        if any(baseline.get(k) is not True for k in (
                "video_stream_verified", "audio_stream_verified", "full_decode_passed")):
            raise V7Blocked("V7_UPSTREAM_FFMPEG_QA_FAILED")
        if baseline.get("published") is not False:
            raise V7Blocked("V7_UPSTREAM_PUBLICATION")
        duration = float(baseline["duration_seconds"])
        video, audio = _filters(profile, duration)
        measured_peak = _audio_peak_db(draft)
        near_silent = measured_peak <= -55.0
        if spec.get("dialogue_priority"):
            # Never fade the start/end of a sentence or re-normalize narration.
            audio = "anull"
        if near_silent and not spec.get("dialogue_priority"):
            # Loudnorm on encoded digital silence can return NaN and crash AAC.
            audio = re.sub(r"^loudnorm=[^,]+,", "volume=0,", audio, count=1)
            if not audio.startswith("volume=0,"):
                raise V7Blocked("V7_SILENT_AUDIO_GUARD_NOT_APPLIED")
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(draft), "-vf", video, "-af", audio,
               "-map", "0:v:0", "-map", "0:a:0",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
               "-ar", "48000", "-ac", "2",
               "-movflags", "+faststart", "-t", str(duration), str(target)]
        v6._exec(cmd, max(90, min(600, int(duration * 15))))
        info = v6.probe(target)
        if (info["video"] is None or info["audio"] is None or
                info["video"].get("codec_name") != "h264" or
                info["audio"].get("codec_name") != "aac" or
                abs(info["duration"] - duration) > 0.25):
            raise V7Blocked("V7_OUTPUT_VIDEO_AUDIO_INVALID")
        if ((info["video"]["width"], info["video"]["height"]) !=
                (spec["width"], spec["height"])):
            raise V7Blocked("V7_OUTPUT_DIMENSIONS_INVALID")
        if spec.get("preserve_full_source") and abs(
                info["duration"] - v6.probe(Path(spec["source"]))["duration"]) > .15:
            raise V7Blocked("V7_DIALOGUE_DURATION_NOT_PRESERVED")
        v6._exec(["ffmpeg", "-hide_banner", "-v", "error", "-xerror",
                  "-i", str(target), "-f", "null", "-"], 300)
        samples = []
        for index, at in enumerate((.25, duration/2, max(.25, duration-.25))):
            jpg = work / ("v7-review-frame-%d.jpg" % index)
            v6._exec(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                      "-ss", str(at), "-i", str(target), "-frames:v", "1",
                      "-q:v", "3", str(jpg)], 35)
            if not jpg.is_file() or jpg.stat().st_size < 1024:
                raise V7Blocked("V7_VISUAL_FRAME_DECODE_FAILED")
            samples.append(jpg.name)
        return {
            **baseline,
            "version": "v7-source-beta",
            "engine": "ffmpeg",
            "v7_preset": spec["v7_preset"],
            "cinematic_finish_applied": True,
            "audio_mastering_mode": ("dialogue_source_preserved" if spec.get("dialogue_priority")
                                     else "near_silent_preserved" if near_silent else "loudnorm"),
            "dialogue_transition_source": transition_source,
            "source_audio_peak_db": round(measured_peak, 2) if math.isfinite(measured_peak) else None,
            "v7_filters": ["eq", "vignette", "noise" if profile["grain"] else "no_grain",
                            "video_fades"] + (["dialogue_original_audio_no_fades"] if
                            spec.get("dialogue_priority") else ["loudnorm", "audio_fades"]),
            "sha256": v6.sha256(target),
            "bytes": target.stat().st_size,
            "ffmpeg_invocations": baseline["ffmpeg_invocations"] + 5,
            "duration_seconds": info["duration"],
            "full_decode_passed": True,
            "video_stream_verified": True,
            "audio_stream_verified": True,
            "visual_presence_check": {"visible": True, "frames_examined": 3},
            "review_frames": samples,
            "independent_visual_and_audio_review": "PENDING",
            "creative_complete": False,
            "published": False, "owner_approval": False,
        }
    finally:
        # Never leave a duplicate base export after finishing the same job.
        draft.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    try:
        record = finish(json.loads(Path(args.spec).read_text()))
        Path(args.receipt).write_text(json.dumps(record, indent=2))
        print("MAD_V7_CINEMATIC_FFMPEG_PRIVATE_QA_PASS")
    except (V7Blocked, v6.RenderBlocked) as error:
        import sys
        print("MAD_V7_PRIVATE_QA_BLOCKED " + str(error), file=sys.stderr)
        raise SystemExit(2)
