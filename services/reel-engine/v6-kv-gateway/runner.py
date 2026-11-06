#!/usr/bin/env python3
"""MAD V6 signed KV runner. MLT + frei0r is sole editor; Gst decode QA only."""
from __future__ import annotations
import argparse,hashlib,json,os,sys,math,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"services/reel-engine"))
sys.path.insert(0,str(ROOT/"experiments/reel-engine-v6"))
import mlt_v6_adapter as mlt
import multimodel_filmcraft_bridge as multimodel
from ges_frame_samples import extract as ges_frames
from original_cc0_audio import compose as cc0_compose,choose as select_audio_profile

GATEWAY="https://mad-v6-kv-private-beta.karanbizweb360.workers.dev"
AUD="mad-v6-cloudflare-kv/1"
CHUNK=4*1024*1024
# Diagnostic output contains only fixed labels and allowlisted codes, never footage or provider data.
STAGES=frozenset(("start","oidc","job_claim","source_download","media_probe","frame_sampling","model_policy","gemini_research","groq_director","groq_reviewer","edl_compile","audio_compose","filmcraft_render","filmcraft_source_preflight","filmcraft_music_rights","filmcraft_mcp_init","filmcraft_source_probe","filmcraft_edl_validate","filmcraft_sequence","filmcraft_source_import","filmcraft_timeline_place","filmcraft_effects","filmcraft_hook","filmcraft_music_mix","filmcraft_export","filmcraft_verify_output","output_upload","private_complete","gstreamer_render","mlt_render"))
ACTIVE_STAGE="start"
SAFE_CAUSES={
 "All currently available free Flash candidate endpoints were unavailable":"GEMINI_ENDPOINT_UNAVAILABLE",
 "No approved free Gemini Flash model available":"GEMINI_MODEL_UNAVAILABLE",
 "Gemini free-tier API key not present":"GEMINI_KEY_MISSING",
 "Model API request rejected; provider response redacted":"MODEL_PROVIDER_REJECTED",
 "Model API rejected or timed out; details redacted":"MODEL_PROVIDER_TIMEOUT",
 "Groq response lacks validated JSON":"GROQ_JSON_REJECTED",
 "Model response was not JSON":"MODEL_JSON_REJECTED",
 "Model returned non-object":"MODEL_JSON_REJECTED",
 "Model JSON missing or over size budget":"MODEL_JSON_REJECTED",
 "Director storyboard required":"DIRECTOR_INVALID",
 "Opening hook missing":"DIRECTOR_HOOK_MISSING",
 "Editor rejected one or more proposed FilmCraft edits":"REVIEW_REJECTED",
 "Editor-review per-segment approval incomplete":"REVIEW_INCOMPLETE",
 "Groq 20B review missing or director hash mismatch":"REVIEW_DIGEST_OR_APPROVAL_MISMATCH",
 "Independent reviewer rejected proposed edit":"REVIEW_REJECTED",
 "Strict reviewer response invalid":"REVIEW_SCHEMA_INVALID",
 "Unsupported GStreamer effect requested":"GES_DIRECTOR_EFFECT_UNSUPPORTED",
 "GStreamer title text invalid":"GES_TITLE_TEXT_INVALID",
 "MLT renderer rejected creative template":"MLT_TEMPLATE_NOT_ALLOWLISTED",
 "Duplicate creative instruction identifier":"EDL_DUPLICATE_EFFECT_ID",
 "Director invented edit time outside reviewed footage":"DIRECTOR_TIMECODE_INVALID",
 "Gemini Flash returned no usable source observations":"GEMINI_OBSERVATIONS_INVALID",
}
def mark(stage):
 global ACTIVE_STAGE
 if stage not in STAGES:raise ValueError("Unknown fixed diagnostic stage")
 ACTIVE_STAGE=stage
 print("V6_KV_STAGE "+stage,flush=True)
FILMCRAFT_SAFE_CAUSES={
 "Source duration outside owner-beta admission":"FILMCRAFT_SOURCE_DURATION",
 "Timeline section exceeds source bounds":"FILMCRAFT_SOURCE_BOUNDS",
 "FilmCraft MCP request failed":"FILMCRAFT_MCP_COMMAND_REJECTED",
 "FilmCraft command_run failed (details redacted)":"FILMCRAFT_COMMAND_REJECTED",
 "Grounded title text required":"FILMCRAFT_TITLE_MISSING",
 "FilmCraft media item ID unverified":"FILMCRAFT_IMPORT_UNVERIFIED",
 "FilmCraft did not confirm placed clip ID":"FILMCRAFT_TIMELINE_PLACE_REJECTED",
 "FilmCraft native command / creative effect count mismatch":"FILMCRAFT_EFFECT_MISMATCH",
 "FilmCraft source SHA256 mismatch":"FILMCRAFT_SOURCE_HASH_MISMATCH",
 "Approved music shorter than timeline; no silent truncation":"FILMCRAFT_MUSIC_DURATION",
 "FilmCraft native audio probe rejected soundtrack":"FILMCRAFT_AUDIO_PROBE",
 "FilmCraft export missing":"FILMCRAFT_EXPORT_MISSING",
}
def safe_failure(exc):
 if isinstance(exc,multimodel.V6Blocked):code=SAFE_CAUSES.get(str(exc),"BLOCKED_UNCLASSIFIED")
 elif isinstance(exc,mlt.RenderBlocked):code=str(exc) if str(exc).startswith("MLT_") else "MLT_REJECTED"
 else:code="NON_MODEL_FAILURE"
 return "V6_KV_PRIVATE_RENDER_FAILED stage="+ACTIVE_STAGE+" code="+code
def recoverable_gemini_timeout(exc):
 """Only observed Gemini research network timeouts may fall back to Groq."""
 return (ACTIVE_STAGE=="gemini_research" and isinstance(exc,multimodel.V6Blocked)
         and str(exc)=="Model API rejected or timed out; details redacted")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def token():
 uri=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL","")
 bearer=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN","")
 if not uri.startswith("https://") or not bearer:raise ValueError("GitHub runner OIDC missing")
 join="&" if "?" in uri else "?"
 req=Request(uri+join+urlencode({"audience":AUD}),headers={"Authorization":"Bearer "+bearer,"Accept":"application/json"})
 with urlopen(req,timeout=15) as res:value=json.load(res).get("value")
 if not isinstance(value,str) or value.count(".")!=2:raise ValueError("Invalid short-lived signed identity")
 return value
def call(path,identity,method="POST",claim=None,payload=None,data=None,digest=None):
 if not path.startswith("/internal/v6/jobs/") or data is not None and payload is not None:
  raise ValueError("Disallowed private runner endpoint or ambiguous payload")
 method=method.upper()
 content=json.dumps(payload,separators=(",",":")).encode() if payload is not None else data
 headers={"Authorization":"Bearer "+identity,"User-Agent":"MAD-V6-Private-KV-MLT"}
 if claim:headers["X-V6-Claim"]=claim
 if digest:headers["X-Chunk-SHA256"]=digest
 if content is not None:headers["Content-Type"]="application/json" if payload is not None else "application/octet-stream"
 req=Request(GATEWAY+path,headers=headers,data=content,method=method)
 try:
  with urlopen(req,timeout=80) as res:
   body=res.read(CHUNK+8192)
   if len(body)>CHUNK+4096:raise ValueError("Signed gateway response exceeded allowed size")
   if method=="GET" and "/source/" in path:return body
   return json.loads(body)
 except HTTPError as e:
  raise RuntimeError("Signed V6 KV endpoint rejected "+str(e.code)) from None
def model_plan(src,brief,description,duration,fixture=False,frames=None):
 manifest={"source_sha256":src,"human_reviewed":True,"rights_and_consent_cleared":True,
   "external_ai_processing_consent":True,"shots":[{"id":"s1","start_seconds":0.0,
   "duration_seconds":min(120.,duration),"visible":description}]}
 brand=""  # Generic content: no brand context unless supplied by the owner.
 if fixture:
  mark("model_policy")
  return multimodel.run(source=manifest,brief=brief,brand=brand,mode="fixture")
 fallback_reason="GEMINI_FREE_TIER_NOT_VERIFIED"
 if os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")=="true" or os.environ.get("GEMINI_INFERENCE_OWNER_APPROVED")=="true":
  try:
   return multimodel.run(source=manifest,brief=brief,brand=brand,mode="live",frames=frames,approved_api_cost=True,on_stage=mark)
  except multimodel.V6Blocked as ex:
   # Only allowlisted Gemini network timeouts trigger fallback. Safety, rights
   # and creative-policy failures remain terminal; provider data is never logged.
   if not recoverable_gemini_timeout(ex):
    raise
   fallback_reason="GEMINI_NETWORK_TIMEOUT"
   print("V6_KV_MODEL_FALLBACK GEMINI_NETWORK_TIMEOUT_TO_GROQ_ONLY",flush=True)
 # Approved free-tier fallback: existing Groq models. No Gemini paid fallback.
 mark("model_policy")
 multimodel.read_config()
 multimodel.validate_source_manifest(manifest,external_gemini_frames=False)
 observed={"observations":[{"shot_id":"s1","visible":description}],
           "research_scope":"Human-reviewed and owner-authorized footage description; no independent visual inference."}
 # Supply concrete JSON values instead of pseudo-schema placeholders.
 schema={"hook":"A moment to reset","segments":[{"shot_id":"s1","start_seconds":0.0,
         "duration_seconds":min(4.0,duration),"effects":[{"name":"color_grade","parameters":{"contrast":12}}]}]}
 prompt=("Act as a premium cinematic director. Return ONLY valid JSON with a non-empty "
         "hook (1-90 characters) and 1-4 verified source segments. Each segment must include "
         "shot_id, numeric start_seconds, numeric duration_seconds >= 0.4 and an effects list. "
         "Allowed effect names: color_grade, title, caption ONLY; each has a "
         "parameters object. Never invent unseen footage, people, dialogue, or off-screen "
         "activities. Timecodes must stay within the verified source. "
         "EXAMPLE JSON shape with concrete values: "+json.dumps(schema)+
         " Verified source: "+json.dumps(manifest["shots"])+
         " Optional brand: "+brand+" Owner direction: "+brief)
 mark("groq_director")
 director=multimodel.groq_call("openai/gpt-oss-120b",prompt,temperature=.40,max_tokens=1800)
 try:
  multimodel.validate_director(manifest,director)
 except multimodel.V6Blocked as ex:
  if str(ex)!="Opening hook missing":raise
  # One bounded hook-only correction; all other policy failures remain terminal.
  print("V6_KV_DIRECTOR_SCHEMA_RETRY HOOK_REQUIRED",flush=True)
  repair=("Your prior reply omitted a non-empty opening hook. Return ONLY "
          "complete valid JSON: hook 1-90 characters and segments using ONLY "
          "verified source facts/timecodes with supported effect names. "
          "Concrete example JSON shape: "+json.dumps(schema)+
          " Verified source: "+json.dumps(manifest["shots"])+
          " Owner direction: "+brief)
  director=multimodel.groq_call("openai/gpt-oss-120b",repair,temperature=.2,max_tokens=1600)
  multimodel.validate_director(manifest,director)
 review=multimodel.groq_strict_review(manifest,director,on_stage=mark)
 mark("edl_compile")
 plan=multimodel.compile_reviewed_edl(manifest,director,review)
 plan.update({"model_roles":{"gemini":"SKIPPED_"+fallback_reason,
    "groq_director":"openai/gpt-oss-120b","groq_reviewer":"openai/gpt-oss-20b"},
    "model_policy":"groq_only_fallback_"+fallback_reason.lower(),"live_model_inference":True,
    "source_rights_admitted":True,"audio_mode":"source_ambience_only",
    "published":False,"owner_approval":False})
 return plan

def run(job_id,*,fixture=False):
 if not job_id.startswith("v6job-") or len(job_id)!=38:raise ValueError("Invalid private V6 job")
 mlt.verify_backend() # fail closed if native MLT/frei0r is missing
 work=Path(os.environ["RUNNER_TEMP"])/("mad-v6-"+job_id)
 work.mkdir(mode=0o700,parents=True,exist_ok=True)
 mark("oidc")
 identity=token()
 mark("job_claim")
 claim=call("/internal/v6/jobs/"+job_id+"/claim",identity)
 if claim.get("job_id")!=job_id or not claim.get("rights_confirmed") or not claim.get("people_consent"):
  raise RuntimeError("Unauthorized owner source")
 lease=claim["claim_id"]
 mime=claim["mime"]
 extension={"video/mp4":"mp4","video/quicktime":"mov","video/webm":"webm"}.get(mime)
 if not extension:raise RuntimeError("Unsupported source media")
 src=work/("source."+extension);out=work/"v6-output.mp4"
 try:
  mark("source_download")
  with src.open("wb") as f:
   for i in range(claim["source_chunks"]):
    part=call("/internal/v6/jobs/"+job_id+"/source/"+str(i),identity,method="GET",claim=lease)
    required=min(CHUNK,claim["source_bytes"]-i*CHUNK)
    if len(part)!=required:raise RuntimeError("Private source part size failure")
    f.write(part)
  if src.stat().st_size!=claim["source_bytes"] or sha(src)!=claim["source_sha256"]:
   raise RuntimeError("Source media SHA-256 verification failed")
  mark("media_probe")
  _gst,metadata=mlt._probe(src,2.5)
  duration=metadata["duration"]
  synthetic=fixture and claim.get("source_description","").startswith("SYNTHETIC QA:")
  if fixture and not synthetic:raise RuntimeError("Synthetic fixture cannot render owner footage")
  mark("frame_sampling")
  frames=[] if synthetic else ges_frames(work,src,duration,
    consent=bool(claim.get("free_gemini_consent")) and bool(claim.get("rights_confirmed")),
    source_sha256=claim["source_sha256"])
  mark("model_policy")
  plan=model_plan(claim["source_sha256"],claim["brief"],claim["source_description"],duration,fixture=synthetic,frames=frames)
  mark("audio_compose")
  audio=cc0_compose(work/"v6-original-cc0-soundtrack.wav",max(3.0,sum(c["seconds"] for c in plan["cuts"])),
    select_audio_profile(claim["brief"]))
  mark("mlt_render")
  music_rights=audio["filmcraft_rights"]
  if music_rights.get("human_verified") is not True or music_rights.get("license")!="CC0":
   raise RuntimeError("Original CC0 music provenance missing")
  spec={"source":str(src),"source_sha256":claim["source_sha256"],
    "template_id":mlt.choose_template(claim["brief"]),
    "workdir":str(work),"output":str(out),
    "music":audio["file"],"music_sha256":audio["sha256"],
    "cuts":plan["cuts"],"operations":plan["operations"],"hook":plan["hook"],
    "width":1080,"height":1920,"fps":30}
  rec=mlt.render(spec)
  if (rec.get("rendered") is not True or rec.get("mlt_only") is not True
      or rec.get("frei0r_verified") is not True
      or rec.get("visual_presence_check",{}).get("visible") is not True
      or rec.get("output_audio_verified") is not True
      or rec.get("ffmpeg_invocations")!=0 or not out.exists()):
   raise RuntimeError("MLT output video/audio visual certification failed")
  digest=sha(out);n=math.ceil(out.stat().st_size/CHUNK)
  if digest!=rec.get("sha256") or not 1<=n<=20:raise RuntimeError("Output SHA/size invalid")
  mark("output_upload")
  with out.open("rb") as f:
   for i in range(n):
    payload=f.read(CHUNK)
    result=call("/internal/v6/jobs/"+job_id+"/output/"+str(i),identity,method="PUT",
      claim=lease,data=payload,digest=hashlib.sha256(payload).hexdigest())
    if result.get("stored") is not True:raise RuntimeError("Private result chunk not admitted")
  receipt={k:v for k,v in rec.items() if k not in ("output","project")}
  receipt["model_roles"]=plan["model_roles"]
  receipt["model_policy"]=plan.get("model_policy","gemini_free_flash_groq")
  receipt["source_sha256"]=claim["source_sha256"]
  receipt["audio_library"]={"title":audio["title"],"license":"CC0","bpm":audio["bpm"],
    "sha256":audio["sha256"],"source":audio["original_source_url"],"native_audio_mix":rec.get("music_native_probed") is True}
  receipt["gemini_frames_sent"]=len(frames)
  receipt["product_context"]="generic"
  receipt["published"]=False
  receipt["owner_approval"]=False
  mark("private_complete")
  result=call("/internal/v6/jobs/"+job_id+"/complete",identity,claim=lease,
    payload={"state":"review_ready","chunks":n,"bytes":out.stat().st_size,"sha256":digest,"receipt":receipt})
  if result.get("state")!="review_ready":raise RuntimeError("Private server output certification rejected")
  print("MAD_V6_PRIVATE_KV_MLT_COMPLETED",job_id,"published=false","fixture="+str(synthetic))
  return result
 except Exception:
  try:call("/internal/v6/jobs/"+job_id+"/complete",identity,claim=lease,payload={"state":"failed"})
  except Exception:pass
  raise
 finally:
  src.unlink(missing_ok=True);out.unlink(missing_ok=True)
  (work/"v6-original-cc0-soundtrack.wav").unlink(missing_ok=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--job-id",required=True);p.add_argument("--synthetic-fixture",action="store_true")
 a=p.parse_args()
 try:run(a.job_id,fixture=a.synthetic_fixture)
 except Exception as ex:
  print(safe_failure(ex),file=sys.stderr,flush=True);sys.exit(2)
