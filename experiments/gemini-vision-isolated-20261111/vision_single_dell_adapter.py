#!/usr/bin/env python3
"""Isolated, one-image-at-a-time Gemini advisory. No signing or artistic scoring."""
import argparse,base64,hashlib,io,json,os,pathlib,socket,sys,time,urllib.error,urllib.request
from PIL import Image
MODEL="gemini-3.5-flash-lite"
API="https://generativelanguage.googleapis.com/v1beta"
WIDTHS=(390,1440)
PAGES=("index.html","rooms.html","experiences.html","explore.html","contact.html","engine-smoke.html")
def digest(b): return hashlib.sha256(b).hexdigest()
def canonical(obj): return json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
def insist(ok,msg):
    if not ok: raise ValueError(msg)
def read_json(p): return json.loads(pathlib.Path(p).read_text())
def site_treehash(root):
    h=hashlib.sha256()
    for f in sorted(root.rglob("*")):
        insist(not f.is_symlink(),"SITE_SYMLINK_FORBIDDEN")
        if f.is_file() and ".git" not in f.parts:
            h.update(f.relative_to(root).as_posix().encode()+b"\0")
            h.update(bytes.fromhex(digest(f.read_bytes())))
    return h.hexdigest()
def fixture_inputs(workspace,packet):
    w=pathlib.Path(workspace)
    insist(w.is_dir() and not w.is_symlink(),"UNSAFE_WORKSPACE")
    w=w.resolve(strict=True)
    state=read_json(w/"engine-state.json"); qa_path=w/"reports/browser-qa.json"; qa=read_json(qa_path)
    insist(state["project"]=="andaz-vibe-stay" and state["owner_release_authorized"] is False,"UNSAFE_PROJECT_OR_RELEASE_STATE")
    insist(qa["pass"] is True and qa["source_hash"]==state["site_sha256"],"INVALID_BROWSER_QA")
    insist(site_treehash(w/"site")==state["site_sha256"],"SITE_HASH_DRIFT")
    insist(digest(qa_path.read_bytes())==state["qa_receipt_sha256"],"QA_RECEIPT_DRIFT")
    p=pathlib.Path(packet)
    insist(p.is_file() and not p.is_symlink(),"UNSAFE_RAG_PACKET")
    p=p.resolve(strict=True); brand=read_json(p)
    insist(brand["project_id"]=="andaz-vibe-stay" and isinstance(brand["design_rules"],list) and brand["design_rules"],"CROSS_PROJECT_RAG")
    entries={(x["page"],x["width"]):x for x in qa["screenshots"] if x["width"] in WIDTHS}
    insist(len(entries)==12 and set(entries)=={(page,v) for page in PAGES for v in WIDTHS},"INCOMPLETE_SCREENSHOT_MATRIX")
    safe=[]
    for page,width in sorted(entries):
        x=entries[(page,width)]; name=x["name"]
        insist(pathlib.Path(name).name==name and name not in (".",".."),"UNSAFE_SCREENSHOT_NAME")
        f=w/"evidence/screenshots"/name
        insist(f.is_file() and not f.is_symlink() and digest(f.read_bytes())==x["sha256"],"SCREENSHOT_HASH_DRIFT")
        safe.append({"page":page,"width":width,"sha256":x["sha256"],"path":str(f),"name":name})
    return {"project_id":brand["project_id"],"rag_sha256":digest(p.read_bytes()),
            "site_sha256":state["site_sha256"],"qa_receipt_sha256":state["qa_receipt_sha256"],
            "job_id":state.get("job_id"),"screenshots":safe,"design_rules":brand["design_rules"]}
def compress(path):
    f=pathlib.Path(path)
    insist(f.is_file() and not f.is_symlink(),"UNSAFE_IMAGE_PATH")
    with Image.open(f) as im:
        im=im.convert("RGB");im.thumbnail((384,512))
        out=io.BytesIO();im.save(out,"JPEG",quality=49,optimize=True)
    raw=out.getvalue();insist(500<len(raw)<=360000,"IMAGE_BODY_OUT_OF_RANGE")
    return {"inline_data":{"mime_type":"image/jpeg","data":base64.b64encode(raw).decode()}}
def request(path,key,body=None,transport=None):
    insist(path=="/models?pageSize=100" or path=="/models/"+MODEL+":generateContent","UNAPPROVED_ENDPOINT")
    if transport is not None: return transport(path,body)
    insist(bool(key),"GITHUB_GEMINI_SECRET_UNAVAILABLE")
    headers={"x-goog-api-key":key,"Accept":"application/json"}
    raw=None if body is None else canonical(body)
    if raw is not None: headers["Content-Type"]="application/json"
    req=urllib.request.Request(API+path,headers=headers,data=raw,method="GET" if raw is None else "POST")
    for i in range(2):
        try:
            with urllib.request.urlopen(req,timeout=38) as response:
                return json.loads(response.read(1000000))
        except urllib.error.HTTPError as exc:
            if exc.code==503 and i==0:time.sleep(3);continue
            raise RuntimeError("GEMINI_HTTP_"+str(exc.code)) from None
        except (socket.timeout,TimeoutError):raise RuntimeError("GEMINI_TIMEOUT") from None
        except urllib.error.URLError:raise RuntimeError("GEMINI_NETWORK_UNAVAILABLE") from None
    raise RuntimeError("GEMINI_RETRY_EXHAUSTED")
def run(workspace,packet,transport=None,key=None):
    ctx=fixture_inputs(workspace,packet)
    key=key if key is not None else os.environ.get("GEMINI_API_KEY","")
    if transport is None: insist(bool(key),"GEMINI_KEY_NOT_IN_DELL_BOUNDARY")
    meta=request("/models?pageSize=100",key,transport=transport)
    models=meta.get("models",[])
    insist(any(m.get("name")=="models/"+MODEL and "generateContent" in m.get("supportedGenerationMethods",[]) for m in models),
           "MODEL_NOT_AUTHENTICATED_ALLOWLIST")
    result={"schema":"shared-art-director-single-v1","model":MODEL,
            "fixture":{"project_id":ctx["project_id"],"rag_sha256":ctx["rag_sha256"],
                       "site_sha256":ctx["site_sha256"],"qa_receipt_sha256":ctx["qa_receipt_sha256"],
                       "job_id":ctx["job_id"]},
            "reviews":[],"scope_complete":False,"model_inference_verified":False,
            "artistic_score":None,"independently_attested":False,"release_authorized":False}
    for shot in ctx["screenshots"]:
        prompt=("Review this SINGLE actual browser screenshot for Andaz Vibe Stay, route "+shot["page"]+
                ", viewport "+str(shot["width"])+"px. Give three concrete visible design improvements and one strength. "+
                "Pay attention to hierarchy, spacing, readability, authentic hospitality tone and brand constraints: "+
                "; ".join(ctx["design_rules"])[:900]+". Only report what you see. No numeric scores or approvals.")
        body={"contents":[{"parts":[{"text":prompt},compress(shot["path"])]}],
              "generationConfig":{"temperature":0,"maxOutputTokens":650}}
        response=request("/models/"+MODEL+":generateContent",key,body,transport)
        first=(response.get("candidates") or [{}])[0]
        raw="".join(p.get("text","") for p in first.get("content",{}).get("parts",[]) if isinstance(p,dict))
        insist(len(raw.strip())>=70,"INSUFFICIENT_MODEL_REVIEW_"+shot["page"]+"_"+str(shot["width"]))
        result["reviews"].append({"page":shot["page"],"width":shot["width"],"name":shot["name"],
                                 "sha256":shot["sha256"],"raw_response_sha256":digest(raw.encode()),
                                 "model_observations":raw[:4000],
                                 "finish_reason":str(first.get("finishReason","UNKNOWN"))[:32]})
    result["scope_complete"]=len(result["reviews"])==12
    result["model_inference_verified"]=transport is None
    result["status"]="VISION_ADVISORY_COMPLETE" if transport is None else "TEST_FIXTURE_ONLY"
    result["receipt_sha256"]=digest(canonical({k:v for k,v in result.items() if k!="receipt_sha256"}))
    return result
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",required=True);ap.add_argument("--packet",required=True);ap.add_argument("--output",required=True)
    a=ap.parse_args();p=pathlib.Path(a.output);p.parent.mkdir(parents=True,exist_ok=True)
    try: r=run(a.workspace,a.packet)
    except Exception as exc:
        r={"status":"BLOCKED","reason":str(exc)[:120],"scope_complete":False,
           "artistic_score":None,"independently_attested":False,"release_authorized":False}
    flags=os.O_CREAT|os.O_WRONLY|os.O_TRUNC|os.O_NOFOLLOW
    fd=os.open(p,flags,0o600)
    with os.fdopen(fd,"w") as f:json.dump(r,f,indent=2);f.write("\n")
    print(json.dumps({k:r[k] for k in ("status","scope_complete","artistic_score","release_authorized")}))
    return 0 if r["status"]=="VISION_ADVISORY_COMPLETE" else 4
if __name__=="__main__":sys.exit(main())
