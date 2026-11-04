#!/usr/bin/env python3
"""Offline V5 capability, creativity and fail-closed contract tests."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, main, mock
import v5_orchestrator as v5

HERE=Path(__file__).resolve().parent

def system():
    return v5.load_system(HERE/"v5_config.json",HERE/"capability_registry.json")

def source(n=5,external=False):
    return {"provenance":"human_reviewed",
            "external_metadata_approved":external,
            "rights_and_consent":external,
            "shots":[
              {"id":"S"+str(i+1),"start_seconds":float(i*7),
               "duration_seconds":7.0,
               "visible_description":"Synthesized test scene number "+str(i+1)}
              for i in range(n)]}

def fake_plan(n,shotids=None,count=5,duration=1.3,extras=None):
    ids=shotids or ["S1","S2","S3","S4","S5"]
    return {"versions":[{
      "id":"T"+str(k+1),"name":"Treatment "+str(k+1),
      "narrative":"Independent story structure with different clip ordering",
      "hook":"Motion in first frame", "emotional_arc":"curiosity to resolution",
      "segments":[{
         "shot_id": ids[(j+k)%len(ids)],"offset_seconds":0.2,
         "duration_seconds":duration,"caption":"",
         "proposed_operations":extras if j==0 and extras else []
      } for j in range(count)]
    } for k in range(n)]}

class V5ContractTests(TestCase):
    def test_system_configuration(self):
        c,r=system()
        self.assertEqual(c["version"],"5.0.0")
        self.assertEqual(c["models"]["creative"][0]["model"],"openai/gpt-oss-120b")
        self.assertEqual(c["models"]["vision"][0]["model"],"qwen/qwen3.8-27b")
        self.assertTrue(all(m["provider"]=="groq" for group in c["models"].values() for m in group))
        self.assertEqual(c["provider_policy"]["allowed"],["groq"])
        self.assertEqual(c["provider_policy"]["plan"],"free_only")
        self.assertIs(c["provider_policy"]["allow_paid_inference"],False)
        self.assertEqual(c["models"]["creative"][1]["model"],"openai/gpt-oss-20b")
        self.assertTrue(all(m["model"] in c["budget"]["groq_free_tier"]["models"]
                            for group in c["models"].values() for m in group))
        self.assertEqual(c["task_routing"]["shot_visual_analysis"]["max_captioned_frames_per_job"],6)
        self.assertEqual(c["task_routing"]["shot_visual_analysis"]["images_per_free_tier_batch"],3)
        self.assertTrue(c["creative"]["allow_model_generated_tool_suggestions"])

    def test_groq_free_tier_limits_cannot_be_silently_relaxed(self):
        c,_=system()
        import tempfile
        c["budget"]["groq_free_tier"]["models"]["qwen/qwen3.8-27b"]["tpm"]=9999
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"not_free.json"
            f.write_text(json.dumps(c))
            with self.assertRaisesRegex(v5.Rejected,"free tier quota"):
                v5.load_system(f,HERE/"capability_registry.json")

    def test_only_production_text_models_for_director_fallback(self):
        c,_=system()
        route=v5.models_for_task(c,"cinematic_direction")
        self.assertEqual([m["model"] for m in route],
                         ["openai/gpt-oss-120b","openai/gpt-oss-20b"])
        self.assertNotIn("qwen/qwen3.8-27b",[m["model"] for m in route])

    def test_model_routing_fallback(self):
        c,_=system()
        chosen=v5.select_model(c,"vision",available={"groq:qwen/qwen3.8-27b"})
        self.assertEqual(chosen["model"],"qwen/qwen3.8-27b")
        self.assertEqual(v5.models_for_task(c,"cinematic_direction")[0]["model"],"openai/gpt-oss-120b")
        self.assertEqual(v5.models_for_task(c,"shot_visual_analysis")[0]["model"],"qwen/qwen3.8-27b")
        self.assertEqual(v5.models_for_task(c,"complex_edit_decision")[0]["model"],"openai/gpt-oss-120b")
        self.assertEqual(v5.models_for_task(c,"quick_edit_validation")[0]["model"],"openai/gpt-oss-20b")
        self.assertEqual(v5.models_for_task(c,"artistic_critique")[0]["model"],"openai/gpt-oss-120b")
        with self.assertRaises(v5.Rejected):
            v5.select_model(c,"vision",available={"groq:openai/gpt-oss-120b"})
        with self.assertRaises(v5.Rejected):
            v5.models_for_task(c,"shot_visual_analysis",available={"groq:openai/gpt-oss-120b"})

    def test_count_not_hardwired_three(self):
        c,_=system()
        self.assertEqual(v5.validate_brief_versions(1,c),1)
        self.assertEqual(v5.validate_brief_versions(6,c),6)
        self.assertEqual(v5.validate_brief_versions(12,c),12)
        with self.assertRaises(v5.Rejected):
            v5.validate_brief_versions(13,c)

    def test_arbitrary_clip_counts_under_workload_budget(self):
        c,_=system();shots=v5.validate_source(source(),c)
        self.assertEqual(len(v5.validate_plan(fake_plan(1,count=1),shots,1,c)[0]["segments"]),1)
        self.assertEqual(len(v5.validate_plan(fake_plan(2,count=50),shots,2,c)[0]["segments"]),50)

    def test_duration_not_fixed_to_40_seconds(self):
        c,_=system();shots=v5.validate_source(source(),c)
        plan=v5.validate_plan(fake_plan(1,count=50,duration=2.0),shots,1,c)
        self.assertEqual(plan[0]["duration_seconds"],100)
        with self.assertRaises(v5.Rejected):
            v5.validate_plan(fake_plan(1,count=100,duration=2.0),shots,1,c)

    def test_source_provenance_is_hard_gate(self):
        c,_=system();x=source();x["provenance"]="unverified"
        with self.assertRaises(v5.Rejected):
            v5.validate_source(x,c)

    def test_source_offset_must_be_real(self):
        c,_=system();shots=v5.validate_source(source(),c)
        p=fake_plan(1);p["versions"][0]["segments"][0]["offset_seconds"]=6.7
        with self.assertRaises(v5.Rejected):
            v5.validate_plan(p,shots,1,c)

    def test_unapproved_external_metadata_is_blocked(self):
        with self.assertRaises(v5.Rejected):
            v5.required_clearance(source(),external=True)
        self.assertIsNone(v5.required_clearance(source(external=True),external=True))

    def test_model_suggested_tools_are_preserved_but_not_executed(self):
        c,r=system();shots=v5.validate_source(source(),c)
        extra=[{"name":"mask","parameters":{"shape":"spherical"}},
               {"name":"future_plug_in","parameters":{"palette":"custom"}},
               {"name":"trim","parameters":{"shot_id":"S1",
                           "offset_seconds":0,"duration_seconds":1.1}}]
        validated=v5.validate_plan(fake_plan(1,extras=extra),shots,1,c)
        report=v5.plan_operations(validated,r)
        self.assertEqual(len(report["deferred_operations"]),2)
        self.assertEqual(len(report["verified_operation_proposals"]),1)
        self.assertFalse(report["execution_ready"])
        self.assertEqual(report["shell_commands_executed"],0)

    def test_clean_plan_does_not_claim_render_or_publish(self):
        c,r=system();shots=v5.validate_source(source(),c)
        validated=v5.validate_plan(fake_plan(1),shots,1,c)
        report=v5.plan_operations(validated,r)
        self.assertTrue(report["execution_ready"])
        self.assertFalse(report["rendered"])
        self.assertFalse(report["published"])

    def test_brief_contains_ambiguity_and_open_creativity(self):
        c,r=system();shots=v5.validate_source(source(),c)
        p=v5.build_director_prompt(c,shots,"Moksha approved brand rules",
                                  "Make three aesthetically different films",6,
                                  "private_preview")
        self.assertIn("exactly 6",p)
        self.assertIn("No fixed number of segments",p)
        self.assertIn("VERIFIED SOURCE SHOTS",p)

    def test_model_api_stub_passes_creativity_profile(self):
        c,_=system()
        fake=mock.Mock()
        fake.chat.completions.create.return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(fake_plan(2))))])
        x=v5.call_groq(c,"verified synthetic description","test-key",client=fake)
        self.assertEqual(len(x["versions"]),2)
        kwargs=fake.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["temperature"],0.85)
        self.assertEqual(kwargs["model"],"openai/gpt-oss-120b")
        self.assertEqual(kwargs["reasoning_effort"],"high")

    def test_external_provider_is_rejected_even_when_inserted_at_runtime(self):
        c,_=system()
        c["models"]["creative"].insert(0,{"provider":"new_free_api",
             "model":"custom-large-creative","temperature":0.92})
        with self.assertRaises(v5.Rejected):
            v5.select_model(c,"creative")
        with self.assertRaises(v5.Rejected):
            v5.models_for_task(c,"creative_direction_not_registered")


    def test_vision_adapter_uses_groq_image_data_only(self):
        c,_=system()
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"frame.jpg"
            f.write_bytes(b"FAKEJPEG"+b"x"*256)
            fake=mock.Mock()
            fake.chat.completions.create.return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(
                    content="A synthetic blue landscape with water ripples."))])
            result=v5.call_groq_vision(c,f,"Describe this synthetic image only.","dummy",client=fake)
            self.assertIn("water ripples",result)
            args=fake.chat.completions.create.call_args.kwargs
            self.assertEqual(args["model"],"qwen/qwen3.8-27b")
            self.assertEqual(args["reasoning_effort"],"none")
            self.assertTrue(args["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
            with self.assertRaises(v5.Rejected):
                v5.call_groq_vision(c,f,"Too short","dummy",client=fake)

    def test_no_arbitrary_model_shell(self):
        c,r=system()
        c["tools"]["never_execute_model_shell"]=False
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/"bad.json";f.write_text(json.dumps(c))
            with self.assertRaises(v5.Rejected):
                v5.load_system(f,HERE/"capability_registry.json")

    def test_tool_registration_is_data_driven(self):
        c,r=system()
        r["operations"].append({"name":"custom_motion_engine",
             "adapter":"future_plugin","status":"candidate",
             "fields":["animation_graph"]})
        shots=v5.validate_source(source(),c)
        plan=v5.validate_plan(fake_plan(1,extras=[
          {"name":"custom_motion_engine","parameters":{"animation_graph":"abc"}}]),
          shots,1,c)
        report=v5.plan_operations(plan,r)
        self.assertEqual(report["deferred_operations"][0]["name"],
                         "custom_motion_engine")

if __name__=="__main__":
    main()
