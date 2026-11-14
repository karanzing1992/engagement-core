#!/usr/bin/env python3
"""Private screenshot handoff and fail-closed Gemini result validation (engine V2.1).

No public URL, upload, workflow dispatch or credential access. The trusted runner
must execute ON DELL (or a separately approved encrypted private transport).
Advisory review cannot certify or update independent_artistic_review.
"""
import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path

from core import workspace,state,treehash,sha,write,require
from version import ENGINE_VERSION,VISION_BRIDGE_PROTOCOL
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

VIEWPORTS=(390,1440)
ALLOWED_STATUS="VISION_ADVISORY_COMPLETE"
MODEL="gemini-3.5-flash-lite"

def trusted_inputs(w):
    s=state(w);qpath=w/"reports/browser-qa.json"
    require(qpath.is_file() and not qpath.is_symlink(),"QA_MISSING_OR_SYMLINK")
    require(sha(qpath)==s.get("qa_receipt_sha256"),"QA_HASH_DRIFT")
    require(treehash(w/"site")==s.get("site_sha256"),"SOURCE_HASH_DRIFT")
    q=json.loads(qpath.read_text())
    require(q.get("pass") is True and q.get("source_hash")==s["site_sha256"],"QA_UNTRUSTED")
    shots=[x for x in q["screenshots"] if x["width"] in VIEWPORTS]
    pages={x["page"] for x in shots}
    require(len(pages)==6 and len(shots)==12 and
      {(x["page"],x["width"]) for x in shots}=={(p,v) for p in pages for v in VIEWPORTS},
      "SIX_ROUTE_PAIR_COVERAGE_REQUIRED")
    proof=[]
    for x in sorted(shots,key=lambda x:(x["page"],x["width"])):
        name=x["name"]
        require(isinstance(name,str) and Path(name).name==name,"UNSAFE_IMAGE_NAME")
        image=w/"evidence/screenshots"/name
        require(image.is_file() and not image.is_symlink() and sha(image)==x["sha256"],
                "IMAGE_HASH_DRIFT")
        proof.append({"page":x["page"],"width":x["width"],"name":name,
                      "sha256":x["sha256"]})
    return s,q,proof

def manifest(w):
    s,_,proof=trusted_inputs(w)
    return {"schema":"design-rag-2.1-private-vision-bridge",
      "version":VISION_BRIDGE_PROTOCOL,"engine_version":ENGINE_VERSION,
      "project":s["project"],"job_id":s.get("job_id"),
      "site_sha256":s["site_sha256"],
      "qa_receipt_sha256":s["qa_receipt_sha256"],
      "screenshots":proof,"transport":"trusted-local-runner-only",
      "scope":"six-isolated-routes-two-viewports",
      "model":MODEL,"release_authorized":False,"independent_artistic_review":"PENDING"}

def prepare(w):
    m=manifest(w)
    path=w/"reports/private-vision-manifest.json"
    require(not path.is_symlink(),"UNSAFE_MANIFEST")
    write(path,m)
    path.chmod(0o600)
    return {"status":"PREPARED_LOCAL_ONLY","manifest_sha256":sha(path),
            "required_screenshots":12,"runner":"NOT_AUTO_AUTHORIZED",
            "review_score":None,"release_authorized":False}

TRUST_REGISTRY=Path("/etc/moksha-uiux-v2/trusted-vision-advisories.json")

def verify_advisory_signature(payload,registry=TRUST_REGISTRY):
    """Fail closed until owner provisions a ROOT-OWNED, allowlisted Ed25519 key."""
    require(registry.is_file() and not registry.is_symlink(),
            "VISION_SIGNER_TRUST_REGISTRY_MISSING")
    stat=registry.stat()
    require(stat.st_uid==0 and (stat.st_mode & 0o022)==0,
            "VISION_SIGNER_REGISTRY_PERMISSIONS_INVALID")
    roster=json.loads(registry.read_text())
    proof=payload.get("trusted_runner_attestation")
    require(isinstance(proof,dict),"VISION_SIGNER_PROOF_MISSING")
    kid=proof.get("key_id")
    pub=roster.get("reviewers",{}).get(kid) if isinstance(kid,str) else None
    require(isinstance(pub,str) and pub,"VISION_SIGNER_NOT_TRUSTED")
    require(proof.get("signature_scheme")=="ed25519" and
            proof.get("scope")=="dell-local-private-12",
            "VISION_SIGNER_SCOPE_INVALID")
    signed={k:v for k,v in payload.items() if k!="trusted_runner_attestation"}
    canonical=json.dumps(signed,sort_keys=True,separators=(",",":")).encode()
    require(hashlib.sha256(canonical).hexdigest()==proof.get("payload_sha256"),
            "VISION_SIGNED_PAYLOAD_DRIFT")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            base64.b64decode(proof["signature"],validate=True),canonical)
    except (ValueError,KeyError,binascii.Error,TypeError):
        raise ValueError("VISION_SIGNER_SIGNATURE_INVALID") from None
    return True

def ingest(w,receipt):
    expected=manifest(w)
    require(receipt.is_file() and not receipt.is_symlink(),"UNSAFE_RECEIPT")
    data=json.loads(receipt.read_text())
    verify_advisory_signature(data)
    require(data.get("status")==ALLOWED_STATUS and
            data.get("scope_complete") is True and
            data.get("model_inference_verified") is True,
            "GENUINE_PRIVATE_REVIEW_REQUIRED")
    require(data.get("model")==MODEL and
            data.get("schema")=="shared-art-director-single-v1",
            "REVIEW_MODEL_OR_SCHEMA_INVALID")
    fx=data.get("fixture",{})
    for key,left in (("project_id",expected["project"]),
                     ("site_sha256",expected["site_sha256"]),
                     ("qa_receipt_sha256",expected["qa_receipt_sha256"]),
                     ("job_id",expected["job_id"])):
        require(fx.get(key)==left,"REVIEW_PROVENANCE_MISMATCH:"+key)
    expected_pairs={(x["page"],x["width"]):x for x in expected["screenshots"]}
    reviews=data.get("reviews",[])
    require(len(reviews)==12,"REVIEW_COVERAGE_INCOMPLETE")
    observed=set()
    for rec in reviews:
        k=rec.get("page"),rec.get("width")
        require(k in expected_pairs and k not in observed,"UNTRUSTED_REVIEW_PAIR")
        observed.add(k);x=expected_pairs[k]
        require(rec.get("sha256")==x["sha256"] and
          rec.get("name")==x["name"],"REVIEW_IMAGE_SHA_MISMATCH")
        require(isinstance(rec.get("raw_response_sha256"),str) and
          len(rec["raw_response_sha256"])==64 and
          hashlib.sha256(str(rec.get("model_observations","")).encode()).hexdigest()==rec["raw_response_sha256"],
          "RAW_MODEL_RESPONSE_UNVERIFIED")
    require(not data.get("release_authorized") and
            data.get("independently_attested") is False and
            data.get("artistic_score") is None,
            "ADVISORY_CANNOT_GRANT_CERTIFICATION")
    input_record={"schema":"design-rag-2.1-private-review-feedback",
      "source_site_sha256":expected["site_sha256"],
      "source_qa_sha256":expected["qa_receipt_sha256"],
      "model":MODEL,"reviewed":12,
      "feedback":[{"route":r["page"],"width":r["width"],
                   "notes":r["model_observations"][:4000]} for r in reviews],
      "artistic_score":None,"independently_attested":False,
      "release_authorized":False}
    out=w/"reports/gemini-design-feedback.json"
    require(not out.is_symlink(),"UNSAFE_OUTPUT_PATH")
    write(out,input_record);out.chmod(0o600)
    return {"status":"ADVISORY_INGESTED","feedback_sha256":sha(out),
            "reviews":12,"design_correction_ready":True,
            "artistic_gate":"BLOCKED","release_authorized":False}

def correction_prompt(w,max_chars=2500):
    f=w/"reports/gemini-design-feedback.json"
    require(f.is_file() and not f.is_symlink(),"NO_GENUINE_FEEDBACK")
    data=json.loads(f.read_text());s,_,_=trusted_inputs(w)
    require(data["source_site_sha256"]==s["site_sha256"] and
            data["source_qa_sha256"]==s["qa_receipt_sha256"],"STALE_FEEDBACK")
    note="\n".join(str(x["route"])+"/"+str(x["width"])+": "+
       str(x["notes"]).replace("\n"," ")[:230] for x in data["feedback"])
    prompt=("Design RAG V2.1 correction request. Apply only visible issues confirmed by "
      "Gemini observations, preserve authoritative project/brand RAG, original "
      "logo and source assets, WCAG AA, mobile-first hierarchy, and real hospitality "
      "presentation. Site is UNAPPROVED. Rebuild, recapture and re-review all "
      "screenshots. No production publishing.\n"+note)
    return prompt[:max_chars]

def main():
    ap=argparse.ArgumentParser();ap.add_argument("command",choices=["prepare","ingest","correction"])
    ap.add_argument("--workspace",required=True,type=Path)
    ap.add_argument("--receipt",type=Path)
    a=ap.parse_args()
    try:
        w=workspace(a.workspace)
        if a.command=="prepare":res=prepare(w)
        elif a.command=="ingest":
            require(a.receipt is not None,"RECEIPT_REQUIRED")
            res=ingest(w,a.receipt)
        else:res={"status":"CORRECTION_READY","prompt":correction_prompt(w),
                  "release_authorized":False}
        print(json.dumps(res,indent=2))
    except Exception as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e)[:160],
                          "artistic_score":None,"release_authorized":False}))
        return 4
    return 0

if __name__=="__main__":raise SystemExit(main())
