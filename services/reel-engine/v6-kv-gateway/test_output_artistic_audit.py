"""V6 finished-frame artistic audit is evidence-limited and never owner approval."""
import hashlib,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"services/reel-engine"))
sys.path.insert(0,str(ROOT/"services/reel-engine/v6-kv-gateway"))
sys.path.insert(0,str(ROOT/"experiments/reel-engine-v6"))
import output_artistic_audit as qa

class VisualReviewTests(unittest.TestCase):
 def test_actual_render_frames_and_independent_editorial_review(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"video.mp4";out.write_bytes(b"synthetic_test"*500)
   frames=[{"time_seconds":float(i),"mime_type":"image/jpeg",
     "data":"aGVsbG8="} for i in (1,2,3)]
   gemini={"candidates":[{"content":{"parts":[{"text":
    '{"visual_readability":"Clear title","color_consistency":"Consistent greens",'
    '"story_clarity":"Simple abstract cut","artifact_concerns":[],"visual_pass":true}'}]}}]}
   response={"approved":True,"quality_concerns":[],"review_scope":"Only sampled still frames"}
   models={"models":[{"name":"models/gemini-3.6-flash","supportedGenerationMethods":["generateContent"]}]}
   with patch.dict(os.environ,{"GEMINI_API_KEY":"synthetic","GEMINI_INFERENCE_OWNER_APPROVED":"true"}),patch.object(qa,"extract",return_value=frames) as extraction,patch.object(qa.bridge,"discover_models",return_value=models),patch.object(qa.bridge,"post_json",return_value=gemini) as api,patch.object(qa.bridge,"groq_call",return_value=response) as groq:
    actual=qa.review(cli="native-filmcraft",workdir=Path(d),output=out,
      receipt={"filmcraft_only":True,"rendered":True,"duration_seconds":4.0,
       "operations_requested":3,"operations_command_accepted":3,
       "output_audio_verified":True},brief="Generic cinematic product",hook="A NEW VIEW",
      source_consent=True)
   self.assertEqual(actual["status"],"automated_visual_pass")
   self.assertEqual(actual["frames_checked"],3)
   self.assertIs(actual["owner_approved"],False)
   self.assertEqual(actual["audio_listening_review"],"not_completed")
   self.assertFalse(actual["published"])
   self.assertEqual(groq.call_count,1)
 def test_review_cannot_send_frames_without_explicit_consent(self):
  with self.assertRaises(qa.V6Blocked):
   qa.review(cli="filmcraft",workdir=Path("/tmp"),output=Path("/tmp/notfound.mp4"),
     receipt={"filmcraft_only":True,"rendered":True,"duration_seconds":4},brief="Generic",
     hook="A title",source_consent=False)
if __name__=="__main__":unittest.main()
