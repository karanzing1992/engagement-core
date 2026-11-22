"""Read-only negative checks for the receipt-bound Lighthouse repair."""
import pathlib
import unittest
from performance_repair import improve_image_dimensions
from core import gate
W=pathlib.Path.home()/'.local/share/dev-design-rag-v1/certification/andaz-v8-v212-performance-fixture-20261112'
class EvidenceSafety(unittest.TestCase):
 def test_wrong_route_rejected(self):
  with self.assertRaises(ValueError):improve_image_dimensions(W,'not-present.html')
 def test_replay_rejected_without_unresolved_failed_audit(self):
  with self.assertRaises(ValueError):improve_image_dimensions(W,'andaz-v8.html')
 def test_bound_original_evidence_stored(self):
  self.assertTrue((W/'reports/qa-repairs/performance-1-lighthouse.json').is_file())
 def test_original_html_stored(self):
  self.assertTrue((W/'reports/qa-repairs/performance-1-before.html').is_file())
 def test_browser_qa_passed_four_widths(self):
  import json
  q=json.loads((W/'reports/browser-qa.json').read_text())
  self.assertTrue(q['pass'])
  self.assertEqual({r['width'] for r in q['rows']},{320,390,768,1440})
 def test_engine_release_still_blocked(self):
  result=gate(W,'preview')
  self.assertEqual(result['status'],'BLOCKED')
  self.assertFalse(result['production_release_allowed'])
if __name__=='__main__':unittest.main()
