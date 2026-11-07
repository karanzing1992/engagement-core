"""V8 independent output critic: measure actual MP4 and never confuse decode with art."""
from __future__ import annotations
import hashlib,json,math,re,subprocess
from pathlib import Path
from director import CreativeBlocked

def _run(args,timeout=70):
    try:return subprocess.run(args,check=True,capture_output=True,timeout=timeout)
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        raise CreativeBlocked("V8_ACTUAL_MEDIA_REVIEW_FAILED") from None

def _volume(path):
    r=_run(["ffmpeg","-hide_banner","-nostats","-loglevel","info","-i",str(path),
      "-vn","-af","volumedetect","-f","null","-"],100)
    m=re.search(r"max_volume:\s*(-inf|[-+]?\d+(?:\.\d+)?)\s*dB",r.stderr.decode("utf8","replace"))
    return float(m.group(1)) if m else None

def _frame(path,t):
    r=_run(["ffmpeg","-hide_banner","-loglevel","error","-ss",str(max(0,t)),
     "-i",str(path),"-frames:v","1","-vf","scale=32:18,format=gray",
     "-f","rawvideo","-"],40)
    if len(r.stdout)!=576:raise CreativeBlocked("V8_REVIEW_FRAME_MISSING")
    return r.stdout

def _audio_duration(path):
    r=_run(["ffprobe","-v","error","-select_streams","a:0",
      "-show_entries","stream=duration","-show_entries","format=duration",
      "-of","json",str(path)],35)
    obj=json.loads(r.stdout)
    return float(obj.get("format",{}).get("duration",0))

def inspect_output(evidence,plan,receipt,output):
    output=Path(output)
    if not output.is_file() or not receipt.get("full_decode_passed"):
        raise CreativeBlocked("V8_OUTPUT_NOT_DECODED")
    if hashlib.sha256(output.read_bytes()).hexdigest()!=receipt.get("output_sha256"):
        raise CreativeBlocked("V8_OUTPUT_HASH_CHANGED")
    duration=float(receipt.get("duration_seconds",0))
    source_duration=float(evidence["source"]["duration"])
    owner=evidence["owner_intent"]
    checks={"hash_and_decode":True,"output_sha256":receipt["output_sha256"],"duration":duration,
      "source_audio_preserved_by_contract":receipt["source_audio_preserved_by_contract"],
      "audio_peak_source_db":_volume(evidence["source"]["path"]) if evidence["source"]["has_audio"] else None,
      "audio_peak_output_db":_volume(output),
      "transitions":[]}
    if (owner["dialogue_priority"] or owner["preserve_full_source"]) and abs(duration-source_duration)>.2:
        raise CreativeBlocked("V8_CREATIVE_QA_TRIMMED_OWNER_AUDIO")
    if owner["dialogue_priority"] and receipt["source_audio_preserved_by_contract"] is not True:
        raise CreativeBlocked("V8_CREATIVE_QA_SOURCE_SOUND_REMOVED")
    if owner["dialogue_priority"] and (checks["audio_peak_output_db"] is None or
        checks["audio_peak_output_db"] == -math.inf):
        raise CreativeBlocked("V8_CREATIVE_QA_OUTPUT_SILENT")
    # Validate interior transition on decoded actual frames, not the FFmpeg command string.
    at=0.;count=0
    for seg in plan["segments"][:-1]:
        at+=seg["end"]-seg["start"]
        index=count+1;next_style=plan["segments"][index]["transition"]
        if next_style=="dissolve":at-=.28
        a=_frame(output,max(.1,at-.30));b=_frame(output,min(duration-.12,at))
        c=_frame(output,min(duration-.04,at+.30))
        avg=lambda v:sum(v)/len(v)
        observation={"boundary":round(at,3),"style":next_style,
         "before_luma":round(avg(a),2),"during_luma":round(avg(b),2),
         "after_luma":round(avg(c),2)}
        if next_style=="dip-to-black":
            observation["visual_signal_confirmed"]=avg(b)<min(avg(a),avg(c))*.75
            if not observation["visual_signal_confirmed"]:
                raise CreativeBlocked("V8_DIP_TRANSITION_NOT_VISIBLE")
        elif next_style=="dissolve":
            # A decoded interior frame proves the transition frame exists, not artistic quality.
            observation["visual_signal_confirmed"]=None
        else:
            observation["visual_signal_confirmed"]=None
        checks["transitions"].append(observation);count+=1
    checks["technical_acceptance"]=True
    checks["artistic_acceptance"]="PENDING_INDEPENDENT_RENDER_REVIEW"
    checks["dialogue_intelligibility"]="UNVERIFIED_REQUIRES_LISTENING_OR_AUTHORIZED_ASR"
    checks["published"]=False
    return checks

def decide_release(review,*,owner_approved=False,independent_visual_audio_review=None):
    """Creative approval remains separate from technical correctness and posting."""
    certified=(review.get("technical_acceptance") is True and
      isinstance(independent_visual_audio_review,dict) and
      independent_visual_audio_review.get("verified_actual_media") is True and
      independent_visual_audio_review.get("reviewed_output_sha256")==review.get("output_sha256") and
      independent_visual_audio_review.get("dialogue_clear") is True and
      independent_visual_audio_review.get("editorial_acceptable") is True)
    return {"private_preview_ready":review.get("technical_acceptance") is True,
      "creative_certified":bool(certified),"owner_approved":bool(owner_approved),
      "publish_authorized":False,"requires_owner_approval":True}
