import json
from pathlib import Path
from unittest import TestCase, main
import reel_engine_router as v

ROOT=Path(__file__).resolve().parent
class RoutingTests(TestCase):
    def setUp(self):
        self.policy=v.load_policy(ROOT/"reel-engine-routing.json")
    def test_default_v5_for_all_registered_projects(self):
        for p in self.policy["projects"]:
            j={"project_id":p["id"],"job_type":"instagram_reel"}
            result=v.route_job(j,self.policy)
            self.assertEqual(result["engine"],"reel-engine-v5")
            self.assertEqual(result["brand_reference"],p["brand"])
            self.assertEqual(result["published"],False)
    def test_video_types(self):
        for t in self.policy["default_for"]:
            r=v.route_job({"project_id":"moksha_wellness","job_type":t},self.policy)
            self.assertEqual(r["version"],"5.0.0")
    def test_game_runtime_unchanged(self):
        for t in self.policy["not_for"]:
            r=v.route_job({"project_id":"shaadi_auntys_dodge","job_type":t},self.policy)
            self.assertEqual(r["status"],"OUT_OF_SCOPE")
    def test_no_silent_v4_1_fallback(self):
        r=v.route_job({"project_id":"moksha_wellness","job_type":"instagram_reel",
                       "engine_override":"reel-engine-v4_1"},self.policy)
        self.assertEqual(r["status"],"REQUIRES_OWNER_OVERRIDE_APPROVAL")
    def test_no_migration_existing_jobs(self):
        r=v.route_job({"project_id":"andaz_vibe_stay","job_type":"instagram_reel",
                       "existing_inflight":True},self.policy)
        self.assertEqual(r["status"],"EXISTING_JOB_UNCHANGED")
    def test_unknown_brand_block(self):
        with self.assertRaises(v.RoutingError):
            v.route_job({"project_id":"fictional_brand","job_type":"instagram_reel"},self.policy)
    def test_non_music_composition(self):
        self.assertFalse(self.policy["music"]["composition_allowed"])
        self.assertEqual(self.policy["music"]["approved_licenses"],["CC0","public domain mark","CC BY with credit"])
    def test_legacy_runtime_claim_not_inferred(self):
        r=v.route_job({"project_id":"moksha_wellness","job_type":"social_video"},self.policy)
        self.assertFalse(r["real_source_v5_certified"])
        self.assertFalse(r["rendered"])
if __name__=="__main__":
    main()
