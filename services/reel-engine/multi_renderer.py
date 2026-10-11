"""Private multi-clip FFmpeg renderer with exact-duration output.

Clips may be much larger than the old connector's upload limit: once they are
available as local files, ffmpeg seeks/streams them rather than reading their
bytes into Python memory. Never publishes video or exposes the source files.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
from pathlib import Path


class MultiClipError(ValueError):
    pass


def _run(command: list[str]) -> None:
    p = subprocess.run(command, capture_output=True, text=True)
    if p.returncode:
        raise MultiClipError((p.stderr or p.stdout or "FFmpeg processing failed")[-1800:])


def probe_media(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size < 1024:
        raise MultiClipError("Missing or empty source video")
    p = subprocess.run(["ffprobe", "-v", "error", "-show_format",
                        "-show_streams", "-of", "json", str(path)],
                       text=True, capture_output=True)
    if p.returncode:
        raise MultiClipError("Input is not a decodable media file")
    data = json.loads(p.stdout)
    videos = [x for x in data.get("streams", []) if x.get("codec_type") == "video"]
    if not videos:
        raise MultiClipError("Source contains no video stream")
    duration = float(data.get("format", {}).get("duration") or videos[0].get("duration") or 0)
    if not 0.2 <= duration <= 24 * 60 * 60:
        raise MultiClipError("Invalid source video duration")
    return {
        "duration": duration,
        "has_audio": any(x.get("codec_type") == "audio" for x in data.get("streams", [])),
        "width": int(videos[0].get("width") or 0),
        "height": int(videos[0].get("height") or 0),
    }


def validate_plan(paths: list[Path], cfg: dict, probes: list[dict]) -> tuple[list[dict], float]:
    if len(paths) < 1 or len(paths) > 8 or len(paths) != len(probes):
        raise MultiClipError("One to eight existing source videos required")
    try:
        target = float(cfg.get("target_seconds", 30))
        width = int(cfg.get("width", 720))
        height = int(cfg.get("height", 1280))
        fps = int(cfg.get("fps", 25))
    except (ValueError, TypeError):
        raise MultiClipError("Invalid video duration or geometry")
    if not 3 <= target <= 120 or (width, height) not in ((360, 640), (540, 960), (720, 1280), (1080, 1920)) or fps not in (15, 24, 25, 30):
        raise MultiClipError("Unsupported duration, aspect ratio or frame rate")
    cuts = cfg.get("clip_plan")
    if cuts is None:
        # A meaningful default for 1-8 clips with no manual timeline editing.
        # If a short source must fill more time, loop only a section of that source;
        # never read beyond EOF and never silently insert foreign footage.
        n = len(paths)
        cuts = []
        for i in range(n):
            amount = target/n if i < n-1 else target-sum(c["seconds"] for c in cuts)
            available = probes[i]["duration"]
            cuts.append({"source_index": i, "start": max(0.0, (available-amount)/2),
                         "seconds": amount, "loop": available < amount})
    if not isinstance(cuts, list) or not 1 <= len(cuts) <= 16:
        raise MultiClipError("One to sixteen timeline sections required")
    clean = []
    total = 0.0
    for pos, item in enumerate(cuts):
        if not isinstance(item, dict):
            raise MultiClipError(f"Clip {pos+1}: malformed timeline item")
        try:
            idx = int(item["source_index"])
            start = float(item.get("start", 0))
            seconds = float(item["seconds"])
        except (ValueError, TypeError, KeyError):
            raise MultiClipError(f"Clip {pos+1}: invalid source index or timing")
        if idx < 0 or idx >= len(paths) or not math.isfinite(start) or not math.isfinite(seconds):
            raise MultiClipError(f"Clip {pos+1}: invalid index/timing")
        if start < 0 or seconds < 0.4 or seconds > 120:
            raise MultiClipError(f"Clip {pos+1}: duration outside valid range")
        source_duration = probes[idx]["duration"]
        if start >= source_duration-0.2:
            raise MultiClipError(f"Clip {pos+1}: start is beyond the source")
        loop = bool(item.get("loop", False))
        if start+seconds > source_duration+0.02 and not loop:
            raise MultiClipError(f"Clip {pos+1}: longer than the source; opt into looping")
        total += seconds
        clean.append({"source_index": idx, "start": round(start, 3),
                      "seconds": seconds, "loop": loop})
    if abs(total - target) > 0.10:
        raise MultiClipError(f"Clip durations must sum to {target:.2f}s (got {total:.2f}s)")
    return clean, target


def render_multiple(paths: list[Path], output: Path, cfg: dict, workdir: Path) -> dict:
    paths = [Path(p) for p in paths]
    probes = [probe_media(p) for p in paths]
    plan, target = validate_plan(paths, cfg, probes)
    width, height, fps = (int(cfg.get("width", 720)),
                          int(cfg.get("height", 1280)), int(cfg.get("fps", 25)))
    workdir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = []
    for index, item in enumerate(plan):
        src = paths[item["source_index"]]
        duration = item["seconds"]
        available = probes[item["source_index"]]["duration"]-item["start"]
        loop = item["loop"] and available < duration-0.02
        seg_path = workdir/f"clip_{index:02}.mp4"
        # Normalise codec and audio for reliable concatenation, regardless of
        # whether phones recorded variable FPS, HEVC, mono, stereo or silence.
        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase:"
            "flags=lanczos,"
            f"crop={width}:{height},setsar=1,fps={fps},"
            "format=yuv420p,"
            f"fade=t=in:st=0:d={min(0.3,duration/5):.3f},"
            f"fade=t=out:st={max(0,duration-0.32):.3f}:d=0.32"
        )
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        if loop:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-ss", str(item["start"]), "-i", str(src)]
        if not probes[item["source_index"]]["has_audio"]:
            cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        audio_map = "0:a:0" if probes[item["source_index"]]["has_audio"] else "1:a:0"
        cmd += ["-map", "0:v:0", "-map", audio_map, "-t", str(duration),
                "-vf", video_filter,
                "-af", f"aresample=async=1:first_pts=0,afade=t=in:st=0:d=0.2,"
                       f"afade=t=out:st={max(0,duration-0.25):.3f}:d=0.25",
                "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", str(int(cfg.get("crf", 22))),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "2",
                "-ar", "48000", "-b:a", "128k", "-avoid_negative_ts", "make_zero",
                str(seg_path)]
        _run(cmd)
        rendered.append(seg_path)

    concat = workdir/"private-concat.txt"
    concat.write_text("".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n"
                              for p in rendered), encoding="utf-8")
    _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
          "-f", "concat", "-safe", "0", "-i", str(concat),
          "-t", str(target), "-c", "copy", "-movflags", "+faststart", str(output)])
    result = probe_media(output)
    if abs(result["duration"] - target) > 0.22:
        raise MultiClipError(f"Output duration is wrong: {result['duration']} vs {target}")
    if not result["has_audio"] or (result["width"], result["height"]) != (width, height):
        raise MultiClipError("Final media did not preserve audio and target aspect ratio")
    return {"output": str(output), "duration": result["duration"],
            "width": width, "height": height, "fps": fps,
            "sources": len(paths), "sections": len(plan), "timeline": plan,
            "private": True, "publishing_enabled": False, "schedule_enabled": False}


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(description="Render a private mobile-first 9:16 Reel from 1-8 local source files")
    p.add_argument("--input", action="append", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--seconds", type=float, default=30)
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--workdir", default="/tmp/moksha-multiclip")
    args=p.parse_args()
    result=render_multiple([Path(x) for x in args.input], Path(args.output),
                           {"target_seconds":args.seconds,"width":args.width,"height":args.height},
                           Path(args.workdir))
    print(json.dumps(result,indent=2))
