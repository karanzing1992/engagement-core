"""V8 reuse of owner-approved V7 Gemini/Groq endpoints. No new keys or providers."""
from __future__ import annotations
import base64,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"experiments/reel-engine-v6"))
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"experiments/reel-engine-v5"))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"v6-kv-gateway"))
import multimodel_filmcraft_bridge as ai
from ffmpeg_frame_samples import extract as sample_frames
from director import CreativeBlocked

def _authorized():
    if (os.environ.get("MAD_V8_OWNER_AI_ENABLED")!="true" or
        os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")!="true" or
        os.environ.get("GEMINI_INFERENCE_OWNER_APPROVED")!="true"):
        raise CreativeBlocked("V8_OWNER_FREE_AI_FLAGS_REQUIRED")

def groq_director(prompt,evidence,prior_review=None):
    _authorized()
    if prior_review:
        prompt+="\nIndependent criticism of previous output (fix only grounded failures): "+json.dumps(prior_review)[:3000]
    return ai.groq_call("openai/gpt-oss-120b",prompt,temperature=0.65,max_tokens=2900)

def gemini_source_analyst(evidence,workdir):
    """Send three sampled source frames only with the separately supplied owner consent."""
    _authorized()
    if not evidence.get("consent_for_external_inference"):
        raise CreativeBlocked("V8_SOURCE_VISUAL_CONSENT_REQUIRED")
    source=evidence["source"];work=Path(workdir)
    frames=sample_frames(work,source["path"],source["duration"],count=3,consent=True,
        source_sha256=source["sha256"])
    manifest={"external_ai_processing_consent":True,"shots":[{"id":"source",
        "visible":"Observed video source; semantics unknown until sampled frames are analyzed",
        "start_seconds":0.0,"duration_seconds":source["duration"]}]}
    model,analysis=ai.gemini_research(manifest,evidence["owner_intent"]["brief"],
        approved_api_cost=True,frames=frames)
    ai.validate_observations(manifest,analysis)
    return {"model":model,"observations":analysis["observations"],
        "research_scope":analysis["research_scope"],
        "frame_sha256":[f["sha256"] for f in frames],"inference_from_consent":True}

def _clip_audio(path,at,duration=2.0):
    r=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
      "-ss",str(max(0,at)),"-t",str(duration),"-i",str(path),
      "-vn","-ac","1","-ar","16000","-c:a","pcm_s16le","-f","wav","-"],
      check=True,capture_output=True,timeout=35)
    if not 512<len(r.stdout)<=1000000:
        raise CreativeBlocked("V8_AUDIO_REVIEW_SAMPLE_INVALID")
    return base64.b64encode(r.stdout).decode()

def gemini_actual_media_reviewer(output,evidence,plan,technical):
    """Review output frames + actual audio samples. Never infer approval from a plan."""
    _authorized()
    if not evidence.get("consent_for_external_inference"):
        raise CreativeBlocked("V8_ACTUAL_MEDIA_AI_CONSENT_REQUIRED")
    source=evidence["source"];duration=float(technical["duration"])
    frames=sample_frames(Path(output).parent,output,duration,count=3,
      consent=True,source_sha256=ai.sha256_file(output) if hasattr(ai,"sha256_file") else
      __import__("hashlib").sha256(Path(output).read_bytes()).hexdigest())
    key=os.environ.get("GEMINI_API_KEY")
    if not key:raise CreativeBlocked("V8_GEMINI_SECRET_MISSING")
    models=ai.free_flash_models(ai.discover_models(key,ai.legacy_adapter()))
    if not models:raise CreativeBlocked("V8_NO_VERIFIED_FREE_REVIEWER_MODEL")
    prompt=("You are an independent film critic examining real decoded output and matched original "
      "audio excerpts. Do not infer dialogue from frames. Compare speech clarity against each "
      "original reference excerpt: if output source voice is masked, fail it. Inspect transitions, "
      "pacing, visible frames and coherence. Reply ONLY JSON: "
      "{\"dialogue_clear\":boolean,\"editorial_acceptable\":boolean,\"findings\":[{\"at_seconds\":0,"
      "\"problem\":\"string\",\"fix\":\"string\"}],\"summary\":\"string\"}. "
      "When evidence is insufficient, return false rather than an optimistic guess. "
      "Owner intent: "+evidence["owner_intent"]["brief"][:1500]+
      ". Transition observations: "+json.dumps(technical.get("transitions",[]))[:1400])
    parts=[{"text":prompt}]
    for f in frames:
        parts.extend([{"text":"Actual rendered frame at "+str(f["time_seconds"])+" seconds"},
          {"inline_data":{"mime_type":"image/jpeg","data":f["data"]}}])
    # Compare a few source and output audio excerpts; no private media URLs or uploads.
    at=[max(0.,min(duration-2.,duration*f)) for f in (.1,.48,.82)]
    for t in at:
        parts.extend([{"text":"Original audio excerpt at "+str(round(t,2))+" seconds"},
          {"inline_data":{"mime_type":"audio/wav","data":_clip_audio(source["path"],t)}},
          {"text":"RENDERED audio excerpt at "+str(round(t,2))+" seconds"},
          {"inline_data":{"mime_type":"audio/wav","data":_clip_audio(output,t)}}])
    response=None
    for model in models[:3]:
        try:
            result=ai.post_json(ai.GEMINI_ENDPOINT+model+":generateContent",
              {"x-goog-api-key":key},
              {"contents":[{"parts":parts}],"generationConfig":{
                 "responseMimeType":"application/json","temperature":0.1,
                 "maxOutputTokens":1500}},timeout=60)
            raw=result["candidates"][0]["content"]["parts"][0]["text"]
            response=ai.decode_json(raw);break
        except (ai.V6Blocked,KeyError,IndexError,TypeError):
            continue
    if not isinstance(response,dict):raise CreativeBlocked("V8_ACTUAL_REVIEW_PROVIDER_UNAVAILABLE")
    if type(response.get("dialogue_clear")) is not bool or type(response.get("editorial_acceptable")) is not bool:
        raise CreativeBlocked("V8_ACTUAL_REVIEW_SCHEMA_INVALID")
    findings=response.get("findings",[])
    if not isinstance(findings,list) or len(findings)>16:
        raise CreativeBlocked("V8_ACTUAL_REVIEW_FINDINGS_INVALID")
    return {"verified_actual_media":True,"reviewed_output_sha256":__import__("hashlib").sha256(Path(output).read_bytes()).hexdigest(),
      "dialogue_clear":response["dialogue_clear"],
      "editorial_acceptable":response["editorial_acceptable"],"findings":findings,
      "reviewer_model":"verified_free_gemini_flash","frame_count":len(frames),
      "matched_original_rendered_audio_samples":len(at)}
