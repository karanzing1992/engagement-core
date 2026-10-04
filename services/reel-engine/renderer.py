from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from audio_sync import analyze_beats, snap_segment_durations
from captions import auto_transcribe_to_srt, write_srt


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


def _has_audio(path: Path) -> bool:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(path),
        ],
        text=True,
    )
    return bool(out.strip())


def _prepare_srt(
    input_path: Path,
    output_path: Path,
    cfg: dict,
    duration: float,
    cta_start: float,
    supplied_srt: Path | None,
) -> Path:
    sidecar = output_path.with_suffix(".srt")
    captions_cfg = cfg.get("captions", {})

    if supplied_srt and supplied_srt.exists():
        shutil.copyfile(supplied_srt, sidecar)
        return sidecar

    if captions_cfg.get("auto_transcribe"):
        return auto_transcribe_to_srt(
            input_path,
            sidecar,
            model_name=str(captions_cfg.get("whisper_model", "base")),
        )

    events = list(captions_cfg.get("events", []))
    opening = cfg.get("opening", {})
    if opening.get("text"):
        events.insert(
            0,
            {
                "start": float(opening.get("start", 0.1)),
                "end": float(opening.get("end", min(2.5, duration))),
                "text": opening["text"],
            },
        )
    ending = cfg.get("ending", {})
    if ending.get("cta"):
        events.append(
            {
                "start": cta_start,
                "end": max(cta_start + 0.1, duration - 0.25),
                "text": ending["cta"],
            }
        )
    return write_srt(events, sidecar)


def _render_audio(
    input_path: Path,
    music_path: Path | None,
    output_path: Path,
    duration: float,
    cfg: dict,
) -> None:
    audio_cfg = cfg.get("audio", {})
    fade_seconds = float(
        audio_cfg.get(
            "fade_out_seconds",
            cfg.get("ending", {}).get("audio_fade_seconds", 1.5),
        )
    )
    fade_start = max(0.0, duration - fade_seconds)
    fade_in = max(0.0, float(audio_cfg.get("fade_in_seconds", 0.35)))

    if music_path:
        music_volume = float(audio_cfg.get("music_volume", 0.78))
        ambient_volume = float(audio_cfg.get("ambient_volume", 0.16))
        music_start = max(0.0, float(audio_cfg.get("music_start_seconds", 0.0)))

        if _has_audio(input_path) and ambient_volume > 0:
            filter_complex = (
                f"[0:a]atrim=0:{duration},asetpts=PTS-STARTPTS,"
                f"volume={ambient_volume}[ambient];"
                f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS,"
                f"volume={music_volume},"
                f"afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={fade_start}:d={fade_seconds}[music];"
                f"[ambient][music]amix=inputs=2:duration=longest:dropout_transition=1.5[mix]"
            )
            _run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(input_path),
                "-stream_loop", "-1", "-ss", str(music_start), "-i", str(music_path),
                "-filter_complex", filter_complex,
                "-map", "[mix]", "-t", str(duration),
                "-c:a", "aac", "-b:a", "192k", str(output_path),
            ])
        else:
            _run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-ss", str(music_start), "-i", str(music_path),
                "-t", str(duration), "-vn",
                "-af",
                f"volume={music_volume},"
                f"afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={fade_start}:d={fade_seconds}",
                "-c:a", "aac", "-b:a", "192k", str(output_path),
            ])
        return

    # No music supplied: preserve the original audio with a clean tail.
    if _has_audio(input_path):
        _run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(input_path),
            "-t", str(duration), "-vn",
            "-af",
            f"volume={float(audio_cfg.get('source_volume', audio_cfg.get('volume', 0.72)))},"
            f"afade=t=out:st={fade_start}:d={fade_seconds}",
            "-c:a", "aac", "-b:a", "192k", str(output_path),
        ])
    else:
        _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration),
            "-c:a", "aac", "-b:a", "128k", str(output_path),
        ])


def render_reel(
    input_path: Path,
    output_path: Path,
    cfg: dict,
    workdir: Path,
    *,
    music_path: Path | None = None,
    srt_path: Path | None = None,
) -> dict:
    workdir.mkdir(parents=True, exist_ok=True)
    width = int(cfg.get("width", 1080))
    height = int(cfg.get("height", 1920))
    fps = int(cfg.get("fps", 30))

    source_durations = [
        max(0.05, float(seg["end"]) - float(seg["start"]))
        for seg in cfg["segments"]
    ]

    beat_info = None
    target_durations = source_durations
    sync_cfg = cfg.get("audio", {}).get("beat_sync", {})
    if music_path and sync_cfg.get("enabled", True):
        beat_info = analyze_beats(
            music_path,
            workdir,
            bpm_override=sync_cfg.get("bpm_override"),
        )
        target_durations = snap_segment_durations(
            source_durations,
            beat_info["beats"],
            beats_per_cut=int(sync_cfg.get("beats_per_cut", 4)),
            min_shot_seconds=float(sync_cfg.get("min_shot_seconds", 1.1)),
            max_shot_seconds=float(sync_cfg.get("max_shot_seconds", 3.2)),
        )

    rendered_segments: list[Path] = []
    for idx, seg in enumerate(cfg["segments"]):
        start = float(seg["start"])
        source_duration = source_durations[idx]
        target_duration = max(0.05, float(target_durations[idx]))
        crop_top = int(seg.get("crop_top", 0))

        ratio = target_duration / source_duration
        speed_factor = min(1.15, max(0.85, ratio))

        filters: list[str] = []
        if crop_top > 0:
            filters.append(f"crop=iw:ih-{crop_top}:0:{crop_top}")
        filters += [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}",
            f"fps={fps}",
            f"setpts={speed_factor}*PTS",
            "format=yuv420p",
        ]

        # Render crop/scale/speed first. Exact duration is enforced separately;
        # doing tpad in the same pass can be shortened by ffmpeg timestamp rules.
        out = workdir / f"seg_{idx:02d}.mp4"
        _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", str(start), "-t", str(source_duration), "-i", str(input_path),
            "-an", "-vf", ",".join(filters),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            str(out),
        ])

        actual_duration = _probe_duration(out)
        exact = workdir / f"seg_{idx:02d}_exact.mp4"
        if actual_duration < target_duration - 0.02:
            _run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(out),
                "-vf",
                f"tpad=stop_mode=clone:stop_duration={target_duration - actual_duration}",
                "-t", str(target_duration),
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                str(exact),
            ])
        else:
            _run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(out), "-t", str(target_duration),
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                str(exact),
            ])
        rendered_segments.append(exact)

    ending = cfg.get("ending", {})
    hold = float(ending.get("min_hold_seconds", 2.5))
    last_duration = target_durations[-1]
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
    audio = workdir / "audio.m4a"
    _render_audio(input_path, music_path, audio, duration, cfg)

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

    sidecar_srt = _prepare_srt(
        input_path,
        output_path,
        cfg,
        duration,
        cta_start,
        srt_path,
    )

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

    captions_cfg = cfg.get("captions", {})
    if captions_cfg.get("burn_subtitles"):
        escaped = str(sidecar_srt).replace("\\", "/").replace(":", "\\:")
        vf.append(
            f"subtitles='{escaped}':force_style="
            f"'FontName=DejaVu Sans,FontSize=18,Alignment=2,MarginV=150,"
            f"Outline=2,Shadow=0,PrimaryColour=&H00FFFFFF'"
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
        "srt": str(sidecar_srt),
        "music_sync": beat_info,
        "segment_durations": [round(float(v), 4) for v in target_durations],
    }
