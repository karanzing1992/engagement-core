"""DEV DESIGN RAG security, review lifecycle and release policy certification."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from dev_design_rag.core import (
    ART_MIN, REQUIRED_TESTS, DesignKnowledge, IsolationError,
    Registry, ReviewLedger, Scope, atomic_write,
    init_registry, make_graph_doc, safe_dir
)

ART="a"*64
OTHER="b"*64

class EnginePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"design"
        self.registry=init_registry(self.root)

    def second_project(self):
        p=deepcopy(self.registry.config)
        p["brands"]["otherbrand"]={"owner":"second_owner","name":"Test brand (synthetic)"}
        p["projects"]["second-dashboard"]={"brand":"otherbrand","type":"saas_dashboard","owner":"second_owner"}
        p["principals"]["owner"]["projects"].append("second-dashboard")
        p["principals"]["second_agent"]={"projects":["second-dashboard"]}
        atomic_write(self.root/"policy.json",json.dumps(p))
        self.registry=Registry(self.root)

    def test_toolwide_unoverridable_95(self):
        self.assertEqual(ART_MIN,95)
        self.assertEqual(self.registry.config["quality"]["artistic_minimum"],95)
        self.assertIs(self.registry.config["quality"]["project_override_allowed"],False)
        self.second_project()
        self.assertEqual(self.registry.config["quality"]["artistic_minimum"],95)
        self.assertEqual(self.registry.scopes("second-dashboard","second_agent")[1],Scope("type","saas_dashboard"))

    def test_policy_tamper_detected(self):
        x=deepcopy(self.registry.config)
        x["quality"]["artistic_minimum"]=80
        atomic_write(self.root/"policy.json",json.dumps(x))
        with self.assertRaises(IsolationError):
            Registry(self.root)

    def test_project_quality_override_denied(self):
        x=deepcopy(self.registry.config)
        x["projects"]["andaz-vibe-stay"]["quality"]={"artistic_minimum":80}
        atomic_write(self.root/"policy.json",json.dumps(x))
        with self.assertRaises(IsolationError):
            Registry(self.root)

    def test_four_physical_layers_separate(self):
        scopes=self.registry.scopes("andaz-vibe-stay","owner")
        self.assertEqual([(s.kind,s.scope_id) for s in scopes],
            [("generic","shared"),("type","hospitality"),("brand","andaz"),("project","andaz-vibe-stay")])
        paths=[self.registry.scope_dir(s) for s in scopes]
        self.assertEqual(len(set(map(str,paths))),4)
        for p in paths:
            self.assertEqual(p.stat().st_mode & 0o777,0o700)

    def test_cross_project_read_denied(self):
        self.second_project()
        self.assertRaises(IsolationError,self.registry.scopes,"andaz-vibe-stay","second_agent")
        self.assertRaises(IsolationError,self.registry.scopes,"second-dashboard","andaz_design_agent")
        self.assertRaises(IsolationError,self.registry.scopes,"second-dashboard","untrusted_agent")
        self.assertEqual(self.registry.scopes("second-dashboard","second_agent")[2].scope_id,"otherbrand")

    def test_brand_scope_cross_write_denied(self):
        self.second_project()
        self.assertFalse(self.registry.writable(Scope("brand","andaz"),"owner","second-dashboard"))
        self.assertFalse(self.registry.writable(Scope("project","andaz-vibe-stay"),"owner","second-dashboard"))
        self.assertFalse(self.registry.writable(Scope("generic","shared"),"second_agent","second-dashboard"))
        self.assertTrue(self.registry.writable(Scope("type","saas_dashboard"),"owner","andaz-vibe-stay"))

    def test_path_traversal_and_symlink_denied(self):
        for x in ("../users","user/private","A", ".", "a"*70):
            with self.assertRaises(IsolationError):
                Scope("project",x)
        base=self.root/"graphs"
        base.mkdir(exist_ok=True)
        (base/"types").symlink_to(self.root, target_is_directory=True)
        self.assertRaises(IsolationError,safe_dir,base,"types","hospitality")

    def test_brand_or_customer_in_shared_denied(self):
        for item in ("Andaz Vibe Stay guest experience","mokshagoa.com landing","customer_email: x"):
            with self.assertRaises(IsolationError):
                self.registry.assert_shared_source(Scope("generic","shared"),item)
            with self.assertRaises(IsolationError):
                self.registry.assert_shared_source(Scope("type","hospitality"),item)

    def test_private_brand_allowed(self):
        self.registry.assert_shared_source(Scope("brand","andaz"),"Andaz Vibe Stay identity")
        self.registry.assert_shared_source(Scope("project","andaz-vibe-stay"),"Andaz design review 54/100")

    def test_document_graph_namespace_and_source(self):
        records=make_graph_doc(Scope("type","hospitality"),"design_guide",
            "# Title\n## Color\nContrast and signposting\n## UX\nClear state feedback",
            "https://www.w3.org/TR/wcag/")
        self.assertGreaterEqual(len(records["entities"]),3)
        self.assertTrue(all(e["entity_name"].startswith("TYPE HOSPITALITY")
                            for e in records["entities"]))
        self.assertTrue(all("w3.org" in e["file_path"] for e in records["entities"]))

class ReviewsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/"design"
        self.reg=init_registry(self.root)
        self.ledger=ReviewLedger(self.reg)

    def review(self,id="art1",kind="artistic",score=95,artifact=ART,verdict="APPROVE",passed=True):
        r={"project":"andaz-vibe-stay","review_id":id,"kind":kind,
          "scope":"homepage","artifact_sha":artifact,
          "source_url":"https://github.com/karanzing1992/engagement-core/actions/runs/42365766838",
          "reviewer":"gemini-3.6-flash" if kind=="artistic" else "independent_playwright",
          "findings":[],"timestamp":"2026-11-07T10:00:00Z"}
        if kind=="artistic":
            r.update({"score":score,"verdict":verdict,"independent":True})
        else:r["passed"]=passed
        return r

    def test_submit_is_durable_pending_and_idempotent(self):
        r=self.review()
        self.assertEqual(self.ledger.submit(r)["status"],"PENDING")
        self.assertTrue(self.ledger.submit(r)["deduplicated"])
        self.assertEqual(len(self.ledger.pending("andaz-vibe-stay")),1)
        reopened=ReviewLedger(self.reg)
        self.assertEqual(reopened.pending("andaz-vibe-stay")[0]["review_id"],"art1")

    def test_conflicting_review_id_is_rejected(self):
        self.ledger.submit(self.review())
        with self.assertRaises(IsolationError):
            self.ledger.submit(self.review(score=96))

    def test_fake_or_unsigned_review_cannot_skip_independence(self):
        r=self.review()
        r["independent"]=False
        self.assertRaises(ValueError,self.ledger.submit,r)
        r=self.review()
        r["reviewer"]="synthetic"
        self.ledger.submit(r)
        # A synthetic scored review is still journaled, but never qualifies.
        self.assertEqual(self.ledger.gate("andaz-vibe-stay",ART)["status"],"BLOCKED")

    def test_no_review_fails_closed(self):
        result=self.ledger.gate("andaz-vibe-stay",ART)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertFalse(result["checks"]["independent_artistic_approve"])

    async def fake_reconcile(self):
        async def fake_index(self,scope,doc_id,text,source_url,principal="owner",project="andaz-vibe-stay"):
            return {"status":"INDEXED"}
        with patch.object(DesignKnowledge,"index",new=fake_index):
            return await self.ledger.reconcile("andaz-vibe-stay")

    def add_pass_reviews(self,score=95,verdict="APPROVE"):
        self.ledger.submit(self.review(score=score,verdict=verdict))
        for k in REQUIRED_TESTS:
            self.ledger.submit(self.review(id=k,kind=k,passed=True))
        asyncio.run(self.fake_reconcile())

    def test_94_rejected_despite_all_qa_and_owner(self):
        self.add_pass_reviews(score=94)
        result=self.ledger.gate("andaz-vibe-stay",ART,owner_approval=True)
        self.assertFalse(result["checks"]["artistic_score_at_least_95"])
        self.assertEqual(result["status"],"BLOCKED")

    def test_95_requires_owner_approval(self):
        self.add_pass_reviews()
        result=self.ledger.gate("andaz-vibe-stay",ART)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertFalse(result["checks"]["owner_approval"])
        self.assertEqual(self.ledger.gate("andaz-vibe-stay",ART,owner_approval=True)["status"],"PASS")

    def test_other_artifact_cannot_borrow_approval(self):
        self.add_pass_reviews()
        self.assertEqual(self.ledger.gate("andaz-vibe-stay",OTHER,owner_approval=True)["status"],"BLOCKED")

    def test_every_bad_review_preserved_no_cherry_picking(self):
        self.add_pass_reviews(score=98)
        self.ledger.submit(self.review(id="second_lower_review",score=81,verdict="REVISE"))
        asyncio.run(self.fake_reconcile())
        v=self.ledger.gate("andaz-vibe-stay",ART,owner_approval=True)
        self.assertEqual(v["artistic_score"],81)
        self.assertEqual(v["status"],"BLOCKED")
        self.assertEqual(v["review_count"],7)

    def test_pending_ingest_blocks_approval(self):
        self.add_pass_reviews()
        self.ledger.submit(self.review(id="new_pending",kind="ux",passed=True))
        v=self.ledger.gate("andaz-vibe-stay",ART,owner_approval=True)
        self.assertFalse(v["checks"]["no_review_backlog"])

    def test_reconcile_failure_is_retained_for_retry(self):
        self.ledger.submit(self.review())
        async def broken(*args,**kwargs):
            raise RuntimeError("LOCAL_EMBEDDING_TEMP_UNAVAILABLE")
        with patch.object(DesignKnowledge,"index",new=broken):
            r=asyncio.run(self.ledger.reconcile("andaz-vibe-stay"))
        self.assertEqual(r["results"][0]["status"],"PENDING")
        self.assertEqual(len(self.ledger.pending("andaz-vibe-stay")),1)
        good=asyncio.run(self.fake_reconcile())
        self.assertEqual(good["results"][0]["status"],"INDEXED")
        self.assertEqual(len(self.ledger.pending("andaz-vibe-stay")),0)

    def test_password_or_token_dropped(self):
        x=self.review()
        x["findings"]=["Authorization: bearer string"]
        self.assertRaises(IsolationError,self.ledger.submit,x)

    def test_project_review_writes_to_selected_project_only(self):
        self.ledger.submit(self.review())
        asyncio.run(self.fake_reconcile())
        self.assertFalse((self.root/"knowledge"/"generic"/"shared"/"review-art1.md").exists())
        self.assertEqual(self.ledger.gate("andaz-vibe-stay",ART)["artistic_score"],95)

if __name__=="__main__":
    unittest.main(verbosity=2)
