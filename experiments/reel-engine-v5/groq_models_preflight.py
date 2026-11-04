#!/usr/bin/env python3
"""Groq-only V5 account model listing; zero inference/token charges, no credentials logged."""
import json,os,sys,urllib.request,urllib.error
from pathlib import Path
HERE=Path(__file__).resolve().parent
cfg=json.loads((HERE/"v5_config.json").read_text())
required={"openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3.8-27b"}
routed={m for v in cfg["task_routing"].values() for m in v["candidate_models"]}
if required!=routed:raise SystemExit("V5 route model set does not match expected high-capability Groq models")
key=os.environ.get("GROQ_API_KEY","")
if not key:
 print("GROQ_MODEL_PREFLIGHT_BLOCKED missing_secret")
 sys.exit(2)
url="https://api.groq.com/openai/v1/models"
req=urllib.request.Request(url,headers={"Authorization":"Bearer "+key,"Accept":"application/json"},method="GET")
try:
 with urllib.request.urlopen(req,timeout=15) as resp:
  if resp.status!=200:raise RuntimeError("not_http_200")
  data=json.load(resp)
except urllib.error.HTTPError as exc:
 print("GROQ_MODEL_PREFLIGHT_BLOCKED status",exc.code)
 sys.exit(3)
except Exception as exc:
 print("GROQ_MODEL_PREFLIGHT_BLOCKED transport",type(exc).__name__)
 sys.exit(4)
available={x["id"] for x in data.get("data",[]) if isinstance(x,dict) and isinstance(x.get("id"),str)}
for model in sorted(required):
 print("GROQ_ACCOUNT_MODEL_LISTED",model,int(model in available))
if not required.issubset(available):
 print("GROQ_MODEL_PREFLIGHT_BLOCKED unlisted_model")
 sys.exit(5)
print("GROQ_MODEL_PREFLIGHT_LIST_PASS; account invoke/quotas not certified")
