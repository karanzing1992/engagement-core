"""V8 private synthetic regression: speech, actual transitions, model and rights gates."""
import copy,math,subprocess,tempfile,unittest
from array import array
from pathlib import Path
from unittest.mock import patch
from intelligence import inspect,intent,SourceBlocked,hash_file
from director import fallback_plan,validate_plan,director_prompt,CreativeBlocked,rank_treatments
from editor import render
from critic import inspect_output,decide_release
from pipeline import execute

class V8CreativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix="v8-private-synthetic-")
  cls.work=Path(cls.temp.name);cls.source=cls.work/"source.mp4";cls.music=cls.work/"synthetic-music.wav"
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
   "-f","lavfi","-i","testsrc2=size=480x270:rate=24:duration=4",
   "-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=4",
   "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
   "-c:a","aac","-shortest",str(cls.source)],check=True,timeout=70)
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
   "-f","lavfi","-i","sine=frequency=880:sample_rate=48000:duration=5",
   "-c:a","pcm_s16le",str(cls.music)],check=True,timeout=40)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def evidence(self,brief="Keep the dialogue clear and don't shorten the video. Cinematic"):
  return inspect(self.source,brief)
 def plan(self,ev,style="dip-to-black",music_gain=0.06):
  p=fallback_plan(ev)
  p["segments"]=[{"start":0.,"end":2.,"transition":"cut","grade":"cinematic_warm","text":None},
    {"start":2.,"end":4.,"transition":style,"grade":"soft_contrast","text":None}]
  p["audio"]={"preserve_source":ev["owner_intent"]["keep_source_audio"],"music_gain":music_gain}
  return p
 def rights(self):
  return {"human_verified":True,"license":"CC0",
   "original_source_url":"https://commons.wikimedia.org/wiki/File:synthetic-QA-only",
   "attribution_approved":True}
 def freq_amplitude(self,path):
  sample=subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",
   "-ss","0.5","-t","0.7","-i",str(path),
   "-vn","-ac","1","-ar","8000","-f","s16le","-"],check=True,capture_output=True,timeout=40).stdout
  data=array('h');data.frombytes(sample)
  cos=sum(v*math.cos(2*math.pi*440*i/8000) for i,v in enumerate(data))
  sin=sum(v*math.sin(2*math.pi*440*i/8000) for i,v in enumerate(data))
  return math.hypot(cos,sin)*2/len(data)
 def test_01_evidence_observable_not_invented(self):
  x=self.evidence()
  self.assertTrue(x["source"]["has_audio"]);self.assertEqual(x["speech_transcript"],None)
  self.assertEqual(x["visual_semantics_status"],"NOT_INFERRED")
  self.assertEqual(x["source"]["sha256"],hash_file(self.source))
 def test_02_director_ranked_and_grounded(self):
  x=self.evidence();r=rank_treatments(x)
  self.assertEqual(len(r),4);self.assertEqual(len(set(a["id"] for a in r)),4)
  self.assertIn("owner",director_prompt(x).lower())
  self.assertTrue(validate_plan(x,self.plan(x))["creative_plan_sha256"])
 def test_03_owner_timing_rejects_trims(self):
  x=self.evidence();p=self.plan(x);p["segments"][0]["start"]=.5
  with self.assertRaisesRegex(CreativeBlocked,"PROTECTED_DURATION_GAP"):validate_plan(x,p)
 def test_04_owner_dialogue_rejects_music_override(self):
  x=self.evidence();p=self.plan(x);p["audio"]["music_gain"]=.60
  with self.assertRaises(CreativeBlocked):validate_plan(x,p)
  p=self.plan(x);p["audio"]["preserve_source"]=False
  with self.assertRaisesRegex(CreativeBlocked,"SOURCE_AUDIO_SUPPRESSED"):validate_plan(x,p)
 def test_05_rejects_model_command_and_text_injection(self):
  x=self.evidence();p=self.plan(x);p["ffmpeg_command"]="rm -rf /"
  with self.assertRaisesRegex(CreativeBlocked,"UNTRUSTED_FIELDS"):validate_plan(x,p)
  p=self.plan(x);p["segments"][0]["text"]="\n"
  with self.assertRaises(CreativeBlocked):validate_plan(x,p)
 def test_06_audio_and_real_dip_transition(self):
  x=self.evidence();p=self.plan(x);out=self.work/"v8-dialogue.mp4"
  rec=render(x,p,self.work,out,music=self.music,music_rights=self.rights(),width=480,height=270,fps=24)
  self.assertTrue(rec["full_decode_passed"])
  self.assertEqual(rec["transition_count_compiled"],1)
  self.assertEqual(rec["music_ducking"],"speech_sidechain")
  self.assertGreater(self.freq_amplitude(out)/self.freq_amplitude(self.source),.65)
  report=inspect_output(x,p,rec,out)
  self.assertTrue(report["transitions"][0]["visual_signal_confirmed"])
  self.assertEqual(report["artistic_acceptance"],"PENDING_INDEPENDENT_RENDER_REVIEW")
  self.assertFalse(decide_release(report)["publish_authorized"])
 def test_07_dissolve_real_render_no_source_audio(self):
  x=self.evidence("Make a fast montage without original audio and no music")
  p=self.plan(x,"dissolve",music_gain=0.0)
  out=self.work/"v8-dissolve.mp4"
  rec=render(x,p,self.work,out,width=480,height=270,fps=24)
  self.assertEqual(rec["transition_types_compiled"],["dissolve"])
  self.assertTrue(rec["full_decode_passed"])
  self.assertLess(rec["duration_seconds"],x["source"]["duration"])
 def test_08_explicit_consent_and_publishing(self):
  x=self.evidence();p=self.plan(x)
  self.assertFalse(decide_release({"technical_acceptance":True},owner_approved=True)["publish_authorized"])
  with self.assertRaisesRegex(CreativeBlocked,"CONSENT_REQUIRED"):
   execute(source=self.source,brief=x["owner_intent"]["brief"],workdir=self.work,
    output=self.work/"v8-blocked.mp4",model_director=lambda *a:p,
    width=480,height=270,fps=24)
 def test_09_brand_isolation(self):
  x=self.evidence()
  with self.assertRaisesRegex(CreativeBlocked,"BRAND_ISOLATION_FAILED"):
   execute(source=self.source,brief=x["owner_intent"]["brief"],workdir=self.work,
    output=self.work/"v8-brand-blocked.mp4",brand_rules="Private brand facts",
    width=480,height=270,fps=24)
 def test_10_separate_rag_and_creative_gates(self):
  x=self.evidence("No music, keep full video and dialogue clear")
  out=self.work/"v8-pipeline.mp4"
  r=execute(source=self.source,brief=x["owner_intent"]["brief"],workdir=self.work,
     output=out,rag_loader=lambda *a:({"universal":"Best practices only"},{"status":"ready","director_ids":["qa05"]}),
     require_rag=True,width=480,height=270,fps=24)
  self.assertTrue(r["release"]["private_preview_ready"])
  self.assertFalse(r["release"]["creative_certified"])
  self.assertFalse(r["published"]);self.assertEqual(r["rag"]["status"],"ready")
 def test_11_unverified_creative_review_never_certifies(self):
  self.assertFalse(decide_release({"technical_acceptance":True},
    independent_visual_audio_review={"approved":True})["creative_certified"])
  self.assertTrue(decide_release({"technical_acceptance":True,"output_sha256":"abc"},
    independent_visual_audio_review={"verified_actual_media":True,"reviewed_output_sha256":"abc",
      "dialogue_clear":True,"editorial_acceptable":True})["creative_certified"])
 def test_12_conflicts_fail_closed(self):
  with self.assertRaises(SourceBlocked):
   intent("Preserve the dialogue and remove original audio")
  x=self.evidence("Keep dialogue clear with no transitions")
  p=self.plan(x)
  with self.assertRaisesRegex(CreativeBlocked,"TRANSITION_FORBIDDEN"):validate_plan(x,p)

if __name__=="__main__":unittest.main()
