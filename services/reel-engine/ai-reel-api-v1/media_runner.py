#!/usr/bin/env python3
"""MAD V5 real-media owner-only private review pipeline, GitHub OIDC to KV.
No private media in repository, CI logs or public Actions artifacts.
This produces an UNAPPROVED REVIEW DRAFT, never an artistic/music-rights certification.
"""
from __future__ import annotations
import argparse,base64,hashlib,json,math,os,re,subprocess,sys,urllib.request,urllib.error,textwrap,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"services"/"reel-engine"))
sys.path.insert(0,str(ROOT/"experiments"/"reel-engine-v5"))
from cloudflare_bridge_runner import token, ENDPOINT
from multi_renderer import probe_media,render_multiple
from v5_orchestrator import Rejected,load_system,build_director_prompt,call_groq,call_groq_vision,validate_plan,models_for_task

CHUNK=4*1024*1024
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(CHUNK),b""):h.update(b)
    return h.hexdigest()

def request(path,*,payload=None,method="POST",claim=None,raw=None,content_type="application/json",sha256=None):
    if not path.startswith("/bridge/v1/media-"):raise ValueError("Unapproved media route")
    if payload is not None and raw is not None:raise ValueError("Ambiguous body")
    data=(json.dumps(payload,separators=(",",":")).encode() if payload is not None else raw)
    headers={"Authorization":"Bearer "+token(),"Accept":"application/json","User-Agent":"MAD-V5-Private-Review"}
    if claim:headers["X-Mad-Claim-Id"]=claim
    if data is not None:headers["Content-Type"]=content_type
    if sha256:headers["X-Chunk-SHA256"]=sha256
    kind=path.split("/")[3] if len(path.split("/"))>3 else "unknown"
    if kind not in {"media-claim","media-source","media-output","media-complete"}:kind="unknown"
    req=urllib.request.Request(ENDPOINT+path,data=data,headers=headers,method=method)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req,timeout=80) as resp:
                body=resp.read(CHUNK+8192) if method=="GET" else resp.read(8192)
                if method=="GET" and len(body)>CHUNK:raise ValueError("Remote chunk exceeded max")
                return body if method=="GET" else json.loads(body)
        except urllib.error.HTTPError as e:
            # Never emit a URL, query, guest metadata, request body or bearer token.
            print("PRIVATE_MEDIA_BRIDGE_HTTP",kind,e.code,"attempt",attempt+1,file=sys.stderr,flush=True)
            if e.code not in (429,500,502,503,504) or attempt==4:
                raise RuntimeError("Private media endpoint unavailable: HTTP "+str(e.code)) from None
        except (TimeoutError,urllib.error.URLError) as e:
            print("PRIVATE_MEDIA_BRIDGE_TRANSPORT",kind,type(e).__name__,"attempt",attempt+1,file=sys.stderr,flush=True)
            if attempt==4:raise RuntimeError("Private media transport exhausted") from None
        import time;time.sleep(2**attempt)
    raise RuntimeError("Private media transport exhausted")

def source(job,where):
    if not all(job["rights"].get(k) is True for k in ("source_rights_confirmed","people_consent_confirmed","external_ai_processing_approved")):
        raise ValueError("Rights/consent gate missing")
    with where.open("wb") as output:
        h=hashlib.sha256()
        for i in range(job["source_chunks"]):
            data=request("/bridge/v1/media-source/"+job["job_id"]+"/"+str(i),method="GET",claim=job["claim_id"])
            if len(data)!=min(CHUNK,job["source_bytes"]-i*CHUNK):raise ValueError("Chunk size mismatch")
            output.write(data);h.update(data)
    if where.stat().st_size!=job["source_bytes"] or h.hexdigest()!=job["source_sha256"]:
        raise ValueError("Private source SHA256 integrity failure")
    p=probe_media(where)
    if not 3<=p["duration"]<=480:raise ValueError("Supported owner MVP source duration is 3–480 seconds")
    return p

def sample_frames(input_path,work,probe):
    frames=[]
    duration=probe["duration"]
    count=max(3,min(8,int(duration/4)))
    for i in range(count):
        at=max(.1,min(duration-.5,(i+.5)*duration/count))
        frame=work/("frame-%02d.jpg"%i)
        proc=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
          "-ss",str(at),"-i",str(input_path),"-frames:v","1","-vf",
          "scale=480:-2","-q:v","5",str(frame)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25)
        if proc.returncode==0 and frame.is_file() and frame.stat().st_size<150000:
            frames.append((at,frame))
    return frames

def groq_vision_caption(frame, cfg, client=None):
    key=os.getenv("GROQ_API_KEY","")
    if not key:return None
    prompt=("Describe ONLY visually observable setting, composition, action, movement "
        "and mood in this actual frame in one sentence. Never identify people, "
        "infer medical effects, invent off-frame moments, or assert venue names.")
    return call_groq_vision(cfg,frame,prompt,key,client=client)


def director_failure_code(exc):
    """Categorize director failures without exposing private prompts or provider bodies."""
    status=getattr(exc,"status_code",None)
    if status in (401,403):return "director_auth_rejected"
    if status==429:return "director_rate_limited"
    if status in (400,404,422):return "director_request_rejected"
    if isinstance(exc,Rejected):return "director_plan_invalid"
    if isinstance(exc,(ValueError,TypeError,KeyError,IndexError)):return "director_response_invalid"
    return "director_provider_failure"


def renderable_plan(plan,source_duration):
    items=plan.get("segments",[])
    if not 1<=len(items)<=16:raise ValueError("unsupported_section_count")
    cuts=[]
    for item in items:
        start,seconds=item["source_start_seconds"],item["duration_seconds"]
        if not (.4<=seconds<=120 and 0<=start<source_duration-.2
                and start+seconds<=source_duration+.02):
            raise ValueError("unsupported_section_timing")
        cuts.append({"source_index":0,"start":round(start,3),
                     "seconds":round(seconds,3),"loop":False})
    total=sum(x["seconds"] for x in cuts)
    if not 3<=total<=45:raise ValueError("unsupported_timeline_duration")
    return cuts,total


def design(job,src,probe,work):
    cfg,registry=load_system(ROOT/"experiments"/"reel-engine-v5"/"v5_config.json",
                             ROOT/"experiments"/"reel-engine-v5"/"capability_registry.json")
    target=min(30.,max(3.,probe["duration"] if probe["duration"]<30 else 30))
    frames=sample_frames(src,work,probe)
    audit={"vision_frames_sampled":len(frames),"vision_frames_captioned":0,
           "vision_model_used":None,"vision_failures":0,
           "director_attempts":0,"director_response_received":False,
           "creative_plan_applied":False,"creative_fallback_reason":None,
           "proposed_effects_not_executed":0}
    vision=models_for_task(cfg,"shot_visual_analysis")[0]
    free_vision=cfg["task_routing"]["shot_visual_analysis"]
    batch_size=free_vision["images_per_free_tier_batch"]
    max_captions=free_vision["max_captioned_frames_per_job"]
    batch_cooldown=free_vision["batch_cooldown_seconds"]
    vision_requests=0
    shots={}
    for k,(t,frame) in enumerate(frames):
        start=max(0.,min(t-.45,probe["duration"]-.8))
        length=min(3.8,probe["duration"]-start-.1)
        if length<.4:continue
        description=None
        if k<max_captions and os.getenv("GROQ_API_KEY",""):
            # Provider free tier allows 8K tokens/minute for Qwen. Each image
            # costs 2048 tokens; spread six shots across two admission windows.
            if vision_requests and vision_requests%batch_size==0:
                time.sleep(batch_cooldown)
            vision_requests+=1
            try:
                description=groq_vision_caption(frame,cfg)
            except Exception:
                # Never log guest frames, private prompts, provider bodies or keys.
                audit["vision_failures"]+=1
            if description:
                audit["vision_frames_captioned"]+=1
                audit["vision_model_used"]=vision["model"]
        shots["f%02d"%k]={"id":"f%02d"%k,"start_seconds":round(start,2),
             "duration_seconds":round(length,2),"visible_description":
             description or ("Unreviewed frame sample from original footage at %.1f seconds; no visual claim"%t)}
    if not shots:raise ValueError("No usable source shots extracted")
    if not os.getenv("GROQ_API_KEY",""):
        audit["vision_status"]="no_vision_credential"
    elif audit["vision_frames_captioned"]==0:
        audit["vision_status"]="no_vision_descriptions"
    else:
        audit["vision_status"]="descriptions_unreviewed"
    brand=("DeluluTech AI Reel Engine V5; owner's authorized original footage, "
       "genuine cinematic vertical story, no invented venue, names, activities, logo, "
       "medical claims, third-party media or music. This is a private review draft.")
    key=os.getenv("GROQ_API_KEY","")
    if not key:
        audit["creative_fallback_reason"]="director_credential_missing"
    else:
        prompt=build_director_prompt(cfg,shots,brand,job["prompt"],1,"instagram_reel")
        for candidate in models_for_task(cfg,"cinematic_direction"):
            audit["director_attempts"]+=1
            try:
                response=call_groq(cfg,prompt,key,model=candidate)
                audit["director_response_received"]=True
                proposed=validate_plan(response,shots,1,cfg)[0]
                cuts,total=renderable_plan(proposed,probe["duration"])
                audit["creative_plan_applied"]=True
                audit["creative_fallback_reason"]=None
                audit["proposed_effects_not_executed"]=sum(
                    len(x.get("proposed_operations",[])) for x in proposed["segments"])
                return cuts,total,proposed,audit
            except Exception as exc:
                audit["creative_fallback_reason"]=director_failure_code(exc)
    n=max(1,min(10,math.floor(target/2.5)))
    seconds=target/n;cuts=[]
    for i in range(n):
        start=max(0.,min(probe["duration"]-seconds-.03,
                  (probe["duration"]-seconds)*i/max(1,n-1)))
        cuts.append({"source_index":0,"start":round(start,3),
                     "seconds":round(seconds,3),"loop":False})
    cuts[-1]["seconds"]=round(target-sum(c["seconds"] for c in cuts[:-1]),3)
    for item in cuts:
        item["seconds"]=min(item["seconds"],probe["duration"]-item["start"])
    target=sum(x["seconds"] for x in cuts)
    if target<3:raise ValueError("Insufficient continuous source for safe reel")
    return cuts,target,None,audit


def creative_title(planned):
    return planned["hook"] if planned and planned.get("hook") else "A MOMENT WORTH FEELING"


def display_title(hook):
    """Wrap only an actual creative hook or neutral safe title on two mobile-safe lines."""
    clean=" ".join(re.sub(r"[\x00-\x1f]"," ",hook or "").split()) or "A MOMENT WORTH FEELING"
    return "\n".join(textwrap.wrap(clean,width=23,max_lines=2,placeholder="…",
                                  break_long_words=True,break_on_hyphens=False))


def postprocess(draft,out,work,hook):
    # Typography is owner-supplied / grounded creative brief only, not a fabricated quote.
    text=display_title(hook)
    # Text is placed in a file, never passed as an untrusted FFmpeg filter expression.
    label=work/"hook.txt";label.write_text(text,encoding="utf-8")
    font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    # Underlying V5 renderer already applies per-cut picture/sound fades.
    vf=("drawtext=fontfile="+font+":textfile="+str(label)+
      ":fontcolor=white:fontsize=58:borderw=3:bordercolor=black@0.65:"
      "x=(w-text_w)/2:y=h*0.18:enable='between(t,0,2.8)'")
    cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y","-i",str(draft),
         "-vf",vf,"-c:v","libx264","-preset","veryfast","-crf","25",
         "-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",str(out)]
    p=subprocess.run(cmd,capture_output=True,timeout=600)
    if p.returncode:raise RuntimeError("Typography overlay rendering failed")
    return out

def verify(out):
    p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(out)],capture_output=True,text=True,timeout=30,check=True)
    data=json.loads(p.stdout)
    v=next(s for s in data["streams"] if s["codec_type"]=="video")
    a=next((s for s in data["streams"] if s["codec_type"]=="audio"),None)
    if (v.get("codec_name"),v.get("width"),v.get("height"))!=("h264",1080,1920) or not a or a["codec_name"]!="aac":
        raise ValueError("Private render h264/aac 1080x1920 verification failed")
    subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(out),"-f","null","-"],check=True,timeout=600,capture_output=True)
    return {"sha256":sha(out),"bytes":out.stat().st_size,"width":1080,"height":1920,"fps":30,
            "audio_codec":"aac","full_decode":True}

def render(job,root):
    root.mkdir(parents=True,exist_ok=True)
    src=root/"owner-source.mp4"
    print("PRIVATE_MEDIA_RENDER_STAGE","SOURCE_VERIFY",flush=True)
    probe=source(job,src)
    print("PRIVATE_MEDIA_RENDER_STAGE","PLAN",flush=True)
    cuts,target,planned,audit=design(job,src,probe,root)
    print("PRIVATE_MEDIA_CREATIVE_REPORT",
          "attempts",audit["director_attempts"],
          "plan_applied",int(audit["creative_plan_applied"]),
          "reason",audit["creative_fallback_reason"] or "none",
          "vision_captioned",audit["vision_frames_captioned"],
          "vision_sampled",audit["vision_frames_sampled"],
          "vision_failures",audit["vision_failures"],
          "unapplied_effects",audit["proposed_effects_not_executed"],flush=True)
    base=root/"unapproved-base.mp4"
    print("PRIVATE_MEDIA_RENDER_STAGE","FFMPEG_RENDER",flush=True)
    render_multiple([src],base,{"target_seconds":target,"width":1080,"height":1920,
         "fps":30,"clip_plan":cuts,"crf":25},root/"edit")
    hook=creative_title(planned)
    out=root/"private-review.mp4"
    print("PRIVATE_MEDIA_RENDER_STAGE","TYPOGRAPHY",flush=True)
    postprocess(base,out,root,hook)
    print("PRIVATE_MEDIA_RENDER_STAGE","VERIFY",flush=True)
    info=verify(out)
    if info["bytes"]>80*1024*1024:raise ValueError("Render over free storage limit")
    receipt={"status":"PRIVATE_REAL_MEDIA_TECHNICAL_DRAFT","video":info,
      "creative_model_called":audit["director_response_received"],
      "director_attempts":audit["director_attempts"],
      "creative_plan_applied":audit["creative_plan_applied"],
      "creative_fallback_reason":audit["creative_fallback_reason"],
      "vision_frames_sampled":audit["vision_frames_sampled"],
      "vision_frames_captioned":audit["vision_frames_captioned"],
      "vision_model_used":audit["vision_model_used"],
      "vision_failures":audit["vision_failures"],
      "vision_status":audit["vision_status"],
      "proposed_effects_not_executed":audit["proposed_effects_not_executed"],
      "applied_operations":["source_trim","concat","scale_crop","fade","static_opening_title"],
      "visual_frames_human_reviewed":False,
      "source_sha256":job["source_sha256"],"shot_count":len(cuts),
      "planning_mode":"groq_v5_unapproved" if planned else "source_only_fallback",
      "soundtrack_source":"authorized_source_audio_only",
      "music_rights_certified":False,"artistic_quality_certified":False,
      "public_release_certified":False,"published":False,"toolchain":"V5 Groq edit plan + FFmpeg" if planned else "V5 FFmpeg fallback"}
    (root/"receipt.json").write_text(json.dumps(receipt))
    print("PRIVATE_MEDIA_RENDER_STAGE","OUTPUT_UPLOAD",flush=True)
    with out.open("rb") as f:
        for i in range(math.ceil(out.stat().st_size/CHUNK)):
            data=f.read(CHUNK)
            request("/bridge/v1/media-output/"+job["job_id"]+"/"+str(i),method="PUT",
                claim=job["claim_id"],raw=data,content_type="application/octet-stream",
                sha256=hashlib.sha256(data).hexdigest())
    return receipt,math.ceil(info["bytes"]/CHUNK)

def main():
    a=argparse.ArgumentParser()
    a.add_argument("mode",choices=["claim","render","complete"])
    a.add_argument("--claim",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    opt=a.parse_args()
    if opt.mode=="claim":
        data=request("/bridge/v1/media-claim",payload={})
        job=data.get("job")
        if not job:
            print("PRIVATE_MEDIA_QUEUE_IDLE")
            if os.getenv("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("has_media=0\n")
            return
        opt.claim.write_text(json.dumps(job));opt.claim.chmod(0o600)
        if os.getenv("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("has_media=1\n")
        print("PRIVATE_MEDIA_JOB_CLAIMED",job["job_id"])
    elif opt.mode=="render":
        job=json.loads(opt.claim.read_text())
        receipt,n=render(job,opt.out)
        print("PRIVATE_REAL_MEDIA_REVIEW_DRAFT_RENDERED",job["job_id"],receipt["video"]["sha256"])
    else:
        print("PRIVATE_MEDIA_RENDER_STAGE","COMPLETE_CALLBACK",flush=True)
        job=json.loads(opt.claim.read_text())
        rec=opt.out/"receipt.json"
        try:
            if rec.is_file():
                d=json.loads(rec.read_text())
                bytes_=d["video"]["bytes"]
                response=request("/bridge/v1/media-complete",payload={
                    "job_id":job["job_id"],"claim_id":job["claim_id"],"status":"review_ready",
                    "sha256":d["video"]["sha256"],"bytes":bytes_,
                    "chunks":math.ceil(bytes_/CHUNK),"receipt":d})
            else:
                response=request("/bridge/v1/media-complete",payload={
                    "job_id":job["job_id"],"claim_id":job["claim_id"],"status":"failed",
                    "error_code":"PRIVATE_RENDER_FAILED"})
            if not response.get("accepted"):raise RuntimeError("Cloudflare did not accept render completion")
            print("PRIVATE_MEDIA_JOB_RECEIPT",job["job_id"],response["state"])
        except Exception:
            raise RuntimeError("Private media completion callback failed") from None

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("PRIVATE_MEDIA_JOB_ERROR",type(e).__name__,file=sys.stderr)
        raise SystemExit(5)
