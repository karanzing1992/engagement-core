#!/usr/bin/env python3
"""MAD V6 signed Cloudflare KV runner. FilmCraft only; private media never in CI artifacts."""
from __future__ import annotations
import argparse,hashlib,json,os,sys,math,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urlencode
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"services/reel-engine"))
sys.path.insert(0,str(ROOT/"experiments/reel-engine-v6"))
import filmcraft_v6_adapter as filmcraft
import multimodel_filmcraft_bridge as multimodel
from native_frames import sample_video_frames
from open_cc0_audio import verified_cc0_audio, AudioRuntimeError
from original_cc0_audio import original_cc0_soundtrack

GATEWAY="https://mad-v6-kv-private-beta.karanbizweb360.workers.dev"
AUD="mad-v6-cloudflare-kv/1"
CHUNK=4*1024*1024
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
 headers={"Authorization":"Bearer "+identity,"User-Agent":"MAD-V6-Private-KV-FilmCraft"}
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
 brand="Generic video editing service. Follow the creator prompt; never invent source footage or unsupported claims."
 if fixture:
  return multimodel.run(source=manifest,brief=brief,brand=brand,mode="fixture")
 if os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")=="true" or os.environ.get("GEMINI_FREE_TIER_OWNER_ATTESTED")=="true":
  return multimodel.run(source=manifest,brief=brief,brand=brand,mode="live",approved_api_cost=True,frames=frames)
 # Approved free-tier fallback: existing Groq models. No Gemini paid fallback.
 multimodel.read_config()
 multimodel.validate_source_manifest(manifest,external_gemini_frames=False)
 observed={"observations":[{"shot_id":"s1","visible":description}],
           "research_scope":"Human-reviewed and owner-authorized footage description; no independent visual inference."}
 prompt=("Return JSON {\"hook\":string,\"segments\":[{\"shot_id\":\"s1\",\"start_seconds\":number,"
         "\"duration_seconds\":number,\"effects\":[{\"name\":\"color_grade\",\"parameters\":{\"contrast\":12}}]}]}. "
         "Act as premium cinematic director. No fabricated shot or off-screen activity. "
         "Actual reviewed source "+json.dumps(manifest["shots"])+
         " Brand "+brand+" Creative direction "+brief)
 director=multimodel.groq_call("openai/gpt-oss-120b",prompt,temperature=.65,max_tokens=1800)
 multimodel.validate_director(manifest,director)
 review_prompt=("Independently reject invented timecodes/effects. Return strict JSON with approved boolean, "
   "director_plan_sha256 and segment_decisions: index+approved for all segments. "
   "Use this exact director sha:"+multimodel.sha_json(director)+" and storyboard:"+json.dumps(director))
 review=multimodel.groq_call("openai/gpt-oss-20b",review_prompt,temperature=.12,max_tokens=1300)
 plan=multimodel.compile_reviewed_edl(manifest,director,review)
 plan.update({"model_roles":{"gemini":"SKIPPED_FREE_TIER_NOT_VERIFIED",
    "groq_director":"openai/gpt-oss-120b","groq_reviewer":"openai/gpt-oss-20b"},
    "model_policy":"free_tier_groq_only_fallback","live_model_inference":True,
    "source_rights_admitted":True,"audio_mode":"source_ambience_only",
    "published":False,"owner_approval":False})
 return plan

def run(job_id,*,fixture=False):
 if not job_id.startswith("v6job-") or len(job_id)!=38:raise ValueError("Invalid private V6 job")
 if not os.environ.get("FILMCRAFT_CLI"):raise ValueError("FilmCraft binary missing")
 work=Path(os.environ["RUNNER_TEMP"])/("mad-v6-"+job_id)
 work.mkdir(mode=0o700,parents=True,exist_ok=True)
 identity=token()
 claim=call("/internal/v6/jobs/"+job_id+"/claim",identity)
 if claim.get("job_id")!=job_id or not claim.get("rights_confirmed") or not claim.get("people_consent"):
  raise RuntimeError("Unauthorized owner source")
 lease=claim["claim_id"]
 mime=claim["mime"]
 extension={"video/mp4":"mp4","video/quicktime":"mov","video/webm":"webm"}.get(mime)
 if not extension:raise RuntimeError("Unsupported source media")
 src=work/("source."+extension);out=work/"v6-output.mp4"
 try:
  with src.open("wb") as f:
   for i in range(claim["source_chunks"]):
    part=call("/internal/v6/jobs/"+job_id+"/source/"+str(i),identity,method="GET",claim=lease)
    required=min(CHUNK,claim["source_bytes"]-i*CHUNK)
    if len(part)!=required:raise RuntimeError("Private source part size failure")
    f.write(part)
  if src.stat().st_size!=claim["source_bytes"] or sha(src)!=claim["source_sha256"]:
   raise RuntimeError("Source media SHA-256 verification failed")
  m=filmcraft.MCP(os.environ["FILMCRAFT_CLI"],work)
  try:
   native=m.cmd("mediaBrowser.probe",{"path":str(src)}).get("info",{})
   duration=native.get("duration",0)/filmcraft.TICKS_PER_SECOND
   if not native.get("video") or not 3<=duration<=480:raise RuntimeError("Native video source probe failed")
  finally:m.close()
  synthetic=fixture and claim.get("source_description","").startswith("SYNTHETIC QA:")
  if fixture and not synthetic:raise RuntimeError("Synthetic fixture cannot render real guest footage")
  frames=[]
  if os.environ.get("MAD_V6_FRAMES_TO_GEMINI")=="true" and not synthetic:
   if claim.get("free_gemini_consent") is not True or claim.get("people_consent") is not True:
    raise RuntimeError("External Gemini vision consent missing")
   frames=sample_video_frames(src,cli=os.environ["FILMCRAFT_CLI"],workdir=work,
     duration=duration,external_ai_consent=True)
  plan=model_plan(claim["source_sha256"],claim["brief"],claim["source_description"],duration,fixture=synthetic,frames=frames)
  audio=None
  if claim.get("audio_mode")=="original_cc0" or (claim.get("project_id")=="synthetic-owner-qa" and os.environ.get("MAD_V6_CURATED_CC0_AUDIO")=="true"):
   timeline_seconds=sum(float(cut["seconds"]) for cut in plan["cuts"])
   if os.environ.get("MAD_V6_AUDIO_SOURCE","original_cc0")=="original_cc0":
    audio=original_cc0_soundtrack(work,seconds=max(8.0,timeline_seconds+2),brief=claim["brief"])
   else:
    try:
     audio=verified_cc0_audio(work,minimum_seconds=timeline_seconds)
    except AudioRuntimeError:
     if os.environ.get("MAD_V6_ALLOW_ORIGINAL_CC0_FALLBACK")!="true":raise
     audio=original_cc0_soundtrack(work,seconds=max(8.0,timeline_seconds+2),brief=claim["brief"])
     audio["source_fallback"]="commons_unavailable"
   print("MAD_V6_CC0_AUDIO_SOURCE_READY",audio["audio_sha256"],flush=True)
  rec=filmcraft.render(cli=os.environ["FILMCRAFT_CLI"],workdir=work,output=out,source=src,
     source_rights_cleared=True,source_sha256=claim["source_sha256"],
     cuts=plan["cuts"],operations=plan["operations"],hook=plan["hook"],
     music=Path(audio["audio_path"]) if audio else None,
     music_rights=audio["filmcraft_rights"] if audio else None,
     width=1080,height=1920,fps=30)
  if rec.get("rendered") is not True or rec.get("ffmpeg_invocations")!=0 or not out.exists():
   raise RuntimeError("Native FilmCraft rendered output verification failed")
  digest=sha(out);n=math.ceil(out.stat().st_size/CHUNK)
  if digest!=rec.get("sha256") or not 1<=n<=20:raise RuntimeError("Output SHA/size invalid")
  with out.open("rb") as f:
   for i in range(n):
    payload=f.read(CHUNK)
    result=call("/internal/v6/jobs/"+job_id+"/output/"+str(i),identity,method="PUT",
      claim=lease,data=payload,digest=hashlib.sha256(payload).hexdigest())
    if result.get("stored") is not True:raise RuntimeError("Private result chunk not admitted")
  receipt={k:v for k,v in rec.items() if k not in ("output","project")}
  receipt["model_roles"]=plan["model_roles"]
  receipt["vision_frames_sent"]=len(frames)
  receipt["vision_frame_sha256"]=[f["sha256"] for f in frames]
  receipt["audio_mode"]="original_cc0" if audio else "source_ambience_only"
  receipt["audio_provenance"]={k:audio[k] for k in ("license","track_title","audio_sha256","original_source_url","original_license_url","attribution_required") if k in audio} if audio else None
  receipt["music_native_probed"]=rec.get("music_native_probed",False)
  receipt["independent_artistic_approval"]=False
  receipt["model_policy"]=plan.get("model_policy","gemini_free_flash_groq")
  receipt["source_sha256"]=claim["source_sha256"]
  receipt["published"]=False
  receipt["owner_approval"]=False
  result=call("/internal/v6/jobs/"+job_id+"/complete",identity,claim=lease,
    payload={"state":"review_ready","chunks":n,"bytes":out.stat().st_size,"sha256":digest,"receipt":receipt})
  if result.get("state")!="review_ready":raise RuntimeError("Private server output certification rejected")
  print("MAD_V6_PRIVATE_KV_FILMCRAFT_COMPLETED",job_id,"published=false","fixture="+str(synthetic))
  return result
 except Exception:
  try:call("/internal/v6/jobs/"+job_id+"/complete",identity,claim=lease,payload={"state":"failed"})
  except Exception:pass
  raise
 finally:
  src.unlink(missing_ok=True);out.unlink(missing_ok=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--job-id",required=True);p.add_argument("--synthetic-fixture",action="store_true")
 a=p.parse_args()
 try:run(a.job_id,fixture=a.synthetic_fixture)
 except Exception as ex:
  print("V6_KV_PRIVATE_RENDER_FAILED",type(ex).__name__,file=sys.stderr);sys.exit(2)
