#!/usr/bin/env python3
"""Read-only source JPEG sampling using FilmCraft's native file.exportFrame.

Never invokes FFmpeg, exports full source footage, or stores frames as GitHub artifacts.
Caller is responsible for obtaining explicit external-vision permission on guest material.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import os
import re
import filmcraft_v6_adapter as filmcraft

class FrameSamplingBlocked(ValueError): pass

def export_native_source_frames(*,cli:str,workdir:Path,source:Path,duration:float,max_frames:int=3)->list[dict]:
    if not isinstance(duration,(int,float)) or not 3<=duration<=480:
        raise FrameSamplingBlocked("Video duration not verified")
    if max_frames not in (1,2,3):raise FrameSamplingBlocked("Maximum three private frames")
    if not source.is_file() or source.stat().st_size<1024:
        raise FrameSamplingBlocked("Private source video missing")
    target=workdir/"sampled-frames"
    target.mkdir(mode=0o700,parents=True,exist_ok=True)
    m=filmcraft.MCP(cli,workdir)
    try:
        check=m.cmd("mediaBrowser.probe",{"path":str(source.resolve())}).get("info",{})
        if not check.get("video"):raise FrameSamplingBlocked("FilmCraft native video probe failed")
        m.tool("media_import",{"paths":[str(source.resolve())]})
        item=filmcraft.find_item(m.tool("project_inspect",{}),source.name)
        if not isinstance(item,int):raise FrameSamplingBlocked("Native media item missing")
        positions=[min(max(.25,duration*f),duration-.10) for f in (.18,.50,.82)[:max_frames]]
        result=[]
        for i,sec in enumerate(positions):
            path=target/("filmcraft-source-%02d.jpeg"%i)
            m.cmd("file.exportFrame",{"target":"source","item":item,
                 "format":"jpeg","depth":8,
                 "time":int(sec*filmcraft.TICKS_PER_SECOND),
                 "path":str(path.resolve())})
            if not path.is_file() or not 1024<=path.stat().st_size<=60000:
                raise FrameSamplingBlocked("Native JPEG missing or outside 60KB privacy budget")
            head=path.read_bytes()
            if not (head.startswith(bytes((255,216))) and head.endswith(bytes((255,217)))):
                raise FrameSamplingBlocked("Native frame is not JPEG")
            result.append({"shot_id":"s1","seconds":round(sec,3),"path":str(path),
                 "bytes":path.stat().st_size,"sha256":hashlib.sha256(head).hexdigest(),
                 "generated_by":"FilmCraft.file.exportFrame"})
        return result
    finally:m.close()
