#!/usr/bin/env python3
"""Owner-private MAD V6 FFmpeg renderer. Validated EDL in; verified MP4 out."""
from __future__ import annotations
import argparse,hashlib,json,math,subprocess
from pathlib import Path
ENGINE="ffmpeg"
TEMPLATES={"wellness-cinema":(1.08,.05,1.06),"earth-editorial":(1.12,.03,1.04),
 "guest-story":(1.04,.02,1.02),"social-kinetic":(1.16,.04,1.10),
 "nature-minimal":(1.03,.02,1.06),"recovery-reset":(1.12,.04,1.10)}
ALLOWED=frozenset(("color_grade","title","caption"))
class RenderBlocked(RuntimeError):pass
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for b in iter(lambda:f.read(1048576),b""):h.update(b)
 return h.hexdigest()
def _exec(cmd,timeout=240):
 try:return subprocess.run(cmd,capture_output=True,check=True,timeout=timeout)
 except (OSError,subprocess.TimeoutExpired,subprocess.CalledProcessError):
  raise RenderBlocked("FFMPEG_PROCESS_FAILED") from None
def verify_backend():
 _exec(["ffmpeg","-hide_banner","-version"],12)
 _exec(["ffprobe","-hide_banner","-version"],12)
 return {"engine":ENGINE,"probe":"ffprobe"}
def probe(path,require_video=True):
 raw=_exec(["ffprobe","-v","error","-show_entries",
  "format=duration:stream=codec_type,codec_name,width,height","-of","json",str(path)],25)
 try:
  info=json.loads(raw.stdout)
  duration=float(info["format"]["duration"])
  video=next((s for s in info["streams"] if s.get("codec_type")=="video"),None)
  audio=next((s for s in info["streams"] if s.get("codec_type")=="audio"),None)
  if not math.isfinite(duration) or duration<=.4 or (require_video and not video) or (not require_video and not audio):raise ValueError()
 except (KeyError,ValueError,TypeError):raise RenderBlocked("FFPROBE_MEDIA_INVALID") from None
 return {"duration":duration,"video":video,"audio":audio}
def choose_template(brief):
 b=(brief or "").casefold()
 for words,choice in ((("guest","testimonial","interview"),"guest-story"),
  (("sauna","ice bath","recovery","reset"),"recovery-reset"),
  (("hype","dynamic","party"),"social-kinetic"),
  (("forest","jungle","nature","earth"),"nature-minimal"),
  (("luxury","editorial","premium"),"earth-editorial")):
  if any(w in b for w in words):return choice
 return "wellness-cinema"
def _validate(spec):
 try:
  work=Path(spec["workdir"]).resolve();src=Path(spec["source"]).resolve();out=Path(spec["output"]).resolve()
  width,height,fps=(spec[x] for x in ("width","height","fps"))
 except (KeyError,TypeError):raise RenderBlocked("FFMPEG_SPEC_MISSING") from None
 if not work.is_dir() or src.parent!=work or out.parent!=work or src==out:raise RenderBlocked("FFMPEG_PRIVATE_WORKDIR_INVALID")
 if not src.is_file() or sha256(src)!=spec.get("source_sha256"):raise RenderBlocked("FFMPEG_SOURCE_HASH_INVALID")
 if (width,height,fps) not in ((1080,1920,30),(720,1280,30),(480,270,24)):raise RenderBlocked("FFMPEG_PROFILE_INVALID")
 template=spec.get("template_id","wellness-cinema")
 if template not in TEMPLATES:raise RenderBlocked("FFMPEG_TEMPLATE_INVALID")
 cuts,ops=spec.get("cuts"),spec.get("operations")
 if not isinstance(cuts,list) or not isinstance(ops,list) or len(cuts)!=len(ops) or not 1<=len(cuts)<=16:
  raise RenderBlocked("FFMPEG_EDL_INVALID")
 source=probe(src);total=0.
 for cut,operations in zip(cuts,ops):
  if not isinstance(cut,dict) or not isinstance(operations,list) or len(operations)>16:raise RenderBlocked("FFMPEG_EDL_INVALID")
  start,seconds=cut.get("start"),cut.get("seconds")
  if type(start) not in (float,int) or type(seconds) not in (float,int) or not math.isfinite(start) or not math.isfinite(seconds) or start<0 or not .4<=seconds<=120 or start+seconds>source["duration"]+.12:
   raise RenderBlocked("FFMPEG_SOURCE_BOUNDS_OR_TIMECODE")
  total+=round(seconds*fps)/fps
  for op in operations:
   if not isinstance(op,dict) or op.get("name") not in ALLOWED or not isinstance(op.get("parameters"),dict):
    raise RenderBlocked("FFMPEG_EFFECT_NOT_ALLOWLISTED")
   p=op["parameters"]
   if op["name"]=="color_grade":
    x=p.get("contrast",0)
    if type(x) not in (float,int) or not math.isfinite(x) or abs(x)>100:raise RenderBlocked("FFMPEG_GRADE_INVALID")
   else:
    txt=p.get("text")
    if not isinstance(txt,str) or not 1<=len(txt.strip())<=90 or any(ord(c)<32 for c in txt):
     raise RenderBlocked("FFMPEG_TITLE_INVALID")
 hook=spec.get("hook","")
 if not isinstance(hook,str) or len(hook)>90 or any(ord(c)<32 for c in hook):
  raise RenderBlocked("FFMPEG_HOOK_INVALID")
 if total<1 or total>120:raise RenderBlocked("FFMPEG_DURATION_INVALID")
 if spec.get("transition_style","none") not in ("none","dip-to-black"):
  raise RenderBlocked("FFMPEG_TRANSITION_NOT_ALLOWLISTED")
 if spec.get("dialogue_priority"):
  if source["audio"] is None:raise RenderBlocked("V7_DIALOGUE_SOURCE_AUDIO_MISSING")
  if spec.get("preserve_full_source"):
   cursor=0.0
   for cut in cuts:
    if abs(cut["start"]-cursor)>.07:
     raise RenderBlocked("V7_DIALOGUE_TIMELINE_GAP_OR_REORDER")
    cursor=cut["start"]+cut["seconds"]
   if abs(cursor-source["duration"])>.12:
    raise RenderBlocked("V7_DIALOGUE_SOURCE_DURATION_TRIMMED")
 music=None
 if spec.get("music") is not None:
  music=Path(spec["music"]).resolve()
  rights=spec.get("music_rights")
  # Separate evidence bases: approved original human review OR a rechecked
  # current Commons file/license API response. Never equate catalog search
  # metadata with verified commercial adaptation rights.
  manual=isinstance(rights,dict) and rights.get("human_verified") is True
  automatic=(isinstance(rights,dict) and
    rights.get("automatic_source_verified") is True and
    rights.get("verification_method")=="commons_api_live" and
    str(rights.get("original_source_url","")).startswith("https://commons.wikimedia.org/wiki/File:") and
    rights.get("source_license_proof_url")==rights.get("original_source_url") and
    str(rights.get("original_license_url","")).startswith("https://creativecommons.org/") and
    isinstance(rights.get("credit_text"),str) and bool(rights["credit_text"].strip()))
  if (music.parent!=work or not music.is_file() or sha256(music)!=spec.get("music_sha256") or
      not (manual or automatic) or
      rights.get("license") not in ("CC0","PDM","CC BY") or
      not str(rights.get("original_source_url","")).startswith("https://")):
   raise RenderBlocked("FFMPEG_MUSIC_RIGHTS_UNVERIFIED")
  if rights["license"]=="CC BY" and rights.get("attribution_approved") is not True:
   raise RenderBlocked("FFMPEG_ATTRIBUTION_REQUIRED")
  if probe(music,require_video=False)["duration"]<total-.1:
   raise RenderBlocked("FFMPEG_MUSIC_TOO_SHORT")
 return work,src,out,music,source,total
def render(spec):
 verify_backend()
 work,src,out,music,source,total=_validate(spec)
 width,height,fps=(spec[x] for x in ("width","height","fps"))
 contrast,bright,sat=TEMPLATES[spec.get("template_id","wellness-cinema")]
 parts=[];effects=0
 for idx,(cut,ops) in enumerate(zip(spec["cuts"],spec["operations"])):
  secs=round(cut["seconds"]*fps)/fps
  part=work/("v6-cut-%02d.mp4"%idx)
  vf=[f"scale={width}:{height}:force_original_aspect_ratio=increase",f"crop={width}:{height}",
      "setsar=1",f"fps={fps}",f"eq=contrast={contrast}:brightness={bright}:saturation={sat}"]
  # Interior video-only fades: keep every source frame and all original audio.
  if spec.get("transition_style")=="dip-to-black" and len(spec["cuts"])>1:
   edge=min(.22,secs/8)
   if idx>0:vf.append(f"fade=t=in:st=0:d={edge:.3f}")
   if idx<len(spec["cuts"])-1:vf.append(f"fade=t=out:st={secs-edge:.3f}:d={edge:.3f}")
  for j,op in enumerate(ops):
   if op["name"]=="color_grade":
    vf.append("eq=contrast=%.4f"%max(.6,min(1.4,1+op["parameters"].get("contrast",0)/300)))
   else:
    txt=work/("v6-text-%02d-%02d.txt"%(idx,j))
    txt.write_text(op["parameters"]["text"],encoding="utf8")
    vf.append("drawtext=textfile='%s':fontcolor=white:fontsize=%d:box=1:boxcolor=black@0.3:boxborderw=12:x=(w-text_w)/2:y=h*0.72"%(txt,52 if width>800 else 34))
   effects+=1
  if idx==0 and spec.get("hook"):
   title=work/"v6-hook.txt";title.write_text(spec["hook"],encoding="utf8")
   vf.append("drawtext=textfile='%s':fontcolor=white:fontsize=%d:box=1:boxcolor=black@0.28:boxborderw=10:x=(w-text_w)/2:y=h*0.25:enable='between(t,0,%.2f)'"%(title,64 if width>800 else 38,min(2.4,secs)))
   effects+=1
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(cut["start"]),"-t",str(secs),"-i",str(src)]
  if source["audio"] is None:cmd+=["-f","lavfi","-t",str(secs),"-i","anullsrc=channel_layout=stereo:sample_rate=48000"]
  cmd+=["-vf",",".join(vf),"-map","0:v:0","-map","0:a:0" if source["audio"] else "1:a:0",
        "-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-r",str(fps),
        "-frames:v",str(round(secs*fps)),"-movflags","+faststart",str(part)]
  _exec(cmd,min(450,max(50,int(secs*18))));parts.append(part)
 playlist=work/"v6-concat.txt"
 playlist.write_text("".join("file '%s'\n"%p.name for p in parts))
 joined=work/"v6-joined.mp4"
 _exec(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(playlist),"-c","copy",str(joined)],90)
 fade=min(1.,total/5)
 voice_priority=spec.get("dialogue_priority") is True
 if music:
  # V7 regression fix: the old [source .25, music .70] mix buried owner speech.
  # Source bed is NOT attenuated when dialogue is protected; music stays ~-23 dB.
  source_input=1 if voice_priority else 0
  source_level=1.0 if voice_priority else .85
  music_input=2 if voice_priority else 1
  music_level=.07 if voice_priority else .20
  filt=(f"[{source_input}:a]volume={source_level:.2f}[voice];"
        f"[{music_input}:a]atrim=duration={total:.3f},volume={music_level:.2f},"
        f"afade=t=in:st=0:d={fade:.3f},"
        f"afade=t=out:st={total-fade:.3f}:d={fade:.3f}[mus];"
        "[voice][mus]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.98[a]")
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(joined)]
  if voice_priority:cmd+=["-i",str(src)]
  cmd+=["-i",str(music),"-filter_complex",filt,
        "-map","0:v:0","-map","[a]"]
 elif voice_priority:
  # Uninterrupted source audio bypasses stitched/trimmed shot audio completely.
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(joined),
       "-i",str(src),"-map","0:v:0","-map","1:a:0"]
 else:
  cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(joined),
       "-af","afade=t=in:st=0:d=%.3f,afade=t=out:st=%.3f:d=%.3f"%(fade,total-fade,fade),
       "-map","0:v:0","-map","0:a:0"]
 cmd+=["-c:v","copy","-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
       "-t",str(total),"-movflags","+faststart",str(out)]
 _exec(cmd,120)
 meta=probe(out)
 if (meta["audio"] is None or meta["video"].get("codec_name")!="h264" or meta["audio"].get("codec_name")!="aac" or
     (meta["video"].get("width"),meta["video"].get("height"))!=(width,height) or abs(meta["duration"]-total)>.25):
  raise RenderBlocked("FFMPEG_OUTPUT_STREAM_OR_DURATION_INVALID")
 _exec(["ffmpeg","-hide_banner","-v","error","-xerror","-i",str(out),"-f","null","-"],300)
 for i,at in enumerate((.2,total/2,max(.2,total-.25))):
  frame=work/("v6-frame-%d.jpg"%i)
  _exec(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",str(at),"-i",str(out),"-frames:v","1","-q:v","3",str(frame)],35)
  if not frame.is_file() or frame.stat().st_size<1024:raise RenderBlocked("FFMPEG_FRAME_DECODE_INVALID")
 return {"engine":ENGINE,"rendered":True,"ffmpeg_invocations":len(parts)+5,
         "video_stream_verified":True,"audio_stream_verified":True,"full_decode_passed":True,
         "output_audio_verified":True,"visual_presence_check":{"visible":True,"frames_examined":3},
         "audio_mode":"licensed_music" if music else "source_ambience_only","music_mixed":bool(music),
         "music_sha256":sha256(music) if music else None,"audio_rights_verified":bool(music),
         "duration_seconds":meta["duration"],"width":width,"height":height,"fps":fps,
         "operations_requested":sum(len(x) for x in spec["operations"]),"operations_command_accepted":effects,
         "operations_visually_verified":0,
         "transition_style":spec.get("transition_style","none"),
         "transition_boundaries_applied":(len(parts)-1) if spec.get("transition_style")=="dip-to-black" else 0,
         "transitions_independently_reviewed":False,
         "dialogue_priority":voice_priority,
         "source_audio_unattenuated":voice_priority,
         "source_duration_preserved":bool(voice_priority and spec.get("preserve_full_source")),
         "music_gain_relative_to_source":(.07 if voice_priority else .20) if music else None,
         "independent_visual_and_audio_review":"PENDING",
         "creative_complete":False,"sha256":sha256(out),"bytes":out.stat().st_size,
         "published":False,"owner_approval":False}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--spec",required=True);p.add_argument("--receipt",required=True)
 a=p.parse_args()
 try:
  receipt=render(json.loads(Path(a.spec).read_text()))
  Path(a.receipt).write_text(json.dumps(receipt,indent=2))
  print("MAD_V6_FFMPEG_PRIVATE_VERIFIED_PASS")
 except Exception as exc:
  import sys
  print("MAD_V6_FFMPEG_BLOCKED "+(str(exc) if isinstance(exc,RenderBlocked) else "UNCLASSIFIED"),file=sys.stderr)
  raise SystemExit(2)
