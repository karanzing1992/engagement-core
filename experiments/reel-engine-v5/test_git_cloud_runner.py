"""Negative and contract tests for Git-hosted V5 synthetic control."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import git_cloud_runner as subject

class GitCloudTests(unittest.TestCase):
    def test_fixture_is_v5_validated(self):
        from v5_orchestrator import load_system, read_json, validate_source, validate_plan
        cfg, _ = load_system(subject.HERE / "v5_config.json",
                             subject.HERE / "capability_registry.json")
        shot_map = validate_source(read_json(subject.HERE / "synthetic_shots.json"), cfg)
        versions = validate_plan(subject.fixture_plan(), shot_map, 1, cfg)
        self.assertEqual(len(versions[0]["segments"]), 3)
        self.assertEqual(sum(c["duration_seconds"] for c in versions[0]["segments"]), 6)

    def test_edl_is_exact_and_bounded(self):
        validated = subject.compile_edl(subject.fixture_plan()["versions"][0]["segments"],
                                        ["S1", "S2", "S3", "S4", "S5"])
        self.assertEqual([x["source_index"] for x in validated], [0, 1, 2])
        self.assertEqual(sum(x["seconds"] for x in validated), 6)

    def test_reject_unverified_effect(self):
        segments = subject.fixture_plan()["versions"][0]["segments"]
        segments[0]["proposed_operations"] = [{"name": "color_grade", "parameters": {}}]
        with self.assertRaisesRegex(subject.Rejected, "Uncertified"):
            subject.compile_edl(segments, ["S1", "S2", "S3"])

    def test_synthetic_live_preview_audits_unexecuted_effects(self):
        original = subject.fixture_plan()["versions"][0]["segments"]
        original[0]["proposed_operations"] = [
            {"name": "color_grade", "parameters": {"creative_look": "warm"}},
            {"name": "motion_typography", "parameters": {"text": "test"}}]
        clean, pending = subject.technical_preview_segments(original)
        self.assertEqual(len(pending), 2)
        self.assertEqual([x["name"] for x in pending], ["color_grade", "motion_typography"])
        self.assertEqual(clean[0]["proposed_operations"], [])
        self.assertEqual(len(original[0]["proposed_operations"]), 2)
        self.assertEqual(len(subject.compile_edl(clean, ["S1", "S2", "S3"])), 3)

    def test_vision_response_requires_synthetic_identity(self):
        ok = {"shots": [{"id": "S"+str(i), "visible": "blue water synthetic frame "+str(i)} for i in range(1,6)],
              "_meta": {"synthetic_only": True, "model_used": "qwen/qwen3.8-27b", "provider":"groq", "real_guest_data_sent":False}}
        brief, proof = subject.describe_synthetic_vision(ok)
        self.assertIn("blue water", brief)
        self.assertTrue(proof["synthetic_only"])
        self.assertFalse(proof["real_guest_data_sent"])
        self.assertEqual(proof["provider"],"groq")
        self.assertEqual(proof["model"],"qwen/qwen3.8-27b")
        for bad in [[], {"shots": []},
                    {"shots": ok["shots"], "_meta": {"synthetic_only": False,
                                                     "model_used": "gemini-3.6-flash"}},
                    {"shots": ok["shots"], "_meta": {"synthetic_only": True,
                                                     "model_used": "unverified"}}]:
            with self.assertRaises(subject.Rejected):
                subject.describe_synthetic_vision(bad)

    def test_multimodal_requires_same_render_source_as_vision_input(self):
        with TemporaryDirectory() as tmp:
            img_dir = Path(tmp) / "images"
            img_dir.mkdir()
            with self.assertRaisesRegex(subject.Rejected, "Groq input image missing"):
                subject.create_synthetic_sources(Path(tmp), {
                    "S1": {"duration_seconds": 3}}, vision_images=img_dir)

    def test_groq_synthetic_visual_fixture_matches_render_input(self):
        with TemporaryDirectory() as t:
            frames=subject.create_synthetic_frames(Path(t))
            self.assertEqual(len(frames),5)
            self.assertTrue(all(f.exists() and f.stat().st_size>100 for f in frames))
            result={"shots":[{"id":"S"+str(i),"visible":"Synthetic source drawing number "+str(i)} for i in range(1,6)],
                    "_meta":{"provider":"groq","model_used":"qwen/qwen3.8-27b",
                             "synthetic_only":True,"real_guest_data_sent":False}}
            brief,proof=subject.describe_synthetic_vision(result)
            self.assertIn("Groq analysis",brief)
            self.assertEqual(proof["shot_count"],5)
            self.assertFalse(proof["real_guest_data_sent"])

    def test_reject_unrenderable_length(self):
        segments = subject.fixture_plan()["versions"][0]["segments"] * 6
        with self.assertRaisesRegex(subject.Rejected, "1-16"):
            subject.compile_edl(segments, ["S1", "S2", "S3"])

    def test_reject_non_fixture_media(self):
        from v5_orchestrator import Rejected
        with TemporaryDirectory() as tmp:
            with self.assertRaises(Rejected):
                subject.execute("arbitrary_url", Path(tmp), "synthetic_test")
            with self.assertRaises(Rejected):
                subject.execute("fixture", Path(tmp), "private_source")

    def test_reject_invalid_clip_reference(self):
        segment = [{"shot_id": "outside", "offset_seconds": 0,
                    "duration_seconds": 4, "proposed_operations": []}]
        with self.assertRaisesRegex(subject.Rejected, "Unknown"):
            subject.compile_edl(segment, ["S1"])

    def test_inference_must_not_be_emulated(self):
        with patch.object(subject, "call_groq", side_effect=subject.Rejected("API absent")):
            with self.assertRaisesRegex(subject.Rejected, "API absent"):
                subject.execute("live", Path("/tmp/not-created-v5"), "synthetic_test")

if __name__ == "__main__":
    unittest.main()
