#!/usr/bin/env python3
"""One bounded free-plan owner-authorized synthetic creative inference admission."""
import json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root))
import multimodel_filmcraft_bridge as m
source={"source_sha256":"a"*64,"human_reviewed":True,"rights_and_consent_cleared":True,
  "external_ai_processing_consent":True,
  "shots":[{"id":"s1","start_seconds":0.,"duration_seconds":4.,"visible":
     "An original digital flat dark green color matte. No humans, product labels or brand names."}]}
if not os.environ.get("GEMINI_API_KEY") or not (os.environ.get("REEL_ENGINE_KEY") or os.environ.get("GROQ_API_KEY")):
    raise SystemExit("PROVIDERS_NOT_CONFIGURED")
if os.environ.get("GEMINI_OWNER_APPROVED_FREE_CALLS")!="true":
    raise SystemExit("OWNER_FREE_CALL_APPROVAL_MISSING")
plan=m.run(source=source,brief="Create a cinematic minimal generic product teaser from this original color matte, no invented people.",
  brand="Generic consumer product teaser. No named brands or factual performance claims.",
  mode="live",approved_api_cost=True)
if plan["live_model_inference"] is not True or plan["editor"]!="FilmCraft":
    raise SystemExit("NOT_LIVE_CREATIVE_PLAN")
print(json.dumps({"result":"MAD_V6_REAL_GEMINI_GROQ_MODEL_PLAN_PASS","models":plan["model_roles"],
 "segments":len(plan["cuts"]),"effects":plan["requested_effects"],"published":False}))
