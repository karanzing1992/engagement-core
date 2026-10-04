from __future__ import annotations

import math
import subprocess
from pathlib import Path

import librosa
import numpy as np


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def analyze_beats(music_path: Path, workdir: Path, bpm_override: float | None = None) -> dict:
    """Return BPM and beat timestamps from an uploaded music track."""
    workdir.mkdir(parents=True, exist_ok=True)
    wav = workdir / "music-analysis.wav"
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(music_path), "-vn", "-ac", "1", "-ar", "22050",
        str(wav),
    ])

    y, sr = librosa.load(wav, sr=22050, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr)

    if bpm_override:
        bpm = float(bpm_override)
        beat_frames = librosa.beat.beat_track(
            onset_envelope=onset, sr=sr, bpm=bpm, units="frames"
        )[1]
    else:
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset, sr=sr, units="frames"
        )
        bpm = float(np.atleast_1d(tempo)[0]) if np.size(tempo) else 0.0

    beats = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    # Sparse/ambient tracks can confuse beat tracking. Fall back to a stable grid.
    if len(beats) < 4:
        if not bpm or not math.isfinite(bpm):
            bpm = 120.0
        duration = librosa.get_duration(y=y, sr=sr)
        step = 60.0 / bpm
        beats = np.arange(0.0, duration + step, step).tolist()

    return {"bpm": round(bpm, 3), "beats": [round(float(v), 4) for v in beats]}


def snap_segment_durations(
    source_durations: list[float],
    beat_times: list[float],
    *,
    beats_per_cut: int = 4,
    min_shot_seconds: float = 1.1,
    max_shot_seconds: float = 3.2,
) -> list[float]:
    """Snap cumulative visual cut points to musical bars while preserving reel rhythm."""
    if len(source_durations) <= 1 or len(beat_times) < 2:
        return source_durations

    beats_per_cut = max(1, int(beats_per_cut))
    anchors = beat_times[::beats_per_cut]
    if not anchors or anchors[0] > 0.25:
        anchors = [0.0] + anchors

    nominal = np.cumsum(source_durations)
    total_nominal = float(nominal[-1])
    result: list[float] = []
    prev = 0.0

    for boundary in nominal[:-1]:
        candidates = [
            a for a in anchors
            if a >= prev + min_shot_seconds
            and a <= prev + max_shot_seconds
            and a < total_nominal
        ]
        if candidates:
            snapped = min(candidates, key=lambda a: abs(a - float(boundary)))
        else:
            snapped = min(
                max(float(boundary), prev + min_shot_seconds),
                prev + max_shot_seconds,
            )
        result.append(max(0.05, snapped - prev))
        prev = snapped

    final_duration = max(min_shot_seconds, total_nominal - prev)
    result.append(final_duration)
    return result
