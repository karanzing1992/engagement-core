#!/usr/bin/env python3
"""Fast, offline FTS5 index of reviewed official legal source pointers. Python stdlib only."""
import argparse
import datetime as dt
import json
import pathlib
import re
import sqlite3
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "records.jsonl"
DB = ROOT / "data" / "legal.sqlite3"
NONBINDING = {"recommendation", "historical", "requires_verification"}
ALLOWED = {"in_force", "reference", "guidance", *NONBINDING}

def load_records(path=DATA):
    rows = []
    seen = set()
    for n, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not ln.strip():
            continue
        r = json.loads(ln)
        for k in ("id", "title", "summary", "source_url", "status", "jurisdiction", "topic", "checked_on"):
            if not r.get(k):
                raise ValueError(f"row {n} missing {k}")
        if r["id"] in seen:
            raise ValueError(f"duplicate id {r['id']}")
        if r["status"] not in ALLOWED or not r["source_url"].startswith("https://"):
            raise ValueError(f"invalid status/url for {r['id']}")
        seen.add(r["id"])
        rows.append(r)
    return sorted(rows, key=lambda x: x["id"])

def build(database=DB, records=DATA):
    database.parent.mkdir(parents=True, exist_ok=True)
    rs = load_records(records)
    db = sqlite3.connect(str(database))
    try:
        db.executescript("""
        DROP TABLE IF EXISTS records;
        CREATE TABLE records (
          id TEXT PRIMARY KEY, title TEXT, summary TEXT, authority TEXT, topic TEXT,
          jurisdiction TEXT, kind TEXT, status TEXT, effective_from TEXT,
          effective_to TEXT, checked_on TEXT, url TEXT, metadata TEXT
        );
        DROP TABLE IF EXISTS documents_fts;
        CREATE VIRTUAL TABLE documents_fts USING fts5(
          id UNINDEXED,title,summary,keywords,topic,authority,content='',
          tokenize='unicode61 remove_diacritics 2'
        );
        """)
        for r in rs:
            db.execute("INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                r["id"], r["title"], r["summary"], r["authority"], r["topic"],
                r["jurisdiction"], r["instrument_type"], r["status"],
                r.get("effective_from"), r.get("effective_to"), r["checked_on"],
                r["source_url"], json.dumps(r, ensure_ascii=False, sort_keys=True)))
            db.execute("INSERT INTO documents_fts(rowid,id,title,summary,keywords,topic,authority) VALUES ((SELECT rowid FROM records WHERE id=?),?,?,?,?,?,?)",(
                r["id"],r["id"],r["title"],r["summary"]," ".join(r["keywords"]),r["topic"],r["authority"]))
        db.commit()
    finally:
        db.close()
    return len(rs)

def query(text, as_of=None, jurisdiction="IN", include_nonbinding=False, strict=False, limit=20, database=DB):
    if not database.exists():
        build(database)
    # FTS5 query is tokenised and parameterised: no SQL injection or wildcards from user input.
    tokens = re.findall(r"[\w]+", text, flags=re.UNICODE)
    if not tokens:
        return []
    expression = " OR ".join('"' + t.replace('"','') + '"*' for t in tokens[:16])
    day = as_of or dt.date.today().isoformat()
    allowed = ("in_force",) if strict else (
        tuple(sorted(ALLOWED)) if include_nonbinding else ("in_force", "reference", "guidance"))
    sql = """
      SELECT r.metadata, bm25(documents_fts,0,9,4,2,3,2) AS relevance
      FROM documents_fts JOIN records r ON r.rowid = documents_fts.rowid
      WHERE documents_fts MATCH ?
        AND (r.jurisdiction='IN' OR r.jurisdiction=?)
        AND (r.effective_from IS NULL OR r.effective_from<=?)
        AND (r.effective_to IS NULL OR r.effective_to>=?)
        AND r.status IN ({statuses})
      ORDER BY relevance LIMIT ?
    """.format(statuses=",".join("?" for _ in allowed))
    with sqlite3.connect(str(database)) as db:
        rs = db.execute(sql, [expression, jurisdiction, day, day, *allowed, limit]).fetchall()
    out = []
    for meta, score in rs:
        rec = json.loads(meta)
        rec["relevance"] = round(score, 4)
        rec["freshness_warning"] = (dt.date.fromisoformat(day) - dt.date.fromisoformat(rec["checked_on"])).days > 14
        out.append(rec)
    return out

def source_check(records=DATA, max_records=50):
    results = []
    for r in load_records(records)[:max_records]:
        req = Request(r["source_url"], headers={"User-Agent":"IndiaLegalReferenceIndex/0.1 (+manual human review)"}, method="HEAD")
        try:
            with urlopen(req, timeout=7) as res:
                status = res.status
        except (HTTPError, URLError, TimeoutError, ValueError) as e:
            status = "unverified: " + str(e)[:130]
        results.append({"id": r["id"],"url":r["source_url"],"availability":status})
    return results

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="cmd", required=True)
    commands.add_parser("build", help="Rebuild SQLite FTS5 index from Git JSONL")
    sp = commands.add_parser("search", help="Case-specific temporal and jurisdiction search")
    sp.add_argument("terms", help="Space separated natural-language query")
    sp.add_argument("--as-of", default=None, help="YYYY-MM-DD transaction or tax date")
    sp.add_argument("--jurisdiction", default="IN", help="IN or IN-GA")
    sp.add_argument("--include-nonbinding", action="store_true")
    sp.add_argument("--strict", action="store_true",help="Only in_force source records")
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    cp = commands.add_parser("source-check", help="Best-effort HEAD probes, no scraping")
    cp.add_argument("--limit", type=int, default=20)
    args = p.parse_args(argv)
    if args.cmd=="build":
        print(json.dumps({"built":build(),"db":str(DB)}))
    elif args.cmd=="source-check":
        print(json.dumps(source_check(max_records=args.limit),indent=2))
    else:
        try:
            hits=query(args.terms,args.as_of,args.jurisdiction,args.include_nonbinding,args.strict,args.limit)
        except (ValueError, sqlite3.Error) as e:
            p.error(str(e))
        if args.json:
            print(json.dumps(hits,ensure_ascii=False,indent=2))
        else:
            for r in hits:
                print(f"[{r['status'].upper()}] {r['id']} | {r['title']}\n"
                      f"  {r['source_url']}\n  {r['summary']}\n"
                      f"  checked={r['checked_on']} stale={'YES' if r['freshness_warning'] else 'no'}")
            if not hits:
                print("No indexed match. Check exact official primary sources; do not infer applicable law.")
if __name__=="__main__":
    main()
