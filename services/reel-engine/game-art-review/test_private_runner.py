import importlib.util,io,json,os,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
P=Path(__file__).with_name("private_runner.py")
s=importlib.util.spec_from_file_location("review_private",P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
ISSUE=88;RUN="123456789"
def pub(k):return m.enc64(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
def frame(label,private):
 b=io.BytesIO()
 Image.new("RGB",(425,920) if label.endswith("mobile") else (540,304),(40,65,89)).save(b,format="JPEG")
 j=b.getvalue();digest=hashlib.sha256(j).hexdigest()
 client=X25519PrivateKey.generate()
 key=m.deriv(client,pub(private),ISSUE,RUN,"frame:"+label)
 nonce=os.urandom(12)
 encrypted=AESGCM(key).encrypt(nonce,j,m.aad_frame(ISSUE,RUN,label,m.BINDINGS[label],digest))
 return {"issue":ISSUE,"run":RUN,"label":label,"source_png_sha256":m.BINDINGS[label],
   "jpeg_sha256":digest,"client_pub":pub(client),"reply_pub":pub(client),
   "nonce":m.enc64(nonce),"ciphertext":m.enc64(encrypted)}
def ok_review():
 return {"scores":{k:14 for k in m.CATEGORIES},"total_score":70,"comparison":"better",
 "observations":["Visible in-game HUD contrasts against the saturated magenta hall.",
 "Warm lighting extends along the background with a perspective corridor.",
 "Character size appears modest compared with the long central aisle."],
 "defects":[{"category":"readability","visible_evidence":"Small center stage lettering is hard to read.",
             "recommended_fix":"Increase contrast without expanding the text panel.","priority":"P1"}],
 "unverifiable":["Animated physics cannot be evaluated in static screenshots."]}
class TestOwnerReview(unittest.TestCase):
 def test_chunk_reassembly(self):
  comments=[]
  for label in m.BINDINGS:
   data=m.enc64(json.dumps({"label":label}).encode())
   for i,part in enumerate([data[:4],data[4:]]):
    d={"issue":ISSUE,"run":RUN,"label":label,"part":i,"total":2,"data":part}
    comments.append({"user":{"id":m.OWNER_ID},"body":m.FRAME_TAG+json.dumps(d)})
  payloads=m.gather_chunks(ISSUE,RUN,comments)
  self.assertIsNotNone(payloads)
  self.assertEqual(payloads["baseline_mobile"],{"label":"baseline_mobile"})
 def test_no_unapproved_actor(self):
  c=[{"user":{"id":500},"body":m.FRAME_TAG+json.dumps({"issue":ISSUE,"run":RUN,"label":"baseline_mobile","part":0,"total":1,"data":"AAAA"})}]
  self.assertIsNone(m.gather_chunks(ISSUE,RUN,c))
 def test_decrypt_three_images(self):
  server=X25519PrivateKey.generate()
  first=X25519PrivateKey.generate();answer=pub(first)
  envelopes={}
  for k in m.BINDINGS:
   env=frame(k,server)
   env["reply_pub"]=answer
   envelopes[k]=env
  images,refs,reply=m.decrypt_frames(ISSUE,RUN,server,envelopes)
  self.assertEqual(len(refs),3);self.assertEqual(len(images),6);self.assertEqual(reply,answer)
 def test_wrong_png_source_rejected(self):
  server=X25519PrivateKey.generate();envelopes={k:frame(k,server) for k in m.BINDINGS}
  r=next(iter(envelopes));envelopes[r]["source_png_sha256"]="0"*64
  with self.assertRaisesRegex(m.Blocked,"SOURCE_FRAME_PROVENANCE_FAILED"):m.decrypt_frames(ISSUE,RUN,server,envelopes)
 def test_wrong_nonce_rejected(self):
  server=X25519PrivateKey.generate();envelopes={k:frame(k,server) for k in m.BINDINGS}
  first=next(iter(envelopes));envelopes[first]["nonce"]=m.enc64(b"\x00"*12)
  with self.assertRaises(m.Blocked):m.decrypt_frames(ISSUE,RUN,server,envelopes)
 def test_no_score_forgery(self):
  x=ok_review();x["total_score"]=98
  with self.assertRaisesRegex(m.Blocked,"GEMINI_TOTAL_INVALID"):m.validate_review(x)
 def test_valid_score(self):self.assertEqual(m.validate_review(ok_review())["total_score"],70)
 def test_extra_model_field_rejected(self):
  x=ok_review();x["run_this_code"]="rm -rf"
  with self.assertRaises(m.Blocked):m.validate_review(x)
 def test_invalid_priority_rejected(self):
  x=ok_review();x["defects"][0]["priority"]="P100"
  with self.assertRaises(m.Blocked):m.validate_review(x)
 def test_response_encryption(self):
  report={"score":70,"source":"game"}
  reply=X25519PrivateKey.generate()
  captured=[]
  with patch.object(m,"comment",side_effect=lambda issue,text:captured.append((issue,text))):
   m.send_encrypted_result(ISSUE,RUN,pub(reply),report)
  self.assertEqual(len(captured),1)
  env=json.loads(captured[0][1][len(m.RESULT_TAG):])
  key=m.deriv(reply,env["runner_pub"],ISSUE,RUN,"review-result")
  aad=f"shaadi-m71-result-v1|{ISSUE}|{RUN}".encode()
  plaintext=AESGCM(key).decrypt(m.dec64(env["nonce"]),m.dec64(env["ciphertext"]),aad)
  self.assertEqual(json.loads(plaintext),report)
 def test_wrong_github_owner(self):
  fake={"issue":{"number":42,"title":"[SHAADI-M71-GEMINI] 20261111-abcdef012345","user":{"id":500}}}
  import tempfile
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"event.json";p.write_text(json.dumps(fake))
   with patch.dict(os.environ,{"GITHUB_EVENT_PATH":str(p),"GITHUB_REPOSITORY":m.REPO,
                    "GITHUB_ACTOR":m.OWNER,"GITHUB_RUN_ID":RUN,
                    "GEMINI_PROJECT_FREE_TIER_VERIFIED":"true","GEMINI_INFERENCE_OWNER_APPROVED":"true"}):
    with self.assertRaisesRegex(m.Blocked,"OWNER_ONLY_ISSUE_GATE"):m.verified_event()
if __name__=="__main__":unittest.main()
