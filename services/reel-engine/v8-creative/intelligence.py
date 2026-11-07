"""V8 source intelligence: observable media evidence, not fabricated scene descriptions."""
from __future__ import annotations
import hashlib,json,math,re,subprocess
from pathlib import Path

class SourceBlocked(ValueError): pass

def _exec(command,timeout=60):
    try: return subprocess.run(command,check=True,capture_output=True,timeout=timeout)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError):
        raise SourceBlocked("V8_MEDIA_ANALYSIS_FAILED") from None

def hash_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as source:
        for block in iter(lambda:source.read(1048576),b""):h.update(block)
    return h.hexdigest()

def intent(brief):
    if not isinstance(brief,str) or not 3<=len(brief)<=2000:raise SourceBlocked("V8_BRIEF_INVALID")
    s=brief.casefold()
    dialogue=bool(re.search(r'\b(dialog(?:ue)?s?|speech|spoken|talking|narrat\w*|voice|interview|conversation)\b',s) or
        re.search(r'(?:keep|preserve|retain|prioritize|clear).{0,18}audio',s) or
        re.search(r'audio.{0,18}(?:important|clear|preserv|keep)',s))
    duration=bool(re.search(r"(?:don't|dont|do not|never)\s+(?:shorten|trim|cut)|full[ -]length|entire (?:clip|video)|keep (?:all|full|original) (?:duration|runtime|length)",s))
    no_music=bool(re.search(r'(?:no|without|remove|avoid)\s+(?:background\s+)?music',s))
    no_transitions=bool(re.search(r'(?:no|without|avoid)\s+transitions?',s))
    remove_source=bool(re.search(r'(?:remove|replace|mute|discard|without|no)\s+(?:all\s+)?(?:original|source)\s+audio',s))
    if dialogue and remove_source:raise SourceBlocked("V8_CONFLICTING_AUDIO_INSTRUCTIONS")
    return {"brief":brief,"dialogue_priority":dialogue,"preserve_full_source":duration,
      "keep_source_audio":not remove_source,"music_allowed":not no_music,
      "transitions_allowed":not no_transitions,
      "tone":"cinematic" if "cinematic" in s else "documentary" if dialogue else "source_led",
      "owner_rules":["dialogue_first"] if dialogue else []}

def probe(path):
    path=Path(path).resolve()
    if not path.is_file() or not path.stat().st_size:raise SourceBlocked("V8_SOURCE_MISSING")
    raw=_exec(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(path)],35)
    try:
        obj=json.loads(raw.stdout);duration=float(obj["format"]["duration"])
        video=next((x for x in obj["streams"] if x["codec_type"]=="video"),None)
        audio=next((x for x in obj["streams"] if x["codec_type"]=="audio"),None)
        if not video or not 1.2<=duration<=120 or not math.isfinite(duration):raise ValueError()
        fps=video.get("avg_frame_rate","30/1").split("/")
        rate=float(fps[0])/float(fps[1]) if len(fps)==2 and float(fps[1]) else 30
        if not math.isfinite(rate) or rate<5:raise ValueError()
    except (KeyError,TypeError,ValueError,ZeroDivisionError):
        raise SourceBlocked("V8_SOURCE_UNSUPPORTED") from None
    return {"path":str(path),"sha256":hash_file(path),"duration":round(duration,3),
      "width":video.get("width"),"height":video.get("height"),"fps":round(rate,3),
      "has_audio":bool(audio),"audio_codec":audio.get("codec_name") if audio else None,
      "video_codec":video.get("codec_name")}

def _scenes(path,duration):
    try:
        result=_exec(["ffmpeg","-hide_banner","-nostats","-loglevel","info","-i",str(path),
         "-vf",r"scale=320:-2,select=gt(scene\,0.30),showinfo","-an","-f","null","-"],min(150,max(30,round(duration*3))))
        times=[float(t) for t in re.findall(r"pts_time:\s*([0-9]+(?:\.[0-9]+)?)",result.stderr.decode("utf8","replace"))]
    except SourceBlocked:return []
    found=[]
    for t in times:
        if 1.2<t<duration-1.2 and (not found or t-found[-1]>1.5):
            found.append(round(t,3))
            if len(found)>=14:break
    return found

def _quiet(path,duration):
    try:
        result=_exec(["ffmpeg","-hide_banner","-nostats","-loglevel","info","-i",str(path),
         "-vn","-af","silencedetect=noise=-35dB:d=0.4","-f","null","-"],min(150,max(30,round(duration*2))))
        msg=result.stderr.decode("utf8","replace")
        starts=[float(t) for t in re.findall(r"silence_start:\s*([0-9.]+)",msg)]
        ends=[float(t) for t in re.findall(r"silence_end:\s*([0-9.]+)",msg)]
    except SourceBlocked:return []
    return [[round(a,2),round(min(duration, next((b for b in ends if b>=a),duration)),2)] for a in starts[:35]]

def inspect(path,brief):
    owner=intent(brief); media=probe(path)
    if owner["dialogue_priority"] and not media["has_audio"]:raise SourceBlocked("V8_REQUIRED_DIALOGUE_AUDIO_MISSING")
    scenes=_scenes(media["path"],media["duration"])
    limits=[0.0,*scenes,media["duration"]]
    shots=[{"id":f"shot-{i+1}","start":round(limits[i],3),"end":round(limits[i+1],3),
      "observed":"scene boundary detected" if i else "source starts; visual semantics unverified"}
      for i in range(len(limits)-1) if limits[i+1]-limits[i]>=.05]
    return {"version":"v8-source-evidence-1","source":media,"owner_intent":owner,
      "shot_boundaries_method":"ffmpeg_scene_score_not_semantic_recognition",
      "shots":shots,"quiet_intervals":_quiet(media["path"],media["duration"]) if media["has_audio"] else [],
      "speech_transcript":None,"speech_recognition_status":"NOT_RUN",
      "visual_semantics_status":"NOT_INFERRED","consent_for_external_inference":False}
