#!/usr/bin/env python3
"""V6 three-model chain admission tests; all provider responses are fixtures."""
import json
from pathlib import Path
from copy import deepcopy
import unittest
from v6_contract import V6Blocked
from multimodel_filmcraft_bridge import (
    decode_json, validate_director, validate_observations,
    compile_reviewed_edl, fixture_chain, run,
)
SOURCE=json.loads((Path(__file__).parent/"fixtures/moksha_synthetic_manifest.json").read_text())
BRIEF="Make a serene, cinematic Moksha synthetic test, without inventing real people."
BRAND="Moksha Wellness, Arambol; forest, ivory and restrained gold; no medical claims."

class MultiModelBridgeTests(unittest.TestCase):
    def test_frozen_synthetic_model_order_and_nonpublication(self):
        p=run(source=SOURCE,brief=BRIEF,brand=BRAND)
        self.assertEqual(p["editor"],"MLT + frei0r"
        self.assertFalse(p["live_model_inference"])
        self.assertFalse(p["renderer_invoked"])
        self.assertFalse(p["native_visual_qa"])
        self.assertFalse(p["published"])
        self.assertEqual(p["requested_effects"],1)
        self.assertEqual(p["operations"][0][0]["name"],"color_grade")
    def test_live_api_requests_block_until_free_entitlement_verified(self):
        with self.assertRaises(V6Blocked):
            run(source=SOURCE,brief=BRIEF,brand=BRAND,mode="live")
    def test_invalid_manifest_blocks_before_models(self):
        x=deepcopy(SOURCE);x["rights_and_consent_cleared"]=False
        with self.assertRaises(V6Blocked):
            run(source=x,brief=BRIEF,brand=BRAND)
    def test_model_json_rejects_invented_prose(self):
        with self.assertRaises(V6Blocked):
            decode_json("please run the editor now")
    def test_model_cannot_invent_source_shots(self):
        _,p,_=fixture_chain(SOURCE,BRIEF)
        p["segments"][0]["shot_id"]="imaginary_shot"
        with self.assertRaises(V6Blocked):
            validate_director(SOURCE,p)
    def test_model_cannot_invent_timecodes(self):
        _,p,_=fixture_chain(SOURCE,BRIEF)
        p["segments"][0]["duration_seconds"]=55
        with self.assertRaises(V6Blocked):
            validate_director(SOURCE,p)
    def test_model_cannot_invent_unknown_effects(self):
        _,p,_=fixture_chain(SOURCE,BRIEF)
        p["segments"][0]["effects"]=[{"name":"unregistered_editor_effect","parameters":{}}]
        with self.assertRaises(V6Blocked):
            validate_director(SOURCE,p)
    def test_plan_hash_mismatch_blocks(self):
        _,p,r=fixture_chain(SOURCE,BRIEF)
        r["director_plan_sha256"]="0"*64
        with self.assertRaises(V6Blocked):
            compile_reviewed_edl(SOURCE,p,r)
    def test_reviewer_must_ack_every_segment(self):
        _,p,r=fixture_chain(SOURCE,BRIEF)
        r["segment_decisions"]=[]
        with self.assertRaises(V6Blocked):
            compile_reviewed_edl(SOURCE,p,r)
    def test_research_shot_mismatch_blocks(self):
        x={"observations":[{"shot_id":"other","visible":"Imaginary"}],
           "research_scope":"Synthetic grounded creative context."}
        with self.assertRaises(V6Blocked):
            validate_observations(SOURCE,x)
    def test_music_request_not_silently_ignored(self):
        with self.assertRaises(ValueError):
            run(source=SOURCE,brief=BRIEF,brand=BRAND,audio_mode="licensed_music")

if __name__=="__main__":
    unittest.main()
