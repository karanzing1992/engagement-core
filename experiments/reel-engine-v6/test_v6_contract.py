#!/usr/bin/env python3
"""Offline source-only V6 acceptance. Deliberately never calls model APIs or renders."""
from copy import deepcopy
import unittest
from v6_contract import (V6Blocked, check_config, read_config, select_pro_model, select_free_flash_model,
                         validate_source_manifest, validate_effect_receipts)
from gemini_pro_preflight import preflight


class V6ContractTests(unittest.TestCase):
    def setUp(self):
        self.cfg = read_config()

    def test_no_v5_change_and_filmcraft_only(self):
        self.assertEqual(self.cfg["delivery"]["default_runtime_version"], "v5")
        self.assertEqual(self.cfg["editor"]["provider"], "FilmCraft")
        self.assertTrue(self.cfg["editor"]["no_ffmpeg_or_ffprobe"])
        self.assertFalse(self.cfg["provider_policy"]["allow_paid_inference"])

    def test_gemini_pro_first_and_distinct_groq_roles(self):
        self.assertEqual(self.cfg["model_roles"]["research"]["provider"], "gemini")
        self.assertEqual(self.cfg["model_roles"]["creative_director"]["model"], "openai/gpt-oss-120b")
        self.assertEqual(self.cfg["model_roles"]["editor_feasibility_reviewer"]["model"], "openai/gpt-oss-20b")

    def test_policy_rejects_groq_only_regression(self):
        edited = deepcopy(self.cfg)
        edited["provider_policy"]["mode"] = "groq_only"
        with self.assertRaises(V6Blocked):
            check_config(edited)

    def test_policy_rejects_paid_or_editor_fallback(self):
        for field, val in [("allow_paid_inference", True), ("cross_provider_fallback", True)]:
            edited = deepcopy(self.cfg)
            edited["provider_policy"][field] = val
            with self.assertRaises(V6Blocked):
                check_config(edited)
        edited = deepcopy(self.cfg)
        edited["editor"]["no_ffmpeg_or_ffprobe"] = False
        with self.assertRaises(V6Blocked):
            check_config(edited)

    def test_dynamic_pro_selection_no_flash_downgrade(self):
        models = {"models": [
            {"name": "models/gemini-3.6-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.6-pro", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.8-pro", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.9-pro", "supportedGenerationMethods": ["embedContent"]},
            {"name": "models/gemini-3.8-pro-preview-customtools", "supportedGenerationMethods": ["generateContent"]},
        ]}
        self.assertEqual(select_pro_model(models), "gemini-3.8-pro")
        self.assertNotEqual(select_pro_model(models), "gemini-3.8-pro-preview-customtools")
        self.assertEqual(select_pro_model(models, approved_model="gemini-3.6-pro"),
                         "gemini-3.6-pro")
        with self.assertRaises(V6Blocked):
            select_pro_model(models, approved_model="gemini-3.6-flash")
        with self.assertRaises(V6Blocked):
            select_pro_model({"models": [models["models"][0]]})

    def test_free_flash_selection_is_exact_allowlist(self):
        models={"models":[
            {"name":"models/gemini-3.1-pro-preview","supportedGenerationMethods":["generateContent"]},
            {"name":"models/gemini-3.7-flash","supportedGenerationMethods":["generateContent"]},
            {"name":"models/gemini-3.8-flash","supportedGenerationMethods":["generateContent"]},
            {"name":"models/gemini-3.9-flash-unverified","supportedGenerationMethods":["generateContent"]},
            {"name":"models/gemini-3.6-flash","supportedGenerationMethods":["embedContent"]},
        ]}
        self.assertEqual(select_free_flash_model(models),"gemini-3.8-flash")
        self.assertEqual(select_free_flash_model(models,approved_model="gemini-3.7-flash"),"gemini-3.7-flash")
        for bad in ("gemini-3.1-pro-preview","gemini-3.9-flash-unverified","gemini-3.6-flash"):
            with self.assertRaises(V6Blocked):
                select_free_flash_model(models,approved_model=bad)
        with self.assertRaises(V6Blocked):
            select_free_flash_model({"models":[models["models"][0]]})

    def test_paid_model_disallowed_by_free_policy(self):
        invalid=deepcopy(self.cfg)
        invalid["provider_policy"]["gemini_model_selection"]="highest_available_pro_generateContent_from_live_model_list"
        with self.assertRaises(V6Blocked):
            check_config(invalid)
        invalid=deepcopy(self.cfg)
        invalid["provider_policy"]["require_verified_free_project"]=False
        with self.assertRaises(V6Blocked):
            check_config(invalid)

    def test_source_requires_verified_rights_and_external_ai_consent(self):
        source = {"source_sha256": "a"*64, "human_reviewed": True,
                  "rights_and_consent_cleared": True,
                  "external_ai_processing_consent": True,
                  "shots": [{"id": "s1", "start_seconds": 1.0,
                             "duration_seconds": 3.5, "visible": "Person enters foliage"}]}
        self.assertEqual(validate_source_manifest(source, external_gemini_frames=True), source)
        for field in ("human_reviewed", "rights_and_consent_cleared",
                      "external_ai_processing_consent"):
            missing = deepcopy(source)
            missing[field] = False
            with self.assertRaises(V6Blocked):
                validate_source_manifest(missing, external_gemini_frames=True)
        bad = deepcopy(source)
        bad["shots"][0]["duration_seconds"] = -1
        with self.assertRaises(V6Blocked):
            validate_source_manifest(bad, external_gemini_frames=False)

    def test_no_silent_effect_omissions_and_no_faked_applied(self):
        req = [{"id": "c1", "name": "title"}, {"id": "c2", "name": "color_grade"}]
        actual = [{"id": "c1", "status": "applied", "filmcraft_command": "graphics.newText",
                   "native_command_ok": True, "output_verified": True},
                  {"id": "c2", "status": "applied", "filmcraft_command": "effects.setParam",
                   "native_command_ok": True, "output_verified": True}]
        receipt = validate_effect_receipts(req, actual)
        self.assertEqual(receipt["verified_applied"], 2)
        self.assertFalse(receipt["owner_artistic_approval"])
        for malformed in (actual[:1], [{**actual[0], "output_verified": False}, actual[1]],
                          [actual[0], {**actual[1], "native_command_ok": False}],
                          [actual[0], actual[0]]):
            with self.assertRaises(V6Blocked):
                validate_effect_receipts(req, malformed)

    def test_offline_preflight_never_uses_api(self):
        result = preflight(online=False, accept_api_terms=False)
        self.assertFalse(result["gemini_api_key_verified"])
        self.assertFalse(result["model_inference_performed"])
        self.assertFalse(result["production_changed"])


if __name__ == "__main__":
    unittest.main()
