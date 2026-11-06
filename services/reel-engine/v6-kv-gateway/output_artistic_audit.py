#!/usr/bin/env python3
"""Private, post-render visual QA through FilmCraft frames, Gemini and Groq.

This is an independent model opinion, NOT creator approval or proof of artistic quality.
Frame files are transient and never uploaded as GitHub artifacts.
"""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from filmcraft_frame_samples import extract
import multimodel_filmcraft_bridge as bridge
from v6_contract import free_flash_models,V6Blocked

def review(*,cli,workdir:Path,output:Path,receipt:dict,brief:str,hook:str,source_consent:bool) -> dict:
 if source_consent is not True:raise V6Blocked("Explicit external visual QA consent missing")
 if receipt.get("filmcraft_only") is not True or receipt.get("rendered") is not True:
  raise V6Blocked("No FilmCraft output to review")
 duration=receipt.get("duration_seconds",0)
 if not 3<=duration<=120:return {"status":"not_admitted","reason":"Short preview cannot support frame audit"}
 frames=extract(cli,workdir,output,duration,count=3,consent=source_consent,
  source_sha256=hashlib.sha256(Path(output).read_bytes()).hexdigest())
 if not (os.environ.get("GEMINI_INFERENCE_OWNER_APPROVED")=="true" or
    os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")=="true"):
  return {"status":"pending","reason":"Owner-approved Flash visual audit not enabled"}
 key=os.environ.get("GEMINI_API_KEY")
 if not key:return {"status":"pending","reason":"Gemini connector not configured"}
 models=free_flash_models(bridge.discover_models(key,bridge.legacy_adapter()))
 if not models:return {"status":"pending","reason":"Approved free Flash unavailable"}
 content=[{"text":("Independently inspect these THREE frames from the ACTUAL finished private video. "
   "The frames are already rendered, not proposed. The user requested a generic reel, "
   "not a named brand. Never infer audio, motion between frames, or unseen content. "
   "Reply JSON object with exactly keys visual_readability (string), color_consistency (string), "
   "story_clarity (string), artifact_concerns (list of strings), visual_pass (boolean). "
   "Use visible evidence only. Brief: "+brief[:800]+". Intended hook: "+hook[:90]+".")}]
 for f in frames:
  content.append({"text":"Actual output frame at "+str(f["time_seconds"])+" seconds."})
  content.append({"inline_data":{"mime_type":"image/jpeg","data":f["data"]}})
 payload={"contents":[{"parts":content}],"generationConfig":{
   "responseMimeType":"application/json","temperature":0.15,"maxOutputTokens":850}}
 observations=None;used=None
 for model in models[:5]:
  try:
   reply=bridge.post_json(bridge.GEMINI_ENDPOINT+model+":generateContent",
     {"x-goog-api-key":key},payload,timeout=65)
   observations=bridge.decode_json(reply["candidates"][0]["content"]["parts"][0]["text"])
   used=model
   break
  except bridge.FreeModelTemporarilyUnavailable:time.sleep(2)
  except (KeyError,IndexError,TypeError,bridge.V6Blocked):continue
 if not observations or used is None:
  return {"status":"unavailable","reason":"Visual analysis provider unavailable","frames_checked":len(frames)}
 valid=all(k in observations for k in ("visual_readability","color_consistency","story_clarity","artifact_concerns","visual_pass"))
 if not valid or not isinstance(observations["artifact_concerns"],list) or type(observations["visual_pass"]) is not bool:
  return {"status":"unverified","reason":"Gemini visual observations malformed","model":used}
 second=("Independent editorial reviewer: you cannot see or hear the raw media. "
  "Assess ONLY whether this image-based evidence supports an artistically coherent "
  "generic reel and whether a human review is still required. "
  "Never claim you watched full motion or heard music. "
  "Return strict JSON {approved:boolean,quality_concerns:[string],review_scope:string}. "
  "Visible frame findings: "+json.dumps(observations)+"; original creative brief: "+brief[:800]+
  "; FilmCraft technical receipt: "+json.dumps({"effects_requested":receipt.get("operations_requested"),
  "effects_command_accepted":receipt.get("operations_command_accepted"),
  "output_audio_verified":receipt.get("output_audio_verified")}) )
 try:review=bridge.groq_call("openai/gpt-oss-20b",second,temperature=.15,max_tokens=750)
 except bridge.V6Blocked:return {"status":"review_pending","visual_model":used,"frames_checked":len(frames),
    "visual_findings":observations,"independent_review":"unavailable"}
 independent=review.get("approved") is True and isinstance(review.get("quality_concerns"),list)
 visual_ok=observations["visual_pass"] is True
 return {"status":"automated_visual_pass" if visual_ok and independent else "needs_human_review",
  "visual_model":used,"groq_reviewer":"openai/gpt-oss-20b","frames_checked":len(frames),
  "visual_findings":observations,"editorial_verdict":review,"owner_approved":False,
  "audio_listening_review":"not_completed","published":False}
