from __future__ import annotations

import json
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nk=1:nw=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip())


def render_reel(input_path: Path, output_path: Path, cfg: dict, workdir: Path) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    width = int(cfg.get("width", 1080))
    height = int(cfg.get("height", 1920))
    fps = int(cfg.get("fps", 30))

    rendered_segments: list[Path] = []
    for idx, seg in enumerate(cfg["segments"]):
        start = float(seg["start"])
        end = float(seg["end"])
        duration = max(0.05, end - start)
        crop_top = int(seg.get("crop_top", 0))
        filters: list[str] = []
        if crop_top > 0:
            filters.append(f"crop=iw:ih-{crop_top}:0:{crop_top}")
        filters += [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}",
            f"fps={fps}",
            "format=yuv420p",
        ]
        out = workdir / f"seg_{idx:02d}.mp4"
        _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(start), "-i", str(input_path), "-t", str(duration),
            "-an", "-vf", ",".join(filters),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            str(out),
        ])
        rendered_segments.append(out)

    ending = cfg.get("ending", {})
    hold = float(ending.get("min_hold_seconds", 2.5))
    last_src = cfg["segments"][-1]
    last_duration = float(last_src["end"]) - float(last_src["start"])
    extra = max(0.0, hold - last_duration)
    if extra > 0:
        extended = workdir / "seg_last_extended.mp4"
        _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(rendered_segments[-1]),
            "-vf", f"tpad=stop_mode=clone:stop_duration={extra}",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            str(extended),
        ])
        rendered_segments[-1] = extended

    concat_file = workdir / "concat.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in rendered_segments))
    base = workdir / "base.mp4"
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(base),
    ])

    duration = _probe_duration(base)
    audio_cfg = cfg.get("audio", {})
    fade_seconds = float(audio_cfg.get("fade_out_seconds", ending.get("audio_fade_seconds", 1.5)))
    audio = workdir / "audio.m4a"
    fade_start = max(0.0, duration - fade_seconds)
    _run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path),
        "-t", str(duration), "-vn",
        "-af", f"volume={float(audio_cfg.get('volume', 0.72))},afade=t=out:st={fade_start}:d={fade_seconds}",
        "-c:a", "aac", "-b:a", "192k", str(audio),
    ])

    opening = cfg.get("opening", {})
    hook_text = opening.get("text", "")
    cta_text = ending.get("cta", "")
    credit = cfg.get("attribution", {}).get("text", "")

    hook_file = workdir / "hook.txt"
    cta_file = workdir / "cta.txt"
    credit_file = workdir / "credit.txt"
    hook_file.write_text(hook_text)
    cta_file.write_text(cta_text)
    credit_file.write_text(credit)

    hook_end = float(opening.get("end", min(2.5, duration)))
    cta_start = max(0.0, duration - hold)
    video_fade = float(ending.get("video_fade_seconds", 1.2))
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    vf = [
        f"drawtext=fontfile={bold}:textfile={hook_file}:fontcolor=white:fontsize=60:line_spacing=12:"
        f"x=(w-text_w)/2:y=h*0.35:box=1:boxcolor=black@0.24:boxborderw=24:"
        f"enable='between(t,{float(opening.get('start', 0.1))},{hook_end})'",
        f"drawtext=fontfile={bold}:textfile={cta_file}:fontcolor=white:fontsize=60:line_spacing=12:"
        f"x=(w-text_w)/2:y=h*0.38:box=1:boxcolor=black@0.30:boxborderw=24:"
        f"enable='between(t,{cta_start},{max(cta_start, duration - 0.3)})'",
    ]
    if credit:
        vf.append(
            f"drawtext=fontfile={font}:textfile={credit_file}:fontcolor=white@0.80:fontsize=28:"
            f"x=36:y=h-88:enable='between(t,{cta_start},{max(cta_start, duration - 0.3)})'"
        )
    vf.append(f"fade=t=out:st={max(0.0, duration-video_fade)}:d={video_fade}")

    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(base), "-i", str(audio),
        "-vf", ",".join(vf),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-shortest", str(output_path),
    ])

    return {
        "output": str(output_path),
        "duration": _probe_duration(output_path),
        "cta_start": cta_start,
    }
