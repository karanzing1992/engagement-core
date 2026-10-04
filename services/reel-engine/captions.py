from __future__ import annotations

from pathlib import Path


def _stamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(events: list[dict], output_path: Path) -> Path:
    lines: list[str] = []
    idx = 1
    for event in events:
        text = str(event.get("text", "")).strip()
        if not text:
            continue
        start = float(event.get("start", 0.0))
        end = max(start + 0.1, float(event.get("end", start + 1.0)))
        lines += [
            str(idx),
            f"{_stamp(start)} --> {_stamp(end)}",
            text,
            "",
        ]
        idx += 1
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def auto_transcribe_to_srt(input_path: Path, output_path: Path, model_name: str = "base") -> Path:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(input_path), word_timestamps=True)

    events = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            events.append({"start": float(seg.start), "end": float(seg.end), "text": text})
    return write_srt(events, output_path)
