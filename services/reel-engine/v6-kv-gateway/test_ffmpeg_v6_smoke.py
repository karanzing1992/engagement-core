"""Synthetic-only smoke: real FFmpeg encode, frame extraction, receipt and fail-closed gates."""
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from ffmpeg_v6_adapter import render,RenderBlocked,sha256
from ffmpeg_frame_samples import extract
class FFmpegV6Smoke(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix="mad-v6-ffmpeg-smoke-")
  cls.work=Path(cls.tmp.name);cls.source=cls.work/"source.mp4"
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
   "-f","lavfi","-i","testsrc2=size=480x270:rate=24:duration=3",
   "-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=3",
   "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",
   "-c:a","aac","-shortest",str(cls.source)],check=True,timeout=90)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def spec(self):
  return {"workdir":str(self.work),"source":str(self.source),"source_sha256":sha256(self.source),
          "output":str(self.work/"finished.mp4"),"width":480,"height":270,"fps":24,
          "template_id":"wellness-cinema","hook":"PRIVATE V6 QA",
          "cuts":[{"start":.2,"seconds":1.2},{"start":1.4,"seconds":1.2}],
          "operations":[[{"id":"test-g","name":"color_grade","parameters":{"contrast":12}}],
                        [{"id":"test-t","name":"title","parameters":{"text":"SYNTHETIC TEST"}}]]}
 def test_real_video_audio_and_receipt(self):
  receipt=render(self.spec())
  self.assertEqual(receipt["engine"],"ffmpeg")
  self.assertTrue(all(receipt[x] for x in ("video_stream_verified","audio_stream_verified","full_decode_passed")))
  self.assertEqual(receipt["visual_presence_check"]["frames_examined"],3)
  self.assertEqual(receipt["music_mixed"],False)
  self.assertEqual(receipt["published"],False)
  self.assertGreater(self.work.joinpath("finished.mp4").stat().st_size,4096)
 def test_frames_require_consent(self):
  with self.assertRaises(RenderBlocked):
   extract(self.work,self.source,3,count=3,source_sha256=sha256(self.source))
  samples=extract(self.work,self.source,3,count=3,source_sha256=sha256(self.source),consent=True)
  self.assertEqual(len(samples),3)
  self.assertTrue(all(item["bytes"]>1024 for item in samples))
 def test_hash_mismatch_rejected(self):
  s=self.spec();s["source_sha256"]="a"*64
  with self.assertRaises(RenderBlocked):render(s)
 def test_unsupported_effect_rejected(self):
  s=self.spec();s["operations"][0][0]["name"]="shell_exec"
  with self.assertRaises(RenderBlocked):render(s)
 def test_unapproved_music_rejected(self):
  s=self.spec();s["music"]=str(self.source);s["music_sha256"]=sha256(self.source)
  s["music_rights"]={"human_verified":False,"license":"CC0","original_source_url":"https://example.org/"}
  with self.assertRaises(RenderBlocked):render(s)
 def test_unsupported_renderer_never_fallback(self):
  s=self.spec();s["template_id"]="filmcraft"
  with self.assertRaises(RenderBlocked):render(s)
if __name__=="__main__":unittest.main()
