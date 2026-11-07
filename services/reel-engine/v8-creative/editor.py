"""V8 controlled FFmpeg editor: typed plan, never model-generated shell commands."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"v6-kv-gateway"))
import ffmpeg_v6_adapter as legacy
from director import CreativeBlocked,validate_plan

def _run(cmd,timeout=180):return legacy._exec(cmd,timeout)

def render(evidence,proposal,workdir,output,*,music=None,music_rights=None,width=1080,height=1920,fps=30):
    plan=validate_plan(evidence,proposal)
    work=Path(workdir).resolve();target=Path(output).resolve()
    if not work.is_dir() or target.parent!=work:raise CreativeBlocked("V8_PRIVATE_WORKDIR_REQUIRED")
    source=Path(evidence["source"]["path"]).resolve()
    if source.parent!=work or source==target:raise CreativeBlocked("V8_SOURCE_SCOPE_VIOLATION")
    if (width,height,fps) not in ((1080,1920,30),(720,1280,30),(480,270,24)):
        raise CreativeBlocked("V8_PROFILE_NOT_ALLOWLISTED")
    audio=plan["audio"];owner=evidence["owner_intent"]
    music=Path(music).resolve() if music else None
    if audio["music_gain"]>0 and not music:raise CreativeBlocked("V8_MUSIC_FILE_REQUIRED")
    if music and audio["music_gain"]==0:raise CreativeBlocked("V8_MUSIC_NOT_AUTHORIZED")
    cuts=[{"start":s["start"],"seconds":s["end"]-s["start"]} for s in plan["segments"]]
    gate={"source":str(source),"source_sha256":evidence["source"]["sha256"],
     "workdir":str(work),"output":str(target),"width":width,"height":height,"fps":fps,
     "template_id":"wellness-cinema","cuts":cuts,"operations":[[] for _ in cuts],
     "music":str(music) if music else None,"music_sha256":legacy.sha256(music) if music else None,
     "music_rights":music_rights}
    legacy._validate(gate) # preserve V7 source SHA, rights and source duration validation
    segments=plan["segments"];durations=[round((s["end"]-s["start"])*fps)/fps for s in segments]
    dissolve=[s["transition"]=="dissolve" for s in segments[1:]]
    if any(dissolve) and not all(dissolve):raise CreativeBlocked("V8_MIXED_TRANSITIONS_UNSUPPORTED")
    if any(dissolve) and (owner["preserve_full_source"] or owner["dialogue_priority"] or audio["preserve_source"]):
        raise CreativeBlocked("V8_DISSOLVE_WOULD_DISRUPT_SOURCE_AUDIO")
    overlap=min(.28,min(durations)/5) if any(dissolve) else 0.
    starts=[s["start"] for s in segments];ends=[s["end"] for s in segments]
    if audio["preserve_source"] and any(abs(starts[i]-ends[i-1])>.05 for i in range(1,len(starts))):
        raise CreativeBlocked("V8_SOUND_TIMELINE_GAP_REQUIRES_SPEECH_MAP")
    parts=[]
    for i,(seg,seconds) in enumerate(zip(segments,durations)):
        part=work/("v8-part-%02d.mp4"%i)
        vf=[f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}","setsar=1",f"fps={fps}"]
        vf.append({"natural":"eq=contrast=1.02:saturation=1.02",
         "cinematic_warm":"eq=contrast=1.08:saturation=1.06:brightness=0.012",
         "soft_contrast":"eq=contrast=1.04:saturation=0.95",
         "monochrome":"hue=s=0,eq=contrast=1.08"}[seg["grade"]])
        edge=min(.18,seconds/8)
        if seg["transition"]=="dip-to-black" and i>0:
            vf.append(f"fade=t=in:st=0:d={edge:.3f}")
        if i<len(segments)-1 and segments[i+1]["transition"]=="dip-to-black":
            vf.append(f"fade=t=out:st={seconds-edge:.3f}:d={edge:.3f}")
        if seg.get("text"):
            file=work/("v8-text-%02d.txt"%i);file.write_text(seg["text"],encoding="utf8")
            vf.append("drawtext=textfile='%s':fontcolor=white:fontsize=%d:box=1:"
              "boxcolor=black@0.4:boxborderw=12:x=(w-text_w)/2:y=h*0.72"%
              (file,52 if width>=720 else 24))
        _run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(seg["start"]),
         "-t",str(seconds),"-i",str(source),"-vf",",".join(vf),"-an","-c:v","libx264",
         "-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-r",str(fps),
         "-frames:v",str(round(seconds*fps)),str(part)],min(450,max(35,int(seconds*16))))
        parts.append(part)
    picture=work/"v8-edited-video.mp4"
    if len(parts)==1:
        _run(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(parts[0]),
         "-map","0:v:0","-c","copy",str(picture)],80)
    elif all(dissolve):
        inputs=sum((["-i",str(p)] for p in parts),[])
        graph=[];last="[0:v]";elapsed=durations[0]
        for i in range(1,len(parts)):
            label=f"[x{i}]"
            graph.append(f"{last}[{i}:v]xfade=transition=fade:duration={overlap:.3f}:"
              f"offset={elapsed-overlap:.3f}{label}")
            last=label;elapsed+=durations[i]-overlap
        _run(["ffmpeg","-hide_banner","-loglevel","error","-y",*inputs,
         "-filter_complex",";".join(graph),"-map",last,"-an","-c:v","libx264",
         "-preset","veryfast","-crf","23","-pix_fmt","yuv420p",str(picture)],240)
    else:
        playlist=work/"v8-concat.txt"
        playlist.write_text("".join("file '%s'\n"%p.name for p in parts))
        _run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
         "-i",str(playlist),"-c","copy",str(picture)],90)
    target_seconds=sum(durations)-overlap*sum(dissolve)
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(picture)]
    if audio["preserve_source"]:
        cmd+=["-ss",str(starts[0]),"-t",str(target_seconds),"-i",str(source)]
    else:
        cmd+=["-f","lavfi","-t",str(target_seconds),"-i",
              "anullsrc=channel_layout=stereo:sample_rate=48000"]
    if music:
        cmd+=["-i",str(music)]
        gain=audio["music_gain"]
        # amix normalize=0 prevents the historical 50% source reduction.
        if owner["dialogue_priority"] and audio["preserve_source"]:
            # The speech itself keys the soundtrack. Music returns between words;
            # no static source gain reduction or auto-amix normalization.
            graph=("[1:a]asplit=2[original][speech_key];"
              f"[2:a]atrim=duration={target_seconds:.3f},volume={gain:.3f}[bed];"
              "[bed][speech_key]sidechaincompress=threshold=0.02:ratio=12:"
              "attack=18:release=220[ducked];"
              "[original][ducked]amix=inputs=2:duration=first:normalize=0,"
              "alimiter=limit=0.98[mixed]")
        else:
            graph=("[1:a]volume=1[original];"
              f"[2:a]atrim=duration={target_seconds:.3f},volume={gain:.3f}[track];"
              "[original][track]amix=inputs=2:duration=first:normalize=0,"
              "alimiter=limit=0.98[mixed]")
        cmd+=["-filter_complex",graph,"-map","0:v:0","-map","[mixed]"]
    else:
        cmd+=["-map","0:v:0","-map","1:a:0"]
    cmd+=["-c:v","copy","-c:a","aac","-b:a","192k","-ar","48000","-ac","2",
          "-t",str(target_seconds),"-movflags","+faststart",str(target)]
    _run(cmd,150)
    info=legacy.probe(target)
    if (info["video"] is None or info["audio"] is None or
        abs(info["duration"]-target_seconds)>.22):
        raise CreativeBlocked("V8_OUTPUT_AUDIO_VIDEO_DURATION_MISMATCH")
    _run(["ffmpeg","-hide_banner","-v","error","-xerror","-i",str(target),
          "-f","null","-"],220)
    return {"engine":"ffmpeg","version":"v8-creative-beta",
     "source_sha256":evidence["source"]["sha256"],"plan_sha256":plan["creative_plan_sha256"],
     "rendered":True,"full_decode_passed":True,"output_sha256":legacy.sha256(target),
     "output_bytes":target.stat().st_size,"duration_seconds":info["duration"],
     "transition_count_compiled":sum(s["transition"]!="cut" for s in segments[1:]),
     "transition_types_compiled":sorted({s["transition"] for s in segments[1:]}),
     "music_mixed":bool(music),"music_rights_admitted":bool(music_rights) if music else None,
     "source_audio_preserved_by_contract":bool(audio["preserve_source"]),
     "music_gain":audio["music_gain"] if music else 0,
     "music_ducking":"speech_sidechain" if music and owner["dialogue_priority"] else "none",
     "actual_artistic_review":"PENDING",
     "speech_intelligibility_verified":False,"published":False,"owner_approval":False}
