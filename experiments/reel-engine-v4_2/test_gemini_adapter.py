#!/usr/bin/env python3
"""Offline-only tests. No customer footage or API calls."""
import io
import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase, main, mock
import gemini_adapter as g

class FakeResponse:
    def __init__(self, body):
        self.body = io.BytesIO(body)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return self.body.read(n)

class GeminiSafetyTests(TestCase):
    def test_key_required(self):
        with self.assertRaises(g.GeminiUnavailable):
            g.make_request(g.BASE_URL + "/models", "")
    def test_key_header_never_url(self):
        calls = []
        def opener(req, timeout):
            calls.append(req)
            return FakeResponse(b'{"models":[]}')
        result = g.make_request(g.BASE_URL + "/models", "test-secret", opener=opener)
        self.assertEqual(result, {"models": []})
        self.assertEqual(calls[0].get_header("X-goog-api-key"), "test-secret")
        self.assertNotIn("test-secret", calls[0].full_url)
    def test_external_url_rejected(self):
        with self.assertRaises(ValueError):
            g.make_request("https://evil.example/models", "test-key")
    def test_body_cap(self):
        with self.assertRaises(ValueError):
            g.make_request(g.BASE_URL + "/models/x:generateContent", "key",
                           {"text": "x" * (g.MAX_BODY_BYTES + 10)})
    def test_frame_count_cap(self):
        with self.assertRaises(ValueError):
            g.frame_request([(0, b"\xff\xd8")] * 9, "brand")
        p = g.frame_request([(0, b"\xff\xd8abc")], "brand")
        self.assertEqual(len(p["contents"][0]["parts"]), 3)
    def test_vision_requires_consent_even_with_key(self):
        args = type("A", (), {"source": "/tmp/absent.mp4", "brand_file": None,
                    "timestamps": "0", "model": g.MODEL, "allow_external_frames": False,
                    "rights_and_consent_cleared": True, "accept_free_tier_terms": True})()
        with mock.patch.object(g, "key_from_environment", return_value="dummy-key"):
            with self.assertRaisesRegex(g.GeminiUnavailable, "Vision blocked"):
                g.run_vision(args)
    def test_key_file_0600(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "gemini.key"
            p.write_text("test-example")
            p.chmod(0o644)
            with mock.patch.dict(os.environ, {"GEMINI_API_KEY_FILE": str(p)}, clear=True):
                with self.assertRaises(g.GeminiUnavailable):
                    g.key_from_environment()
                p.chmod(0o600)
                self.assertEqual(g.key_from_environment(), "test-example")
    def test_offline_preflight(self):
        args = type("A", (), {"model":g.MODEL,"verify_connection":False,
                              "accept_free_tier_terms":False})()
        with mock.patch.dict(os.environ, {}, clear=True):
            result = g.run_preflight(args)
        self.assertFalse(result["key_present"])
        self.assertFalse(result["network_tested"])
    def test_preflight_network_requires_terms(self):
        args = type("A", (), {"model":g.MODEL,"verify_connection":True,
                              "accept_free_tier_terms":False})()
        with mock.patch.object(g, "key_from_environment", return_value="dummy"):
            with self.assertRaises(g.GeminiUnavailable):
                g.run_preflight(args)
    def test_structured_result(self):
        r = {"candidates": [{"content": {"parts": [{"text": '{"shots":[]}'}]}}]}
        self.assertEqual(g.extract_json(r), {"shots":[]})
        self.assertEqual(g.visible_model_names({"models":[{"name":"models/gemini-3.8-flash"}]}),
                         ["gemini-3.8-flash"])

if __name__ == "__main__":
    main()
