from __future__ import annotations
import sys
import types
import unittest
from cloudrun_batch import gs_object, prefix, validate_manifest

class CloudRunBatchTests(unittest.TestCase):
    def test_gcs_scope(self):
        self.assertEqual(gs_object("gs://reel-pilot/approved/c1.mp4"), ("reel-pilot","approved/c1.mp4"))
        for bad in ("https://example.com/a.mp4", "gs://buck/a/../p.mp4",
                    "gs://buck/a//p.mp4","gs://buck/a?q=1","gs://buck/../../evil"):
            with self.subTest(uri=bad), self.assertRaises(ValueError):
                gs_object(bad)

    def test_prefix(self):
        self.assertEqual(prefix("gs://reel-pilot/approved/"), ("reel-pilot","approved/"))
        with self.assertRaises(ValueError):
            prefix("gs://reel-pilot/approved")

    def test_provenance_and_brand_gates(self):
        # Structural tests only: production uses the actual geo_policy.py.
        geo = types.ModuleType("geo_policy")
        geo.validate_render_config = lambda config: True
        prior = sys.modules.get("geo_policy")
        sys.modules["geo_policy"] = geo
        try:
            base = {
                "schema_version":1,"job_id":"pilot-20261013","brand":"generic",
                "source_objects":[{"uri":"gs://reel-pilot/approved/source.mp4","sha256":"a"*64}],
                "config":{"brand":"generic","source_provenance":[{"verified":True}],
                          "editorial_region":"Goa","target_seconds":30,
                          "width":720,"height":1280,"fps":25},
            }
            plan=validate_manifest(base,"gs://reel-pilot/approved/","gs://reel-pilot/drafts/")
            self.assertEqual(plan["output_key"],"drafts/pilot-20261013.mp4")
            for changes in (
                {"brand":"moksha"},
                {"source_objects":[{"uri":"gs://wrong/approved/source.mp4","sha256":"a"*64}]},
                {"config":{**base["config"],"height":1920}},
            ):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    validate_manifest({**base,**changes},
                                      "gs://reel-pilot/approved/","gs://reel-pilot/drafts/")
        finally:
            if prior is None: sys.modules.pop("geo_policy",None)
            else: sys.modules["geo_policy"] = prior

if __name__ == "__main__":
    unittest.main()
