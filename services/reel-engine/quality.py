from __future__ import annotations
import json, math, subprocess
from pathlib import Path

def _ffprobe(path: Path) -> dict:
    out=subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],text=True)
    return json.loads(out)

def media_preflight(path: Path, *, max_seconds: float = 180.0) -> dict:
    data=_ffprobe(path)
    video=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),None)
    if not video: raise ValueError("Input has no video stream")
    duration=float(data.get("format",{}).get("duration") or video.get("duration") or 0)
    if duration<=0: raise ValueError("Input duration is invalid")
    if duration>max_seconds: raise ValueError(f"Input exceeds configured maximum of {max_seconds}s")
    w,h=int(video.get("width",0)),int(video.get("height",0))
    return {"duration":duration,"width":w,"height":h,"codec":video.get("codec_name"),"has_audio":any(s.get("codec_type")=="audio" for s in data.get("streams",[]))}

def detect_silence(path: Path, *, noise_db: float=-38.0, min_seconds: float=0.45) -> list[dict]:
    p=subprocess.run(["ffmpeg","-hide_banner","-i",str(path),"-af",f"silencedetect=noise={noise_db}dB:d={min_seconds}","-f","null","-"],capture_output=True,text=True)
    spans=[]; start=None
    for line in p.stderr.splitlines():
        if "silence_start:" in line:
            try:start=float(line.rsplit("silence_start:",1)[1].strip())
            except ValueError:start=None
        elif "silence_end:" in line and start is not None:
            try:end=float(line.split("silence_end:",1)[1].split("|",1)[0].strip()); spans.append({"start":start,"end":end,"duration":max(0,end-start)})
            except ValueError:pass
            start=None
    return spans

def retention_report(duration: float, captions: list[dict], silence: list[dict], *, hook_window: float=2.5) -> dict:
    spoken=sum(max(0,float(x.get("end",0))-float(x.get("start",0))) for x in captions if x.get("kind")!="credit")
    silent=sum(float(x["duration"]) for x in silence)
    first_text=min((float(x.get("start",999)) for x in captions if str(x.get("text","")).strip()),default=999)
    return {
      "hook_present": first_text <= hook_window,
      "first_text_seconds": None if first_text==999 else round(first_text,3),
      "caption_coverage": round(min(1.0,spoken/max(duration,0.001)),3),
      "silence_ratio": round(min(1.0,silent/max(duration,0.001)),3),
      "warnings": (["late-hook"] if first_text>hook_window else []) + (["excess-dead-air"] if silent/max(duration,0.001)>0.18 else [])
    }
