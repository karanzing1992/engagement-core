#!/usr/bin/env python3
"""Private GitHub V5 technical renderer. Source is supplied by a private Actions runner.

Real-media mode MUST have human-reviewed shot provenance and live Groq authorization.
Output is an owner-review draft, never a commercial/artistic rights certification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/"services"/"reel-engine"))
sys.path.insert(0,str(ROOT/"experiments"/"reel-engine-v5"))
from multi_renderer import render_multiple,probe_media
from v5_orchestrator import (load_system,validate_source,required_clearance,
    build_director_prompt,call_groq,validate_plan,plan_operations,Rejected)

class PrivateRunError(ValueError): pass

def digest(path):
    d=hashlib.sha256()
    with open(path,"rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):d.update(part)
    return d.hexdigest()

def verify_output(path,width,height,fps):
    p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
                     check=True,capture_output=True,text=True,timeout=30)
    obj=json.loads(p.stdout);v=next((s for s in obj["streams"] if s.get("codec_type")=="video"),{})
    a=next((s for s in obj["streams"] if s.get("codec_type")=="audio"),{})
    num,den=map(int,v.get("avg_frame_rate","0/1").split("/"))
    if (v.get("codec_name"),v.get("width"),v.get("height"),a.get("codec_name"))!=("h264",width,height,"aac"):
        raise PrivateRunError("Private draft codec/profile mismatch")
    if den==0 or abs(num/den-fps)>0.1:raise PrivateRunError("Video FPS mismatch")
    subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(path),"-f","null","-"],
                   check=True,capture_output=True,timeout=180)
    return {"sha256":digest(path),"size_bytes":path.stat().st_size,
            "width":width,"height":height,"fps":fps,"full_decode":True,"audio_codec":"aac"}

def run(meta,source,out):
    if meta.get("schema")!=1 or not isinstance(meta.get("prompt"),str) or len(meta["prompt"])<10:
        raise PrivateRunError("Missing prompt in signed private job metadata")
    if digest(source)!=meta.get("source_sha256") or source.stat().st_size!=meta.get("source_bytes"):
        raise PrivateRunError("Source SHA-256/size verification failed")
    probe=probe_media(source)
    synthetic=bool(meta.get("synthetic_selftest"))
    if not synthetic:
        rights=meta.get("rights") or {}
        if not all(rights.get(k) is True for k in
                   ("source_rights_confirmed","people_consent_confirmed","external_ai_processing_approved")):
            raise PrivateRunError("Real-media consent gate is not satisfied")
        manifest=meta.get("verified_shots")
        if not isinstance(manifest,dict) or manifest.get("provenance")!="human_reviewed":
            raise PrivateRunError("Human-reviewed source shot/timecode manifest required")
        cfg,registry=load_system(ROOT/"experiments"/"reel-engine-v5"/"v5_config.json",
                                 ROOT/"experiments"/"reel-engine-v5"/"capability_registry.json")
        shots=validate_source(manifest,cfg)
        if any(x["start_seconds"]+x["duration_seconds"]>probe["duration"]+0.01 for x in shots.values()):
            raise PrivateRunError("Shot claims exceed actual source duration")
        required_clearance(manifest,external=True)
        brand_file=ROOT/"experiments"/"reel-engine-v5"/"fixture_brand.txt"
        # Fixture brand file is NOT valid for real customers. Require explicit verified brand.
        brand=meta.get("verified_brand")
        if not isinstance(brand,str) or len(brand.strip())<25:
            raise PrivateRunError("Verified production brand context required")
        directive=build_director_prompt(cfg,shots,brand,meta["prompt"],1,"instagram_reel")
        if not os.getenv("GROQ_API_KEY"):
            raise PrivateRunError("Groq production model credential unavailable")
        creative=call_groq(cfg,directive,os.environ["GROQ_API_KEY"])
        validated=validate_plan(creative,shots,1,cfg)
        report=plan_operations(validated,registry)
        if not report["execution_ready"]:
            raise PrivateRunError("Unimplemented proposed effects: full creative plan cannot be rendered faithfully")
        sections=validated[0]["segments"]
        if len(sections)>16:
            raise PrivateRunError("Renderer supports at most 16 validated source sections")
        cuts=[{"source_index":0,"start":c["source_start_seconds"],
               "seconds":c["duration_seconds"],"loop":False} for c in sections]
        duration=sum(c["seconds"] for c in cuts)
        width,height,fps=1080,1920,30
    else:
        # Synthetic probe is deliberately NOT marked as V5 real creative operation.
        duration=min(4.0,probe["duration"]-0.2)
        if duration<3:raise PrivateRunError("Synthetic source too short")
        cuts=[{"source_index":0,"start":0,"seconds":duration,"loop":False}]
        width,height,fps=360,640,15
        report={"execution_ready":True,"deferred_operations":[]}
    out.mkdir(parents=True,exist_ok=True)
    video=out/"v5-output.mp4"
    info=render_multiple([source],video,{"target_seconds":duration,
            "width":width,"height":height,"fps":fps,"clip_plan":cuts},out/"work")
    verified=verify_output(video,width,height,fps)
    receipt={"version":"V5.1 candidate","status":"SYNTHETIC_PRIVATE_STORAGE_E2E"
             if synthetic else "PRIVATE_REAL_MEDIA_TECHNICAL_DRAFT",
             "prompt_sha256":hashlib.sha256(meta["prompt"].encode()).hexdigest(),
             "source_sha256":meta["source_sha256"],"video":verified,
             "run_duration":info["duration"],"segments":info["sections"],
             "creative_model_called":not synthetic,
             "source_provenance": "SYNTHETIC_FIXTURE" if synthetic else "human_reviewed",
             "music_rights_certified":False,"artistic_quality_certified":False,
             "public_release_certified":False,"published":False}
    (out/"v5-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--metadata",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    args=p.parse_args()
    r=run(json.loads(args.metadata.read_text()),args.source,args.output_dir)
    print(json.dumps({"status":r["status"],"video_sha256":r["video"]["sha256"]}))
if __name__=="__main__":main()
