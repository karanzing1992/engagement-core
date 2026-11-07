"""V7 cinematic postproduction. Synthetic media only; no guest footage in CI."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from ffmpeg_v7_cinema import finish, V7Blocked, PRESETS, preset_for
import ffmpeg_v6_adapter as v6


class V7CinematicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="mad-v7-synth-")
        cls.work = Path(cls.temp.name)
        cls.raw = cls.work / "original.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=480x270:rate=24:duration=3.2",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3.2",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(cls.raw)], check=True, timeout=100)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def spec(self):
        return {
            "workdir": str(self.work),
            "source": str(self.raw),
            "source_sha256": v6.sha256(self.raw),
            "output": str(self.work / "cinematic.mp4"),
            "width": 480, "height": 270, "fps": 24,
            "template_id": "wellness-cinema",
            "v7_preset": "sauna-cinema",
            "hook": "SYNTHETIC V7",
            "cuts": [{"start": .2, "seconds": 1.2},
                     {"start": 1.5, "seconds": 1.2}],
            "operations": [
                [{"id":"warm", "name":"color_grade", "parameters":{"contrast":10}}],
                [{"id":"label", "name":"title", "parameters":{"text":"FICTIONAL QA ONLY"}}]
            ],
        }

    def test_01_reuses_v6_and_exports_real_av(self):
        rec = finish(self.spec())
        self.assertEqual(rec["engine"], "ffmpeg")
        self.assertEqual(rec["version"], "v7-source-beta")
        self.assertEqual(rec["v7_preset"], "sauna-cinema")
        self.assertTrue(rec["cinematic_finish_applied"])
        self.assertTrue(rec["video_stream_verified"])
        self.assertTrue(rec["audio_stream_verified"])
        self.assertTrue(rec["full_decode_passed"])
        self.assertEqual(rec["visual_presence_check"]["frames_examined"], 3)
        self.assertFalse(rec["published"])
        self.assertFalse(rec["creative_complete"])
        self.assertFalse(rec["music_mixed"])
        self.assertEqual(rec["audio_mastering_mode"], "loudnorm")
        self.assertGreater((self.work / "cinematic.mp4").stat().st_size,4096)
        self.assertFalse((self.work / "v7-base-private.mp4").exists())

    def test_02_reject_untrusted_commands(self):
        s = self.spec()
        s["ffmpeg_filter"] = "movie=private.mov"
        with self.assertRaisesRegex(V7Blocked,"V7_UNTRUSTED"):
            finish(s)

    def test_03_publication_is_separate_gate(self):
        s = self.spec()
        s["published"] = True
        with self.assertRaisesRegex(V7Blocked,"PUBLICATION"):
            finish(s)

    def test_04_reject_invalid_style(self):
        s = self.spec()
        s["v7_preset"] = "arbitrary_api_editor"
        with self.assertRaisesRegex(V7Blocked,"PRESET"):
            finish(s)

    def test_05_chooses_grounded_style(self):
        self.assertEqual(preset_for("Moksha sauna cinematic"),"sauna-cinema")
        self.assertEqual(preset_for("Earth Rejuvenation mud ritual"),"earth-rejuvenation")
        self.assertEqual(preset_for("Guest testimonial interview"),"guest-reflections")
        self.assertEqual(preset_for("Unknown content"),"clean-editorial")

    def test_06_presets_are_finite(self):
        self.assertEqual(set(PRESETS),{
            "elemental-sanctuary","sauna-cinema","guest-reflections",
            "earth-rejuvenation","clean-editorial"})


    def test_07_highres_silent_aac_avoids_loudnorm_nan(self):
        """Production-shaped 1080p synthetic input without source audio."""
        silent = self.work / "silent-input.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(self.raw), "-map", "0:v:0", "-c:v", "copy", "-an",
             str(silent)], check=True, timeout=40)
        s = self.spec()
        s["source"] = str(silent)
        s["source_sha256"] = v6.sha256(silent)
        s["output"] = str(self.work / "silent-cinematic-1080.mp4")
        s["width"] = 1080
        s["height"] = 1920
        s["fps"] = 30
        result = finish(s)
        self.assertEqual(result["audio_mastering_mode"], "near_silent_preserved")
        self.assertTrue(result["full_decode_passed"])
        self.assertTrue(result["audio_stream_verified"])
        self.assertEqual((result["width"], result["height"]),(1080,1920))
        self.assertGreater((self.work / "silent-cinematic-1080.mp4").stat().st_size,4096)


if __name__ == "__main__":
    unittest.main()
