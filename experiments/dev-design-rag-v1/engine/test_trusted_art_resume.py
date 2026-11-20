import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import site_builder
from core import STAGES
class SignedResumeSafety(unittest.TestCase):
 def fixture(self):
  t=tempfile.TemporaryDirectory();root=Path(t.name);w=root/'isolated'
  (w/'site').mkdir(parents=True);(w/'reports').mkdir()
  (w/'site/index.html').write_text('<html><main><h1>Fixture</h1></main></html>')
  s={'site_sha256':site_builder.treehash(w/'site'),
     'stage_status':{k:'PASS' if k in ('rag_retrieval','autonomous_concept_and_design','autonomous_implementation','actual_render_and_screenshot','technical_qa') else 'PENDING' for k in STAGES}}
  q={'pass':True,'source_hash':s['site_sha256'],'screenshots':[{'page':'index.html','width':390}]}
  f=w/'reports/browser-qa.json';f.write_text(json.dumps(q));s['qa_receipt_sha256']=site_builder.sha(f)
  lh={'status':'PASS','pages':{'index.html':{}},'source_sha256':s['site_sha256'],'browser_receipt_sha256':s['qa_receipt_sha256']}
  f=w/'reports/lighthouse-summary.json';f.write_text(json.dumps(lh));s['lighthouse_summary_sha256']=site_builder.sha(f)
  return t,root,w,s
 def test_missing_independent_receipt_rejected(self):
  t,root,w,s=self.fixture()
  with t,patch.object(site_builder,'ROOT',root),patch.object(site_builder,'state',return_value=s):
   before=site_builder.treehash(w/'site')
   with self.assertRaisesRegex(ValueError,'EXTERNAL_INDEPENDENT_SIGNED_RECEIPT_MISSING'):site_builder.resume_artistic_only(w)
   self.assertEqual(site_builder.treehash(w/'site'),before)
 def test_mutated_lighthouse_rejected(self):
  t,root,w,s=self.fixture()
  with t,patch.object(site_builder,'ROOT',root),patch.object(site_builder,'state',return_value=s):
   (w/'reports/lighthouse-summary.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'LIGHTHOUSE_RECEIPT_DRIFT'):site_builder.resume_artistic_only(w)
 def test_mutated_source_rejected(self):
  t,root,w,s=self.fixture()
  with t,patch.object(site_builder,'ROOT',root),patch.object(site_builder,'state',return_value=s):
   (w/'site/index.html').write_text('TAMPER')
   with self.assertRaisesRegex(ValueError,'SOURCE_HASH_DRIFT'):site_builder.resume_artistic_only(w)
if __name__=='__main__':unittest.main()
