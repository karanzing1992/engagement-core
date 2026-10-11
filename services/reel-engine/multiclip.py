"""Multi-source FFmpeg preparation with explicit 30s (or configured) timeline.

The output remains an internal private source. The existing Reel Engine caption,
Goa/India provenance and exact official logo gates are applied afterwards.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess

from chunked_ingest import UploadError


MAX_CLIPS = 20
MAX_OUTPUT_SECONDS = 180
SUPPORTED_FPS = (24, 25, 30)


def _run(args: list[str], *, timeout: int = 900) -> None:
    try:
        subprocess.run(args, check=True, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired as e:
        raise UploadError("FFmpeg rendering timed out", 504) from e
    except subprocess.CalledProcessError as e:
        raise UploadError("FFmpeg processing failed: " + (e.stderr or "")[-1000:], 422) from e


def media_info(path: Path) -> dict:
    try:
        result = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            text=True, timeout=45,
        )
        metadata = json.loads(result)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        raise UploadError("Input is not valid readable media", 422) from e
    streams = metadata.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise UploadError("Input has no video track", 422)
    try:
        duration = float(metadata.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    if not math.isfinite(duration) or duration <= 0:
        raise UploadError("Input duration is missing or invalid", 422)
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    if width < 64 or height < 64 or width > 7680 or height > 7680:
        raise UploadError("Input resolution outside safe range", 422)
    return {"duration": duration, "width": width, "height": height,
            "audio": any(s.get("codec_type") == "audio" for s in streams)}


def validate_timeline(paths: list[Path], cuts: list[dict], *, duration: float,
                      width: int, height: int, fps: int) -> tuple[dict, list[dict]]:
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_CLIPS:
        raise UploadError("Provide 1 to 20 uploaded video sources")
    if not isinstance(cuts, list) or not 1 <= len(cuts) <= MAX_CLIPS:
        raise UploadError("Timeline needs 1 to 20 clip cuts")
    if type(width) is not int or type(height) is not int or width % 2 or height % 2 or \
            not 360 <= width <= 1920 or not 640 <= height <= 3840:
        raise UploadError("Output resolution must be a valid even-sized portrait frame")
    if height <= width:
        raise UploadError("Only vertical video outputs are supported")
    if fps not in SUPPORTED_FPS:
        raise UploadError("FPS must be 24, 25, or 30")
    if type(duration) not in (int, float) or not math.isfinite(duration) or not 10 <= duration <= MAX_OUTPUT_SECONDS:
        raise UploadError("Reel duration must be 10-180 seconds")
    probes = [media_info(p) for p in paths]
    total = 0.0
    selected = []
    for idx, cut in enumerate(cuts):
        if not isinstance(cut, dict) or type(cut.get("source_index")) is not int:
            raise UploadError(f"Cut {idx + 1}: source_index must be an integer")
        index = cut["source_index"]
        if index < 0 or index >= len(paths):
            raise UploadError(f"Cut {idx + 1}: source index outside uploaded files")
        try:
            start, end = float(cut["start"]), float(cut["end"])
        except (KeyError, TypeError, ValueError) as e:
            raise UploadError(f"Cut {idx + 1}: start/end required") from e
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start:
            raise UploadError(f"Cut {idx + 1}: invalid trim range")
        if end > probes[index]["duration"] + 0.04:
            raise UploadError(f"Cut {idx + 1}: trim extends past source video")
        if end - start < 0.5:
            raise UploadError(f"Cut {idx + 1}: minimum 0.5 second clip")
        total += end - start
        selected.append({"source_index": index, "start": start, "end": end})
    if abs(total - duration) > .04:
        raise UploadError(f"Timeline totals {total:.2f}s but target is {duration:.2f}s")
    return {"duration": duration, "source_count": len(paths), "cut_count": len(cuts),
            "total_cut_seconds": round(total, 3), "inputs": probes}, selected


def assemble_multiclip(paths: list[Path], cuts: list[dict], output: Path, workdir: Path,
                       *, duration: float = 30.0, width: int = 1080, height: int = 1920,
                       fps: int = 30, audio_source_index: int | None = None,
                       audio_volume: float = 0.7) -> dict:
    """Pre-concatenate uploaded videos while retaining a user-provided audio bed.

    No arbitrary shell; no external URLs; FFmpeg receives only validated local paths.
    Transcript/text branding happens in existing Reel Engine after compilation.
    """
    report, clean = validate_timeline(paths, cuts, duration=duration, width=width,
                                      height=height, fps=fps)
    if audio_source_index is not None and (type(audio_source_index) is not int or
                                          not 0 <= audio_source_index < len(paths)):
        raise UploadError("Audio source index outside uploaded videos")
    if type(audio_volume) not in (float, int) or not math.isfinite(audio_volume) or not 0 <= audio_volume <= 1:
        raise UploadError("Audio volume must be 0 to 1")
    if audio_source_index is None:
        audio_source_index = next((i for i, meta in enumerate(report["inputs"]) if meta["audio"]), None)
    if audio_source_index is not None and not report["inputs"][audio_source_index]["audio"]:
        raise UploadError("Selected audio source has no audio track")

    workdir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized: list[Path] = []
    for i, cut in enumerate(clean):
        src = paths[cut["source_index"]]
        part = workdir / f"normalized_{i:02d}.mp4"
        d = cut["end"] - cut["start"]
        _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(cut["start"]),
              "-t", str(d), "-i", str(src), "-an", "-vf",
              f"scale={width}:{height}:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p",
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", str(fps),
              "-movflags", "+faststart", str(part)])
        normalized.append(part)
    listing = workdir / "segments.txt"
    listing.write_text("".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\n"
                               for p in normalized))
    silent = workdir / "video_only.mp4"
    _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0",
          "-i", str(listing), "-c", "copy", str(silent)])
    audio_filter = f"volume={audio_volume},afade=t=in:st=0:d=0.35,afade=t=out:st={max(0, duration-1.5)}:d=1.5"
    if audio_source_index is None:
        _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(silent),
              "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
              "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration),
              "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)])
    else:
        _run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(silent),
              "-stream_loop", "-1", "-i", str(paths[audio_source_index]),
              "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration), "-af", audio_filter,
              "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(output)])
    output_info = media_info(output)
    if abs(output_info["duration"] - duration) > .12:
        raise UploadError("Rendered video duration deviates from timeline", 422)
    if not output_info["audio"]:
        raise UploadError("Rendered video has no audio track", 422)
    return {**report, "output_duration": output_info["duration"],
            "output_width": output_info["width"], "output_height": output_info["height"],
            "audio_source_index": audio_source_index,
            "output": str(output), "publishing_enabled": False}