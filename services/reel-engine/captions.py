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


def _word_weight(word: str) -> float:
    clean = re.sub(r"[^A-Za-z0-9]", "", word)
    return max(1.0, min(2.2, len(clean) / 4.2))


def _timed_words(text: str, start: float, end: float) -> list[dict]:
    words = [x for x in text.strip().split() if x]
    if not words:
        return []

    duration = max(0.12, end - start)
    weights = [_word_weight(word) for word in words]
    total = sum(weights)
    cursor = start
    out: list[dict] = []
    for idx, (word, weight) in enumerate(zip(words, weights)):
        word_end = end if idx == len(words) - 1 else cursor + duration * weight / total
        out.append({"word": word, "start": cursor, "end": max(cursor + 0.06, word_end)})
        cursor = word_end
    return out


def _wrap_words(words: list[str], max_chars: int = 25, max_lines: int = 2) -> str:
    lines: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and current_len + extra > max_chars and len(lines) < max_lines - 1:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += extra

    if current:
        lines.append(" ".join(current))
    return "\n".join(lines[:max_lines])


def _chunk_timed_words(
    words: list[dict],
    *,
    max_words: int = 5,
    max_chars: int = 27,
    pause_break: float = 0.52,
) -> list[dict]:
    chunks: list[list[dict]] = []
    current: list[dict] = []

    for item in words:
        word = str(item.get("word", "")).strip()
        if not word:
            continue
        candidate = current + [item]
        candidate_text = " ".join(str(x["word"]).strip() for x in candidate)
        previous_end = float(current[-1]["end"]) if current else None
        pause = float(item["start"]) - previous_end if previous_end is not None else 0.0
        sentence_end = bool(current and re.search(r"[.!?…]$", str(current[-1]["word"])))

        should_break = bool(
            current
            and (
                len(candidate) > max_words
                or len(candidate_text) > max_chars * 2
                or pause > pause_break
                or sentence_end
            )
        )
        if should_break:
            chunks.append(current)
            current = [item]
        else:
            current = candidate

    if current:
        chunks.append(current)

    events: list[dict] = []
    for chunk in chunks:
        text_words = [str(x["word"]).strip() for x in chunk]
        events.append(
            {
                "start": float(chunk[0]["start"]),
                "end": float(chunk[-1]["end"]),
                "text": _wrap_words(text_words, max_chars=max_chars),
                "words": chunk,
            }
        )
    return events


def normalize_events(
    events: list[dict],
    *,
    max_words: int = 5,
    max_chars: int = 27,
) -> list[dict]:
    normalized: list[dict] = []
    for event in events:
        text = str(event.get("text", "")).strip()
        if not text:
            continue
        start = float(event.get("start", 0.0))
        end = max(start + 0.12, float(event.get("end", start + 1.0)))
        words = list(event.get("words") or _timed_words(text, start, end))
        if not words:
            continue
        normalized.extend(
            _chunk_timed_words(
                words,
                max_words=max_words,
                max_chars=max_chars,
                pause_break=99.0,
            )
        )
    return normalized


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


def parse_srt_events(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\n\s*\n", raw.strip())
    events: list[dict] = []

    def seconds(stamp: str) -> float:
        hh, mm, rest = stamp.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0

    for block in blocks:
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        if len(lines) < 2:
            continue
        time_idx = 1 if "-->" in lines[1] else 0
        if "-->" not in lines[time_idx]:
            continue
        left, right = [x.strip() for x in lines[time_idx].split("-->", 1)]
        text = " ".join(lines[time_idx + 1 :]).strip()
        if text:
            events.append({"start": seconds(left), "end": seconds(right), "text": text})
    return events


def transcribe_events(
    input_path: Path,
    model_name: str = "base",
    *,
    max_words: int = 5,
    max_chars: int = 27,
) -> list[dict]:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        str(input_path),
        word_timestamps=True,
        vad_filter=True,
    )

    timed: list[dict] = []
    fallback_events: list[dict] = []
    for seg in segments:
        seg_words = []
        for word in list(seg.words or []):
            value = (word.word or "").strip()
            if not value:
                continue
            seg_words.append(
                {
                    "word": value,
                    "start": float(word.start if word.start is not None else seg.start),
                    "end": float(word.end if word.end is not None else seg.end),
                }
            )
        if seg_words:
            timed.extend(seg_words)
        else:
            text = (seg.text or "").strip()
            if text:
                fallback_events.append(
                    {"start": float(seg.start), "end": float(seg.end), "text": text}
                )

    events = _chunk_timed_words(
        timed,
        max_words=max_words,
        max_chars=max_chars,
    )
    if fallback_events:
        events.extend(normalize_events(fallback_events, max_words=max_words, max_chars=max_chars))
    return sorted(events, key=lambda x: float(x["start"]))


def auto_transcribe_to_srt(
    input_path: Path,
    output_path: Path,
    model_name: str = "base",
) -> Path:
    return write_srt(transcribe_events(input_path, model_name=model_name), output_path)


def write_ass(
    events: list[dict],
    output_path: Path,
    style: dict | None = None,
) -> Path:
    style = style or {}
    width = int(style.get("play_res_x", 1080))
    height = int(style.get("play_res_y", 1920))
    font_name = str(style.get("font_name", "DejaVu Sans"))
    font_size = int(style.get("font_size", 64))
    active_size = int(style.get("active_size_pct", 106))
    y = int(style.get("y", round(height * 0.67)))
    outline = float(style.get("outline", 3.0))
    shadow = float(style.get("shadow", 1.0))
    primary = _ass_color(str(style.get("primary_color", "#FFFFFF")))
    active = _ass_color(str(style.get("active_color", "#DDE9CF")))
    outline_color = _ass_color(str(style.get("outline_color", "#111111")), alpha=18)
    shadow_color = _ass_color(str(style.get("shadow_color", "#000000")), alpha=90)
    margin_lr = int(style.get("margin_lr", 95))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Premium,{font_name},{font_size},{primary},{active},{outline_color},{shadow_color},0,0,0,0,100,100,0,0,1,{outline},{shadow},5,{margin_lr},{margin_lr},0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    dialogue: list[str] = []
    for event in events:
        start = float(event.get("start", 0.0))
        end = max(start + 0.1, float(event.get("end", start + 1.0)))
        words = list(event.get("words") or _timed_words(str(event.get("text", "")), start, end))
        if not words:
            continue

        # Keep the same chunk on-screen while the active word changes.
        raw_words = [str(item["word"]).strip() for item in words]
        wrapped = _wrap_words(raw_words, max_chars=int(style.get("max_chars", 27)))
        line_break_after = []
        running = 0
        for line in wrapped.split("\n")[:-1]:
            running += len(line.split())
            line_break_after.append(running - 1)

        for active_idx, item in enumerate(words):
            item_start = max(start, float(item.get("start", start)))
            item_end = min(end, max(item_start + 0.06, float(item.get("end", end))))
            rendered: list[str] = []
            for idx, word in enumerate(raw_words):
                escaped_word = _ass_escape(word)
                if idx == active_idx:
                    rendered.append(
                        "{"
                        + f"\\c{active}\\b1\\fscx{active_size}\\fscy{active_size}"
                        + "}"
                        + escaped_word
                        + "{"
                        + f"\\c{primary}\\b0\\fscx100\\fscy100"
                        + "}"
                    )
                else:
                    rendered.append(escaped_word)
                if idx in line_break_after:
                    rendered[-1] += r"\N"

            payload = " ".join(rendered)
            prefix = (
                "{"
                + f"\\an5\\pos({width // 2},{y})\\fad(70,70)"
                + "}"
            )
            dialogue.append(
                "Dialogue: 0,"
                + _ass_stamp(item_start)
                + ","
                + _ass_stamp(item_end)
                + ",Premium,,0,0,0,,"
                + prefix
                + payload
            )

    output_path.write_text(header + "\n".join(dialogue) + "\n", encoding="utf-8")
    return output_path
