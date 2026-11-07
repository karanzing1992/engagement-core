"""Actual packaged txtai BM25/SQLite retrieval tests. No AI inference or private video."""
from __future__ import annotations
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import txtai_reel_guidance as rag


class CorpusSecurityTests(unittest.TestCase):
    def test_curated_source_only_and_hash(self):
        data,raw=rag.corpus()
        self.assertEqual(data["scope"],"reel_making_best_practices_only")
        self.assertEqual(len(data["items"]),43)
        self.assertEqual(len({r["id"] for r in data["items"]}),43)
        self.assertEqual(len(rag.sha256(raw)),64)
        self.assertEqual({role for r in data["items"] for role in r["roles"]},
                         set(rag.ROLES))

    def test_external_untrusted_source_denied(self):
        data,_=rag.corpus()
        data["items"][0]["source_url"]="https://unknown-site.example/guidance"
        with tempfile.TemporaryDirectory() as root:
            hostile=Path(root)/"corpus.json"
            hostile.write_text(json.dumps(data),encoding="utf-8")
            with patch.object(rag,"CORPUS",hostile):
                with self.assertRaisesRegex(rag.GuidanceError,"SOURCE_URL"):
                    rag.corpus()

    def test_duplicate_citation_id_denied(self):
        data,_=rag.corpus()
        data["items"][0]["id"]=data["items"][1]["id"]
        with tempfile.TemporaryDirectory() as root:
            hostile=Path(root)/"corpus.json"
            hostile.write_text(json.dumps(data),encoding="utf-8")
            with patch.object(rag,"CORPUS",hostile):
                with self.assertRaisesRegex(rag.GuidanceError,"ID_INVALID"):
                    rag.corpus()

    def test_index_disabled_for_unavailable_dependency(self):
        with patch.object(rag,"_txtai",side_effect=ImportError("arbitrary API key: SECRET")):
            with tempfile.TemporaryDirectory() as root:
                result=rag.collect("Moksha nature cinematic Reel",
                                   "recorded footage",Path(root))
        self.assertEqual(result["status"],"unavailable")
        self.assertEqual(result["reason"],"RAG_TXTAI_DEPENDENCY_MISSING")
        self.assertNotIn("SECRET",str(result))
        self.assertEqual(rag.receipt(result)["source_ids"]["director"],[])

    def test_disabled_never_creates_index(self):
        with tempfile.TemporaryDirectory() as root:
            result=rag.collect("Any filming question","source",Path(root),enable=False)
            self.assertEqual(result["reason"],"DISABLED")
            self.assertEqual(list(Path(root).iterdir()),[])

    def test_untrusted_query_cannot_change_retrieved_corpus(self):
        with self.assertRaisesRegex(rag.GuidanceError,"QUERY_INVALID"):
            rag._plain(123,100)


class ActualTxtaiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test the upstream packaged txtai library, not a mocked substitute.
        cls.version=importlib.metadata.version("txtai-minimal")
        cls.temp=tempfile.TemporaryDirectory(prefix="mad-v7-real-txtai-")
        cls.work=Path(cls.temp.name)
        cls.retrieval=rag.collect(
            "cinematic sauna wellness nature Reel with guests and steam",
            "authentic footage of steam, water and breathwork",cls.work)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_01_txtai_is_present_and_has_real_index(self):
        self.assertEqual(self.retrieval["status"],"ready",self.retrieval)
        self.assertEqual(self.retrieval["engine"],"txtai")
        self.assertEqual(self.retrieval["retrieval"],"bm25")
        self.assertTrue((self.work/"mad-v7-reel-micro-rag"/"index"/"config.json").exists())
        self.assertEqual(self.retrieval["records"],43)
        self.assertTrue(self.version.startswith("9."))

    def test_02_each_model_has_citations_with_bounded_context(self):
        source,raw=rag.corpus()
        by_id={x["id"]:x for x in source["items"]}
        self.assertEqual(self.retrieval["corpus_sha256"],rag.sha256(raw))
        for role in rag.ROLES:
            context=self.retrieval["roles"][role]["context"]
            ids=self.retrieval["roles"][role]["ids"]
            self.assertTrue(ids,role)
            self.assertLessEqual(len(ids),3)
            self.assertLessEqual(len(context),rag.MAX_CONTEXT+180)
            for uid in ids:
                self.assertIn(role,by_id[uid]["roles"])
                self.assertIn("["+uid+"]",context)
                self.assertIn(by_id[uid]["source_url"],context)
            self.assertNotIn("source_sha256",context)

    def test_03_no_private_footage_or_prompt_in_receipt(self):
        p=rag.receipt(self.retrieval)
        self.assertEqual(p["status"],"ready")
        self.assertEqual(p["engine"],"txtai")
        self.assertIn("director",p["source_ids"])
        self.assertNotIn("cinematic sauna",str(p))
        self.assertNotIn("authentic footage",str(p))
        self.assertNotIn("text",str(p).split("'source_ids'")[0])

    def test_04_at_least_30_reel_intents_have_role_grounded_retrieval(self):
        from txtai import Embeddings
        indexpath=self.work/"mad-v7-reel-micro-rag"/"index"
        rows,_=rag.corpus()
        by_id={x["id"]:x for x in rows["items"]}
        cases=[
         ("research","vertical footage face framing safe zones"),
         ("director","opening hook first shot"),
         ("reviewer","captions accessibility contrast"),
         ("director","pacing calm cinematic story"),
         ("reviewer","soundtrack rights and license"),
         ("director","immersive environment natural ambience"),
         ("reviewer","ffprobe verify audio and video"),
         ("research","do not invent footage or people"),
         ("director","mood cinematic natural colors"),
         ("reviewer","check final frame fade out"),
         ("director","match cuts action"),
         ("reviewer","technical video QA decode"),
         ("research","hands gestures sauna steam"),
         ("director","nature sunlight storytelling"),
         ("reviewer","check voices against music"),
         ("director","edit music beat rhythm"),
         ("reviewer","video text legibility"),
         ("director","testimonial narrative emotional"),
         ("research","authentic recorded guest visuals"),
         ("reviewer","vertical crop important subject"),
         ("director","transition continuity"),
         ("reviewer","color grading highlights"),
         ("director","breathwork movement shots"),
         ("research","scene facts visible context"),
         ("reviewer","publishing requires owner approval"),
         ("director","visual motif steam water"),
         ("reviewer","avoid music cutoff"),
         ("director","short vertical social Reel"),
         ("reviewer","audio loudnorm silence"),
         ("director","title caption typography"),
         ("reviewer","viewer safe framing"),
         ("director","coherent message and story")
        ]
        with Embeddings().load(str(indexpath)) as index:
            self.assertEqual(index.count(),43)
            for role,query in cases:
                matched=rag._search_for(index,by_id,role,query,"real footage",3)
                self.assertTrue(matched,(role,query))
                self.assertLessEqual(len(matched),3)
                self.assertTrue(all(role in row["roles"] for row in matched))
                self.assertTrue(all(row["source_url"].startswith("https://")
                                    for row in matched))

    def test_05_write_is_separate_from_read_only_retrieval(self):
        # Querying a persisted index must not modify the curated corpus or
        # include owner footage / arbitrary user text in the txtai database.
        manifest=json.loads((self.work/"mad-v7-reel-micro-rag"/"manifest.json").read_text())
        self.assertTrue(manifest["read_only"])
        data,raw=rag.corpus()
        self.assertEqual(manifest["corpus_sha256"],rag.sha256(raw))
        self.assertEqual(manifest["record_count"],len(data["items"]))


if __name__=="__main__":
    unittest.main(verbosity=2)
