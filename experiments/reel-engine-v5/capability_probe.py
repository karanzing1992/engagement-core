#!/usr/bin/env python3
"""Read-only local creative-tool discovery for Reel Engine V5.

FFmpeg and FilmCraft capability claims must be based on runnable installed
binaries; model API claims require authenticated provider metadata. Does not
execute generated edit commands, import any media, read API keys or publish.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

FILTER_RE = re.compile(r"^\s*[TSC\.]{3}\s+([A-Za-z0-9_]+)\s")
ENCODER_RE = re.compile(r"^\s*[A-Z\.]{6}\s+([A-Za-z0-9_]+)\s")


def bounded_command(cmd, timeout=15):
    r=subprocess.run(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     text=True,timeout=timeout,check=False)
    if r.returncode != 0:
        raise RuntimeError("Tool discovery failed; exit %s" % r.returncode)
    return (r.stdout or r.stderr)[:350000]


def probe_ffmpeg(ffmpeg="ffmpeg", ffprobe="ffprobe", runner=bounded_command):
    if not shutil.which(ffmpeg) or not shutil.which(ffprobe):
        return {"installed":False,"discovered":False}
    try:
        v=runner([ffmpeg,"-version"],timeout=12).splitlines()[0]
        fl=runner([ffmpeg,"-hide_banner","-filters"],timeout=12)
        enc=runner([ffmpeg,"-hide_banner","-encoders"],timeout=12)
        filters=sorted(set(x for x in FILTER_RE.findall(fl)))
        encoders=sorted(set(x for x in ENCODER_RE.findall(enc)))
        return {"installed":True,"discovered":True,"version":v[:130],
                "filter_count":len(filters),"encoder_count":len(encoders),
                "filters":filters,"encoders":encoders,
                "h264_encoder_available":"libx264" in encoders,
                "fade_filter_available":"fade" in filters,
                "xfade_filter_available":"xfade" in filters,
                "drawtext_filter_available":"drawtext" in filters}
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        return {"installed":True,"discovered":False,"error":"read-only probe failed"}


def probe_filmcraft(binary=None, runner=bounded_command):
    if not binary or not Path(binary).is_file():
        return {"installed":False,"discovered":False}
    try:
        version=runner([binary,"--version"],timeout=15).strip()[:130]
        data=json.loads(runner([binary,"commands","--json"],timeout=25))
        a=data.get("commands",data) if isinstance(data,dict) else data
        ids=sorted({v.get("id","") for v in a if isinstance(v,dict) and v.get("id")})
        return {"installed":True,"discovered":True,
                "version":version,"command_count":len(ids),"commands":ids}
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        return {"installed":True,"discovered":False,"error":"read-only probe failed"}


def report(registry, ffmpeg=None, filmcraft=None):
    result={"version":"5.0.0","read_only":True,
            "source_video_processed":False,"rendered":False,
            "model_calls":0,"tools":{}}
    for a in registry["adapters"]:
        ident=a["id"]
        if ident == "ffmpeg_core":
            result["tools"][ident]=ffmpeg if ffmpeg is not None else probe_ffmpeg()
        elif ident == "filmcraft_mcp":
            result["tools"][ident]=filmcraft if filmcraft is not None else {"installed":False,"discovered":False}
        else:
            result["tools"][ident]={"installed":"external-provider",
                                     "discovered":False,
                                     "verified_from":"prior_release_receipts_only"}
    result["verified_edit_capabilities"]=[]
    result["future_or_unverified_capabilities"]=[]
    for op in registry["operations"]:
        if op["status"]=="verified":
            result["verified_edit_capabilities"].append(op["name"])
        else:
            result["future_or_unverified_capabilities"].append(op["name"])
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",default=str(Path(__file__).parent/"capability_registry.json"))
    p.add_argument("--filmcraft-cli",default=None)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    x=json.loads(Path(a.registry).read_text())
    result=report(x,filmcraft=probe_filmcraft(a.filmcraft_cli))
    f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":"PASS", "ffmpeg_discovered":
          result["tools"]["ffmpeg_core"].get("discovered"),
          "filmcraft_discovered":result["tools"]["filmcraft_mcp"].get("discovered"),
          "tool_capability_count":len(result["verified_edit_capabilities"])+
                                  len(result["future_or_unverified_capabilities"]),
          "output":str(f)}))
if __name__=="__main__":
    main()
