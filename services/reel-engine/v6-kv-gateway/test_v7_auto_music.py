#!/usr/bin/env python3
"""Pure, offline V7 music decision contract tests. No provider, video or owner data."""
from __future__ import annotations
import unittest
import v7_auto_music as auto


def record(digest="a" * 64, license_name="cc0", title="Warm organic forest ambience"):
    page = "https://commons.wikimedia.org/wiki/File:Reviewed_recording"
    license_url = (
        "https://creativecommons.org/licenses/by/4.0/"
        if license_name == "by" else "https://creativecommons.org/publicdomain/zero/1.0/"
    )
    track = {"source": "Openverse", "id": "f" * 32, "title": title,
             "creator": "Reviewed Creator", "license": license_name,
             "license_url": license_url, "original_source_page": page}
    evidence = {"track_id": track["id"], "original_source_page": page,
                "license_url": license_url, "source_license_proof_url": page,
                "reviewer_confirmed_rights": True, "reviewed_on": "2026-11-07",
                "reviewed_by": "Independent Reviewer", "attribution_approved": True}
    return {"sha256": digest, "bytes": 2048, "mime": "audio/mpeg",
            "track": track, "evidence": evidence}


class AutoMusicContract(unittest.TestCase):
    def test_groq_can_choose_only_exact_preapproved_sha(self):
        a, b = record(), record("b" * 64, title="Energetic upbeat recovery music")
        def groq(model, prompt, **kw):
            self.assertEqual(model, "openai/gpt-oss-120b")
            self.assertIn("Energetic", prompt)
            return {"sha256": b["sha256"]}
        items, receipt = auto.choose([a, b], "Energetic recovery", "Strong recovery", groq)
        self.assertEqual(items[0]["sha256"], b["sha256"])
        self.assertEqual(receipt["selection"], "groq_120b")

    def test_unreviewed_or_attribution_missing_never_reaches_model(self):
        bad = record()
        bad["evidence"]["reviewer_confirmed_rights"] = False
        cc_by = record("b" * 64, license_name="by")
        cc_by["evidence"]["attribution_approved"] = False
        called = []
        selected, receipt = auto.choose([bad, cc_by], "Wellness", "", lambda *a, **k: called.append(True))
        self.assertEqual(selected, [])
        self.assertEqual(receipt["state"], "no_reviewed_tracks")
        self.assertEqual(called, [])

    def test_malicious_model_output_cannot_download_unlisted_media(self):
        a = record()
        items, receipt = auto.choose([a], "Wellness", "", lambda *x, **y: {
            "sha256": "https://attacker.invalid/unapproved.mp3"})
        self.assertEqual(items[0]["sha256"], a["sha256"])
        self.assertEqual(receipt["selection"], "deterministic_fallback")

    def test_failed_inference_degrades_to_safe_ranked_library_track(self):
        a, b = record(), record("b" * 64, title="Meditative wellness sauna")
        def fail(*args, **kwargs):
            raise TimeoutError("No free-model availability")
        items, receipt = auto.choose([a, b], "sauna wellness meditation", "", fail)
        self.assertEqual(items[0]["sha256"], b["sha256"])
        self.assertEqual(receipt["selection"], "deterministic_fallback")

    def test_catalog_metadata_alone_is_not_rights_approval(self):
        a = record()
        a["evidence"] = {}
        self.assertEqual(auto.eligible([a]), [])
        a = record()
        a["track"]["license"] = "by-nc"
        self.assertEqual(auto.eligible([a]), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
