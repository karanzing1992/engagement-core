"""Synthetic contract tests; a valid sealed package is NOT a Gemini review."""
import base64, json, os, pathlib, sys, tempfile, unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import vision_bridge_v21 as bridge

FIXTURE=pathlib.Path.home()/".local/share/dev-design-rag-v1/certification/uiux-v2-andaz-fixture-20261110"

class PrivateBridgeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  cls.key=X25519PrivateKey.generate()
  cls.private=base64.b64encode(cls.key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode()
  cls.public=base64.b64encode(cls.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
  cls.source=json.loads((FIXTURE/"engine-state.json").read_text())
  cls.path=pathlib.Path(cls.tmp.name)/"test-only-12-capsule.enc"
  cls.receipt=bridge.seal(FIXTURE,cls.public,cls.path)
  cls.bytes=cls.path.read_bytes()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def open(self,*args,**kw):
  return bridge.open_capsule(kw.get("data",self.bytes),kw.get("private",self.private),
      *(args if args else (self.source["project"],self.source["site_sha256"],self.source["qa_receipt_sha256"])))
 def test_01_all_six_actual_routes(self):
  result=self.open()
  self.assertEqual(result["manifest"]["count"],12)
  self.assertEqual(len(result["images"]),12)
  self.assertEqual(len(result["manifest"]["pages"]),6)
  self.assertIn("engine-smoke.html",result["manifest"]["pages"])
  self.assertIsNone(result["manifest"]["artistic_score"])
  self.assertFalse(result["manifest"]["production_release_allowed"])
 def test_02_sealed_file_acl(self):
  self.assertEqual(self.path.stat().st_mode&0o777,0o600)
  self.assertFalse(self.receipt["release_authorized"])
  self.assertEqual(self.receipt["transfer"],"NOT_CONFIGURED")
 def test_03_wrong_project_denied(self):
  with self.assertRaisesRegex(ValueError,"PROJECT_MISMATCH"):
   self.open("other-project",self.source["site_sha256"],self.source["qa_receipt_sha256"])
 def test_04_wrong_site_denied(self):
  with self.assertRaisesRegex(ValueError,"SITE_MISMATCH"):
   self.open(self.source["project"],"0"*64,self.source["qa_receipt_sha256"])
 def test_05_wrong_qa_denied(self):
  with self.assertRaisesRegex(ValueError,"QA_MISMATCH"):
   self.open(self.source["project"],self.source["site_sha256"],"0"*64)
 def test_06_wrong_encryption_key_denied(self):
  another=base64.b64encode(X25519PrivateKey.generate().private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())).decode()
  with self.assertRaises(Exception):self.open(private=another)
 def test_07_ciphertext_tamper_denied(self):
  data=json.loads(self.bytes);c=data["ciphertext"]
  data["ciphertext"]=("A" if c[0]!="A" else "B")+c[1:]
  with self.assertRaisesRegex(ValueError,"CAPSULE_HASH_MISMATCH"):self.open(data=json.dumps(data).encode())
 def test_08_source_manifest_pinned(self):
  obj=self.open();self.assertEqual(obj["manifest"]["site_sha256"],self.source["site_sha256"])
  self.assertEqual(obj["manifest"]["qa_receipt_sha256"],self.source["qa_receipt_sha256"])
 def test_09_output_collision_denied(self):
  with self.assertRaisesRegex(ValueError,"OUTPUT_ALREADY_EXISTS"):bridge.seal(FIXTURE,self.public,self.path)
 def test_10_public_certificate_claim_denied(self):
  result=self.open()
  self.assertFalse(result["manifest"]["independently_attested"])
  self.assertFalse(self.receipt["release_authorized"])

if __name__=="__main__":unittest.main(verbosity=2)
