"""Event-driven review ingestion adapter used at completion of EVERY design review.

A review producer must either call record_completed_review() inline or drop an
atomically renamed JSON into its project's protected inbox and call sync_inbox().
No event disappears on failure. Project data never reaches generic/type stores.
"""
import asyncio
import json
from pathlib import Path

from .core import Registry, ReviewLedger, atomic_write, safe_dir, name_ok

def inbox_dir(registry: Registry, project: str) -> Path:
    registry.scopes(project,"owner")
    path=safe_dir(registry.root/"inbox",project)
    path.mkdir(parents=True,mode=0o700,exist_ok=True)
    path.chmod(0o700)
    return path

def pending_inbox_count(registry: Registry, project: str) -> int:
    return sum(1 for p in inbox_dir(registry,project).iterdir()
               if p.is_file() and p.suffix==".json")

def record_completed_review(registry: Registry, receipt: dict) -> dict:
    """Synch adapter: first durable inbox, then ingest and ACK; failure stays queued."""
    ledger=ReviewLedger(registry)
    ledger.validate(receipt)
    project=name_ok(receipt["project"])
    name=name_ok(receipt["review_id"])
    path=inbox_dir(registry,project)/(name+".json")
    content=json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)
    if path.exists() and path.read_text()!=content:
        raise ValueError("REVIEW_RECEIPT_CONFLICT")
    if not path.exists():
        atomic_write(path,content)
    return asyncio.run(sync_inbox(registry,project))

async def sync_inbox(registry: Registry, project: str) -> dict:
    """Processes all discovered reviews; unprocessable entries remain for retry."""
    root=inbox_dir(registry,project)
    archived=safe_dir(registry.root/"processed",project)
    archived.mkdir(parents=True,exist_ok=True,mode=0o700)
    archived.chmod(0o700)
    ledger=ReviewLedger(registry)
    records=[];failed=[]
    for path in sorted(root.iterdir()):
        if path.suffix!=".json":
            continue
        if path.is_symlink() or not path.is_file():
            failed.append({"file":path.name,"error":"SYMLINK_OR_NOT_FILE"})
            continue
        try:
            receipt=json.loads(path.read_text())
            ledger.validate(receipt)
            if receipt["project"]!=project:
                raise ValueError("CROSS_PROJECT_RECEIPT_DENIED")
            admitted=ledger.submit(receipt)
            results=await ledger.reconcile(project)
            if any(x["status"]!="INDEXED" for x in results["results"]):
                raise RuntimeError("REVIEW_GRAPH_INGEST_PENDING")
            if any(x["review_id"]==receipt["review_id"] for x in ledger.pending(project)):
                raise RuntimeError("REVIEW_EVENT_NOT_ACKNOWLEDGED")
            target=archived/path.name
            if target.exists():
                if target.read_text()!=path.read_text():
                    raise ValueError("IMMUTABLE_ARCHIVE_CONFLICT")
                path.unlink()
            else:
                path.replace(target)
            records.append({"review_id":receipt["review_id"],"status":"INDEXED_AND_ARCHIVED",
                            "duplicate":admitted["deduplicated"]})
        except Exception as e:
            failed.append({"file":path.name,"error":type(e).__name__})
    backlog=len(ledger.pending(project))+pending_inbox_count(registry,project)
    return {"status":"PASS" if not failed and backlog==0 else "BLOCKED",
            "project":project,"processed":records,"failures":failed,"backlog":backlog}
