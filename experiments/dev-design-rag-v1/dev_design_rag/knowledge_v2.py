"""Generic UI/UX Design RAG V2: bounded, source-attributed, version-pinned retrieval.
No external LLM or paid inference. Reads scoped LightRAG chunk stores; never mutates them.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from .version import DESIGN_RAG_VERSION, SUPPORTED_MANIFEST_VERSIONS

WORD = re.compile(r"[a-z0-9]+")
BUDGETS = {"project":2700,"brand":1800,"generic":2800,"type":850}
MAX_DOC_EXCERPT = 1080
STOP = {"the","and","to","with","from","into","for","that","these","this","what","about","where","when","your","only","have","how","which","using","should","current","site","website","design","ui","ux"}

class KnowledgeV2Error(ValueError):
    pass

def terms(text):
    return [s for s in WORD.findall(text.lower()) if len(s)>2 and s not in STOP]

def _manifest(registry):
    path=registry.root/"knowledge_manifest_v2.json"
    if not path.is_file():
        raise KnowledgeV2Error("V2_MANIFEST_MISSING")
    m=json.loads(path.read_text())
    if m.get("version") not in SUPPORTED_MANIFEST_VERSIONS or m.get("max_packet_chars",0)>14000:
        raise KnowledgeV2Error("V2_VERSION_OR_BUDGET_INVALID")
    if m.get("priority")!=["project","brand","generic","type"]:
        raise KnowledgeV2Error("V2_PRECEDENCE_INVALID")
    return m

def _cut(text, limit):
    s=" ".join(text.split())
    if len(s)<=limit:return s
    s=s[:limit]
    j=s.rfind(" ")
    return s[:j].strip()+"…" if j>limit//2 else s

def _source(registry, scope, doc_id):
    d=registry.source_dir(scope)/(doc_id+".md")
    if not d.is_file():
        raise KnowledgeV2Error("ACTIVE_DOC_SOURCE_MISSING:"+scope.key()+":"+doc_id)
    s=d.read_text(encoding="utf8")
    match=re.search(r"https://[^\s<>]+",s)
    # Public research sources have public citations; owner/project facts are internal.
    uri=(match.group(0).rstrip(".,);") if match else "internal://reference")
    if scope.kind in ("brand","project"):
        uri="internal://owner-verified/"+scope.key()+"/"+doc_id
    return uri,s

def _chunks(registry, scope):
    path=registry.scope_dir(scope)/"kv_store_text_chunks.json"
    if not path.is_file():raise KnowledgeV2Error("SCOPED_GRAPH_MISSING:"+scope.key())
    data=json.loads(path.read_text())
    if not isinstance(data,dict):raise KnowledgeV2Error("SCOPED_GRAPH_INVALID")
    return [{"source_id":v.get("source_id",""),"content":v.get("content",""),
             "order":v.get("chunk_order_index",9999)}
            for v in data.values() if isinstance(v,dict) and v.get("content")]

def _bm25_ranks(chunks, query):
    q=terms(query); q += ["v2","current","owner","original","accessible","mobile"] if not q else []
    corpus=[Counter(terms(c["content"])) for c in chunks]
    n=len(corpus);df=Counter()
    for c in corpus:df.update(c.keys())
    avg=sum(sum(c.values()) for c in corpus)/max(1,n)
    result=[]
    for c,b in zip(chunks,corpus):
        size=sum(b.values())
        score=0.
        for word in set(q):
            count=b[word]
            if not count:continue
            idf=math.log(1+(n-df[word]+.5)/(df[word]+.5))
            score+=idf*(count*2.2)/(count+1.2*(.25+.75*size/max(1,avg)))
        result.append((score,c))
    return result

def build_packet(registry, project, question, principal="owner"):
    if not isinstance(question,str) or not question.strip() or len(question)>800:
        raise KnowledgeV2Error("QUERY_INVALID")
    scopes=registry.scopes(project,principal)  # Enforce authenticated Dell owner ACL first
    m=_manifest(registry)
    keyed={s.kind:s for s in scopes}
    layers={}; segments=[]; selected=[]; historical=[]; remaining=m["max_packet_chars"]
    prefix=("UIUX-RAG-V2 ACTIVE KNOWLEDGE PACKET | 2026-11-10 | "
            "Authority: CURRENT owner/project then brand, universal WCAG/QA hard gates, "
            "hospitality/generic. Historical critiques are NOT active art direction. "
            "No source here grants artistic certification or release.\n")
    prefix += ("Hard standards: WCAG 2.2 AA, >=4.5:1 ordinary text contrast, "
               "keyboard/focus, target size AA, no horizontal overflow; "
               "field LCP <=2.5s, INP <=200ms, CLS <=0.1. "
               "These are checks, not a claim the current artifact passes. "
               "Sources: https://www.w3.org/TR/WCAG22/ and "
               "https://developers.google.com/search/docs/appearance/core-web-vitals\n")
    if any(t in terms(question) for t in ("award","awards","trend","trends","inspiration","example","examples")):
        prefix += ("Verified award examples: 2026 Webby aesthetic Igloo Inc; "
                   "2026 Webby functional FOLLOW.ART; 2026 Webby mobile Dunes & Stars; "
                   "CSSDA WOTY 2025 Dropbox Brand (announced Feb 2026). "
                   "Inspiration ONLY; never copy layouts/assets. "
                   "Source: https://winners.webbyawards.com/winners/websites-and-mobile-sites/features-design/best-visual-design-aesthetic\n")
    segments.append(prefix);remaining-=len(prefix)
    for kind in m["priority"]:
        scope=keyed[kind]; key=scope.key()
        entry=m["scopes"].get(key)
        if not entry or not entry.get("active"):
            raise KnowledgeV2Error("V2_SCOPE_MANIFEST_MISSING:"+key)
        active=entry["active"]
        if len(active)!=len(set(active)) or not all(re.fullmatch(r"[a-z0-9][a-z0-9_-]+",d) for d in active):
            raise KnowledgeV2Error("V2_MANIFEST_INVALID_DOC_IDS")
        all_chunks=_chunks(registry,scope)
        unused=sorted(set(v["source_id"] for v in all_chunks)-set(active))
        historical.extend({"scope":key,"source_id":x,"reason":"superseded_or_diagnostic_only"} for x in unused)
        picks=[];budget=min(BUDGETS[kind],remaining-260)
        if budget<=0:raise KnowledgeV2Error("PACKET_BUDGET_EXHAUSTED")
        source_meta={}
        ranked=_bm25_ranks(all_chunks,question)
        for doc_id in active:
            source_meta[doc_id]=_source(registry,scope,doc_id)
            subset=[(score,c) for score,c in ranked if c["source_id"]==doc_id]
            if not subset:raise KnowledgeV2Error("ACTIVE_DOC_NOT_INDEXED:"+key+":"+doc_id)
            subset.sort(key=lambda x:(-x[0],x[1]["order"]))
            # One top excerpt per pinned source; active source order is intentional.
            picks.append((doc_id,subset[0],0))
        # Allocate one excerpt per active source before optional second excerpts.
        if kind in ("project","brand"):
            for doc_id in active[:1]:
                subset=[(score,c) for score,c in ranked if c["source_id"]==doc_id]
                subset.sort(key=lambda x:(-x[0],x[1]["order"]))
                if len(subset)>1:picks.insert(1,(doc_id,subset[1],1))
        block=[]
        for i,(doc_id,(score,chunk),extra) in enumerate(picks):
            url,_=source_meta[doc_id]
            header=f"[{key} | {doc_id} | ACTIVE | score={score:.2f} | source={url}]\n"
            remaining_picks=len(picks)-i
            free=budget-sum(len(x) for x in block)
            future_headers=sum(len(f"[{key} | {d} | ACTIVE | score={sc:.2f} | source={source_meta[d][0]}]\n")
                               for d,(sc,_),_ in picks[i:])
            allowance=min(MAX_DOC_EXCERPT, (free-future_headers)//remaining_picks-3)
            if allowance<120:
                if extra:continue
                raise KnowledgeV2Error("ACTIVE_DOC_BUDGET_TOO_SMALL:"+doc_id)
            snippet=_cut(chunk["content"],allowance)
            seg=header+snippet+"\n"
            block.append(seg)
            selected.append({"scope":key,"source_id":doc_id,"source_url":url,
                             "status":"ACTIVE","rank_score":round(score,3),
                             "chunk_order":chunk["order"],"excerpt_chars":len(snippet)})
        text="".join(block)
        layers[key]={"status":"OK","context":text,"active_sources":active,
                     "excluded_historical_count":len(unused)}
        segments.append(text)
        remaining-=len(text)
    packet="".join(segments)
    if len(packet)>m["max_packet_chars"]:
        raise KnowledgeV2Error("PACKET_MAX_CHARS_VIOLATED")
    # Conservative estimate: output budget excludes headers and input prompt context.
    return {"status":"READY","version":DESIGN_RAG_VERSION,"project":project,"question":question,
            "scope_order":[s.key() for s in scopes],"authority_order":m["priority"],
            "quality_floor":95,"layer_count":len(layers),"layers":layers,
            "packet_text":packet,"packet_chars":len(packet),
            "estimated_tokens_upper_bound":math.ceil(len(packet)/3.0),
            "packet_sha256":hashlib.sha256(packet.encode()).hexdigest(),
            "sources":selected,"excluded_historical":historical,
            "retrieval":"source-grounded BM25 with mandatory active-source inclusion and pinned precedence"}

