"""Synthetic cryptographic protocol tests; never artistic certification."""
import base64,copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
sys.path.insert(0,str(Path(__file__).resolve().parent))
import attestation
from core import STAGES,gate,sha,state,treehash,verify_review,write

class ReceiptSecurity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.w=Path(self.tmp.name)
        (self.w/'site').mkdir()
        (self.w/'evidence/screenshots').mkdir(parents=True)
        (self.w/'reports').mkdir()
        self.pages=['index.html','other.html']
        for name in self.pages:
            (self.w/'site'/name).write_text('<!doctype html><title>Fixture</title><p>Test-only</p>')
        shots=[]
        for page in self.pages:
            for width in (320,390,768,1440):
                name=page.replace('.html','')+'-'+str(width)+'.jpg'
                (self.w/'evidence/screenshots'/name).write_bytes(b'SYNTHETIC-NOT-A-REAL-SCREENSHOT-'+name.encode())
                shots.append({'page':page,'width':width,'name':name,
                  'sha256':sha(self.w/'evidence/screenshots'/name)})
        qa={'pass':True,'source_hash':treehash(self.w/'site'),'screenshots':shots,'rows':[{}]*8}
        write(self.w/'reports/browser-qa.json',qa)
        st={'version':'2.0.0','execution_mode':'autonomous_engine_required',
            'stage_status':{k:'PASS' for k in STAGES},'job_id':'unit-job-A','project':'test-project-alpha',
            'site_sha256':qa['source_hash'],'qa_receipt_sha256':sha(self.w/'reports/browser-qa.json'),
            'independent_verdict':None,'artistic_score':None,'manual_only_build':False}
        write(self.w/'engine-state.json',st)
        self.priv=Ed25519PrivateKey.generate()
        public=self.priv.public_key().public_bytes(serialization.Encoding.Raw,
                                                     serialization.PublicFormat.Raw)
        self.policy={'test-key':{'public_key':base64.b64encode(public).decode(),
          'reviewer_id':'separate-test-reviewer','models':['qwen3-vl:2b-instruct'],'enabled':True}}
        self.raw=[{'page':page,'raw':json.dumps({'score':96,'verdict':'APPROVE',
              'issues':['Minor spacing needs checking'],
              'visual_evidence':'Both header and CTA are visible in this fixture.'})}
             for page in self.pages]
        self.receipt={'signature_scheme':'Ed25519','key_id':'test-key',
          'reviewer_kind':'independent_service','reviewer_id':'separate-test-reviewer',
          'model':'qwen3-vl:2b-instruct','job_id':'unit-job-A','project_id':'test-project-alpha',
          'site_sha256':st['site_sha256'],'qa_receipt_sha256':st['qa_receipt_sha256'],
          'assessment_method':'actual_screenshots','evidence_source':'independent_visual_model',
          'signed_or_verifiable_receipt':True,'score':96,'verdict':'APPROVE',
          'issues':['Minor spacing needs checking'],'scope_complete':True,
          'screenshots':shots,'reviewed_screenshots':[x for x in shots if x['width'] in (390,1440)],
          'raw_model_outputs':self.raw,
          'model_response_sha256':hashlib.sha256('\n'.join(x['raw'] for x in self.raw).encode()).hexdigest()}
        self.receiptfile=self.w/'reports/receipt-test.json'
    def save_signed(self,receipt=None):
        r=copy.deepcopy(receipt if receipt is not None else self.receipt)
        r.pop('signature',None)
        r['signature']=base64.b64encode(self.priv.sign(attestation.canonical(r))).decode()
        write(self.receiptfile,r)
    def verify(self):
        with patch.object(attestation,'_trust',return_value=self.policy):
            return verify_review(self.w,self.receiptfile)
    def must_reject(self,keyword=None):
        with self.assertRaises(ValueError) as context:self.verify()
        if keyword:self.assertIn(keyword,str(context.exception))
    def test_01_valid_test_only_signature(self):
        self.save_signed()
        self.assertEqual(self.verify()['score'],96)
        self.assertIn('LIGHTHOUSE_ROUTE_COVERAGE_MISSING',gate(self.w)['missing'])
    def test_02_unsigned_forgery(self):
        self.save_signed()
        r=json.loads(self.receiptfile.read_text());r['score']=100
        write(self.receiptfile,r)
        self.must_reject('REVIEW_SIGNATURE_INVALID')
    def test_03_wrong_source_signed(self):
        r=copy.deepcopy(self.receipt);r['site_sha256']='0'*64;self.save_signed(r)
        self.must_reject('REVIEW_BUILD_MISMATCH')
    def test_04_wrong_screenshot_signed(self):
        r=copy.deepcopy(self.receipt);r['screenshots'][0]['sha256']='f'*64
        self.save_signed(r);self.must_reject('REVIEW_SCREENSHOT_RECEIPT_MISMATCH')
    def test_05_missing_reviewed_page(self):
        r=copy.deepcopy(self.receipt);r['reviewed_screenshots']=[x for x in r['reviewed_screenshots'] if x['page']=='index.html']
        self.save_signed(r);self.must_reject('REVIEW_FULL_SCREEN_COVERAGE_MISSING')
    def test_06_fake_95_with_raw_78(self):
        r=copy.deepcopy(self.receipt)
        raw=json.dumps({'score':78,'issues':['Actual visible defect'],'visual_evidence':'The content is clipped on mobile.'})
        r['raw_model_outputs'][0]['raw']=raw
        r['model_response_sha256']=hashlib.sha256('\n'.join(x['raw'] for x in r['raw_model_outputs']).encode()).hexdigest()
        self.save_signed(r);self.must_reject('REVIEW_SCORE_NOT_RAW_DERIVED')
    def test_07_replay_other_job(self):
        r=copy.deepcopy(self.receipt);r['job_id']='different-job';self.save_signed(r)
        self.must_reject('REVIEW_JOB_BINDING_MISMATCH')
    def test_08_cross_project_signed_replay_rejected(self):
        r=copy.deepcopy(self.receipt);r['project_id']='test-project-beta';self.save_signed(r)
        self.must_reject('REVIEW_PROJECT_BINDING_MISMATCH')
    def test_08_malicious_identity(self):
        r=copy.deepcopy(self.receipt);r['reviewer_id']='site-builder';self.save_signed(r)
        self.must_reject('UNTRUSTED_REVIEWER_IDENTITY')
    def test_09_untrusted_signer(self):
        self.save_signed()
        with patch.object(attestation,'_trust',return_value={}):
            with self.assertRaisesRegex(ValueError,'UNTRUSTED_REVIEWER_IDENTITY'):
                verify_review(self.w,self.receiptfile)
    def test_10_missing_trust_root_protected(self):
        self.save_signed()
        with patch.object(attestation,'TRUST_FILE',self.w/'missing-policy.json'):
            with self.assertRaisesRegex(ValueError,'REVIEW_TRUST_ROOT_'):
                verify_review(self.w,self.receiptfile)
    def test_11_symlink_in_site_rejected(self):
        (self.w/'site'/'bad.html').symlink_to('/etc/hostname')
        self.assertIn('UNSAFE_OR_UNREADABLE_SITE',gate(self.w)['missing'])
    def test_12_missing_lighthouse_fail_closed(self):
        self.save_signed();self.verify()
        self.assertEqual(gate(self.w)['status'],'BLOCKED')
        self.assertIn('OWNER_RELEASE_AUTHORITY_EXTERNAL_ONLY',gate(self.w,'release')['missing'])
if __name__=='__main__':unittest.main(verbosity=2)
