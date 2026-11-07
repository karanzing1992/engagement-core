"""V8 isolated creative loop. Real model inference and export require explicit owner lanes."""
from __future__ import annotations
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"v7-micro-rag"))
from intelligence import inspect,SourceBlocked
from director import director_prompt,fallback_plan,validate_plan,CreativeBlocked
from editor import render
from critic import inspect_output,decide_release

def v7_retrieval(brief,description,work):
    """Reuse native txtai for universal film rules, without mixing brand/private memory."""
    import txtai_reel_guidance as rag
    data=rag.collect(brief,description,Path(work),enable=True)
    if data.get("status")!="ready":raise CreativeBlocked("V8_REQUIRED_TXTAI_UNAVAILABLE")
    return {"universal":data["roles"]["director"]["context"]}, {
      "engine":"txtai","status":"ready",
      "director_ids":data["roles"]["director"]["ids"],
      "reviewer_ids":data["roles"]["reviewer"]["ids"]}

def execute(*,source,brief,workdir,output,music=None,music_rights=None,
            model_director=None,independent_reviewer=None,source_analyst=None,rag_loader=None,
            model_owner_approved=False,external_inference_consent=False,
            require_ai=False,require_rag=False,brand_id="generic",brand_rules=None,
            feedback_rules=None,width=1080,height=1920,fps=30,max_revisions=1):
    """Runs once in a private isolated workdir. No deployment, upload, publication or network by default."""
    work=Path(workdir).resolve()
    if not work.is_dir() or Path(source).resolve().parent!=work or Path(output).resolve().parent!=work:
        raise CreativeBlocked("V8_PRIVATE_MEDIA_ONLY")
    if not isinstance(brand_id,str) or len(brand_id)>64 or not brand_id.replace("-","").replace("_","").isalnum():
        raise CreativeBlocked("V8_BRAND_ID_INVALID")
    if not 0<=max_revisions<=2:raise CreativeBlocked("V8_REVISION_BUDGET_INVALID")
    evidence=inspect(source,brief)
    if source_analyst:
        if not (model_owner_approved and external_inference_consent):
            raise CreativeBlocked("V8_SOURCE_ANALYSIS_CONSENT_REQUIRED")
        evidence["consent_for_external_inference"]=True
        source_review=source_analyst(evidence,work)
        if (not isinstance(source_review,dict) or not source_review.get("inference_from_consent")
            or not isinstance(source_review.get("observations"),list)):
            raise CreativeBlocked("V8_SOURCE_MODEL_EVIDENCE_INVALID")
        evidence["visual_observations"]=source_review["observations"][:5]
        evidence["visual_semantics_status"]="CONSENTED_VISUAL_RESEARCH"
    if independent_reviewer and external_inference_consent:
        evidence["consent_for_external_inference"]=True
    rag_status={"status":"not_requested"}
    layers={}
    if rag_loader:
        layers,rag_status=rag_loader(brief,"source visual facts only",work)
    elif require_rag:
        layers,rag_status=v7_retrieval(brief,"source visual facts only",work)
    if require_rag and rag_status.get("status")!="ready":
        raise CreativeBlocked("V8_REQUIRED_RAG_NOT_READY")
    if brand_rules:
        if brand_id=="generic" or not isinstance(brand_rules,str):raise CreativeBlocked("V8_BRAND_ISOLATION_FAILED")
        layers["brand"]="Brand scope "+brand_id+": "+brand_rules[:1500]
    if feedback_rules:
        if not isinstance(feedback_rules,str):raise CreativeBlocked("V8_FEEDBACK_NOT_VERIFIED")
        layers["feedback"]="Owner-approved creative feedback: "+feedback_rules[:1500]
    if require_ai and not model_director:raise CreativeBlocked("V8_AI_DIRECTOR_UNAVAILABLE")
    if model_director and not (model_owner_approved and external_inference_consent):
        raise CreativeBlocked("V8_EXTERNAL_MODEL_CONSENT_REQUIRED")
    if independent_reviewer and not external_inference_consent:
        raise CreativeBlocked("V8_REVIEWER_EXTERNAL_CONSENT_REQUIRED")
    last_review=None
    for attempt in range(max_revisions+1):
        proposal=(model_director(director_prompt(evidence,layers),evidence,last_review)
                  if model_director else fallback_plan(evidence))
        if not isinstance(proposal,dict):raise CreativeBlocked("V8_DIRECTOR_NON_OBJECT")
        proposal=dict(proposal)
        if not music:proposal["audio"]=dict(proposal["audio"],music_gain=0.0)
        try:
            plan=validate_plan(evidence,proposal)
        except CreativeBlocked as invalid:
            # Explicit plan-repair pass (same allowlisted model) instead of a
            # deterministic replacement masquerading as an AI creative result.
            # Structural owner/source constraints stay binding; no rendering on
            # invalid plans and no open-ended retries.
            if model_director and attempt<max_revisions:
                last_review={"stage":"creative_plan_validation",
                    "validation_code":str(invalid),
                    "instruction":"Return a fully corrected JSON plan. First segment transition MUST be 'cut'. Subsequent transitions may be purposeful allowed styles. Preserve required original audio and all source timecodes. Do not invent source facts."}
                continue
            raise
        candidate=work/("v8-attempt-%d.mp4"%attempt)
        receipt=render(evidence,proposal,work,candidate,music=music,music_rights=music_rights,
           width=width,height=height,fps=fps)
        measured=inspect_output(evidence,plan,receipt,candidate)
        creative=None
        if independent_reviewer:
            # Reviewer must inspect actual bytes or frames/audio. A plan review is insufficient.
            try:
                creative=independent_reviewer(candidate,evidence,plan,measured)
            except CreativeBlocked as error:
                # Private preview is allowed with explicit PENDING status, never creative
                # certification. This prevents free-tier outages masquerading as approval.
                if str(error) not in ("V8_ACTUAL_REVIEW_PROVIDER_UNAVAILABLE",
                    "V8_NO_VERIFIED_FREE_REVIEWER_MODEL","V8_ACTUAL_REVIEW_SCHEMA_INVALID"):
                    raise
                creative={"verified_actual_media":False,"review_status":"PENDING_PROVIDER_UNAVAILABLE"}
            if not isinstance(creative,dict):
                raise CreativeBlocked("V8_ACTUAL_MEDIA_REVIEW_UNVERIFIED")
        release=decide_release(measured,independent_visual_audio_review=creative)
        last_review={"technical":measured,"artistic":creative}
        if release["creative_certified"] or attempt==max_revisions or not model_director:
            if candidate.resolve()!=Path(output).resolve():
                candidate.replace(output)
            return {"version":"v8-creative-beta","owner_brief":brief,"brand_id":brand_id,
             "creative_director":"external_model" if model_director else "deterministic_source_led_fallback",
             "rag":rag_status,"attempts":attempt+1,"source_evidence":{
               "duration":evidence["source"]["duration"],"has_audio":evidence["source"]["has_audio"],
               "scene_count":len(evidence["shots"]),"transcript_inferred":False},
             "plan":plan,"render":receipt,"independent_review":last_review,
             "release":release,"published":False,"owner_approval":False}
        candidate.unlink(missing_ok=True)
    raise AssertionError("unreachable")
