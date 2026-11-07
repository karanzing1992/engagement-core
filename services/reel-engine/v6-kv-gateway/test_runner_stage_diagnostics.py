"""Tests that private V6 diagnostic messages never contain provider or guest data."""
import contextlib
import io
import unittest
import runner

class StageDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.old_stage=runner.ACTIVE_STAGE
    def tearDown(self):
        runner.ACTIVE_STAGE=self.old_stage

    def test_fixed_stage_only(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            runner.mark("gemini_research")
        self.assertEqual(out.getvalue().strip(),"V6_KV_STAGE gemini_research")
        self.assertEqual(runner.ACTIVE_STAGE,"gemini_research")
        with self.assertRaises(ValueError):
            runner.mark("guest name: John")

    def test_allowlisted_model_cause(self):
        runner.ACTIVE_STAGE="gemini_research"
        fail=runner.safe_failure(runner.multimodel.V6Blocked(
            "All currently available free Flash candidate endpoints were unavailable"))
        self.assertEqual(fail,
            "V6_KV_PRIVATE_RENDER_FAILED stage=gemini_research code=GEMINI_ENDPOINT_UNAVAILABLE")

    def test_redacts_unknown_model_exceptions(self):
        runner.ACTIVE_STAGE="groq_director"
        secret="SECRET_ACCOUNT_GUEST_DO_NOT_EMIT"
        fail=runner.safe_failure(runner.multimodel.V6Blocked(secret))
        self.assertEqual(fail,
            "V6_KV_PRIVATE_RENDER_FAILED stage=groq_director code=BLOCKED_UNCLASSIFIED")
        self.assertNotIn(secret,fail)

    def test_redacts_exception_strings_for_other_types(self):
        runner.ACTIVE_STAGE="cinematic_finish"
        secret="SECRET_GUEST_PATH"
        fail=runner.safe_failure(RuntimeError(secret))
        self.assertEqual(fail,
            "V6_KV_PRIVATE_RENDER_FAILED stage=cinematic_finish code=NON_MODEL_FAILURE")
        self.assertNotIn(secret,fail)

    def test_allowlisted_ffmpeg_failure_without_exposure(self):
        runner.ACTIVE_STAGE="cinematic_finish"
        error=runner.ffmpeg_editor.RenderBlocked("FFMPEG_TITLE_INVALID")
        self.assertEqual(runner.safe_failure(error),
            "V6_KV_PRIVATE_RENDER_FAILED stage=cinematic_finish code=FFMPEG_TITLE_INVALID")
        error=runner.ffmpeg_editor.RenderBlocked("secret guest folder")
        self.assertNotIn("secret guest folder",runner.safe_failure(error))

    def test_edl_failure_is_classified_without_guest_or_model_data(self):
        runner.ACTIVE_STAGE="edl_compile"
        cases={
            "Groq 20B review missing or director hash mismatch":"REVIEW_DIGEST_OR_APPROVAL_MISMATCH",
            "Editor-review per-segment approval incomplete":"REVIEW_INCOMPLETE",
            "Editor rejected one or more proposed FilmCraft edits":"REVIEW_REJECTED",
        }
        for message,code in cases.items():
            self.assertEqual(runner.safe_failure(runner.multimodel.V6Blocked(message)),
                "V6_KV_PRIVATE_RENDER_FAILED stage=edl_compile code="+code)

    def test_timeout_fallback_only_for_gemini_research(self):
        runner.ACTIVE_STAGE="gemini_research"
        self.assertTrue(runner.recoverable_gemini_timeout(
            runner.multimodel.V6Blocked("Model API rejected or timed out; details redacted")))
        self.assertFalse(runner.recoverable_gemini_timeout(
            runner.multimodel.V6Blocked("Explicit still-image processing consent and frame count required")))
        self.assertFalse(runner.recoverable_gemini_timeout(
            runner.multimodel.V6Blocked("Director storyboard required")))
        runner.ACTIVE_STAGE="groq_director"
        self.assertFalse(runner.recoverable_gemini_timeout(
            runner.multimodel.V6Blocked("Model API rejected or timed out; details redacted")))
        runner.ACTIVE_STAGE="gemini_research"
        self.assertFalse(runner.recoverable_gemini_timeout(
            RuntimeError("Model API rejected or timed out; details redacted")))

if __name__=="__main__":
    unittest.main()
