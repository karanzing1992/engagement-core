"""Tests that private V6 diagnostic messages never contain provider or guest data."""
import contextlib
import io
import unittest
from . import runner

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
        runner.ACTIVE_STAGE="filmcraft_render"
        secret="SECRET_GUEST_PATH"
        fail=runner.safe_failure(RuntimeError(secret))
        self.assertEqual(fail,
            "V6_KV_PRIVATE_RENDER_FAILED stage=filmcraft_render code=NON_MODEL_FAILURE")
        self.assertNotIn(secret,fail)

if __name__=="__main__":
    unittest.main()
