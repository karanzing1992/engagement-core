"""V6 brand-neutral Gemini frame, owner admission and CC0 audio tests."""
import base64,hashlib,os,tempfile
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"services/reel-engine"))
sys.path.insert(0,str(ROOT/"services/reel-engine/v6-kv-gateway"))
sys.path.insert(0,str(ROOT/"experiments/reel-engine-v6"))
import multimodel_filmcraft_bridge as mm
import original_cc0_audio as audio

SOURCE={"source_sha256":"a"*64,"human_reviewed":True,
 "rights_and_consent_cleared":True,"external_ai_processing_consent":True,
 "shots":[{"id":"s1","start_seconds":0.0,"duration_seconds":4.0,
           "visible":"Original abstract geometric footage with no people."}]}
FRAME={"time_seconds":2.0,"mime_type":"image/jpeg","data":base64.b64encode(b"fake-jpeg-contract").decode(),"sha256":"b"*64}
class IntegrationTests(unittest.TestCase):
 def test_owner_approved_gemini_inline_frame_and_grounded_text(self):
  captured=[]
  def call(url,headers,payload,timeout=50):
   captured.append((url,payload))
   return {"candidates":[{"content":{"parts":[{"text":
     '{"observations":[{"shot_id":"s1","visible":"abstract geometry"}],'
     '"research_scope":"Source imagery and approved human description only"}'}]}}]}
  models={"models":[{"name":"models/gemini-3.8-flash","supportedGenerationMethods":["generateContent"]}]}
  with patch.dict(os.environ,{"GEMINI_API_KEY":"synthetic-test","GEMINI_INFERENCE_OWNER_APPROVED":"true"},clear=False),patch.object(mm,"discover_models",return_value=models),patch.object(mm,"post_json",side_effect=call):
   model,result=mm.gemini_research(SOURCE,"Make a cinematic generic product montage.",approved_api_cost=True,frames=[FRAME])
  self.assertEqual(model,"gemini-3.8-flash")
  parts=captured[0][1]["contents"][0]["parts"]
  self.assertEqual(len(parts),3)
  self.assertIn("source frame at",parts[1]["text"].lower())
  self.assertEqual(parts[2]["inline_data"]["mime_type"],"image/jpeg")
  self.assertEqual(result["observations"][0]["shot_id"],"s1")
  self.assertNotIn("moksha",parts[0]["text"].lower())
 def test_refuses_frames_without_consent(self):
  source=dict(SOURCE);source["external_ai_processing_consent"]=False
  with self.assertRaises(mm.V6Blocked):
   mm.run(source=source,brief="Generic cinematic product montage",brand="",
      mode="fixture",frames=[FRAME])
 def test_free_model_only_owner_approval_not_billing_claim(self):
  with patch.dict(os.environ,{"GEMINI_INFERENCE_OWNER_APPROVED":"false",
    "GEMINI_PROJECT_FREE_TIER_VERIFIED":"false"}):
   with self.assertRaises(mm.V6Blocked):
    mm.gemini_research(SOURCE,"Generic reel",approved_api_cost=True,frames=[FRAME])
 def test_cc0_audio_is_original_has_beats_and_checksum(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"track.wav"
   music=audio.compose(path,3.3,"ambient")
   self.assertEqual(music["license"],"CC0")
   self.assertEqual(music["mode"],"original_cc0_music")
   self.assertTrue(music["bytes"]>1000)
   self.assertEqual(music["sha256"],hashlib.sha256(path.read_bytes()).hexdigest())
   self.assertGreater(music["beat_seconds"],0)
   self.assertLess(music["peak"],0.89)
   self.assertTrue(music["filmcraft_rights"]["human_verified"])
 def test_bounded_503_free_model_fallback(self):
  urls=[]
  catalog={"models":[{"name":"models/gemini-3.8-flash","supportedGenerationMethods":["generateContent"]},
   {"name":"models/gemini-3.7-flash","supportedGenerationMethods":["generateContent"]}]}
  def pretend(url,headers,payload,timeout=50):
   urls.append(url)
   if "gemini-3.8-flash" in url:raise mm.FreeModelTemporarilyUnavailable("Synthetic 503")
   return {"candidates":[{"content":{"parts":[{"text":
     '{"observations":[{"shot_id":"s1","visible":"abstract geometry"}],'
     '"research_scope":"Grounded visual evidence from the sampled frames"}'}]}}]}
  with patch.dict(os.environ,{"GEMINI_INFERENCE_OWNER_APPROVED":"true","GEMINI_API_KEY":"synthetic-test"}),patch.object(mm,"discover_models",return_value=catalog),patch.object(mm,"post_json",side_effect=pretend),patch.object(mm.time,"sleep",return_value=None):
   model,_=mm.gemini_research(SOURCE,"Generic footage",approved_api_cost=True,frames=[FRAME])
  self.assertEqual(model,"gemini-3.7-flash")
  self.assertEqual(len(urls),3)
  self.assertFalse(any("-pro" in z for z in urls))
 def test_reviewer_metadata_repair_never_overrides_rejection(self):
  proposal={"hook":"A calm reset","segments":[
   {"shot_id":"s1","start_seconds":0,"duration_seconds":1.3,"effects":[]},
   {"shot_id":"s1","start_seconds":1.3,"duration_seconds":1.3,"effects":[]}]}
  good={"approved":True,"director_plan_sha256":mm.sha_json(proposal),
        "segment_decisions":[{"segment_index":0,"approved":True},
                             {"segment_index":1,"approved":True}]}
  self.assertFalse(mm.reviewer_schema_needs_retry(proposal,good))
  mismatch={**good,"director_plan_sha256":"z"*64}
  self.assertTrue(mm.reviewer_schema_needs_retry(proposal,mismatch))
  missing={**good,"segment_decisions":[{"segment_index":0,"approved":True}]}
  self.assertTrue(mm.reviewer_schema_needs_retry(proposal,missing))
  wrong={**good,"segment_decisions":[{"segment_index":1,"approved":True},
                                     {"segment_index":0,"approved":True}]}
  self.assertTrue(mm.reviewer_schema_needs_retry(proposal,wrong))
  denied={**good,"approved":False}
  self.assertFalse(mm.reviewer_schema_needs_retry(proposal,denied))
  segment_denied={**good,"segment_decisions":[{"segment_index":0,"approved":False},
                                             {"segment_index":1,"approved":True}]}
  self.assertFalse(mm.reviewer_schema_needs_retry(proposal,segment_denied))
  with self.assertRaises(mm.V6Blocked):
   mm.compile_reviewed_edl(SOURCE,proposal,segment_denied)
  self.assertFalse(mm.reviewer_schema_needs_retry(proposal,{}))

 def test_strict_groq_review_schema_binds_local_sha_and_indices(self):
  proposal={"hook":"A moment of calm","segments":[
   {"shot_id":"s1","start_seconds":0.0,"duration_seconds":1.5,"effects":[{"name":"color_grade","parameters":{"contrast":12}}]},
   {"shot_id":"s1","start_seconds":1.5,"duration_seconds":1.5,"effects":[{"name":"title","parameters":{"text":"BREATHE"}}]}]}
  fmt=mm.strict_review_response_format(proposal)
  self.assertEqual(fmt["type"],"json_schema")
  self.assertIs(fmt["json_schema"]["strict"],True)
  schema=fmt["json_schema"]["schema"]
  self.assertEqual(set(schema["properties"]),{"approved","decisions"})
  self.assertEqual(schema["properties"]["decisions"]["required"],["s0","s1"])
  self.assertNotIn("director_plan_sha256",str(schema))
  raw={"approved":True,"decisions":{
    "s0":{"approved":True,"reason_code":"APPROVED"},
    "s1":{"approved":True,"reason_code":"APPROVED"}}}
  with patch.object(mm,"groq_call",return_value=raw) as fake:
   reviewed=mm.groq_strict_review(SOURCE,proposal)
  self.assertEqual(fake.call_count,1)
  self.assertEqual(fake.call_args.kwargs["response_format"],fmt)
  self.assertEqual(reviewed["director_plan_sha256"],mm.sha_json(proposal))
  self.assertEqual(reviewed["segment_decisions"],[
    {"segment_index":0,"approved":True},{"segment_index":1,"approved":True}])
  edl=mm.compile_reviewed_edl(SOURCE,proposal,reviewed)
  self.assertEqual(len(edl["cuts"]),2)
  self.assertEqual(edl["editor"],"FFmpeg")
 def test_strict_groq_reviewer_explicit_rejections_do_not_retry(self):
  p={"hook":"Stay present","segments":[{"shot_id":"s1","start_seconds":0.0,
   "duration_seconds":1.2,"effects":[]}]}
  for response in (
   {"approved":False,"decisions":{"s0":{"approved":False,"reason_code":"SOURCE_UNVERIFIED"}}},
   {"approved":False,"decisions":{"s0":{"approved":True,"reason_code":"APPROVED"}}},
   {"approved":True,"decisions":{"s0":{"approved":False,"reason_code":"RIGHTS_CONSENT_MISSING"}}},
  ):
   with patch.object(mm,"groq_call",return_value=response) as mock_review:
    with self.assertRaisesRegex(mm.V6Blocked,"Independent reviewer rejected"):
     mm.groq_strict_review(SOURCE,p)
    self.assertEqual(mock_review.call_count,1)
 def test_strict_groq_reviewer_malformed_or_inconsistent_fails_closed(self):
  p={"hook":"Stay present","segments":[{"shot_id":"s1","start_seconds":0.0,
   "duration_seconds":1.2,"effects":[]}]}
  invalid=[
    {"approved":True,"decisions":{}},
    {"approved":True,"decisions":{"s0":{"approved":True,"reason_code":"OTHER"}}},
    {"approved":True,"decisions":{"s0":{"approved":"true","reason_code":"APPROVED"}}},
    {"approved":True,"decisions":{"s0":{"approved":True,"reason_code":"APPROVED"}},"director_plan_sha256":"FAKE"},
  ]
  for response in invalid:
   with self.assertRaisesRegex(mm.V6Blocked,"Strict reviewer response invalid"):
    mm.bind_strict_review_to_plan(p,response)
 def test_groq_structured_request_never_uses_json_object(self):
  p={"hook":"Stay present","segments":[{"shot_id":"s1","start_seconds":0.0,
   "duration_seconds":1.2,"effects":[]}]}
  fmt=mm.strict_review_response_format(p)
  sent=[]
  def canned(url,headers,payload,timeout=50):
   sent.append(payload)
   return {"choices":[{"message":{"content":'{"approved":true,"decisions":{"s0":{"approved":true,"reason_code":"APPROVED"}}}'}}]}
  with patch.dict(os.environ,{"GROQ_API_KEY":"synthetic_only","REEL_ENGINE_KEY":""}),patch.object(mm,"post_json",side_effect=canned):
   review=mm.groq_call("openai/gpt-oss-20b","Review abstract geometry",temperature=0.1,
                       max_tokens=1600,response_format=fmt)
  self.assertTrue(review["approved"])
  self.assertEqual(sent[0]["response_format"],fmt)
  self.assertNotIn("director_plan_sha256",sent[0]["messages"][-1]["content"])
 def test_strict_reviewer_rejects_unsupported_ges_effect_locally(self):
  p={"hook":"Stay present","segments":[{"shot_id":"s1","start_seconds":0.0,
   "duration_seconds":1.2,"effects":[{"name":"zoom","parameters":{}}]}]}
  with patch.object(mm,"groq_call") as groq:
   with self.assertRaisesRegex(mm.V6Blocked,"Unsupported FFmpeg effect"):
    mm.groq_strict_review(SOURCE,p)
   groq.assert_not_called()
 def test_live_bridge_preserves_independent_strict_reviewer(self):
  proposal={"hook":"A reset","segments":[{"shot_id":"s1","start_seconds":0.0,
   "duration_seconds":1.4,"effects":[{"name":"color_grade","parameters":{"contrast":12}}]}]}
  raw={"approved":True,"decisions":{"s0":{"approved":True,"reason_code":"APPROVED"}}}
  calls=[]
  def groq(model,prompt,**kwargs):
   calls.append((model,kwargs.get("response_format")))
   return proposal if model=="openai/gpt-oss-120b" else raw
  research={"observations":[{"shot_id":"s1","visible":"Original abstract geometric footage"}],
            "research_scope":"Only consented source images and owner verified notes"}
  with patch.object(mm,"gemini_research",return_value=("gemini-3.8-flash",research)),patch.object(mm,"groq_call",side_effect=groq):
   r=mm.run(source=SOURCE,brief="Create a private cinematic reel",brand="",
            mode="live",approved_api_cost=True)
  self.assertEqual([c[0] for c in calls],["openai/gpt-oss-120b","openai/gpt-oss-20b"])
  self.assertIsNone(calls[0][1])
  self.assertTrue(calls[1][1]["json_schema"]["strict"])
  self.assertEqual(r["editor"],"FFmpeg")

 def test_audio_profile_generic(self):
  self.assertEqual(audio.choose("A calm serene scenic sequence"),"ambient")
  self.assertEqual(audio.choose("A high energy fitness reel"),"uplift")
if __name__=="__main__":unittest.main()
