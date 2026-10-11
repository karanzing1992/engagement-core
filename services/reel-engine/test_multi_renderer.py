from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from multi_renderer import MultiClipError, probe_media, validate_plan, render_multiple


class MultiClipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make_video(self, name: str, duration: float, audio: bool=True):
        p=self.root/name
        cmd=["ffmpeg","-v","error","-y","-f","lavfi","-i","testsrc=size=320x180:rate=15"]
        if audio: cmd+=["-f","lavfi","-i","sine=frequency=440:sample_rate=48000"]
        cmd+=["-t",str(duration),"-c:v","libx264","-preset","ultrafast",
              "-pix_fmt","yuv420p"]
        if audio: cmd+=["-c:a","aac"]
        else: cmd+=["-an"]
        cmd+=[str(p)]
        subprocess.run(cmd,check=True)
        return p

    def test_reject_timeline_longer_than_target(self):
        p=[{"duration":40}, {"duration":50}]
        with self.assertRaisesRegex(MultiClipError,"sum"):
            validate_plan([Path("/a"),Path("/b")],
                          {"target_seconds":30,"clip_plan":[{"source_index":0,"seconds":19},
                                                              {"source_index":1,"seconds":20}]},p)

    def test_reject_timing_beyond_end(self):
        with self.assertRaisesRegex(MultiClipError,"longer than"):
            validate_plan([Path("/a")],{"target_seconds":30,"clip_plan":[
                {"source_index":0,"start":0,"seconds":30}]},[{"duration":10}])

    def test_bad_source_indices_rejected(self):
        with self.assertRaises(MultiClipError):
            validate_plan([Path("/a")],{"target_seconds":30,"clip_plan":[
                {"source_index":8,"seconds":30}]},[{"duration":60}])

    def test_no_unbounded_duration_or_invalid_aspect(self):
        with self.assertRaises(MultiClipError):
            validate_plan([Path("/a")],{"target_seconds":3600},[{"duration":3600}])
        with self.assertRaises(MultiClipError):
            validate_plan([Path("/a")],{"target_seconds":30,"width":2000},[{"duration":30}])

    def test_default_uses_all_sources(self):
        paths=[Path("/a"),Path("/b")]
        plan,target=validate_plan(paths,{"target_seconds":30},[{"duration":18},{"duration":20}])
        self.assertEqual(target,30)
        self.assertEqual([x["source_index"] for x in plan],[0,1])
        self.assertAlmostEqual(sum(x["seconds"] for x in plan),30,places=2)

    def test_short_video_loop_is_explicit(self):
        plan,_=validate_plan([Path("/a")],{"target_seconds":30},
                              [{"duration":8}])
        self.assertTrue(plan[0]["loop"])

    def test_reject_malicious_values(self):
        for x in (float("nan"),float("inf"),-10):
            with self.assertRaises(MultiClipError):
                validate_plan([Path("/a")],{"target_seconds":30,"clip_plan":[
                    {"source_index":0,"start":x,"seconds":30}]},[{"duration":35}])

    def test_multi_video_retains_original_audio_and_portrait(self):
        a=self.make_video("one.mp4",4,True)
        b=self.make_video("two.mp4",4,False)
        out=self.root/"final.mp4"
        result=render_multiple([a,b],out,
              {"target_seconds":6,"width":360,"height":640,"fps":15,
               "clip_plan":[{"source_index":0,"start":0,"seconds":3},
                            {"source_index":1,"start":0,"seconds":3}]},
              self.root/"work")
        probe=probe_media(out)
        self.assertTrue(probe["has_audio"])
        self.assertEqual((probe["width"],probe["height"]),(360,640))
        self.assertAlmostEqual(probe["duration"],6,delta=0.22)
        self.assertEqual(result["sources"],2)
        self.assertFalse(result["publishing_enabled"])
        self.assertGreater(out.stat().st_size,5000)

    def test_default_can_loop_short_second_source(self):
        a=self.make_video("long.mp4",4)
        b=self.make_video("short.mp4",1.2)
        result=render_multiple([a,b],self.root/"loop.mp4",
                               {"target_seconds":6,"width":360,"height":640,"fps":15},
                               self.root/"w2")
        self.assertEqual(len(result["timeline"]),2)
        self.assertTrue(result["timeline"][1]["loop"])


if __name__ == "__main__":
    unittest.main()
