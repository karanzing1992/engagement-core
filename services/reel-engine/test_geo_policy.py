from __future__ import annotations
import unittest
from geo_policy import GeoPolicyError, validate_asset, validate_render_config

GOOD = {
    "origin": "licensed_stock",
    "capture_country": "India",
    "capture_region": "Goa",
    "source_url": "https://commons.wikimedia.org/wiki/File:Goa_coast.webm",
    "location_evidence_url": "https://commons.wikimedia.org/wiki/File:Goa_coast.webm",
    "verification_status": "human_verified",
    "verified_by": "Media Studio editor",
}
BASE = {"brand": "moksha", "editorial_region": "Goa",
        "source_provenance": [GOOD], "segments": [{"start": 0, "end": 10}]}


class IndiaGeographyPolicyTests(unittest.TestCase):
    def test_goa_clip(self):
        self.assertEqual(validate_render_config(BASE)["geography_gate"], "passed")

    def test_india_elsewhere_eligible(self):
        asset = {**GOOD, "capture_country": "India", "capture_region": "Karnataka"}
        self.assertEqual(validate_asset(asset)["capture_country"], "India")

    def test_foreign_clip_rejected_even_with_goa_caption(self):
        video = {**GOOD, "capture_country": "Iceland"}
        with self.assertRaisesRegex(GeoPolicyError, "filmed in Goa or India"):
            validate_render_config({**BASE, "caption": "Beautiful Goa waves!", "source_provenance": [video]})

    def test_unknown_location_rejected(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "source_provenance": [{**GOOD, "capture_country": ""}]})

    def test_missing_provenance_rejected(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "source_provenance": []})

    def test_all_sources_checked(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "source_provenance": [GOOD, {**GOOD, "capture_country": "Spain"}]})

    def test_assistant_location_assertion_not_enough(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "source_provenance": [{**GOOD, "verified_by": "AI"}]})

    def test_unsupported_override_blocked(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "regional_override": {"user_approved": True}})

    def test_regional_brief_required(self):
        with self.assertRaises(GeoPolicyError):
            validate_render_config({**BASE, "editorial_region": "Iceland"})

    def test_generated_illustrative_goa_video(self):
        video = {**GOOD, "origin": "generated", "subject_region": "Goa",
                 "is_illustrative": True, "claims_real_footage": False}
        self.assertEqual(validate_asset(video)["eligibility"], "india_illustrative")

    def test_generated_pretending_to_be_real_rejected(self):
        video = {**GOOD, "origin": "generated", "subject_region": "Goa",
                 "is_illustrative": False, "claims_real_footage": True}
        with self.assertRaises(GeoPolicyError):
            validate_asset(video)

    def test_missing_location_evidence_rejected(self):
        with self.assertRaises(GeoPolicyError):
            validate_asset({**GOOD, "location_evidence_url": ""})

    def test_https_required(self):
        with self.assertRaises(GeoPolicyError):
            validate_asset({**GOOD, "source_url": "http://example.com"})

    def test_andaz_also_uses_india_rule(self):
        self.assertEqual(validate_render_config({**BASE, "brand": "andaz"})["geography_gate"], "passed")


if __name__ == "__main__":
    unittest.main()
