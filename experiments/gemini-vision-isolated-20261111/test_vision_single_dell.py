import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import vision_single as v
ROOT=pathlib.Path('/var/lib/generic-linux-automator-exec/.local/share/dev-design-rag-v1/certification/uiux-v2-andaz-fixture-20261110')
PACKET=pathlib.Path(__file__).resolve().parents[1]/'evidence/brand-packet.json'
META={"models":[{"name":"models/gemini-3.5-flash-lite","supportedGenerationMethods":["generateContent"]}]}
ANSWER={"candidates":[{"content":{"parts":[{"text":"This screenshot shows coherent hotel hierarchy but some cramped body copy. Increase whitespace, improve contrast, and clarify primary call to action. The layout uses consistent title sizing."}]},"finishReason":"STOP"}]}
class SingleTests(unittest.TestCase):
 def test_12_actual_hash_bound_screens(self):
  x=v.fixture_inputs(ROOT,PACKET)
  self.assertEqual(len(x["screenshots"]),12)
  self.assertEqual(len(set((s["page"],s["width"]) for s in x["screenshots"])),12)
  self.assertEqual(set(s["page"] for s in x["screenshots"]),set(v.PAGES))
 def test_real_single_image_mocked_is_only_test_fixture(self):
  calls=[]
  def mock(path,body):
   if body is not None:
    self.assertEqual(len([p for p in body["contents"][0]["parts"] if "inline_data" in p]),1)
    calls.append(path)
   return META if body is None else ANSWER
  r=v.run(ROOT,PACKET,transport=mock)
  self.assertEqual(len(calls),12)
  self.assertEqual(len(r["reviews"]),12)
  self.assertEqual(r["status"],"TEST_FIXTURE_ONLY")
  self.assertFalse(r["model_inference_verified"])
  self.assertIsNone(r["artistic_score"])
  self.assertFalse(r["release_authorized"])
  self.assertFalse(r["independently_attested"])
 def test_model_metadata_deny(self):
  with self.assertRaisesRegex(ValueError,"MODEL_NOT_AUTHENTICATED"):
   v.run(ROOT,PACKET,transport=lambda path,body: {"models":[]} if body is None else ANSWER)
 def test_provider_insufficient_response_deny(self):
  with self.assertRaisesRegex(ValueError,"INSUFFICIENT_MODEL_REVIEW"):
   v.run(ROOT,PACKET,transport=lambda path,body:META if body is None else {"candidates":[{"content":{"parts":[{"text":"bad"}]}}]})
 def test_bad_project_rag_deny(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/"rag.json"
   b=json.loads(PACKET.read_text());b["project_id"]="another-project";p.write_text(json.dumps(b))
   with self.assertRaisesRegex(ValueError,"CROSS_PROJECT_RAG"):v.fixture_inputs(ROOT,p)
 def test_empty_rag_rules_deny(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/"rag.json"
   b=json.loads(PACKET.read_text());b["design_rules"]=[];p.write_text(json.dumps(b))
   with self.assertRaisesRegex(ValueError,"CROSS_PROJECT_RAG"):v.fixture_inputs(ROOT,p)
 def test_no_key_deny_without_network(self):
  with patch.dict("os.environ",{"GEMINI_API_KEY":""}):
   with self.assertRaisesRegex(ValueError,"GEMINI_KEY_NOT_IN_DELL_BOUNDARY"):v.run(ROOT,PACKET)
 def test_bad_endpoint_deny(self):
  with self.assertRaisesRegex(ValueError,"UNAPPROVED_ENDPOINT"):v.request("/models/other:generateContent","x",transport=lambda a,b:{})
 def test_malformed_image_deny(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/"bad.jpg";p.write_bytes(b"nonsense")
   with self.assertRaises(Exception):v.compress(p)
 def test_symlink_image_deny(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/"real.jpg";p.write_bytes(b"tiny");link=pathlib.Path(t)/"link.jpg";link.symlink_to(p)
   with self.assertRaisesRegex(ValueError,"UNSAFE_IMAGE_PATH"):v.compress(link)
 def test_http_503_fails_closed(self):
  from urllib.error import HTTPError
  def transport(path,body):raise HTTPError("x",503,"",{},None)
  with self.assertRaises(HTTPError):v.run(ROOT,PACKET,transport=transport)
 def test_response_cannot_insert_release(self):
  changed=copy.deepcopy(ANSWER)
  changed["release_authorized"]=True
  r=v.run(ROOT,PACKET,transport=lambda path,body:META if body is None else changed)
  self.assertFalse(r["release_authorized"]);self.assertIsNone(r["artistic_score"])
if __name__=="__main__":unittest.main()
