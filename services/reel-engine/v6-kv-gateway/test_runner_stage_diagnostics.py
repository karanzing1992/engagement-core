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

    def test_gemini_requires_two_independent_free_tier_gates(self):
        from unittest.mock import patch
        for tier,owner,allowed in (("","true",False),("true","",False),
                                    ("false","true",False),("true","false",False),
                                    ("true","true",True)):
            with patch.dict("os.environ",{
                "GEMINI_PROJECT_FREE_TIER_VERIFIED":tier,
                "GEMINI_INFERENCE_OWNER_APPROVED":owner}):
                self.assertEqual(runner.gemini_free_path_authorized(),allowed)


    def test_groq_fallback_reviewer_receives_txtai_text_not_role_dictionary(self):
        """The Gemini timeout/free-tier fallback must use reviewer advice only."""
        from unittest.mock import patch
        captured = {}
        proposal = {"hook": "A moment to reset", "segments": [
            {"shot_id": "s1", "start_seconds": 0.0, "duration_seconds": 4.0,
             "effects": [{"name": "color_grade", "parameters": {"contrast": 12}}]}]}
        reviewer_context = "Independently check Reel timing and audio. " * 70

        def reviewer(_source, _proposal, *, on_stage=None, guidance=None):
            self.assertIsInstance(guidance, str)
            captured["context"] = guidance
            if on_stage:
                on_stage("groq_reviewer")
            return {"approved": True}

        with patch.object(runner, "gemini_free_path_authorized", return_value=False), \
             patch.object(runner.multimodel, "read_config"), \
             patch.object(runner.multimodel, "validate_source_manifest"), \
             patch.object(runner.multimodel, "validate_director"), \
             patch.object(runner.multimodel, "groq_call", return_value=proposal), \
             patch.object(runner.multimodel, "groq_strict_review", side_effect=reviewer), \
             patch.object(runner.multimodel, "compile_reviewed_edl",
                          return_value={"hook": "A moment to reset", "cuts": [], "operations": []}):
            result = runner.model_plan("0" * 64, "Cinematic quiet river", "River and sky", 4.0,
                fixture=False, guidance={
                    "director": {"context": "Creative advice"},
                    "reviewer": {"context": reviewer_context},
                    "research": {"context": "Research advice"}})
        self.assertEqual(captured["context"], reviewer_context[:1750])
        self.assertEqual(result["model_policy"],
                         "groq_only_fallback_gemini_free_tier_not_verified")
        self.assertFalse(result["published"])


    def test_transient_gemini_network_timeout_retries_with_same_consented_frames(self):
        from unittest.mock import patch
        bridge=runner.multimodel
        response={"candidates":[{"content":{"parts":[{"text":
            '{"observations":[{"shot_id":"s1","visible":"river"}],'
            '"research_scope":"verified"}'}]}}]}
        source={"shots":[{"id":"s1","start_seconds":0,
                "duration_seconds":4,"visible":"river"}]}
        with patch.dict("os.environ",{
                "GEMINI_INFERENCE_OWNER_APPROVED":"true",
                "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true",
                "GEMINI_API_KEY":"fixture-key"}), \
             patch.object(bridge,"discover_models",return_value=["test-flash"]), \
             patch.object(bridge,"free_flash_models",return_value=["test-flash"]), \
             patch.object(bridge,"post_json",side_effect=[
                 bridge.V6Blocked("Model API rejected or timed out; details redacted"),
                 response]) as requests, \
             patch.object(bridge.time,"sleep") as sleep:
            model,research=bridge.gemini_research(source,"Cinematic river",
                approved_api_cost=True,guidance="Use authentic footage")
        self.assertEqual(model,"test-flash")
        self.assertEqual(research["observations"][0]["visible"],"river")
        self.assertEqual(requests.call_count,2)
        sleep.assert_called_once_with(2)

    def test_gemini_nontransient_rejection_never_retries(self):
        from unittest.mock import patch
        bridge=runner.multimodel
        source={"shots":[{"id":"s1","start_seconds":0,
                "duration_seconds":4,"visible":"river"}]}
        with patch.dict("os.environ",{
                "GEMINI_INFERENCE_OWNER_APPROVED":"true",
                "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true",
                "GEMINI_API_KEY":"fixture-key"}), \
             patch.object(bridge,"discover_models",return_value=["test-flash"]), \
             patch.object(bridge,"free_flash_models",return_value=["test-flash"]), \
             patch.object(bridge,"post_json",side_effect=bridge.V6Blocked(
                 "Model API request rejected; provider response redacted")) as requests:
            with self.assertRaises(bridge.V6Blocked):
                bridge.gemini_research(source,"Cinematic river",approved_api_cost=True)
        self.assertEqual(requests.call_count,1)

    def test_required_rag_failure_is_redacted_and_classified(self):
        runner.ACTIVE_STAGE="micro_rag"
        self.assertEqual(runner.safe_failure(runner.multimodel.V6Blocked(
            "V7 required Reel RAG unavailable")),
            "V6_KV_PRIVATE_RENDER_FAILED stage=micro_rag code=V7_RAG_UNAVAILABLE")

if __name__=="__main__":
    unittest.main()
