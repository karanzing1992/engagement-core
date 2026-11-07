"""Bootstrap brand-neutral/typed/brand/project graphs from approved source files.

Copies only *source documents*, not the original mixed Andaz graph. Thus existing
Andaz LightRAG is preserved as a read-only rollback while new graphs remain
physically isolated and contain only the layer's authorized material.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from .core import DesignKnowledge, Scope, ReviewLedger, init_registry

ROOTSRC=Path(__file__).resolve().parents[1]

SEEDS=(
    (Scope("generic","shared"),"uiux_art_basics",ROOTSRC/"knowledge/generic/design_basics.md",
     "https://www.w3.org/TR/wcag/"),
    (Scope("type","hospitality"),"hospitality_design",ROOTSRC/"knowledge/types/hospitality.md",
     "https://www.nngroup.com/articles/ten-usability-heuristics/"),
    (Scope("type","saas_dashboard"),"saas_dashboard_design",ROOTSRC/"knowledge/types/saas_dashboard.md",
     "https://designsystem.digital.gov/"),
    (Scope("type","mobile_native"),"native_mobile_design",ROOTSRC/"knowledge/types/mobile_native.md",
     "https://developer.android.com/design/ui/mobile/guides/foundations/accessibility"),
    (Scope("type","ecommerce"),"ecommerce_design",ROOTSRC/"knowledge/types/ecommerce.md",
     "https://baymard.com/research-articles/ecommerce-navigation-best-practice"),
    (Scope("type","editorial_content"),"editorial_design",ROOTSRC/"knowledge/types/editorial_content.md",
     "https://www.nngroup.com/articles/ten-usability-heuristics/"),
    (Scope("type","interactive_game"),"interactive_game_design",ROOTSRC/"knowledge/types/interactive_game.md",
     "https://developer.apple.com/design/human-interface-guidelines/"),
)

def legacy_reviews() -> list[dict]:
    """Verified Andaz review checkpoints, with matching source URIs and evidence."""
    legacy=[
        ("andaz-v1-gemini-20261107","artistic","site",54,"REJECT",
         "474b5ebd3bf15215d4d0de45fa46f640b6eca1289066a2ed9dcbc705ecf985c3",
         "https://github.com/karanzing1992/engagement-core/actions/runs/42353404120",
         ["generic graphic hero","oversized mobile hero","brand weak","room visual inconsistency","Explore empty"]),
        ("andaz-v2-gemini-20261107","artistic","site",68,"REVISE",
         "bc82700d1dd3c825929741c07940b0c68230464b45c14a224ceefa268dbe5e49",
         "https://github.com/karanzing1992/engagement-core/actions/runs/42362067203",
         ["desktop hero empty right side","social-hostel identity insufficient","mobile metadata-looking tag",
          "contact actions lack clear cards","Explore/Rooms visual repetitions"]),
        ("andaz-v3-home-gemini-20261107","artistic","homepage",96,"APPROVE",
         "7d4126dcef1ef9b0e9e3320accd055bee413c161b1a7955df63feb67f8589624",
         "https://github.com/karanzing1992/engagement-core/actions/runs/42365766838",
         ["minor 320px eyebrow spacing","small desktop image attribution close to fold"])
    ]
    records=[]
    for name,kind,scope,score,verdict,digest,url,findings in legacy:
        records.append({
            "project":"andaz-vibe-stay","review_id":name,"kind":kind,
            "scope":scope,"score":score,"verdict":verdict,"reviewer":"gemini-3.6-flash",
            "independent":True,"findings":findings,"source_url":url,
            "timestamp":"2026-11-07T10:52:00Z" if scope=="homepage" else "2026-11-07T10:00:00Z",
            "artifact_sha":digest,
            "evidence":{"source_type":"authenticated_github_actions_run",
                        "raw_source":"owner-side original evidence",
                        "artifact_digest_type":"stylesheet_sha256" if scope=="site" else "homepage_html_sha256",
                        "historical_backfill":True}
        })
    # Preserve technical test evidence as separate reviews; all are ingested, regardless of pass/fail.
    for item in [
       ("andaz-v1-axe-20261107","accessibility",False,legacy[0][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6703618644",
        ["166 contrast occurrences over 20 scans","68 accessible-name mismatch occurrences"]),
       ("andaz-v2-axe-20261107","accessibility",True,legacy[1][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6705380089",[]),
       ("andaz-v3-axe-20261107","accessibility",True,legacy[2][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6705885652",[]),
       ("andaz-v3-playwright-20261107","functional",True,legacy[2][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6705885652",[]),
       ("andaz-v3-lighthouse-20261107","performance",True,legacy[2][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6705885652",[]),
       ("andaz-v3-keyboard-20261107","ux",True,legacy[2][5],
        "https://github.com/karanzing1992/andaz-vibe-stay/issues/4#issuecomment-6705885652",[]),
    ]:
        review_id,kind,passed,digest,url,findings=item
        records.append({
            "project":"andaz-vibe-stay","review_id":review_id,"kind":kind,
            "scope":"homepage" if "v3" in review_id else "site",
            "reviewer":"independent_dell_browser_qa","passed":passed,
            "findings":findings,"source_url":url,"timestamp":"2026-11-07T11:00:00Z",
            "artifact_sha":digest,"evidence":{"historical_backfill":True,"public_audit_receipt":True}
        })
    return records

async def run(args):
    root=Path(args.root).expanduser()
    reg=init_registry(root)
    service=DesignKnowledge(reg)
    result=[]
    if args.stage in ("generic","all"):
        result.append(await service.index(*SEEDS[0][:2],SEEDS[0][2].read_text(),SEEDS[0][3]))
    if args.stage in ("types","all"):
        for scope,doc_id,path,source in SEEDS[1:]:
            result.append(await service.index(scope,doc_id,path.read_text(),source))
    if args.stage in ("brand","all"):
        original=Path(args.legacy_root).resolve()
        brief=original/"ANDAZ_BRAND_FUNCTION_SCOPE.md"
        if not brief.is_file():
            raise FileNotFoundError("EXPLICIT_LEGACY_BRAND_SOURCE_NOT_FOUND")
        result.append(await service.index(Scope("brand","andaz"),"andaz_owner_brief_20261107",
                                         brief.read_text(),"internal://andaz/owner-approved-brand-brief"))
    if args.stage in ("project","all"):
        original=Path(args.legacy_root).resolve()
        names=(
            ("ANDAZ_COMBINED_AUDIT_SHORTCOMINGS_20261107.md","andaz_historical_defects"),
            ("ANDAZ_DEFAULT_UI_UX_ART_AUDIT_STANDARD_V1.md","andaz_existing_review_standard"),
            ("ANDAZ_EXTERNAL_UI_UX_COLOR_ART_DIRECTION_HOME95_20261107.md","andaz_home95_creative_iteration")
        )
        for filename,doc_id in names:
            source=original/"knowledge"/filename
            if not source.is_file():
                raise FileNotFoundError("SOURCE_EVIDENCE_MISSING_"+filename)
            result.append(await service.index(Scope("project","andaz-vibe-stay"),doc_id,
                       source.read_text(),"internal://andaz/legacy-quality-evidence"))
    if args.stage in ("reviews","all"):
        ledger=ReviewLedger(reg)
        for receipt in legacy_reviews():
            ledger.submit(receipt)
        rr=await ledger.reconcile("andaz-vibe-stay")
        result.append({"historical_reviews":rr})
        if ledger.pending("andaz-vibe-stay"):
            raise RuntimeError("REVIEW_BACKFILL_NOT_FULLY_INDEXED")
    json_print={"status":"PASS","stage":args.stage,"results":result,
        "scope_graphs":service.layer_status("andaz-vibe-stay"),
        "review_backlog":len(ReviewLedger(reg).pending("andaz-vibe-stay"))}
    receipt_dir=root/"receipts"
    receipt_dir.mkdir(exist_ok=True,parents=True,mode=0o700)
    p=receipt_dir/("bootstrap_"+args.stage+".json")
    p.write_text(json.dumps(json_print,indent=2))
    p.chmod(0o600)
    print(json.dumps(json_print,indent=2))

def main():
    p=argparse.ArgumentParser(description="Seed independent Design RAG layers from source files")
    p.add_argument("--root",required=True)
    p.add_argument("--legacy-root",required=True,help="Existing Andaz LightRAG owner workspace; READ ONLY")
    p.add_argument("--stage",choices=["generic","types","brand","project","reviews","all"],default="all")
    args=p.parse_args()
    asyncio.run(run(args))

if __name__=="__main__":main()
