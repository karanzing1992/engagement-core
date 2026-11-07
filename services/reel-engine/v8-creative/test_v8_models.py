"""Security and independent-review contracts; no external provider calls in CI."""
import unittest
from unittest.mock import patch
from intelligence import intent
from director import CreativeBlocked
from critic import decide_release
import models

class V8ProviderContracts(unittest.TestCase):
 def test_explicit_dialogue_direction_not_overridden(self):
  r=intent("Make a cinematic film. The dialogues are important, don't shorten")
  self.assertTrue(r["dialogue_priority"])
  self.assertTrue(r["preserve_full_source"])
  self.assertTrue(r["keep_source_audio"])
 def test_without_original_audio_is_not_dialogue_instruction(self):
  r=intent("A rhythmic montage without original audio and no music")
  self.assertFalse(r["dialogue_priority"])
  self.assertFalse(r["keep_source_audio"])
  self.assertFalse(r["music_allowed"])
 def test_groq_never_calls_api_without_owner_free_flags(self):
  with patch.dict("os.environ",{"MAD_V8_OWNER_AI_ENABLED":"false"},clear=True):
   with patch.object(models.ai,"groq_call") as api:
    with self.assertRaisesRegex(CreativeBlocked,"OWNER_FREE_AI_FLAGS"):
     models.groq_director("safe prompt",{})
    api.assert_not_called()
 def test_gemini_never_samples_footage_without_consent(self):
  with patch.dict("os.environ",{"MAD_V8_OWNER_AI_ENABLED":"true",
    "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true",
    "GEMINI_INFERENCE_OWNER_APPROVED":"true"},clear=True):
   with patch.object(models,"sample_frames") as sampling:
    with self.assertRaisesRegex(CreativeBlocked,"VISUAL_CONSENT"):
     models.gemini_source_analyst({"consent_for_external_inference":False}, "/tmp")
    sampling.assert_not_called()
 def test_fake_reviewer_hash_rejected(self):
  r=decide_release({"technical_acceptance":True,"output_sha256":"immutable-a"},
    independent_visual_audio_review={"verified_actual_media":True,
    "reviewed_output_sha256":"different-b","dialogue_clear":True,
    "editorial_acceptable":True})
  self.assertFalse(r["creative_certified"])
  self.assertFalse(r["publish_authorized"])
 def test_gemini_source_visual_contract_reuses_canonical_s1_shot(self):
  evidence={"consent_for_external_inference":True,
    "source":{"path":"/private/source.mp4","duration":6.0,"sha256":"a"*64},
    "owner_intent":{"brief":"Cinematic footage; preserve original dialogue"}}
  frames=[{"sha256":"b"*64,"mime_type":"image/jpeg","data":"bW9jaw==","time_seconds":2.0}]
  observation={"observations":[{"shot_id":"s1","visible":"Synthetic moving colour pattern"}],
    "research_scope":"Source frame evidence only"}
  with patch.dict("os.environ",{"MAD_V8_OWNER_AI_ENABLED":"true",
    "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true",
    "GEMINI_INFERENCE_OWNER_APPROVED":"true"},clear=True):
   with patch.object(models,"sample_frames",return_value=frames):
    with patch.object(models.ai,"gemini_research",return_value=("gemini-free-flash",observation)) as research:
     result=models.gemini_source_analyst(evidence,"/tmp")
     self.assertTrue(result["inference_from_consent"])
     self.assertEqual(result["observations"][0]["shot_id"],"s1")
     manifest=research.call_args[0][0]
     self.assertEqual(manifest["shots"][0]["id"],"s1")
 def test_gemini_rejects_unknown_source_identity(self):
  evidence={"consent_for_external_inference":True,
    "source":{"path":"/private/source.mp4","duration":6.0,"sha256":"a"*64},
    "owner_intent":{"brief":"Observe scenes without inventing them"}}
  frames=[{"sha256":"b"*64,"mime_type":"image/jpeg","data":"bW9jaw==","time_seconds":2.0}]
  bad={"observations":[{"shot_id":"unverified","visible":"Unknown source label"}],
    "research_scope":"Source frame evidence only"}
  with patch.dict("os.environ",{"MAD_V8_OWNER_AI_ENABLED":"true",
    "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true",
    "GEMINI_INFERENCE_OWNER_APPROVED":"true"},clear=True):
   with patch.object(models,"sample_frames",return_value=frames):
    with patch.object(models.ai,"gemini_research",return_value=("gemini-free-flash",bad)):
     with self.assertRaises(models.ai.V6Blocked):
      models.gemini_source_analyst(evidence,"/tmp")
if __name__=="__main__":unittest.main()
