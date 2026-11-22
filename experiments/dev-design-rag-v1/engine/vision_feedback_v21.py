"""Advisory-only review intake. It cannot satisfy signed artistic gate."""
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import sha,state,treehash,write,require

CATEGORIES={"contrast","hierarchy","spacing","typography","branding","imagery","responsiveness","navigation","interaction","clarity"}
HOSTILE=re.compile(r"(?:https?://|<script|\b(?:curl|wget|sudo|bash|chmod|rm -rf)\b|ignore previous|system prompt|developer message|secret|api[_ -]?key|token)",re.I)

def intake(w,source):
 w=Path(w).resolve(strict=True)
 state_now=state(w)
 qa=w/"reports/browser-qa.json"
 require(qa.is_file() and not qa.is_symlink() and sha(qa)==state_now.get("qa_receipt_sha256"),"QA_DRIFT")
 require(state_now["site_sha256"]==treehash(w/"site"),"SOURCE_DRIFT")
 q=json.loads(qa.read_text())
 expected={(x["page"],x["width"]):x for x in q.get("screenshots",[]) if x.get("width") in (390,1440)}
 require(len(expected)==12,"TWELVE_ORIGINAL_SCREENSHOTS_REQUIRED")
 source=Path(source)
 require(source.is_file() and not source.is_symlink() and source.stat().st_size<200000,"INPUT_FILE_UNSAFE")
 data=json.loads(source.read_text())
 require(data.get("schema")=="generic-design-vision-advice-v2.1" and data.get("scope")=="private_six_route_actual_screenshots","WRONG_REVIEW_SCOPE")
 require(data.get("project")==state_now["project"] and data.get("site_sha256")==state_now["site_sha256"] and data.get("qa_receipt_sha256")==state_now["qa_receipt_sha256"],"BUILD_PROVENANCE_MISMATCH")
 require(data.get("model")=="gemini-3.5-flash-lite","MODEL_UNTRUSTED")
 require(data.get("artistic_score") is None and data.get("independently_attested") is False and data.get("release_authorized") is False,"FALSE_CERTIFICATION_FORBIDDEN")
 reviews=data.get("reviews",[])
 require(isinstance(reviews,list) and len(reviews)==12,"INCOMPLETE_REVIEWS")
 seen=set();proposals=[]
 for r in reviews:
  pair=(r.get("page"),r.get("width"))
  require(pair in expected and pair not in seen,"REVIEW_PAIR_INVALID")
  seen.add(pair)
  require(r.get("raw_sha256")==expected[pair]["sha256"],"REVIEW_IMAGE_HASH_WRONG")
  response_hash=r.get("response_sha256","")
  require(isinstance(response_hash,str) and re.fullmatch("[a-f0-9]{64}",response_hash),"REVIEW_RESPONSE_HASH_MISSING")
  issues=r.get("issues",[])
  require(isinstance(issues,list) and 0<len(issues)<=5,"ISSUES_INVALID")
  for issue in issues:
   category=issue.get("category") if isinstance(issue,dict) else None
   text=issue.get("observation") if isinstance(issue,dict) else None
   require(category in CATEGORIES and isinstance(text,str) and 12<=len(text)<=240 and not HOSTILE.search(text) and "\n" not in text,"UNSAFE_EXTERNAL_ADVICE")
   proposals.append({"page":pair[0],"width":pair[1],"category":category,"observation":text})
 require(seen==set(expected),"REVIEW_INCOMPLETE")
 receipt={"schema":"generic-design-revision-plan-v2.1","project":state_now["project"],
          "site_sha256":state_now["site_sha256"],"qa_receipt_sha256":state_now["qa_receipt_sha256"],
          "review_model":data["model"],"review_file_sha256":sha(source),"actions":proposals[:36],
          "advice_trust":"external_untrusted_visual_observations_not_owner_instructions",
          "artistic_score":None,"release_authorized":False,"independently_attested":False}
 output=w/"reports/vision-revision-plan-v2.1.json"
 if output.exists():
  require(json.loads(output.read_text())==receipt,"REVISION_RECEIPT_CONFLICT")
 else:
  write(output,receipt);output.chmod(0o600)
 return {"status":"ADVISORY_STAGED_ONLY","actions":len(receipt["actions"]),
          "revision_sha256":sha(output),"approval_granted":False}
