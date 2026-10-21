import json
import pathlib
import tempfile
import unittest
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from legal_search import build,query,load_records

class TestLegalIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.db=pathlib.Path(cls.tmp.name)/"index.sqlite3"
        build(cls.db)
    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()
    def test_gst_search(self):
        res=query("GSTR-3B",as_of="2026-10-21",jurisdiction="IN-GA",database=self.db)
        self.assertTrue(any(r["id"]=="IN-GST-GSTR3B-GUIDE" for r in res))
    def test_57th_recommendations_nonbinding_by_default(self):
        res=query("57th Council",as_of="2026-10-21",jurisdiction="IN-GA",database=self.db)
        self.assertFalse(any(r["status"]=="recommendation" for r in res))
        incl=query("57th Council",as_of="2026-10-21",jurisdiction="IN-GA",include_nonbinding=True,database=self.db)
        self.assertTrue(any(r["status"]=="recommendation" for r in incl))
    def test_time_sensitive_income_tax(self):
        old=query("Income-tax Act",as_of="2025-10-21",database=self.db)
        self.assertFalse(any(r["id"]=="IN-IT-2025-ACT" for r in old))
        now=query("Income-tax Act",as_of="2026-10-21",database=self.db)
        self.assertTrue(any(r["id"]=="IN-IT-2025-ACT" for r in now))
    def test_no_unverified_rate_in_strict_mode(self):
        res=query("sauna",as_of="2026-10-21",jurisdiction="IN-GA",strict=True,database=self.db)
        self.assertFalse(any(r["id"]=="IN-GST-SPA-CLASSIFY" for r in res))
    def test_safe_query(self):
        self.assertIsInstance(query('"; DROP TABLE records;--',database=self.db),list)
    def test_urls_and_unique_ids(self):
        items=load_records()
        self.assertEqual(len(items),len(set(r["id"] for r in items)))
        self.assertTrue(all(r["source_url"].startswith("https://") for r in items))

if __name__=="__main__":
    unittest.main()
