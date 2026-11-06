#!/usr/bin/env python3
"""FilmCraft-only source frame sampling for user-approved Gemini vision.

Samples up to 3 frames with the native FilmCraft renderer, never FFmpeg.
All image bytes are stored only in the GitHub runner's ephemeral temp directory.
"""
from __future__ import annotations
import base64
from hashlib import sha256
from pathlib import Path
import subprocess
import tempfile

from filmcraft_v6_adapter import MCP, find_item, TICKS_PER_SECOND, FilmCraftError

PNG_SIG=b"\x89PNG\r\n\x1a\n"

def sample_video_frames(source: Path, *, cli: str, workdir: Path,
                        duration: float, external_ai_consent: bool,
                        max_samples: int=3) -> list[dict]:
    if external_ai_consent is not True:
        raise FilmCraftError("User consent for external AI frame processing missing")
    if max_samples not in (1,2,3) or not (3 <= duration <= 480):
        raise FilmCraftError("Invalid private source frame sampling limits")
    root=workdir/"gemini-frames"
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    project=root/"sample.fcproj"
    m=MCP(cli,root)
    try:
        probe=m.cmd("mediaBrowser.probe",{"path":str(source.resolve())}).get("info",{})
        if not probe.get("video"):
            raise FilmCraftError("Private source does not contain video")
        actual=probe.get("duration",0)/TICKS_PER_SECOND
        if abs(actual-duration)>0.15:
            raise FilmCraftError("Video metadata and native probe disagree")
        m.cmd("file.newSequence",{"name":"V6_GEMINI_PRIVATE_FRAME_SAMPLER",
          "width":480,"height":270,"fps":24,"video":1,"audio":0})
        m.tool("media_import",{"paths":[str(source.resolve())]})
        source_id=find_item(m.tool("project_inspect",{}),source.name)
        if not isinstance(source_id,int):
            raise FilmCraftError("Native video import not confirmed for frame sampling")
        placed=m.cmd("timeline.place",{"item":source_id,"track":"V1","seconds":0.0,
           "sourceIn":{"seconds":0.0},"duration":{"seconds":duration},
           "video":True,"audio":False,"matchSequence":False})
        if not placed.get("clips"):
            raise FilmCraftError("FilmCraft could not stage native source sample timeline")
        m.cmd("file.saveAs",{"path":str(project)})
    finally:
        m.close()
    times=[min(0.5,duration/4),duration/2,max(duration-0.5,0.5)]
    times=sorted(set(round(max(0.0,min(t,duration-0.15)),2) for t in times))
    frames=[]
    try:
        for i,t in enumerate(times[:max_samples]):
            path=root/("frame-"+str(i)+".png")
            p=subprocess.run([cli,"--project",str(project),"render",
                 "--seconds",str(t),"--out",str(path)],
                 capture_output=True,text=True,timeout=70,check=False)
            if p.returncode!=0:
                raise FilmCraftError("Native FilmCraft frame export failed")
            raw=path.read_bytes()
            if not raw.startswith(PNG_SIG) or not 100<=len(raw)<=850000:
                raise FilmCraftError("Native FilmCraft frame PNG failed sanity/size gate")
            frames.append({"shot_id":"s1","at_seconds":t,"mime_type":"image/png",
                "sha256":sha256(raw).hexdigest(),
                "data_b64":base64.b64encode(raw).decode("ascii")})
        return frames
    finally:
        for p in root.glob("frame-*.png"):p.unlink(missing_ok=True)
        project.unlink(missing_ok=True)
