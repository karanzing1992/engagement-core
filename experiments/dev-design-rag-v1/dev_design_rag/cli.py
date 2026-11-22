"""Owner-scoped CLI for DEV DESIGN RAG 1.0.

No public HTTP service. Invoke from the authenticated Dell development lane.
Every accepted design review is durably journaled before graph indexing.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from .core import (
    ART_MIN, DesignKnowledge, IsolationError, QualityBlocked, Registry,
    ReviewLedger, Scope, init_registry,
)

def json_print(value):
    print(json.dumps(value,ensure_ascii=False,indent=2))

async def run(args):
    root=Path(args.root).expanduser()
    if args.command=="init":
        reg=init_registry(root)
        json_print({"status":"INITIALIZED","root":str(reg.root),"global_artistic_minimum":ART_MIN,
                    "project_count":len(reg.config["projects"]),"project_types":reg.config["types"]})
        return 0
    registry=Registry(root)
    service=DesignKnowledge(registry)
    if args.command=="register-brand":
        json_print(registry.register_brand(args.brand,args.display_name,args.owner))
        return 0
    if args.command=="register-project":
        json_print(registry.register_project(args.project,args.brand,args.project_type,args.owner))
        return 0
    if args.command=="status":
        project=args.project
        json_print({"status":"READY","version":"1.0.0","knowledge_version":json.loads((registry.root/"knowledge_manifest_v2.json").read_text())["version"],"quality":registry.config["quality"],
                    "layers":service.layer_status(project,args.principal),
                    "review_backlog":len(ReviewLedger(registry).pending(project))})
        return 0
    if args.command=="index":
        scope=Scope(args.layer,args.scope)
        text=Path(args.file).read_text(encoding="utf-8")
        json_print(await service.index(scope,args.doc_id,text,args.source,
                                       args.principal,args.project))
        return 0
    if args.command=="query":
        json_print(await service.query(args.project,args.prompt,args.principal))
        return 0
    if args.command=="inbox-sync":
        from .inbox import sync_inbox
        output=await sync_inbox(registry,args.project)
        json_print(output)
        return 0 if output["status"]=="PASS" else 3
    if args.command=="review-complete":
        obj=json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        ledger=ReviewLedger(registry)
        admitted=ledger.submit(obj)
        indexed=await ledger.reconcile(obj["project"])
        pending=len(ledger.pending(obj["project"]))
        json_print({"admission":admitted,"reconciliation":indexed,"pending":pending})
        return 0 if pending==0 else 3
    if args.command=="reconcile":
        ledger=ReviewLedger(registry)
        result=await ledger.reconcile(args.project)
        backlog=len(ledger.pending(args.project))
        json_print({**result,"pending":backlog})
        return 0 if backlog==0 else 3
    if args.command=="gate":
        # No --owner-approved CLI flag: owner release authorization belongs to
        # the separate authenticated Master workflow, NEVER to this process.
        verdict=ReviewLedger(registry).gate(args.project,args.artifact_sha,
                                           owner_approval=False)
        json_print(verdict)
        return 0 if verdict["status"]=="PASS" else 4
    raise ValueError("UNSUPPORTED_COMMAND")

def main(argv=None):
    p=argparse.ArgumentParser(description="DEV DESIGN RAG 1.0 owner-scoped CLI")
    p.add_argument("--root",required=True,help="Isolated root created in owner Dell workspace")
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("init")
    br=sub.add_parser("register-brand")
    br.add_argument("--brand",required=True);br.add_argument("--display-name",required=True);br.add_argument("--owner",required=True)
    pr=sub.add_parser("register-project")
    pr.add_argument("--project",required=True);pr.add_argument("--brand",required=True)
    pr.add_argument("--project-type",required=True);pr.add_argument("--owner",required=True)
    st=sub.add_parser("status");st.add_argument("--project",required=True);st.add_argument("--principal",default="owner")
    ind=sub.add_parser("index")
    ind.add_argument("--project",required=True);ind.add_argument("--principal",default="owner")
    ind.add_argument("--layer",required=True,choices=["generic","type","brand","project"])
    ind.add_argument("--scope",required=True);ind.add_argument("--doc-id",required=True)
    ind.add_argument("--file",required=True);ind.add_argument("--source",required=True)
    que=sub.add_parser("query");que.add_argument("--project",required=True)
    que.add_argument("--prompt",required=True);que.add_argument("--principal",default="owner")
    ib=sub.add_parser("inbox-sync");ib.add_argument("--project",required=True)
    rev=sub.add_parser("review-complete");rev.add_argument("--receipt",required=True)
    rec=sub.add_parser("reconcile");rec.add_argument("--project")
    gate=sub.add_parser("gate");gate.add_argument("--project",required=True)
    gate.add_argument("--artifact-sha",required=True)
    args=p.parse_args(argv)
    try:
        return asyncio.run(run(args))
    except (IsolationError,QualityBlocked,ValueError,FileNotFoundError) as e:
        print(json.dumps({"status":"BLOCKED","error":str(e)[:160]}),file=sys.stderr)
        return 5

if __name__=="__main__":
    sys.exit(main())
