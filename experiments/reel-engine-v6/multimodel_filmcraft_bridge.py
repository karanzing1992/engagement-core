#!/usr/bin/env python3
"""MAD V6 free Gemini Flash -> Groq 120B -> Groq 20B film editing-plan bridge.

No model executes shell, writes to timeline, downloads footage or publishes.
Run offline --fixture for certification; live requires explicit approved API gate.
MLT Framework with frei0r is the V6 video/audio renderer.
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request
import urllib.error
import time

from v6_contract import (V6Blocked, read_config, validate_source_manifest,
                         select_free_flash_model,free_flash_models)
from gemini_pro_preflight import adapter as legacy_adapter, discover_models
from audio_library_v6 import resolve_audio

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/"
ALLOWED_EFFECTS = {"color_grade", "lumetri", "blur", "gaussian_blur",
                   "motion", "zoom", "title", "caption", "audio_gain"}
MODEL_JSON_MAX = 25000

class FreeModelTemporarilyUnavailable(V6Blocked):
    pass


def sha_json(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def decode_json(text):
    if not isinstance(text,str) or len(text)>MODEL_JSON_MAX:
        raise V6Blocked("Model JSON missing or over size budget")
    clean=text.strip()
    if clean.startswith("```"):
        clean=re.sub(r"^```(?:json)?\s*|\s*```$","",clean,flags=re.I)
    try:
        data=json.loads(clean)
    except json.JSONDecodeError as exc:
        raise V6Blocked("Model response was not JSON") from exc
    if not isinstance(data,dict):
        raise V6Blocked("Model returned non-object")
    return data


def post_json(url, headers, payload, timeout=50):
    if not (url==GROQ_ENDPOINT or
            url.startswith(GEMINI_ENDPOINT) and url.endswith(":generateContent")):
        raise V6Blocked("Inference URL not allowlisted")
    raw=json.dumps(payload,separators=(",",":")).encode()
    cap=5*1024*1024 if url.startswith(GEMINI_ENDPOINT) else 50000
    if len(raw)>cap:
        raise V6Blocked("Model request too large")
    req=urllib.request.Request(url,data=raw,headers={
        **headers, "Content-Type":"application/json", "Accept":"application/json",
        "User-Agent":"MAD-ReelEngine-V6-owner-private"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            data=response.read(400001)
    except urllib.error.HTTPError as exc:
        if exc.code in (429,500,502,503,504):
            raise FreeModelTemporarilyUnavailable("Free model endpoint temporarily unavailable: HTTP "+str(exc.code)) from None
        raise V6Blocked("Model API request rejected; provider response redacted") from None
    except Exception as exc:
        raise V6Blocked("Model API rejected or timed out; details redacted") from exc
    if len(data)>400000:
        raise V6Blocked("Provider response too large")
    try:
        return json.loads(data)
    except (ValueError,UnicodeDecodeError) as exc:
        raise V6Blocked("Provider response not parseable") from exc


def gemini_research(source, brief, *, approved_api_cost=False, frames=None, guidance=None):
    owner_ok=os.environ.get("GEMINI_INFERENCE_OWNER_APPROVED")=="true"
    tier_ok=os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")=="true"
    if not approved_api_cost or not (tier_ok and owner_ok):
        raise V6Blocked("Owner approval for allowlisted Gemini Flash request required")
    key=os.environ.get("GEMINI_API_KEY")
    if not key:
        raise V6Blocked("Gemini free-tier API key not present")
    available=discover_models(key,legacy_adapter())
    models=free_flash_models(available)
    if not models:raise V6Blocked("No approved free Gemini Flash model available")
    # Frame sampling uses FilmCraft-native exports; only three consented stills, no private URLs.
    facts=[{"id":s["id"],"observed":s["visible"],
            "start_seconds":s["start_seconds"],
            "duration_seconds":s["duration_seconds"]} for s in source["shots"]]
    prompt=("You are the source-intelligence analyst for a private cinematic reel. "
            "Use ONLY the human-verified facts; never invent unseen footage, people, "
            "brands or medical claims. Reply with JSON object: "
            "{\"observations\":[{\"shot_id\":\"s1\",\"visible\":\"source-grounded observation\"}],"
            "\"research_scope\":\"grounded creative context\"}. "
            "Every source shot must appear exactly once. Creative brief: "+
            brief[:1800]+"\nVerified input: "+json.dumps(facts)+
            "\nRetrieved Reel craft advice (not source facts): "+(guidance or "")[:1750])
    parts=[{"text":prompt}]
    if frames:
        if source.get("external_ai_processing_consent") is not True or len(frames)>3:
            raise V6Blocked("Explicit still-image processing consent and frame count required")
        for frame in frames:
            if (frame.get("mime_type")!="image/jpeg" or not isinstance(frame.get("data"),str)
                or len(frame["data"])>4*1024*1024 or not isinstance(frame.get("time_seconds"),(float,int))):
                raise V6Blocked("Gemini frame payload malformed")
            parts.append({"text":"Source frame at "+str(frame["time_seconds"])+" seconds; describe only visible content."})
            parts.append({"inline_data":{"mime_type":"image/jpeg","data":frame["data"]}})
    result=None
    model=None
    for candidate in models[:5]:
        for attempt in range(2):
            try:
                result=post_json(GEMINI_ENDPOINT+candidate+":generateContent",
                     {"x-goog-api-key":key},
                     {"contents":[{"parts":parts}],
                      "generationConfig":{"responseMimeType":"application/json",
                                          "temperature":0.2,"maxOutputTokens":1400}},timeout=30)
                model=candidate
                break
            except FreeModelTemporarilyUnavailable:
                if attempt==0:time.sleep(2)
            except V6Blocked as exc:
                # Transient transport failures also deserve the same bounded
                # free-tier retry; consent/auth/invalid-output failures do not.
                if str(exc)!="Model API rejected or timed out; details redacted":
                    raise
                if attempt==0:time.sleep(2)
        if result is not None:break
    if result is None:
        raise V6Blocked("All currently available free Flash candidate endpoints were unavailable")
    try:
        answer=result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError,IndexError,TypeError) as exc:
        raise V6Blocked("Gemini Flash returned no usable source observations") from exc
    return model,decode_json(answer)


def groq_call(model, prompt, *, temperature, max_tokens, response_format=None):
    key=os.environ.get("REEL_ENGINE_KEY") or os.environ.get("GROQ_API_KEY")
    if not key:
        raise V6Blocked("Existing Groq secret not provided to runner")
    result=post_json(GROQ_ENDPOINT,{"Authorization":"Bearer "+key},
                     {"model":model,"messages":[
                         {"role":"system","content":"Return strict JSON only. Never request shell commands. Source facts override creative claims."},
                         {"role":"user","content":prompt[:14500]}],
                      "temperature":temperature,"max_completion_tokens":max_tokens,
                      "response_format":response_format or {"type":"json_object"}},timeout=65)
    try:
        return decode_json(result["choices"][0]["message"]["content"])
    except (KeyError,IndexError,TypeError) as exc:
        raise V6Blocked("Groq response lacks validated JSON") from exc



def gemini_music_choice(_model, prompt, *, temperature=0.1, max_tokens=220):
    """Free-tier, owner-approved metadata-only music choice after Groq exhaustion.

    The upstream discovery layer still validates the exact candidate ID, and
    this function cannot download media, approve licenses or publish.
    """
    if (os.environ.get("GEMINI_INFERENCE_OWNER_APPROVED")!="true" or
        os.environ.get("GEMINI_PROJECT_FREE_TIER_VERIFIED")!="true"):
        raise V6Blocked("Owner approval for allowlisted Gemini Flash request required")
    key=os.environ.get("GEMINI_API_KEY")
    if not key:
        raise V6Blocked("Gemini free-tier API key not present")
    available=free_flash_models(discover_models(key,legacy_adapter()))
    if not available:
        raise V6Blocked("No approved free Gemini Flash model available")
    for candidate in available[:2]:
        try:
            payload=post_json(GEMINI_ENDPOINT+candidate+":generateContent",
                {"x-goog-api-key":key},
                {"contents":[{"parts":[{"text":prompt[:4500]}]}],
                 "generationConfig":{"responseMimeType":"application/json",
                                     "temperature":0.1,"maxOutputTokens":256}},timeout=25)
            answer=payload["candidates"][0]["content"]["parts"][0]["text"]
            return decode_json(answer)
        except (FreeModelTemporarilyUnavailable,KeyError,IndexError,TypeError):
            continue
        except V6Blocked as error:
            if str(error)=="Model API rejected or timed out; details redacted":
                continue
            raise
    raise V6Blocked("All currently available free Flash candidate endpoints were unavailable")


def validate_observations(source, research):
    observations=research.get("observations")
    by_source={s["id"]:s for s in source["shots"]}
    if not isinstance(observations,list) or len(observations)!=len(by_source):
        raise V6Blocked("Research has missing or fabricated shot IDs")
    seen=set()
    for s in observations:
        if not isinstance(s,dict) or s.get("shot_id") not in by_source:
            raise V6Blocked("Research uses unknown shot")
        if s["shot_id"] in seen:
            raise V6Blocked("Duplicate research shot")
        seen.add(s["shot_id"])
        desc=s.get("visible")
        if not isinstance(desc,str) or not 5<=len(desc)<=1000:
            raise V6Blocked("Research observations must be grounded and bounded")
    scope=research.get("research_scope")
    if not isinstance(scope,str) or not 10<=len(scope)<=2000:
        raise V6Blocked("Grounded research scope required")
    return research


def validate_director(source, proposal):
    if not isinstance(proposal,dict):
        raise V6Blocked("Director storyboard required")
    hook=proposal.get("hook")
    segments=proposal.get("segments")
    if not isinstance(hook,str) or not 1<=len(hook)<=90:
        raise V6Blocked("Opening hook missing")
    if not isinstance(segments,list) or not 1<=len(segments)<=16:
        raise V6Blocked("Director must produce one to sixteen source-grounded segments")
    by_source={s["id"]:s for s in source["shots"]}
    for seg in segments:
        if not isinstance(seg,dict) or seg.get("shot_id") not in by_source:
            raise V6Blocked("Director referenced imaginary shot")
        effects=seg.get("effects")
        if not isinstance(effects,list) or len(effects)>16:
            raise V6Blocked("Effects must be bounded list")
        for e in effects:
            if not isinstance(e,dict) or e.get("name") not in ALLOWED_EFFECTS:
                raise V6Blocked("Unsupported FilmCraft effect requested")
            if not isinstance(e.get("parameters",{}),dict):
                raise V6Blocked("Effect parameters must be structured")
        shot=by_source[seg["shot_id"]]
        if not (type(seg.get("start_seconds")) in (float,int)
                and type(seg.get("duration_seconds")) in (float,int)
                and shot["start_seconds"]<=seg["start_seconds"]
                and seg["duration_seconds"]>=0.4
                and seg["start_seconds"]+seg["duration_seconds"] <=
                      shot["start_seconds"]+shot["duration_seconds"]+0.001):
            raise V6Blocked("Director invented edit time outside reviewed footage")
    if sum(s["duration_seconds"] for s in segments)>120:
        raise V6Blocked("Planned reel exceeds 120 seconds")
    return proposal


# The external reviewer judges creative feasibility; the application owns
# proposal identity, ordered segment indices and the cryptographic digest.
_REVIEW_REASONS = ("APPROVED","UNSUPPORTED_EFFECT","SOURCE_UNVERIFIED",
                   "OUT_OF_BOUNDS","RIGHTS_CONSENT_MISSING","OTHER")

def strict_review_response_format(proposal):
    validate_segments=proposal.get("segments")
    if not isinstance(validate_segments,list) or not 1<=len(validate_segments)<=16:
        raise V6Blocked("Director storyboard required")
    segment_schema={
        "type":"object",
        "properties":{
            "approved":{"type":"boolean"},
            "reason_code":{"type":"string","enum":list(_REVIEW_REASONS)}},
        "required":["approved","reason_code"],
        "additionalProperties":False}
    keys=["s"+str(i) for i in range(len(validate_segments))]
    return {"type":"json_schema","json_schema":{
        "name":"mad_v61_independent_editor_review",
        "strict":True,
        "schema":{
            "type":"object",
            "properties":{
                "approved":{"type":"boolean"},
                "decisions":{"type":"object",
                             "properties":{key:segment_schema for key in keys},
                             "required":keys,
                             "additionalProperties":False}},
            "required":["approved","decisions"],
            "additionalProperties":False}}}

def bind_strict_review_to_plan(proposal,raw_review):
    """Never allow the model to supply a digest, segment index or approval default.

    Strict schema gives syntax/shape; we independently check semantics and
    explicitly distinguish rejection from malformed or contradictory verdicts.
    """
    spec=strict_review_response_format(proposal)["json_schema"]["schema"]
    if not isinstance(raw_review,dict) or set(raw_review)!={"approved","decisions"}:
        raise V6Blocked("Strict reviewer response invalid")
    if type(raw_review["approved"]) is not bool:
        raise V6Blocked("Strict reviewer response invalid")
    declared=raw_review["decisions"]
    keys=list(spec["properties"]["decisions"]["required"])
    if not isinstance(declared,dict) or set(declared)!=set(keys):
        raise V6Blocked("Strict reviewer response invalid")
    decisions=[]
    any_rejection=False
    for index,key in enumerate(keys):
        v=declared[key]
        if not isinstance(v,dict) or set(v)!={"approved","reason_code"}:
            raise V6Blocked("Strict reviewer response invalid")
        approved,reason=v["approved"],v["reason_code"]
        if type(approved) is not bool or reason not in _REVIEW_REASONS:
            raise V6Blocked("Strict reviewer response invalid")
        if approved and reason!="APPROVED":
            raise V6Blocked("Strict reviewer response invalid")
        if not approved:
            any_rejection=True
        decisions.append({"segment_index":index,"approved":approved})
    if raw_review["approved"] is False or any_rejection:
        raise V6Blocked("Independent reviewer rejected proposed edit")
    return {"approved":True,
            # Hash is *computed here*, never copied from model response.
            "director_plan_sha256":sha_json(proposal),
            "segment_decisions":decisions,
            "strict_schema_verified":True}

def groq_strict_review(source,proposal,*,on_stage=None,guidance=None):
    validate_source_manifest(source,external_gemini_frames=False)
    validate_director(source,proposal)
    for segment in proposal["segments"]:
        for effect in segment["effects"]:
            if effect["name"] not in ("color_grade","title","caption"):
                raise V6Blocked("Unsupported FFmpeg effect requested")
            if effect["name"] in ("title","caption"):
                line=effect.get("parameters",{}).get("text","")
                if not isinstance(line,str) or not 1<=len(line.strip())<=90:
                    raise V6Blocked("FFmpeg title text invalid")
    if on_stage:on_stage("groq_reviewer")
    prompt=("Independently assess the exact immutable video edit plan for "
            "source-grounding, rights/consent, usable timecodes and actual "
            "FFmpeg effects. Respond in the required strict JSON schema. "
            "Use approved=true and reason_code=APPROVED for each safe segment. "
            "Reject unsafe or infeasible segments using approved=false and a "
            "specific reason code. Overall approved must be false if ANY segment "
            "is rejected. Do not copy hashes, assign indices, modify footage, "
            "invent shots, or assume approval. The application binds decisions "
            "to the exact plan and source independently. Supported FFmpeg effects "
            "are color_grade, title, caption. A title/caption needs text. "
            "Owner-verified source rights and consent metadata: "+json.dumps({
                "human_reviewed":source["human_reviewed"],
                "rights_and_consent_cleared":source["rights_and_consent_cleared"],
                "external_ai_processing_consent":source["external_ai_processing_consent"]})+
            " Verified source: "+json.dumps(source["shots"])+
            " Immutable director proposal: "+json.dumps(proposal)+
            "\nRetrieved technical Reel checks (advisory only): "+(guidance or "")[:1750])
    raw=groq_call("openai/gpt-oss-20b",prompt,temperature=0.1,
                  max_tokens=1900,
                  response_format=strict_review_response_format(proposal))
    return bind_strict_review_to_plan(proposal,raw)

def reviewer_schema_needs_retry(proposal,review):
    """Only malformed metadata in an explicit reviewer approval can be retried.
    Never retry/override explicit rejection by reviewer or any segment.
    """
    if not isinstance(review,dict) or review.get("approved") is not True:
        return False
    decisions=review.get("segment_decisions")
    if isinstance(decisions,list) and any(
        isinstance(d,dict) and d.get("approved") is False for d in decisions):
        return False
    segments=proposal.get("segments",[])
    if review.get("director_plan_sha256")!=sha_json(proposal):
        return True
    if not isinstance(decisions,list) or len(decisions)!=len(segments):
        return True
    return any(not isinstance(d,dict) or d.get("segment_index")!=i or
               d.get("approved") is not True
               for i,d in enumerate(decisions))

def compile_reviewed_edl(source, proposal, review):
    validate_director(source,proposal)
    if review.get("approved") is not True or review.get("director_plan_sha256")!=sha_json(proposal):
        raise V6Blocked("Groq 20B review missing or director hash mismatch")
    decision=review.get("segment_decisions")
    segments=proposal["segments"]
    if not isinstance(decision,list) or len(decision)!=len(segments):
        raise V6Blocked("Editor-review per-segment approval incomplete")
    cuts=[];operations=[];ids=set()
    for index,(seg,d) in enumerate(zip(segments,decision)):
        if not isinstance(d,dict) or d.get("segment_index")!=index or d.get("approved") is not True:
            raise V6Blocked("Editor rejected one or more proposed FilmCraft edits")
        cuts.append({"start":seg["start_seconds"],
                     "seconds":seg["duration_seconds"],"source_index":index})
        current=[]
        for j,e in enumerate(seg["effects"]):
            eid=f"v6_s{index:02d}_e{j:02d}"
            if eid in ids:
                raise V6Blocked("Duplicate creative instruction identifier")
            ids.add(eid)
            current.append({"id":eid,"name":e["name"],"parameters":e.get("parameters",{})})
        operations.append(current)
    return {"cuts":cuts,"operations":operations,"hook":proposal["hook"],
            "requested_effects":sum(map(len,operations)),
            "director_sha256":sha_json(proposal),"review_sha256":sha_json(review),
            "editor":"FFmpeg","source":source["source_sha256"],
            "artistic_approval":False}


def fixture_chain(source, brief):
    # Deterministic synthetic planning; NOT a claim that providers ran.
    research={"observations":[{"shot_id":s["id"],"visible":s["visible"]}
                              for s in source["shots"]],
              "research_scope":"Synthetic offline editorial planning using verified source descriptions."}
    s=source["shots"][0]
    proposal={"hook":"MOKSHA - SYNTHETIC TEST",
              "segments":[{"shot_id":s["id"],"start_seconds":s["start_seconds"],
                           "duration_seconds":min(2.0,s["duration_seconds"]),
                           "effects":[{"name":"color_grade","parameters":{"contrast":12}}]}]}
    review={"approved":True,"director_plan_sha256":sha_json(proposal),
            "segment_decisions":[{"segment_index":0,"approved":True}]}
    return research,proposal,review


def run(*,source,brief,brand="",mode="fixture",audio_mode="source_ambience_only",
        approved_api_cost=False,frames=None,on_stage=None,guidance=None,music_candidates=None):
    read_config()
    validate_source_manifest(source,external_gemini_frames=bool(frames))
    if not isinstance(brief,str) or not 8<=len(brief)<=2000:
        raise V6Blocked("Human creative prompt missing")
    if not isinstance(brand,str) or len(brand)>1800:
        raise V6Blocked("Optional generic product context invalid")
    audio=resolve_audio(audio_mode)
    guidance=guidance or {}
    if not isinstance(guidance,dict):raise V6Blocked("Retrieved guidance input invalid")
    music_candidates=music_candidates or []
    if not isinstance(music_candidates,list) or len(music_candidates)>8:
        raise V6Blocked("Music shortlist invalid")
    music_ids={v.get("id") for v in music_candidates if isinstance(v,dict) and isinstance(v.get("id"),str)}
    if mode=="fixture":
        model_ids={"gemini":"FIXTURE","groq_director":"FIXTURE","groq_reviewer":"FIXTURE"}
        research,proposal,review=fixture_chain(source,brief)
    elif mode=="live":
        if not approved_api_cost:
            raise V6Blocked("Gemini API project free tier not confirmed")
        if on_stage:on_stage("gemini_research")
        model,research=gemini_research(source,brief,approved_api_cost=True,frames=frames,
                                       guidance=guidance.get("research",{}).get("context",""))
        model_ids={"gemini":model,"groq_director":"openai/gpt-oss-120b",
                   "groq_reviewer":"openai/gpt-oss-20b"}
        validate_observations(source,research)
        prompt=("Product context (optional): "+(brand or "generic creative content")+"\nOwner brief: "+brief+"\nValidated research: "+
                json.dumps(research)+"\nExact verified shots: "+json.dumps(source["shots"])+
                "\nReturn JSON: {\"hook\":string<=90,\"segments\":[{\"shot_id\":id,"
                "\"start_seconds\":number,\"duration_seconds\":number,"
                "\"effects\":[{\"name\":one of color_grade/title/caption,\"parameters\":object}]}]. "
                "No invented timecodes/people. FFmpeg only; no music invented."+ 
                "\nRetrieved Reel craft advice (advisory only): "+
                guidance.get("director",{}).get("context","")[:1750]+
                ("\nUntrusted metadata-only eligible music shortlist: "+json.dumps(music_candidates,ensure_ascii=True)[:2000]+
                 "\nAlso return music_candidate_id as EXACT id from this shortlist; do not infer rights or download." if music_candidates else ""))
        if on_stage:on_stage("groq_director")
        proposal=groq_call("openai/gpt-oss-120b",prompt,temperature=0.7,max_tokens=1800)
        validate_director(source,proposal)
        review=groq_strict_review(source,proposal,on_stage=on_stage,
                                  guidance=guidance.get("reviewer",{}).get("context",""))
    else:
        raise V6Blocked("Unknown V6 inference mode")
    validate_observations(source,research)
    if on_stage:on_stage("edl_compile")
    output=compile_reviewed_edl(source,proposal,review)
    if music_ids and proposal.get("music_candidate_id") in music_ids:
        output["music_candidate_id"]=proposal["music_candidate_id"]
        output["music_choice_role"]="groq_director_integrated"
    output.update({"model_roles":model_ids,
                   "live_model_inference":mode=="live","source_rights_admitted":True,
                   "audio_mode":audio["mode"],"audio_approved":audio_mode!="licensed_music",
                   "owner_approval":False,"published":False,
                   "renderer_invoked":False,"native_visual_qa":False,
                   "created_at":datetime.now(timezone.utc).isoformat()})
    return output


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-manifest",required=True)
    ap.add_argument("--brief",required=True)
    ap.add_argument("--brand",required=True)
    ap.add_argument("--output",required=True)
    ap.add_argument("--mode",choices=("fixture","live"),default="fixture")
    ap.add_argument("--confirm-free-api",action="store_true",help="Operator confirms the separate API key is in the Gemini Free tier; requires GEMINI_PROJECT_FREE_TIER_VERIFIED=true")
    args=ap.parse_args()
    source=json.loads(Path(args.source_manifest).read_text())
    result=run(source=source,brief=args.brief,brand=args.brand,
               mode=args.mode,approved_api_cost=args.confirm_free_api)
    Path(args.output).write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"v6_plan":"PASS","mode":args.mode,
                      "models_called":result["live_model_inference"],
                      "editor":result["editor"],"published":False}))


if __name__=="__main__":
    try:
        main()
    except (V6Blocked,OSError,ValueError,KeyError) as exc:
        print("MAD_V6_MODEL_CHAIN_BLOCKED",type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
