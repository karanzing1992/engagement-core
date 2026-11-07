import unittest
from copy import deepcopy
from backend_selection import load_policy, select_renderer, validate_receipt, UnsupportedRenderer

class ExclusiveBackendTests(unittest.TestCase):
    def test_strict_default_and_models_retained(self):
        p = load_policy()
        self.assertEqual(select_renderer(policy=p)["engine"], "ffmpeg")
        self.assertFalse(p["automatic_publish"])
        self.assertIn("gemini_research", p["preserve_owner_models"])
    def test_explicit_ffmpeg(self):
        self.assertTrue(select_renderer("ffmpeg-cli")["ffmpeg_required"])
    def test_deprecated_rejected(self):
        for name in ("filmcraft", "FilmCraft", "gstreamer", "GStreamer", "mlt", "frei0r", "unknown"):
            with self.subTest(name=name), self.assertRaises(UnsupportedRenderer):
                select_renderer(name)
    def test_no_legacy_fallback(self):
        self.assertFalse(select_renderer()["legacy_editor_fallback"])
    def test_policy_tamper_rejected(self):
        for field, value in (("default_renderer", "mlt"), ("renderer_mode", "auto"), ("automatic_publish", True)):
            p=deepcopy(load_policy()); p[field]=value
            with self.subTest(field=field), self.assertRaises(UnsupportedRenderer):
                select_renderer(policy=p)
    def test_verified_audiovisual_required(self):
        receipt={"engine":"ffmpeg", "video_stream_verified":True, "audio_stream_verified":True, "full_decode_passed":True, "published":False}
        self.assertTrue(validate_receipt(receipt)["media_technically_verified"])
        for key in ("video_stream_verified","audio_stream_verified","full_decode_passed"):
            p={**receipt,key:False}
            with self.subTest(key=key), self.assertRaises(UnsupportedRenderer):
                validate_receipt(p)
    def test_publishing_denied(self):
        r={"engine":"ffmpeg", "video_stream_verified":True, "audio_stream_verified":True, "full_decode_passed":True, "published":True}
        with self.assertRaises(UnsupportedRenderer): validate_receipt(r)
    def test_wrong_renderer_receipt_denied(self):
        r={"engine":"MLT", "video_stream_verified":True, "audio_stream_verified":True, "full_decode_passed":True, "published":False}
        with self.assertRaises(UnsupportedRenderer): validate_receipt(r)

if __name__=='__main__': unittest.main()
