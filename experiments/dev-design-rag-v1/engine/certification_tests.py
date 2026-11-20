import json,shutil,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import gate,verify_review,treehash
W=Path.home()/'.local/share/dev-design-rag-v1/certification/uiux-v2-andaz-fixture-20261110'
class TestUIUXV2(unittest.TestCase):
 def test_agent(self):
  x=json.loads((W/'reports/accepted-agent.json').read_text());self.assertTrue(x['tool_file_write_verified']);self.assertEqual(x['output_site_sha256'],treehash(W/'site'))
 def test_browser(self):
  x=json.loads((W/'reports/browser-qa.json').read_text());self.assertTrue(x['pass']);self.assertEqual(len(x['rows']),24)
 def test_performance(self):
  x=json.loads((W/'reports/lighthouse-summary.json').read_text())
  self.assertEqual(x['status'],'PASS')
  self.assertEqual(set(x['pages']),set(x['required_pages']))
  for page,result in x['pages'].items():
   for mode in ('mobile','desktop'):
    scores=result[mode]['scores']
    for category,minimum in (('performance',90),('accessibility',95),('best-practices',90)):
     self.assertGreaterEqual(scores[category],minimum,(page,mode,category))
 def test_no_art(self):self.assertIn('MISSING:independent_artistic_review',gate(W)['missing'])
 def test_no_release(self):self.assertIn('OWNER_RELEASE_AUTHORITY_EXTERNAL_ONLY',gate(W,'release')['missing'])
 def test_forged_review(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'fake.json';p.write_text(json.dumps({'score':100,'verdict':'APPROVE','signature_scheme':'HMAC-SHA256'}))
   with self.assertRaises(ValueError):verify_review(W,p)
 def test_source_tamper(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);shutil.copytree(W/'site',p/'site');shutil.copytree(W/'reports',p/'reports');(p/'engine-state.json').write_bytes((W/'engine-state.json').read_bytes());(p/'site/index.html').write_text('TAMPER')
   self.assertIn('SOURCE_HASH_DRIFT',gate(p)['missing'])
 def test_lighthouse_summary_score_forgery_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);shutil.copytree(W/'site',p/'site');shutil.copytree(W/'reports',p/'reports')
   state=json.loads((W/'engine-state.json').read_text())
   summary=json.loads((p/'reports/lighthouse-summary.json').read_text())
   summary['pages']['index.html']['mobile']['scores']['performance']=99
   from core import write,sha
   write(p/'reports/lighthouse-summary.json',summary)
   state['lighthouse_summary_sha256']=sha(p/'reports/lighthouse-summary.json')
   write(p/'engine-state.json',state)
   self.assertIn('LIGHTHOUSE_RAW_SCORE_MISMATCH:index.html:mobile:performance',gate(p)['missing'])
 def test_missing_lh(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);shutil.copytree(W/'site',p/'site');shutil.copytree(W/'reports',p/'reports');(p/'engine-state.json').write_bytes((W/'engine-state.json').read_bytes());(p/'reports/lighthouse-summary.json').unlink()
   self.assertIn('LIGHTHOUSE_ROUTE_COVERAGE_MISSING',gate(p)['missing'])
if __name__=='__main__':unittest.main(verbosity=2)
