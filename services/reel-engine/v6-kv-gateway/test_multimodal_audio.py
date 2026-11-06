"""V6 brand-neutral Gemini frame, owner admission and CC0 audio tests."""
import base64,hashlib,os,tempfile
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
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
  self.assertNotIn("brand",parts[0]["text"].lower())
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
 def test_audio_profile_generic(self):
  self.assertEqual(audio.choose("A calm serene scenic sequence"),"ambient")
  self.assertEqual(audio.choose("A high energy fitness reel"),"uplift")
if __name__=="__main__":unittest.main()
