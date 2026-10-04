from __future__ import annotations

import re
from pathlib import Path


def _stamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _ass_stamp(seconds: float) -> str:
    cs = max(0, int(round(seconds * 100)))
    hours, cs = divmod(cs, 360_000)
    minutes, cs = divmod(cs, 6_000)
    secs, cs = divmod(cs, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def _ass_color(hex_rgb: str, alpha: int = 0) -> str:
    value = hex_rgb.strip().lstrip("#")
    if len(value) != 6:
        value = "FFFFFF"
    r, g, b = value[0:2], value[2:4], value[4:6]
    return f"&H{alpha:02X}{b}{g}{r}&"


def _wrap_text(text: str, max_chars: int = 28, max_lines: int = 2) -> str:
    words = [w for w in text.strip().split() if w]
    if not words:
        return ""
    lines: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > max_chars and len(lines) < max_lines - 1:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += extra
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines[:max_lines])


def write_srt(events: list[dict], output_path: Path) -> Path:
    lines: list[str] = []
    idx = 1
    for event in events:
        if event.get("kind") == "credit":
            continue
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


def parse_srt_events(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n", raw.strip())
    events: list[dict] = []

    def seconds(stamp: str) -> float:
        hh, mm, rest = stamp.split(":")
        ss, ms = rest.replace(".", ",").split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms[:3].ljust(3, "0")) / 1000.0

    for block in blocks:
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        if len(lines) < 2:
            continue
        time_idx = 1 if len(lines) > 1 and "-->" in lines[1] else 0
        if "-->" not in lines[time_idx]:
            continue
        left, right = [x.strip() for x in lines[time_idx].split("-->", 1)]
        text = " ".join(lines[time_idx + 1 :]).strip()
        if text:
            events.append(
                {
                    "start": seconds(left),
                    "end": seconds(right),
                    "text": text,
                    "kind": "speech",
                }
            )
    return events


def transcribe_events(
    input_path: Path,
    model_name: str = "base",
    *,
    max_words: int = 5,
    max_chars: int = 28,
) -> list[dict]:
    """Speech mode only: preserve real word timestamps from faster-whisper."""
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(input_path),
        word_timestamps=True,
        vad_filter=True,
    )

    output: list[dict] = []
    current_words: list[dict] = []

    def flush() -> None:
        nonlocal current_words
        if not current_words:
            return
        text = " ".join(str(x["word"]).strip() for x in current_words).strip()
        output.append(
            {
                "start": float(current_words[0]["start"]),
                "end": float(current_words[-1]["end"]),
                "text": _wrap_text(text, max_chars=max_chars),
                "words": list(current_words),
                "kind": "speech",
            }
        )
        current_words = []

    for seg in segments:
        for word in list(seg.words or []):
            value = (word.word or "").strip()
            if not value:
                continue
            item = {
                "word": value,
                "start": float(word.start if word.start is not None else seg.start),
                "end": float(word.end if word.end is not None else seg.end),
            }
            candidate = current_words + [item]
            candidate_text = " ".join(str(x["word"]) for x in candidate)
            pause = (
                float(item["start"]) - float(current_words[-1]["end"])
                if current_words
                else 0.0
            )
            if current_words and (
                len(candidate) > max_words
                or len(candidate_text) > max_chars * 2
                or pause > 0.5
                or re.search(r"[.!?…]$", str(current_words[-1]["word"]))
            ):
                flush()
            current_words.append(item)
    flush()
    return output


def scene_boundaries(segment_durations: list[float]) -> list[float]:
    boundaries = [0.0]
    cursor = 0.0
    for value in segment_durations:
        cursor += float(value)
        boundaries.append(cursor)
    return boundaries


def resolve_scene_events(
    raw_events: list[dict],
    segment_durations: list[float],
    *,
    duration: float,
    padding_in: float = 0.12,
    padding_out: float = 0.14,
) -> list[dict]:
    """Resolve scene-index captions after beat-sync has changed clip durations."""
    boundaries = scene_boundaries(segment_durations)
    resolved: list[dict] = []

    for raw in raw_events:
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        item = dict(raw)
        if "scene_index" in raw:
            idx = int(raw["scene_index"])
            if idx < 0 or idx >= len(segment_durations):
                continue
            start = boundaries[idx] + float(raw.get("start_offset", padding_in))
            end = boundaries[idx + 1] - float(raw.get("end_offset", padding_out))
        else:
            start = float(raw.get("start", 0.0))
            end = float(raw.get("end", min(duration, start + 1.8)))

        start = max(0.0, min(start, duration))
        end = max(start + 0.12, min(end, duration))
        item.update({"start": start, "end": end, "kind": raw.get("kind", "body")})
        resolved.append(item)

    return resolved


def build_unified_events(
    *,
    body_events: list[dict],
    segment_durations: list[float],
    duration: float,
    hook: dict | None = None,
    cta: dict | None = None,
    credit: dict | None = None,
    speech_events: list[dict] | None = None,
) -> list[dict]:
    """One visual text timeline. Prevents double-caption layers and overlaps."""
    body = resolve_scene_events(body_events, segment_durations, duration=duration)
    events: list[dict] = []

    hook_start = None
    hook_end = None
    if hook and str(hook.get("text", "")).strip():
        hook_start = max(0.0, float(hook.get("start", 0.12)))
        hook_end = min(duration, float(hook.get("end", min(2.55, duration))))
        events.append(
            {
                "kind": "hook",
                "text": str(hook["text"]).strip(),
                "start": hook_start,
                "end": max(hook_start + 0.2, hook_end),
            }
        )

    cta_start = None
    if cta and str(cta.get("text", "")).strip():
        cta_start = max(0.0, float(cta.get("start", max(0.0, duration - 2.8))))
        cta_end = min(duration, float(cta.get("end", max(cta_start + 0.2, duration - 0.25))))
        events.append(
            {
                "kind": "cta",
                "text": str(cta["text"]).strip(),
                "start": cta_start,
                "end": max(cta_start + 0.2, cta_end),
            }
        )

    # Body captions must never overlap reserved hook/CTA windows.
    for item in body:
        start = float(item["start"])
        end = float(item["end"])
        if hook_end is not None and start < hook_end:
            start = hook_end + 0.10
        if cta_start is not None and end > cta_start:
            end = cta_start - 0.10
        if end - start >= 0.35:
            item["start"], item["end"] = start, end
            events.append(item)

    for item in speech_events or []:
        start = float(item.get("start", 0.0))
        end = float(item.get("end", start + 0.1))
        if hook_end is not None and start < hook_end:
            continue
        if cta_start is not None and end > cta_start:
            continue
        events.append(item)

    if credit and str(credit.get("text", "")).strip():
        events.append(
            {
                "kind": "credit",
                "text": str(credit["text"]).strip(),
                "start": max(0.0, float(credit.get("start", cta_start or duration - 2.8))),
                "end": min(duration, float(credit.get("end", duration - 0.25))),
            }
        )

    # Remove accidental duplicate text in overlapping windows.
    events.sort(key=lambda e: (float(e["start"]), float(e["end"])))
    deduped: list[dict] = []
    for item in events:
        duplicate = False
        for prev in deduped[-3:]:
            overlap = min(float(item["end"]), float(prev["end"])) - max(
                float(item["start"]), float(prev["start"])
            )
            if overlap > 0 and str(item["text"]).strip().lower() == str(prev["text"]).strip().lower():
                duplicate = True
                break
        if not duplicate:
            deduped.append(item)
    return deduped


def _styles(style: dict) -> tuple[str, dict[str, str]]:
    width = int(style.get("play_res_x", 1080))
    height = int(style.get("play_res_y", 1920))
    font = str(style.get("font_name", "DejaVu Sans"))
    primary = _ass_color(str(style.get("primary_color", "#FFFFFF")))
    accent = _ass_color(str(style.get("active_color", "#DDE9CF")))
    outline = _ass_color(str(style.get("outline_color", "#111111")), alpha=12)
    back = _ass_color("#000000", alpha=170)

    hook_size = int(style.get("hook_font_size", 66))
    body_size = int(style.get("font_size", 56))
    cta_size = int(style.get("cta_font_size", 62))
    speech_size = int(style.get("speech_font_size", 60))
    credit_size = int(style.get("credit_font_size", 25))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Hook,{font},{hook_size},{primary},{accent},{outline},{back},1,0,0,0,100,100,0,0,1,3,1,5,80,80,0,1
Style: Body,{font},{body_size},{primary},{accent},{outline},{back},0,0,0,0,100,100,0,0,1,3,1,5,90,90,0,1
Style: CTA,{font},{cta_size},{primary},{accent},{outline},{back},1,0,0,0,100,100,0,0,1,3,1,5,75,75,0,1
Style: Speech,{font},{speech_size},{primary},{accent},{outline},{back},0,0,0,0,100,100,0,0,1,3,1,5,90,90,0,1
Style: Credit,{font},{credit_size},{primary},{accent},{outline},{back},0,0,0,0,100,100,0,0,1,1,36,36,42,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    meta = {
        "width": str(width),
        "height": str(height),
        "primary": primary,
        "accent": accent,
        "hook_y": str(int(style.get("hook_y", round(height * 0.36)))),
        "body_y": str(int(style.get("body_y", round(height * 0.67)))),
        "cta_y": str(int(style.get("cta_y", round(height * 0.50)))),
        "speech_y": str(int(style.get("speech_y", round(height * 0.68)))),
        "max_chars": str(int(style.get("max_chars", 28))),
    }
    return header, meta


def write_reel_ass(events: list[dict], output_path: Path, style: dict | None = None) -> Path:
    """Single ASS track for hook/body/speech/CTA/credit."""
    style = style or {}
    header, meta = _styles(style)
    width = int(meta["width"])
    primary = meta["primary"]
    accent = meta["accent"]
    max_chars = int(meta["max_chars"])
    lines: list[str] = []

    for event in events:
        kind = str(event.get("kind", "body")).lower()
        text = str(event.get("text", "")).strip()
        if not text:
            continue
        start = float(event.get("start", 0.0))
        end = max(start + 0.12, float(event.get("end", start + 1.0)))

        if kind == "credit":
            payload = "{\\an1\\fad(100,140)}" + _ass_escape(text)
            lines.append(
                f"Dialogue: 0,{_ass_stamp(start)},{_ass_stamp(end)},Credit,,0,0,0,,{payload}"
            )
            continue

        style_name = {"hook": "Hook", "cta": "CTA", "speech": "Speech"}.get(kind, "Body")
        y = int(meta[{"hook": "hook_y", "cta": "cta_y", "speech": "speech_y"}.get(kind, "body_y")])

        if kind == "speech" and event.get("words"):
            words = list(event["words"])
            raw_words = [str(w["word"]).strip() for w in words]
            wrapped = _wrap_text(" ".join(raw_words), max_chars=max_chars)
            line_breaks: set[int] = set()
            count = 0
            for line in wrapped.split("\n")[:-1]:
                count += len(line.split())
                line_breaks.add(count - 1)

            for active_idx, word_meta in enumerate(words):
                ws = max(start, float(word_meta.get("start", start)))
                we = min(end, max(ws + 0.06, float(word_meta.get("end", end))))
                rendered: list[str] = []
                for idx, word in enumerate(raw_words):
                    token = _ass_escape(word)
                    if idx == active_idx:
                        token = "{\\b1\\c" + accent + "}" + token + "{\\b0\\c" + primary + "}"
                    if idx in line_breaks:
                        token += r"\N"
                    rendered.append(token)
                payload = "{\\an5\\pos(" + str(width // 2) + "," + str(y) + ")}" + " ".join(rendered)
                lines.append(
                    f"Dialogue: 0,{_ass_stamp(ws)},{_ass_stamp(we)},{style_name},,0,0,0,,{payload}"
                )
            continue

        wrapped = _wrap_text(text, max_chars=max_chars)
        # Scenic captions: one phrase, one layer, gentle entrance/exit.
        payload = (
            "{\\an5\\pos("
            + str(width // 2)
            + ","
            + str(y)
            + ")\\fad(90,120)}"
            + _ass_escape(wrapped)
        )
        lines.append(
            f"Dialogue: 0,{_ass_stamp(start)},{_ass_stamp(end)},{style_name},,0,0,0,,{payload}"
        )

    output_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return output_path
