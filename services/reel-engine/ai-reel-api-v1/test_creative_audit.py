#!/usr/bin/env python3
"""Offline, synthetic-only regression: no owner video, provider calls or secrets."""
import importlib.util
import os
from pathlib import Path
from unittest import TestCase, main, mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("mad_v5_media_runner", HERE/"media_runner.py")
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

VALID={
  "versions":[{
    "id":"T1","name":"Grounded cinematic source",
    "hook":"FEEL THE MOMENT","narrative":"Grounded visual story",
    "segments":[{"shot_id":"f00","offset_seconds":0.1,"duration_seconds":1.1,
       "caption":"","proposed_operations":[{"name":"color_grade","parameters":{"look":"soft"}}]}
       for _ in range(3)]
  }]
}
JOB={"prompt":"Make a beautiful film from the synthetic footage with stylish pacing."}
PROBE={"duration":20.0,"has_audio":True,"width":640,"height":360}


class PrivateCreativeMisfireTests(TestCase):
    def run_design(self,groq_key="",effect=None):
        with mock.patch.dict(os.environ,{"GROQ_API_KEY":groq_key}):
            with mock.patch.object(runner,"sample_frames",return_value=[(4.0,Path("synthetic-frame.jpg"))]):
                with mock.patch.object(runner,"call_groq",side_effect=effect) as groq:
                    with mock.patch.object(runner,"groq_vision_caption",return_value="Verified synthetic blue horizon."):
                        cuts,seconds,planned,report=runner.design(JOB,Path("synthetic.mp4"),PROBE,Path("/tmp"))
        return cuts,seconds,planned,report,groq.call_count

    def test_missing_key_is_explicit_and_never_overlays_editing_instructions(self):
        cuts,seconds,planned,report,calls=self.run_design()
        self.assertIsNone(planned)
        self.assertEqual(report["creative_fallback_reason"],"director_credential_missing")
        self.assertEqual(report["director_attempts"],0)
        self.assertFalse(report["creative_plan_applied"])
        self.assertEqual(calls,0)
        self.assertTrue(3<=seconds<=30)
        self.assertEqual(runner.creative_title(planned),"A MOMENT WORTH FEELING")
        self.assertNotIn("synthetic footage",runner.creative_title(planned))

    def test_invalid_director_plan_retries_alternate_and_reports_fallback(self):
        cuts,seconds,planned,report,calls=self.run_design(
            "dummy-test-key",[{"versions":[]},{"versions":[]}])
        self.assertIsNone(planned)
        self.assertEqual(calls,2)
        self.assertTrue(report["director_response_received"])
        self.assertEqual(report["director_attempts"],2)
        self.assertEqual(report["creative_fallback_reason"],"director_plan_invalid")

    def test_second_director_can_recover_first_invalid_plan_without_claiming_effects(self):
        cuts,seconds,planned,report,calls=self.run_design(
            "dummy-test-key",[{"versions":[]},VALID])
        self.assertIsNotNone(planned)
        self.assertEqual(calls,2)
        self.assertTrue(report["creative_plan_applied"])
        self.assertEqual(report["vision_frames_captioned"],1)
        self.assertEqual(report["vision_model_used"],"qwen/qwen3.8-27b")
        self.assertIsNone(report["creative_fallback_reason"])
        self.assertEqual(report["proposed_effects_not_executed"],3)
        self.assertAlmostEqual(seconds,3.3)
        self.assertEqual(runner.creative_title(planned),"FEEL THE MOMENT")

    def test_unsupported_timeline_does_not_masquerade_as_rendered_edit(self):
        bad=dict(VALID["versions"][0])
        bad["segments"]=VALID["versions"][0]["segments"]*7
        with self.assertRaisesRegex(ValueError,"unsupported_section_count"):
            runner.renderable_plan(bad,PROBE["duration"])

    def test_text_is_line_wrapped_and_never_taken_from_fallback_prompt(self):
        title=runner.display_title("CINEMATIC GUEST REVIEW FROM MOKSHA WITH WONDERFUL EXPERIENCES AND FEELINGS")
        self.assertLessEqual(len(title.split("\n")),2)
        self.assertTrue(all(len(x)<=23 for x in title.split("\n")))
        self.assertEqual(runner.display_title(runner.creative_title(None)),
                         "A MOMENT WORTH FEELING")

    def test_provider_status_appears_as_opaque_failure_code_only(self):
        class TooManyRequests(Exception):status_code=429
        self.assertEqual(runner.director_failure_code(TooManyRequests("private details")),
                         "director_rate_limited")
        self.assertEqual(runner.director_failure_code(Exception("secret")),
                         "director_provider_failure")


if __name__=="__main__":
    main()
