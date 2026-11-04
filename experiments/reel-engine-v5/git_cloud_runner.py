#!/usr/bin/env python3
"""V5 synthetic-only GitHub execution: bounded V5 plan -> owned FFmpeg renderer.

This module never accepts user media, arbitrary URLs/paths, or publish requests.
A synthetic technical pass is NOT real-footage, sound-rights or artistic certification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "services" / "reel-engine"))
from multi_renderer import render_multiple  # noqa: E402
from v5_orchestrator import (Rejected, build_director_prompt, call_groq,
    load_system, plan_operations, read_json, required_clearance,
    validate_plan, validate_source)  # noqa: E402

COLORS = ("#2A5D86", "#395C39", "#916C47", "#B09A4E", "#224C49")


def run(command):
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE, text=True, timeout=180)


def fixture_plan():
    return {"versions": [{"id": "T1", "name": "Synthetic diagnostic only",
        "hook": "Technical integration", "narrative": "Not Moksha imagery",
        "emotional_arc": "not artistically reviewed",
        "segments": [
            {"shot_id": sid, "offset_seconds": 0, "duration_seconds": 2,
             "caption": "", "proposed_operations": []}
            for sid in ("S1", "S2", "S3")]}]}


def compile_edl(segments, ids):
    """No silent removal of model-suggested operations or timeline truncation."""
    if not 1 <= len(segments) <= 16:
        raise Rejected("Existing multi_renderer only supports 1-16 cuts")
    index = {sid: i for i, sid in enumerate(ids)}
    result = []
    for segment in segments:
        if segment.get("proposed_operations"):
            raise Rejected("Uncertified proposed effect may not be silently dropped")
        if segment["shot_id"] not in index:
            raise Rejected("Unknown source shot")
        result.append({"source_index": index[segment["shot_id"]],
                       "start": segment["offset_seconds"],
                       "seconds": segment["duration_seconds"], "loop": False})
    return result


def technical_preview_segments(segments):
    """Synthetic-only: log every unequipped proposed effect; render verified cuts only."""
    clean, unexecuted = [], []
    for segment in segments:
        for op in segment.get("proposed_operations", []):
            unexecuted.append({"shot_id": segment["shot_id"],
                               "name": op["name"], "parameters": op.get("parameters", {}),
                               "reason": "no_execution_adapter_invoked_in_synthetic_technical_mode"})
        clean.append(dict(segment, proposed_operations=[]))
    return clean, unexecuted


def create_synthetic_sources(folder, shots, vision_images=None):
    """Use the SAME synthetic drawings presented to Groq for multimodal runs."""
    paths = []
    for i, shot in enumerate(shots.values()):
        path = folder / ("synthetic-%02d.mp4" % i)
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        if vision_images is not None:
            image = vision_images / ("scene_%d.jpg" % (i + 1))
            if not image.is_file() or image.stat().st_size < 1024:
                raise Rejected("Groq input image missing; cannot establish visual source parity")
            command += ["-loop", "1", "-framerate", "15", "-i", str(image)]
        else:
            command += ["-f", "lavfi", "-i",
                        "color=c=%s:s=320x180:r=15" % COLORS[i % len(COLORS)]]
        command += ["-t", str(shot["duration_seconds"]), "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an", str(path)]
        run(command)
        paths.append(path)
    return paths


def verify_video(path, width, height, fps):
    raw = subprocess.check_output(["ffprobe", "-v", "error",
        "-show_format", "-show_streams", "-of", "json", str(path)], text=True, timeout=30)
    parsed = json.loads(raw)
    video = next(s for s in parsed["streams"] if s.get("codec_type") == "video")
    audio = next((s for s in parsed["streams"] if s.get("codec_type") == "audio"), None)
    if (video.get("codec_name"), video.get("pix_fmt"), video.get("width"),
            video.get("height")) != ("h264", "yuv420p", width, height):
        raise Rejected("Synthetic technical output profile mismatch")
    if not audio or audio.get("codec_name") != "aac":
        raise Rejected("AAC stream missing from private synthetic test")
    numerator, denominator = (int(x) for x in video.get("avg_frame_rate", "0/1").split("/"))
    if not denominator or abs(numerator / denominator - fps) > 0.05:
        raise Rejected("Frame-rate mismatch")
    run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"])
    return {"dimensions": [width, height], "fps": fps, "codec": "h264",
            "audio_codec": "aac", "decoded": True, "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sound": "silent diagnostic audio, NOT music or cleared soundtrack"}


def create_synthetic_frames(folder):
    """Reuse V4.2's five deterministic synthetic concepts, never private footage."""
    from PIL import Image, ImageDraw
    folder.mkdir(parents=True,exist_ok=True)
    colors=["#204E6C","#587545","#A77A4D","#D4A55B","#18382F"]
    frames=[]
    for i,color in enumerate(colors):
        img=Image.new("RGB",(360,640),color)
        d=ImageDraw.Draw(img)
        if i==0:
            for y in range(160,620,38):d.arc((12,y,340,y+110),0,180,fill="#9BC5D1",width=4)
        elif i==1:
            d.line((190,650,175,60),fill="#554735",width=24)
            for x,y in [(75,130),(230,150),(100,250),(265,300)]:
                d.ellipse((x-82,y-66,x+82,y+66),fill="#7B9852",outline="#C7D28F",width=3)
        elif i==2:
            for b in [(20,330,220,430),(120,230,335,330),(40,455,335,570)]:
                d.rounded_rectangle(b,radius=17,fill="#D4BA93",outline="#654936",width=8)
        elif i==3:
            d.ellipse((90,120,275,305),fill="#FBE7A2")
            for x in [60,105,155,220,280]:d.line((x,640,x+35,325),fill="#234438",width=28)
        else:
            for x in [30,105,200,310]:
                d.line((x,640,x-15,90),fill="#0B2923",width=29)
                d.ellipse((x-84,55,x+85,285),fill="#42684B",outline="#94A86D",width=4)
        d.rectangle((0,555,360,640),fill="#18382F")
        d.text((22,579),"SYNTHETIC TEST - "+str(i+1),fill="#F9F5EA")
        frame=folder/("scene_%d.jpg"%(i+1))
        img.save(frame,quality=83)
        frames.append(frame)
    return frames


def observe_synthetic_frames(cfg,folder):
    """Groq Qwen vision reads exact generated frames later used by the renderer."""
    from v5_orchestrator import models_for_task,call_groq_vision
    vision=models_for_task(cfg,"shot_visual_analysis")[0]
    key=os.environ.get("GROQ_API_KEY","")
    if not key:raise Rejected("Groq key required for synthetic multimodal vision")
    frames=create_synthetic_frames(folder)
    descriptions=[]
    for i,frame in enumerate(frames,1):
        visible=call_groq_vision(cfg,frame,
            "Describe the visible composition of this synthetic generated graphic only. "
            "Do not identify people, invent a location, or claim real customer footage.",key,model=vision)
        descriptions.append({"id":"S"+str(i),"visible":visible[:300]})
    return {"shots":descriptions,"_meta":{
       "model_used":vision["model"],"provider":"groq",
       "synthetic_only":True,"real_guest_data_sent":False}}


def describe_synthetic_vision(result):
    """Use only authenticated Groq model outputs as synthetic visual corroboration."""
    if not isinstance(result,dict) or not isinstance(result.get("shots"),list) or len(result["shots"])!=5:
        raise Rejected("Groq did not analyze the five synthetic frames")
    meta=result.get("_meta") or {}
    if (meta.get("synthetic_only") is not True or meta.get("provider")!="groq"
            or meta.get("model_used")!="qwen/qwen3.8-27b"
            or meta.get("real_guest_data_sent") is not False):
        raise Rejected("Vision response missing verified Groq synthetic identity")
    if any(not isinstance(item.get("visible"),str) or len(item["visible"])<8 for item in result["shots"]):
        raise Rejected("Invalid synthetic Groq visual analysis")
    brief=("Groq analysis of synthetic drawings used as actual render sources ONLY. "
        "These descriptions are unreviewed visual observations, not certified footage facts. "
        "Never claim real guest or venue images. "+
        json.dumps(result["shots"],ensure_ascii=False)[:2500])
    return brief,{"provider":"groq","model":meta["model_used"],
        "shot_count":len(result["shots"]),"synthetic_only":True,
        "real_guest_data_sent":False}



def execute(mode, destination, profile, brief=""):
    if not isinstance(brief, str) or len(brief)>600 or (brief and len(brief)<12) or any(x in brief.lower() for x in ("http://", "https://", "github_pat_", "data:video/")):
        raise Rejected("Invalid synthetic-only Cloudflare brief")
    if mode not in ("fixture", "live", "multimodal") or profile not in ("synthetic_test", "instagram_reel"):
        raise Rejected("Only bounded synthetic certification jobs are accepted")
    manifest = read_json(HERE / "synthetic_shots.json")
    if manifest.get("content_origin") != "GENERATED TEXT FIXTURE ONLY - ZERO CUSTOMER FOOTAGE":
        raise Rejected("Source identity must be the synthetic-only public fixture")
    cfg, registry = load_system(HERE / "v5_config.json", HERE / "capability_registry.json")
    shots = validate_source(manifest, cfg)
    vision_meta = {"status": "not_executed", "synthetic_only": True}
    vision_brief = ""
    destination.mkdir(parents=True,exist_ok=True)
    if mode == "multimodal":
        # All frames are synthetic, and are later used as exact render sources.
        synthetic_frames=destination/"groq-only-synthetic-frames"
        vision_brief, vision_meta = describe_synthetic_vision(
            observe_synthetic_frames(cfg,synthetic_frames))
        vision_meta["status"] = "live_synthetic_observation"
    if mode in ("live", "multimodal"):
        required_clearance(manifest, external=True)
        prompt = build_director_prompt(cfg, shots,
            (HERE / "fixture_brand.txt").read_text(encoding="utf-8"),
            "Synthetic-only owner brief: " + (brief or "Creative diagnostic") + ". One synthetic-only edit of 3 short segments. "
            "Proposed effects without an executor will be audited as unexecuted. "
            + vision_brief,
            1, profile)
        proposal = call_groq(cfg, prompt, os.environ.get("GROQ_API_KEY", ""))
    else:
        proposal = fixture_plan()
    plans = validate_plan(proposal, shots, 1, cfg)
    ops = plan_operations(plans, registry)
    # Technical preview deliberately does not claim FilmCraft/effect fidelity.
    # Every proposed operation is recorded as UNEXECUTED, not silently dropped.
    preview_segments, unexecuted = technical_preview_segments(plans[0]["segments"])
    cuts = compile_edl(preview_segments, list(shots))
    duration = sum(c["seconds"] for c in cuts)
    if duration < 3 or duration > 120:
        raise Rejected("Existing renderer duration limit")
    width, height = cfg["profiles"][profile]["dimensions"]
    fps = cfg["profiles"][profile]["fps"]
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="v5-synthetic-") as name:
        tmp = Path(name)
        vision_images = (destination/"groq-only-synthetic-frames"
                         if mode == "multimodal" else None)
        originals = create_synthetic_sources(tmp, shots, vision_images=vision_images)
        output = destination / "v5-synthetic-diagnostic.mp4"
        render = render_multiple(originals, output, {
            "target_seconds": duration, "width": width, "height": height,
            "fps": fps, "clip_plan": cuts}, tmp / "segments")
        # Existing concat/copy step can retain non-constant average frame rate.
        # Normalize *synthetic diagnostic only* before independent certification.
        normalized = tmp / "v5-synthetic-constant-fps.mp4"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(output), "-vf", "fps=%d" % fps, "-r", str(fps),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
             "-pix_fmt", "yuv420p", "-c:a", "copy",
             "-movflags", "+faststart", str(normalized)])
        normalized.replace(output)
        video = verify_video(output, width, height, fps)
    report = {"engine": "MAD Reel Engine", "version": "5.0.0",
        "status": "SYNTHETIC_TECHNICAL_CERTIFICATION_ONLY",
        "mode": mode, "profile": profile, "queued_brief_applied": bool(brief) and mode in ("live", "multimodal"), "model_inference": mode in ("live", "multimodal"),
        "vision_analysis": vision_meta,
        "synthetic_render_sources_match_groq_frames": mode == "multimodal",
        "director_planning_validated": True,
        "deferred_operations": ops["deferred_operations"],
        "unexecuted_operations": unexecuted,
        "creative_operation_fidelity": len(unexecuted) == 0,
        "render_engine": "services/reel-engine/multi_renderer.py",
        "segments": render["sections"], "duration_seconds": render["duration"],
        "real_footage_certified": False, "artistic_quality_certified": False,
        "music_licensed": False, "private_media_uploaded": False,
        "published": False, "publishing_enabled": False, "video": video}
    (destination / "v5-technical-receipt.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("fixture", "live", "multimodal"), default="fixture")
    p.add_argument("--profile", choices=("synthetic_test", "instagram_reel"),
                   default="synthetic_test")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--brief", default="", help="Synthetic-only owner creative brief; no media paths or URLs")
    opts = p.parse_args()
    result = execute(opts.mode, opts.out_dir, opts.profile, opts.brief)
    print(json.dumps({"status": result["status"],
        "sha256": result["video"]["sha256"], "bytes": result["video"]["bytes"]}))


if __name__ == "__main__":
    main()
