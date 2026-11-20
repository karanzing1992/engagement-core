"""Pure isolated bridge tests with MOCKED genuine-review contract inputs."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from vision_bridge import ingest,correction_prompt,MODEL

class VisionBridgeSecurity(unittest.TestCase):
 def setUp(self):
  self.t=TemporaryDirectory()
  self.addCleanup(self.t.cleanup)
  self.w=Path(self.t.name);(self.w/'reports').mkdir()
  self.proof=[{'page':p+'.html','width':v,'name':p+'-'+str(v)+'.jpg','sha256':'a'*64}
   for p in ('index','rooms','experiences','explore','contact','engine-smoke') for v in (390,1440)]
  self.man={'project':'andaz-vibe-stay','site_sha256':'b'*64,'qa_receipt_sha256':'c'*64,
     'job_id':'synthetic','screenshots':self.proof}
  self.reviews=[]
  for x in self.proof:
   note='Visible design critique for synthetic fixture. Not a real model output.'
   self.reviews.append({'page':x['page'],'width':x['width'],'name':x['name'],
    'sha256':x['sha256'],'raw_response_sha256':hashlib.sha256(note.encode()).hexdigest(),
    'model_observations':note})
  self.data={'status':'VISION_ADVISORY_COMPLETE','scope_complete':True,
   'model_inference_verified':True,'schema':'shared-art-director-single-v1',
   'model':MODEL,'fixture':{'project_id':'andaz-vibe-stay','site_sha256':'b'*64,
   'qa_receipt_sha256':'c'*64,'job_id':'synthetic'},
   'reviews':self.reviews,'artistic_score':None,'independently_attested':False,
   'release_authorized':False}
  self.receipt=self.w/'candidate.json'
  self.receipt.write_text(json.dumps(self.data))
  self.patch=patch('vision_bridge.manifest',return_value=self.man);self.patch.start()
  self.addCleanup(self.patch.stop)
  self.signature=patch('vision_bridge.verify_advisory_signature',return_value=True)
  self.signature.start();self.addCleanup(self.signature.stop)
 def update(self,**k):
  self.data.update(k);self.receipt.write_text(json.dumps(self.data))
 def test_mock_contract_advisory_no_certification(self):
  result=ingest(self.w,self.receipt)
  self.assertEqual(result['status'],'ADVISORY_INGESTED')
  self.assertEqual(result['artistic_gate'],'BLOCKED')
  self.assertFalse(result['release_authorized'])
  feedback=json.loads((self.w/'reports/gemini-design-feedback.json').read_text())
  self.assertIsNone(feedback['artistic_score'])
  self.assertEqual(len(feedback['feedback']),12)
 def test_public_site_receipt_denied(self):
  self.update(schema='andaz-public-routes-gemini-advisory-v1')
  with self.assertRaisesRegex(ValueError,'MODEL_OR_SCHEMA'):ingest(self.w,self.receipt)
 def test_wrong_build_denied(self):
  self.data['fixture']['site_sha256']='f'*64;self.update()
  with self.assertRaisesRegex(ValueError,'PROVENANCE'):ingest(self.w,self.receipt)
 def test_score_spoof_denied(self):
  self.update(artistic_score=99)
  with self.assertRaisesRegex(ValueError,'CANNOT_GRANT_CERTIFICATION'):ingest(self.w,self.receipt)
 def test_release_spoof_denied(self):
  self.update(release_authorized=True)
  with self.assertRaisesRegex(ValueError,'CANNOT_GRANT_CERTIFICATION'):ingest(self.w,self.receipt)
 def test_fixture_flag_denied(self):
  self.update(model_inference_verified=False)
  with self.assertRaisesRegex(ValueError,'GENUINE_PRIVATE_REVIEW'):ingest(self.w,self.receipt)
 def test_missing_pair_denied(self):
  self.update(reviews=self.reviews[:-1])
  with self.assertRaisesRegex(ValueError,'COVERAGE'):ingest(self.w,self.receipt)
 def test_tampered_raw_response_denied(self):
  self.reviews[0]['model_observations']='tampered';self.update()
  with self.assertRaisesRegex(ValueError,'RAW_MODEL_RESPONSE'):ingest(self.w,self.receipt)
 def test_duplicate_pair_denied(self):
  self.update(reviews=self.reviews[:-1]+[self.reviews[0]])
  with self.assertRaisesRegex(ValueError,'UNTRUSTED_REVIEW_PAIR'):ingest(self.w,self.receipt)
 def test_symlink_receipt_denied(self):
  link=self.w/'linked.json';link.symlink_to(self.receipt)
  with self.assertRaisesRegex(ValueError,'UNSAFE_RECEIPT'):ingest(self.w,link)
 def test_untrusted_receipt_denied_without_artifact(self):
  self.update(status='TEST_FIXTURE_ONLY')
  with self.assertRaisesRegex(ValueError,'GENUINE_PRIVATE_REVIEW'):ingest(self.w,self.receipt)
 def test_feedback_is_stale_if_site_changes(self):
  ingest(self.w,self.receipt)
  with patch('vision_bridge.trusted_inputs',return_value=({'site_sha256':'e'*64,
    'qa_receipt_sha256':'c'*64},None,None)):
   with self.assertRaisesRegex(ValueError,'STALE_FEEDBACK'):correction_prompt(self.w)

class TrustBoundary(unittest.TestCase):
 def test_missing_root_trust_registry_blocks(self):
  from vision_bridge import verify_advisory_signature
  with TemporaryDirectory() as td:
   with self.assertRaisesRegex(ValueError,'TRUST_REGISTRY_MISSING'):
    verify_advisory_signature({},Path(td)/'missing.json')
 def test_non_root_registry_blocks(self):
  from vision_bridge import verify_advisory_signature
  with TemporaryDirectory() as td:
   p=Path(td)/'untrusted.json';p.write_text('{}')
   with self.assertRaisesRegex(ValueError,'REGISTRY_PERMISSIONS_INVALID'):
    verify_advisory_signature({},p)

if __name__=='__main__':unittest.main()
