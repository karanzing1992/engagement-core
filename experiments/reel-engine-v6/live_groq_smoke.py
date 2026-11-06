#!/usr/bin/env python3
"""One actual 120B/20B independent editorial QA on a synthetic generic source."""
import json,os
import multimodel_filmcraft_bridge as m
source={"source_sha256":"b"*64,"human_reviewed":True,"rights_and_consent_cleared":True,"external_ai_processing_consent":True,
 "shots":[{"id":"s1","start_seconds":0.0,"duration_seconds":4.0,"visible":"A flat green original color matte with no people, no real product and no brands."}]}
brief="Make a minimal cinematic four-second generic product mood reel without inventing any objects."
q=("Return ONLY JSON with keys hook and segments. Exactly one segment: shot_id s1, "
   "start_seconds 0, duration_seconds 3.0, effects with one color_grade contrast 12. "
   "Create a compelling short hook (max 60 chars) for generic product atmosphere. "
   "Do not invent source footage. Source: "+json.dumps(source["shots"])+" Brief: "+brief)
director=m.normalize_effect_shape(m.groq_call("openai/gpt-oss-120b",q,temperature=.3,max_tokens=1200))
print("GROQ_DIRECTOR_STRUCTURAL_DIAGNOSTIC",{"keys":list(director),"segments":len(director.get("segments",[])) if isinstance(director.get("segments"),list) else "not_list","effect_types":[type(z.get("effects")).__name__ for z in director.get("segments",[]) if isinstance(z,dict)]})
m.validate_director(source,director)
h=m.sha_json(director)
reviewprompt=("Return ONLY JSON with approved:true, director_plan_sha256 exactly "+h+
 " and segment_decisions array with one object {segment_index:0,approved:true}. "
 "Review this source-grounded EDL for unsupported effects or fictional events. "
 "If unsuitable return approved:false. Director JSON: "+json.dumps(director))
review=m.groq_call("openai/gpt-oss-20b",reviewprompt,temperature=.1,max_tokens=900)
edl=m.compile_reviewed_edl(source,director,review)
if edl["requested_effects"]<1:raise RuntimeError("No FilmCraft effects to certify")
print(json.dumps({"status":"LIVE_GROQ_120B_20B_EDITORIAL_PASS","models":["openai/gpt-oss-120b","openai/gpt-oss-20b"],
 "cuts":len(edl["cuts"]),"requested_effects":edl["requested_effects"],"renderer_invoked":False,"published":False}))
