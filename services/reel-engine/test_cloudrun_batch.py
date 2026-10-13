from __future__ import annotations
import unittest

from cloudrun_batch import gs_object, prefix, validate_manifest
from geo_policy import GeoPolicyError

# Synthetic test fixture only. Never represents human-approved real footage.
TEST_SOURCE = {
    "origin": "owned", "capture_country": "India", "capture_region": "Goa",
    "source_url": "https://example.invalid/test-media",
    "location_evidence_url": "https://example.invalid/test-location",
    "verification_status": "human_verified", "verified_by": "Synthetic Test Fixture",
}

class CloudRunBatchTests(unittest.TestCase):
    def setUp(self):
        self.source = "gs://reel-pilot/approved/"
        self.dest = "gs://reel-pilot/drafts/"
        self.spec = {
            "schema_version": 1, "job_id": "pilot-20261013", "brand": "generic",
            "source_objects": [
                {"uri": "gs://reel-pilot/approved/source.mp4", "sha256": "a" * 64}],
            "config": {"brand": "generic", "editorial_region": "Goa",
                       "source_provenance": [TEST_SOURCE],
                       "target_seconds": 30, "width": 720, "height": 1280, "fps": 25},
        }

    def test_gcs_scope(self):
        self.assertEqual(gs_object("gs://reel-pilot/approved/c1.mp4"),
                         ("reel-pilot", "approved/c1.mp4"))
        for bad in ("https://example.com/a.mp4", "gs://buck/a/../p.mp4",
                    "gs://buck/a//p.mp4", "gs://buck/a?q=1",
                    "gs://buck/../../evil"):
            with self.subTest(uri=bad), self.assertRaises(ValueError):
                gs_object(bad)

    def test_prefix(self):
        self.assertEqual(prefix(self.source), ("reel-pilot", "approved/"))
        with self.assertRaises(ValueError):
            prefix("gs://reel-pilot/approved")

    def test_valid_private_pilot(self):
        result = validate_manifest(self.spec, self.source, self.dest)
        self.assertEqual(result["output_key"], "drafts/pilot-20261013.mp4")

    def test_wrong_bucket_refused(self):
        self.spec["source_objects"][0]["uri"] = "gs://wrong/approved/source.mp4"
        with self.assertRaisesRegex(ValueError, "outside approved"):
            validate_manifest(self.spec, self.source, self.dest)

    def test_unapproved_moksha_brand_refused(self):
        self.spec["brand"] = "moksha"
        self.spec["config"]["brand"] = "moksha"
        with self.assertRaisesRegex(ValueError, "unbranded only"):
            validate_manifest(self.spec, self.source, self.dest)

    def test_foreign_video_rejected_by_real_geo_policy(self):
        self.spec["config"]["source_provenance"][0] = {
            **TEST_SOURCE, "capture_country": "Spain"}
        with self.assertRaises(GeoPolicyError):
            validate_manifest(self.spec, self.source, self.dest)

    def test_no_fake_geography_override(self):
        self.spec["config"]["regional_override"] = {"approved": True}
        with self.assertRaises(GeoPolicyError):
            validate_manifest(self.spec, self.source, self.dest)

    def test_non_vertical_output_refused(self):
        self.spec["config"]["height"] = 1920
        with self.assertRaises(ValueError):
            validate_manifest(self.spec, self.source, self.dest)

if __name__ == "__main__":
    unittest.main()
