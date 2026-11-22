"""DEV DESIGN RAG 1.0. Project-isolated LightRAG and quality gate.

This process is intended to be invoked through an owner-authenticated Dell CLI.
It deliberately exposes no HTTP server and never accepts a filesystem path as a
scope. Cross-project access is resolved from a trusted, local registry.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
IDENT = re.compile(r"^[a-z][a-z0-9_-]{1,62}$")
SOURCE_MAX_BYTES = 40000
REVIEW_MAX_BYTES = 40000
REQUIRED_TESTS = ("playwright", "axe_wcag", "lighthouse_mobile", "lighthouse_desktop", "keyboard")
ART_MIN = 95

class IsolationError(PermissionError):
    pass

class QualityBlocked(RuntimeError):
    pass

def name_ok(name: str) -> str:
    if not isinstance(name, str) or not IDENT.fullmatch(name):
        raise IsolationError("INVALID_SCOPE_NAME")
    return name

def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        f.write(content)
        os.fchmod(f.fileno(), mode)
        tmp = Path(f.name)
    os.replace(tmp, path)
    os.chmod(path, mode)

def safe_dir(root: Path, *parts: str) -> Path:
    for part in parts:
        name_ok(part)
    path = root.joinpath(*parts)
    root_abs = root.resolve()
    # Parent symlinks are disallowed. This avoids path tricks in compromised stores.
    current = root
    for component in parts:
        current = current / component
        if current.is_symlink():
            raise IsolationError("SYMLINK_SCOPE_DENIED")
    if not path.resolve(strict=False).is_relative_to(root_abs):
        raise IsolationError("PATH_ESCAPE_DENIED")
    return path

@dataclass(frozen=True)
class Scope:
    kind: str
    scope_id: str

    def __post_init__(self):
        if self.kind not in ("generic", "type", "brand", "project"):
            raise IsolationError("UNKNOWN_LAYER")
        name_ok(self.scope_id)
        if self.kind == "generic" and self.scope_id != "shared":
            raise IsolationError("INVALID_GENERIC_SCOPE")

    def key(self) -> str:
        return self.kind + "/" + self.scope_id

class Registry:
    """Trusted owner-file ACL; never trusts an arbitrary brand/project from a document."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.policy_path = self.root / "policy.json"
        if not self.policy_path.exists():
            raise IsolationError("REGISTRY_UNINITIALIZED")
        self.config = json.loads(self.policy_path.read_text())
        self._validate()

    def _validate(self):
        if self.config.get("version") != VERSION:
            raise IsolationError("REGISTRY_VERSION_MISMATCH")
        if self.config.get("quality", {}).get("artistic_minimum") != ART_MIN:
            raise IsolationError("GLOBAL_95_GATE_NOT_ENFORCED")
        if self.config["quality"].get("owner_gate_required") is not True:
            raise IsolationError("OWNER_RELEASE_GATE_DISABLED")
        if sorted(self.config["quality"].get("required_tests", [])) != sorted(REQUIRED_TESTS):
            raise IsolationError("MANDATORY_TESTS_CHANGED")
        if self.config["quality"].get("project_override_allowed") is not False:
            raise IsolationError("QUALITY_OVERRIDE_ALLOWED")
        for b in self.config.get("brands", {}):
            name_ok(b)
        for t in self.config.get("types", []):
            name_ok(t)
        for p, item in self.config.get("projects", {}).items():
            name_ok(p)
            if item["brand"] not in self.config["brands"] or item["type"] not in self.config["types"]:
                raise IsolationError("UNREGISTERED_PROJECT_RELATION")
            if "quality" in item:
                raise IsolationError("PROJECT_QUALITY_OVERRIDE_DENIED")

    def scopes(self, project: str, principal: str = "owner") -> list[Scope]:
        name_ok(project)
        # This identity is meaningful ONLY inside an authenticated owner SSH
        # execution channel. Never expose this class as a remote untrusted API.
        grants = self.config.get("principals", {}).get(principal)
        if not grants:
            raise IsolationError("PRINCIPAL_NOT_ALLOWED")
        if project not in grants.get("projects", []) and "*" not in grants.get("projects", []):
            raise IsolationError("CROSS_PROJECT_ACCESS_DENIED")
        p = self.config["projects"].get(project)
        if not p:
            raise IsolationError("UNKNOWN_PROJECT")
        return [
            Scope("generic", "shared"),
            Scope("type", p["type"]),
            Scope("brand", p["brand"]),
            Scope("project", project),
        ]

    def writable(self, scope: Scope, principal: str, project: str) -> bool:
        if principal != "owner":
            return False
        # Only owner-admin may seed brand-neutral shared/type knowledge. They
        # cannot accidentally seed one project's brand into another.
        if scope.kind == "generic":
            return scope.scope_id == "shared"
        if scope.kind == "type":
            return scope.scope_id in self.config["types"]
        return scope in self.scopes(project, principal)

    def scope_dir(self, scope: Scope) -> Path:
        folder = {
            "generic": "generic", "type": "types",
            "brand": "brands", "project": "projects",
        }[scope.kind]
        graph_root = self.root / "graphs"
        path = safe_dir(graph_root, folder, scope.scope_id)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)
        return path

    def source_dir(self, scope: Scope) -> Path:
        folder = {
            "generic": "generic", "type": "types",
            "brand": "brands", "project": "projects",
        }[scope.kind]
        path = safe_dir(self.root / "knowledge", folder, scope.scope_id)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)
        return path

    def register_brand(self, brand_id: str, display_name: str, owner: str) -> dict:
        name_ok(brand_id)
        name_ok(owner)
        if not isinstance(display_name,str) or not (2 <= len(display_name) <= 120):
            raise ValueError("INVALID_BRAND_NAME")
        if brand_id in self.config["brands"]:
            raise IsolationError("BRAND_ALREADY_REGISTERED")
        self.config["brands"][brand_id]={"owner":owner,"name":display_name}
        atomic_write(self.policy_path,json.dumps(self.config,indent=2))
        # Store created independently; never copy a different brand graph.
        path=self.scope_dir(Scope("brand",brand_id))
        return {"status":"REGISTERED","brand":brand_id,"graph_path":str(path)}

    def register_project(self, project_id: str, brand_id: str, project_type: str, owner: str) -> dict:
        name_ok(project_id);name_ok(brand_id);name_ok(project_type);name_ok(owner)
        if project_id in self.config["projects"]:
            raise IsolationError("PROJECT_ALREADY_REGISTERED")
        if brand_id not in self.config["brands"]:
            raise IsolationError("BRAND_NOT_REGISTERED")
        if project_type not in self.config["types"]:
            raise IsolationError("PROJECT_TYPE_NOT_REGISTERED")
        if self.config["brands"][brand_id]["owner"]!=owner:
            raise IsolationError("CROSS_OWNER_BRAND_BINDING_DENIED")
        self.config["projects"][project_id]={"brand":brand_id,"type":project_type,"owner":owner}
        self.config["principals"]["owner"]["projects"].append(project_id)
        atomic_write(self.policy_path,json.dumps(self.config,indent=2))
        path=self.scope_dir(Scope("project",project_id))
        self.artifact_dir(project_id)
        return {"status":"REGISTERED","project":project_id,"type":project_type,
                "brand":brand_id,"graph_path":str(path),"artistic_minimum":ART_MIN}

    def artifact_dir(self, project: str) -> Path:
        name_ok(project)
        if project not in self.config["projects"]:
            raise IsolationError("UNKNOWN_PROJECT")
        path = safe_dir(self.root / "events", project)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(path, 0o700)
        return path

    def assert_shared_source(self, scope: Scope, text: str):
        if len(text.encode("utf-8")) > SOURCE_MAX_BYTES or not text.strip():
            raise IsolationError("DOCUMENT_SIZE_INVALID")
        # Fail-closed for indexed free-form data in globally shared layers.
        if scope.kind in ("generic", "type"):
            forbidden = ("andaz vibe", "andaz.", "moksha wellness",
                         "andazgoa.com", "mokshagoa.com",
                         "karanbizweb360@", "customer_name", "customer_email")
            if any(x in text.lower() for x in forbidden):
                raise IsolationError("BRAND_OR_CUSTOMER_DATA_IN_SHARED_LAYER")

def make_policy() -> dict:
    return {
        "version": VERSION,
        "security": {
            "boundary": "authenticated Dell owner CLI; no network listener",
            "sharing": "generic and project type text only; no brand facts",
            "root_mode": "0700",
            "scope_mode": "0700",
            "secrets": "never in knowledge; no credentials in graph",
        },
        "quality": {
            "artistic_minimum": ART_MIN,
            "mandatory_artist_verdict": "APPROVE",
            "required_tests": list(REQUIRED_TESTS),
            "owner_gate_required": True,
            "project_override_allowed": False,
            "independent_review_required": True,
            "applies_to": "all UI/UX and design tools, all registered projects",
        },
        "types": ["hospitality", "saas_dashboard", "mobile_native", "ecommerce", "editorial_content", "interactive_game"],
        "brands": {"andaz": {"owner": "karanzing1992", "name": "Andaz Vibe Stay"}},
        "projects": {"andaz-vibe-stay": {"type": "hospitality", "brand": "andaz", "owner": "karanzing1992"}},
        "principals": {
            "owner": {"projects": ["andaz-vibe-stay"]},
            "andaz_design_agent": {"projects": ["andaz-vibe-stay"]},
            "untrusted_agent": {"projects": []}
        }
    }

def init_registry(root: Path) -> Registry:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    policy = root / "policy.json"
    if not policy.exists():
        atomic_write(policy, json.dumps(make_policy(), indent=2))
    return Registry(root)

async def no_external_model(*args, **kwargs):
    raise RuntimeError("GENERATIVE_MODEL_DISABLED_DURING_INDEX_AND_RETRIEVAL")

async def local_embed(texts):
    import httpx
    import numpy as np
    async with httpx.AsyncClient(timeout=36, trust_env=False) as client:
        r = await client.post("http://127.0.0.1:11434/api/embed", json={
            "model": "all-minilm", "input": list(texts),
            "options": {"num_thread": 1}, "keep_alive": "20s"
        })
        r.raise_for_status()
        values = r.json()["embeddings"]
        if len(values) != len(texts) or any(len(a) != 384 for a in values):
            raise RuntimeError("INVALID_EMBEDDING_384")
        return np.asarray(values, dtype=np.float32)

def make_graph_doc(scope: Scope, doc_id: str, text: str, source: str) -> dict:
    """Deterministic entity/heading extraction with verifiable source attribution."""
    name_ok(doc_id)
    heading = f"{scope.kind.upper()} {scope.scope_id.upper()} {doc_id.upper()}"
    blocks = []
    current = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            blocks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    chunks = []
    entities = [{
        "entity_name": heading, "entity_type": "Document",
        "description": f"Source-backed {scope.kind}/{scope.scope_id} knowledge document {doc_id}",
        "source_id": doc_id, "file_path": source
    }]
    relationships = []
    for i, block in enumerate(blocks):
        words = block.split()
        for j in range(0, len(words), 170):
            part = " ".join(words[j:j+170])
            if not part.strip():
                continue
            chunks.append({"content": part, "source_id": doc_id, "file_path": source})
        section = block.splitlines()[0].lstrip("# ").strip()[:75] or f"Section {i+1}"
        key = f"{heading} :: {i+1}"
        entities.append({
            "entity_name": key, "entity_type": "DesignKnowledge",
            "description": f"{section}: {block[:330]}",
            "source_id": doc_id, "file_path": source
        })
        relationships.append({
            "src_id": heading, "tgt_id": key, "description": "Contains source-backed " + section,
            "keywords": "design,source,knowledge", "weight": 1.0,
            "source_id": doc_id, "file_path": source
        })
    if not chunks:
        raise ValueError("EMPTY_GRAPH_DOC")
    return {"chunks": chunks, "entities": entities, "relationships": relationships}

async def _rag(scope_dir: Path):
    from lightrag import LightRAG
    from lightrag.utils import EmbeddingFunc
    graph = LightRAG(
        working_dir=str(scope_dir),
        llm_model_func=no_external_model,
        embedding_func=EmbeddingFunc(embedding_dim=384,max_token_size=512,func=local_embed),
        embedding_batch_num=1,embedding_func_max_async=1,llm_model_max_async=1,
        chunk_token_size=220,chunk_overlap_token_size=20,
        max_total_tokens=4300,max_entity_tokens=1100,max_relation_tokens=1100,
        enable_llm_cache=False,
    )
    await graph.initialize_storages()
    return graph

class DesignKnowledge:
    def __init__(self, registry: Registry):
        self.registry = registry

    async def index(self, scope: Scope, doc_id: str, text: str, source_url: str, principal="owner", project="andaz-vibe-stay") -> dict:
        if not self.registry.writable(scope,principal,project):
            raise IsolationError("WRITE_SCOPE_DENIED")
        self.registry.assert_shared_source(scope,text)
        if not source_url.startswith(("https://", "internal://")):
            raise ValueError("SOURCE_URL_REQUIRED")
        source_dir=self.registry.source_dir(scope)
        doc_path = source_dir / f"{name_ok(doc_id)}.md"
        checksum=sha_text(text)
        if doc_path.exists():
            if sha_text(doc_path.read_text()) != checksum:
                raise IsolationError("IMMUTABLE_DOC_ID_CONFLICT")
            return {"status":"DEDUPLICATED","scope":scope.key(),"sha256":checksum}
        # Contents never cross knowledge layers; graph storage is per-layer.
        graph_doc = make_graph_doc(scope,doc_id,text,source_url)
        graph = await _rag(self.registry.scope_dir(scope))
        try:
            await asyncio.wait_for(graph.ainsert_custom_kg(graph_doc,full_doc_id=f"{scope.key()}::{doc_id}"),timeout=100)
        finally:
            await graph.finalize_storages()
        atomic_write(doc_path,text)
        return {"status":"INDEXED","scope":scope.key(),"doc_id":doc_id,"sha256":checksum,
                "chunks":len(graph_doc["chunks"]), "entities":len(graph_doc["entities"])}

    async def query(self, project: str, query: str, principal="owner") -> dict:
        if not isinstance(query,str) or len(query)>800:
            raise ValueError("QUERY_INVALID")
        scopes = self.registry.scopes(project,principal)
        from lightrag import QueryParam
        result={}
        for scope in scopes:
            storage=self.registry.scope_dir(scope)
            if not (storage/"kv_store_text_chunks.json").exists():
                result[scope.key()] = {"status":"EMPTY","context":""}
                continue
            rag=await _rag(storage)
            try:
                value = await asyncio.wait_for(rag.aquery(query,
                    param=QueryParam(mode="naive",only_need_context=True,
                    top_k=10,chunk_top_k=10,max_total_tokens=2900,
                    include_references=True)),timeout=40)
                result[scope.key()] = {"status":"OK","context":str(value)[:17500]}
            finally:
                await rag.finalize_storages()
        return {"project":project,"scope_order":[s.key() for s in scopes],"layers":result,
                "quality_floor":ART_MIN}

    def layer_status(self, project: str, principal="owner") -> dict:
        out={}
        for s in self.registry.scopes(project,principal):
            path = self.registry.scope_dir(s)
            graph=path/"graph_chunk_entity_relation.graphml"
            out[s.key()]={"indexed":graph.is_file(),"graph_bytes":graph.stat().st_size if graph.exists() else 0}
        return out

class ReviewLedger:
    """Durable, scoped, idempotent reviews; every admitted review must be indexed."""
    def __init__(self, registry: Registry):
        self.registry=registry
        self.db=registry.root/"reviews.sqlite3"
        connection=self._db()
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS reviews(
                project TEXT NOT NULL, review_id TEXT NOT NULL,
                event_sha TEXT NOT NULL, kind TEXT NOT NULL,
                artifact_sha TEXT NOT NULL, state TEXT NOT NULL,
                receipt TEXT NOT NULL, error_code TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY(project,review_id)
            );
            CREATE INDEX IF NOT EXISTS idx_reviews_state ON reviews(state);
        """)
        connection.commit()
        connection.close()
        os.chmod(self.db,0o600)

    def _db(self):
        con=sqlite3.connect(self.db,timeout=15,isolation_level=None)
        con.execute("PRAGMA busy_timeout=15000")
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def validate(self, obj: dict) -> dict:
        if not isinstance(obj,dict):
            raise ValueError("REVIEW_NOT_OBJECT")
        project=name_ok(obj.get("project",""))
        self.registry.scopes(project,"owner")
        review_id=name_ok(obj.get("review_id",""))
        kind=obj.get("kind")
        if kind not in ("artistic","ux","accessibility","functional","performance","security","owner",*REQUIRED_TESTS):
            raise ValueError("REVIEW_KIND_INVALID")
        if obj.get("scope") not in ("homepage","site","feature","mobile_app","dashboard","component"):
            raise ValueError("REVIEW_SCOPE_INVALID")
        if not re.fullmatch(r"[a-f0-9]{64}",str(obj.get("artifact_sha",""))):
            raise ValueError("ARTIFACT_SHA_REQUIRED")
        if not isinstance(obj.get("source_url"),str) or not obj["source_url"].startswith("https://"):
            raise ValueError("EVIDENCE_SOURCE_REQUIRED")
        if not isinstance(obj.get("reviewer"),str) or not obj["reviewer"].strip():
            raise ValueError("REVIEWER_REQUIRED")
        if not isinstance(obj.get("findings"),list):
            raise ValueError("FINDINGS_LIST_REQUIRED")
        if kind=="artistic":
            if type(obj.get("score")) is not int or not 0<=obj["score"]<=100:
                raise ValueError("ARTISTIC_SCORE_REQUIRED")
            if obj.get("verdict") not in ("APPROVE","REVISE","REJECT"):
                raise ValueError("ARTISTIC_VERDICT_REQUIRED")
            if obj.get("independent") is not True:
                raise ValueError("ARTISTIC_REVIEW_NOT_INDEPENDENT")
        if kind != "artistic" and not isinstance(obj.get("passed"),bool):
            raise ValueError("TECHNICAL_RESULT_REQUIRED")
        if len(json.dumps(obj))>REVIEW_MAX_BYTES:
            raise ValueError("REVIEW_TOO_LARGE")
        # Avoid inserting known PII and secrets into any project graph.
        representation=json.dumps(obj).lower()
        if any(secret in representation for secret in ("api_key","access_token","authorization:","password=")):
            raise IsolationError("REVIEW_CONTAINS_SECRET")
        return obj

    def submit(self,obj:dict)->dict:
        self.validate(obj)
        project=obj["project"]
        name=obj["review_id"]
        payload=json.dumps(obj,sort_keys=True,ensure_ascii=False)
        digest=sha_text(payload)
        con=self._db()
        try:
            row=con.execute("SELECT event_sha,state FROM reviews WHERE project=? AND review_id=?",(project,name)).fetchone()
            if row is not None:
                if row[0]!=digest:
                    raise IsolationError("REVIEW_ID_COLLISION")
                return {"status":row[1],"project":project,"review_id":name,"deduplicated":True}
            con.execute("BEGIN IMMEDIATE")
            con.execute("INSERT INTO reviews VALUES (?,?,?,?,?,?,?,?,?)",(
                project,name,digest,obj["kind"],obj["artifact_sha"],"PENDING",
                payload,None,datetime.now(timezone.utc).isoformat()
            ))
            con.commit()
        finally:
            con.close()
        return {"status":"PENDING","project":project,"review_id":name,"deduplicated":False}

    def pending(self,project: str | None=None)->list[dict]:
        con=self._db()
        try:
            if project:
                self.registry.scopes(project,"owner")
                rows=con.execute("SELECT receipt FROM reviews WHERE project=? AND state!='INDEXED' ORDER BY created_at",(project,)).fetchall()
            else:
                rows=con.execute("SELECT receipt FROM reviews WHERE state!='INDEXED' ORDER BY created_at").fetchall()
            return [json.loads(r[0]) for r in rows]
        finally:
            con.close()

    async def reconcile(self,project: str | None=None)->dict:
        receipts=[]
        for obj in self.pending(project):
            project_id=obj["project"]
            public={
                "review_id":obj["review_id"],"kind":obj["kind"],
                "reviewer":obj["reviewer"],"artifact_sha":obj["artifact_sha"],
                "scope":obj["scope"],"verdict":obj.get("verdict"),
                "score":obj.get("score"),"passed":obj.get("passed"),
                "findings":obj["findings"],"source_url":obj["source_url"],
                "timestamp":obj.get("timestamp"),
                "evidence":obj.get("evidence",{}),
                "status":"REVIEW_EVIDENCE; not design knowledge promotion"
            }
            label=f"Design review {obj['review_id']} / {obj['kind']}\n"
            content=label+json.dumps(public,sort_keys=True,ensure_ascii=False,indent=2)
            try:
                result=await DesignKnowledge(self.registry).index(
                    Scope("project",project_id),
                    "review-"+obj["review_id"],content,obj["source_url"],
                    principal="owner",project=project_id
                )
                state="INDEXED";error=None
            except Exception as exc:
                state="PENDING";error=type(exc).__name__
                result={"status":"INDEX_FAILED","error_code":error}
            con=self._db()
            try:
                con.execute("UPDATE reviews SET state=?,error_code=? WHERE project=? AND review_id=?",(state,error,project_id,obj["review_id"]))
                con.commit()
            finally:con.close()
            receipts.append({"project":project_id,"review_id":obj["review_id"],"status":state,"graph":result})
        return {"processed":len(receipts),"results":receipts}

    def gate(self,project:str,artifact_sha:str,owner_approval:bool=False)->dict:
        self.registry.scopes(project,"owner")
        if not re.fullmatch(r"[a-f0-9]{64}",artifact_sha):
            raise ValueError("INVALID_ARTIFACT_ID")
        con=self._db()
        try:
            pending=con.execute("SELECT count(*) FROM reviews WHERE project=? AND state!='INDEXED'",(project,)).fetchone()[0]
            rows=con.execute("SELECT receipt FROM reviews WHERE project=? AND artifact_sha=? AND state='INDEXED'",(project,artifact_sha)).fetchall()
            all_reviews=[json.loads(row[0]) for row in rows]
        finally:con.close()
        # Pending inbox files (including invalid/foreign project events) are
        # also release blockers; failed files cannot be silently dropped.
        from .inbox import pending_inbox_count
        pending += pending_inbox_count(self.registry,project)
        valid_art=[x for x in all_reviews if x["kind"]=="artistic" and x.get("independent") is True and x.get("reviewer") not in ("synthetic","test")]
        # A later or earlier failed test of the same artifact must not be
        # overwritten by a passing receipt of the same kind.
        stage_reviews={kind:[x for x in all_reviews if x["kind"]==kind]
                       for kind in REQUIRED_TESTS}
        # Evaluate every independent critique of this exact artifact; lower
        # scores cannot be hidden by selecting an older, nicer review.
        scores=[x["score"] for x in valid_art]
        score=min(scores) if scores else None
        requirements={
            "no_review_backlog":pending==0,
            "artistic_score_at_least_95":isinstance(score,int) and score>=ART_MIN,
            "independent_artistic_approve":bool(valid_art) and all(x.get("verdict")=="APPROVE" for x in valid_art),
            "all_required_tests_pass":all(stage_reviews[k] and all(x.get("passed") is True
                                                 for x in stage_reviews[k])
                                          for k in REQUIRED_TESTS),
            "owner_approval":owner_approval is True,
        }
        passed=all(requirements.values())
        return {"status":"PASS" if passed else "BLOCKED","project":project,"artifact_sha":artifact_sha,
                "artistic_score":score,"minimum_artistic_score":ART_MIN,
                "checks":requirements,"pending_reviews":pending,
                "review_count":len(all_reviews),
                "owner_release_required":True}
