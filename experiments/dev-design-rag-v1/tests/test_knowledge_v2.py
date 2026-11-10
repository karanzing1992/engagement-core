"""Design RAG V2 precedence, bounded retrieval, source integrity and isolation tests."""
import json
import tempfile
import unittest
from pathlib import Path

from dev_design_rag.core import init_registry
from dev_design_rag.knowledge_v2 import build_packet, KnowledgeV2Error

class DesignKnowledgeV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.registry=init_registry(self.root)
        self.scopes=self.registry.scopes("andaz-vibe-stay")
        self.docs={
         "generic/shared":["uiux-v2-foundations-20261110","uiux-v2-awards-trends-2026"],
         "type/hospitality":["hospitality_design"],
         "brand/andaz":["andaz-brand-current-v6-20261110"],
         "project/andaz-vibe-stay":["andaz-v6-arambol-edit-20261110"]
        }
        content={
         "uiux-v2-foundations-20261110":"WCAG 2.2 AA keyboard real alt text focus visible >=4.5 text source https://www.w3.org/TR/WCAG22/",
         "uiux-v2-awards-trends-2026":"2026 Webby award aesthetic Igloo Inc; functional FOLLOW.ART; source https://winners.webbyawards.com/",
         "hospitality_design":"Guests compare real room categories, accurate booking, location, inclusive enquiry.",
         "andaz-brand-current-v6-20261110":"Active V6 owner-approved Andaz exact logo original PNG, Salt Paper #F8F5EE coral #C8684F; old deep green rejected.",
         "andaz-v6-arambol-edit-20261110":"Current V6 Arambol Edit: five actual pages, official logo, real photos of same room; no gold-dominant design.",
         "andaz-old-v5-20261109":"Historic V5 luxury dark jungle teal gold style; NEVER ACTIVE."
        }
        manifest={"version":"2.0.0","as_of":"2026-11-10","max_packet_chars":11500,
                  "priority":["project","brand","generic","type"],"scopes":{}}
        for scope in self.scopes:
            key=scope.key()
            manifest["scopes"][key]={"active":self.docs[key],"historical":[]}
            entries={}
            ids=self.docs[key]+(["andaz-old-v5-20261109"] if scope.kind=="brand" else [])
            for i,doc in enumerate(ids):
                text=content[doc]
                (self.registry.source_dir(scope)/(doc+".md")).write_text(text)
                entries["chunk-"+str(i)]={"content":text,"source_id":doc,"chunk_order_index":0}
            (self.registry.scope_dir(scope)/"kv_store_text_chunks.json").write_text(json.dumps(entries))
        (self.root/"knowledge_manifest_v2.json").write_text(json.dumps(manifest))

    def test_current_versions_always_first(self):
        result=build_packet(self.registry,"andaz-vibe-stay","V6 current owner palette")
        self.assertEqual(result["status"],"READY")
        self.assertEqual(result["version"],"2.1.0")
        self.assertEqual(result["authority_order"],["project","brand","generic","type"])
        self.assertLess(result["packet_text"].find("andaz-v6-arambol-edit"),
                        result["packet_text"].find("andaz-brand-current-v6"))
        self.assertIn("#F8F5EE",result["packet_text"])

    def test_historical_not_present_in_active_prompt(self):
        q=build_packet(self.registry,"andaz-vibe-stay","historic luxury V5 colour")
        self.assertNotIn("Historic V5 luxury dark jungle",q["packet_text"])
        self.assertIn("andaz-old-v5-20261109",[x["source_id"] for x in q["excluded_historical"]])

    def test_budget_and_awards_anchors(self):
        q=build_packet(self.registry,"andaz-vibe-stay","latest 2026 UX award-winning examples and mobile trends")
        self.assertLessEqual(q["packet_chars"],11500)
        self.assertIn("Igloo Inc",q["packet_text"])
        self.assertIn("FOLLOW.ART",q["packet_text"])
        self.assertEqual(q["layer_count"],4)
        self.assertTrue(all(x["status"]=="ACTIVE" for x in q["sources"]))
        self.assertTrue(all(x["source_url"].startswith(("https://","internal://")) for x in q["sources"]))

    def test_scoped_brand_provenance_and_untrusted_denial(self):
        q=build_packet(self.registry,"andaz-vibe-stay","logo")
        brand=[a for a in q["sources"] if a["scope"]=="brand/andaz"]
        self.assertTrue(brand)
        self.assertTrue(all(x["source_url"].startswith("internal://owner-verified/") for x in brand))
        with self.assertRaises(PermissionError):
            build_packet(self.registry,"andaz-vibe-stay","logo",principal="untrusted_agent")

    def test_missing_active_document_fails_closed(self):
        scope=[s for s in self.scopes if s.kind=="brand"][0]
        (self.registry.source_dir(scope)/"andaz-brand-current-v6-20261110.md").unlink()
        with self.assertRaisesRegex(KnowledgeV2Error,"ACTIVE_DOC_SOURCE_MISSING"):
            build_packet(self.registry,"andaz-vibe-stay","logo")

    def test_malformed_manifest_and_invalid_query_blocked(self):
        p=self.root/"knowledge_manifest_v2.json"
        obj=json.loads(p.read_text());obj["priority"]=["generic","project","brand","type"]
        p.write_text(json.dumps(obj))
        with self.assertRaisesRegex(KnowledgeV2Error,"V2_PRECEDENCE_INVALID"):
            build_packet(self.registry,"andaz-vibe-stay","website")
        with self.assertRaises(KnowledgeV2Error):
            build_packet(self.registry,"andaz-vibe-stay","")

if __name__=="__main__":
    unittest.main()

