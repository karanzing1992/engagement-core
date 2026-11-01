import json
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import Mock
import creative_director as d


def source():
    return {"provenance": "human_reviewed", "shots": [
        {"id": "water", "start_seconds": 0, "duration_seconds": 7,
         "visible_description": "Blue moving water and leaves in daylight"},
        {"id": "leaves", "start_seconds": 8, "duration_seconds": 7,
         "visible_description": "Green leaves blowing against a forest background"},
        {"id": "stones", "start_seconds": 18, "duration_seconds": 7,
         "visible_description": "Someone walks across a rocky footpath"},
        {"id": "sky", "start_seconds": 30, "duration_seconds": 7,
         "visible_description": "A wide daytime sky and floating clouds"},
        {"id": "light", "start_seconds": 40, "duration_seconds": 7,
         "visible_description": "Soft sunlight falling on a textured wall"},
    ]}


def plan():
    base = ["water", "leaves", "stones", "sky", "light", "water"]
    return {"versions": [
        {"id": cid, "name": name, "hook": "A real sensory moment",
         "narrative": "Different source-grounded rhythm",
         "segments": [{"shot_id": sid, "duration_seconds": 2.5, "caption": ""}
                      for sid in (base if cid == "A" else list(reversed(base)) if cid == "B" else base[2:] + base[:2])]}
        for cid, name in [("A","Nature"),("B","Movement"),("C","Textures")]]}


class TestDirector(TestCase):
    def test_manifest_requires_human_attestation(self):
        s = source()
        s["provenance"] = "unverified"
        with self.assertRaises(d.ContractError):
            d.require_shots(s)

    def test_grounded_edl(self):
        shots = d.require_shots(source())
        concepts = d.check_concepts(plan(), shots)
        self.assertEqual(len(concepts), 3)
        edl = d.compile_edl(concepts, shots)
        self.assertEqual(len(edl), 3)
        self.assertEqual(edl[0]["commands"][0]["source_start_seconds"], 0)
        self.assertEqual(edl[0]["duration_seconds"], 15.0)

    def test_unknown_shot_rejected(self):
        p = plan()
        p["versions"][1]["segments"][0]["shot_id"] = "invented"
        with self.assertRaises(d.ContractError):
            d.check_concepts(p, d.require_shots(source()))

    def test_excess_duration_rejected(self):
        p = plan()
        p["versions"][0]["segments"][0]["duration_seconds"] = 99
        with self.assertRaises(d.ContractError):
            d.check_concepts(p, d.require_shots(source()))

    def test_groq_120b_model_selection(self):
        c = Mock()
        c.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(plan())))])
        out = d.run_director(d.require_shots(source()), "Moksha verified tone", "calm travel", "testkey", client=c)
        self.assertEqual(out["director_model"], "openai/gpt-oss-120b")
        self.assertTrue(out["not_rendered"])
        self.assertEqual(out["edl"][1]["id"], "B")
        self.assertEqual(c.chat.completions.create.call_args.kwargs["model"], "openai/gpt-oss-120b")

if __name__ == "__main__":
    main()
