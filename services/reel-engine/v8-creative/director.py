"""V8 declarative creative direction, ranked treatments and strict owner-rule compiler."""
from __future__ import annotations
import hashlib,json,math
from intelligence import SourceBlocked

TREATMENTS={
 "human_story":{"dialogue":5,"many_scenes":1,"source_led":2,"cinematic":2,"transition":"dip-to-black",
                "arc":["human hook","natural progression","thoughtful close"]},
 "observational_cinema":{"dialogue":2,"many_scenes":2,"source_led":4,"cinematic":5,"transition":"dip-to-black",
                "arc":["visual immersion","emotional development","lingering resolution"]},
 "rhythmic_montage":{"dialogue":-5,"many_scenes":5,"source_led":1,"cinematic":2,"transition":"dissolve",
                "arc":["energetic hook","rhythmic expansion","strong finish"]},
 "minimal_editorial":{"dialogue":2,"many_scenes":0,"source_led":4,"cinematic":1,"transition":"cut",
                "arc":["direct entrance","uninterrupted observation","clean closing"]}
}
TRANSITIONS={"cut","dip-to-black","dissolve"}
GRADES={"natural","cinematic_warm","soft_contrast","monochrome"}
ALLOWED_KEYS={"treatment","segments","audio","reasoning_summary","captions","concept","music_candidate_id"}
class CreativeBlocked(ValueError):pass

def rank_treatments(evidence):
    owner=evidence["owner_intent"]; scene_count=len(evidence["shots"])
    def score(name,p):
        return p["dialogue"]*bool(owner["dialogue_priority"])+p["many_scenes"]*(scene_count>=3)+p["cinematic"]*(owner["tone"]=="cinematic")+p["source_led"]*(owner["tone"]=="source_led")
    return [{"id":name,"score":score(name,rule),"story_arc":rule["arc"]} for name,rule in
        sorted(TREATMENTS.items(),key=lambda it:(-score(*it),it[0]))]

def director_prompt(evidence,guidance=None):
    """Send through existing owner-approved Groq/Gemini adapter; never issue calls here."""
    g=guidance or {}
    if any(k not in ("universal","brand","feedback") for k in g):raise CreativeBlocked("V8_RAG_LAYERS_INVALID")
    for k in g:
        if not isinstance(g[k],str) or len(g[k])>2200:raise CreativeBlocked("V8_RAG_TEXT_INVALID")
    snapshot={"source":{"duration":evidence["source"]["duration"],
      "has_audio":evidence["source"]["has_audio"],"shots":evidence["shots"],
      "quiet_intervals":evidence["quiet_intervals"],"visual_observations":evidence.get("visual_observations",[])[:5]},"constraints":evidence["owner_intent"],
      "ranked_treatments":rank_treatments(evidence),"guidance":g}
    return ("You are an independent documentary film director, not a generic template generator. "
      "Do not invent visual content, spoken words, emotions or people. Treat source evidence as facts and the owner brief as binding. "
      "Return ONLY JSON with treatment, segments[{start,end,transition,grade,text}], "
      "reasoning_summary, audio{preserve_source,music_gain}. "
      "Select an editorial treatment deliberately. For requested preserved dialogue, retain all source timecodes "
      "and original speech without trimming, time-stretch or fades. When speech timing is unknown, never cut source audio. "
      "Transitions must be purposeful, not decorative. Never claim that a proposal or render passed visual review. "
      "Allowed treatments: "+",".join(TREATMENTS)+". Allowed transitions: "+",".join(TRANSITIONS)+
      ". Allowed grades: "+",".join(GRADES)+". Evidence: "+json.dumps(snapshot,sort_keys=True))

def fallback_plan(evidence):
    """Non-AI safe baseline. Explicitly labelled, never represented as creative certification."""
    duration=evidence["source"]["duration"];owner=evidence["owner_intent"]
    treatment=rank_treatments(evidence)[0]["id"]
    # Scene cuts become editing boundaries while original soundtrack remains continuous.
    boundaries=[float(s["start"]) for s in evidence["shots"][1:]]
    if len(boundaries)==0 and duration>16 and owner["transitions_allowed"]:
        # Editorial chapter boundaries, not falsely detected semantic scene cuts.
        boundaries=[duration/3,2*duration/3]
    boundaries=[0.0,*boundaries,duration]
    style=TREATMENTS[treatment]["transition"]
    if owner["dialogue_priority"] and style=="dissolve":style="dip-to-black"
    return {"treatment":treatment,"concept":"Source-led evidence-safe editorial baseline",
       "reasoning_summary":"Non-AI fallback; creative review required",
       "segments":[{"start":round(a,4),"end":round(b,4),
          "transition":"cut" if not i or not owner["transitions_allowed"] else style,
          "grade":"natural","text":None} for i,(a,b) in enumerate(zip(boundaries,boundaries[1:]))],
       "audio":{"preserve_source":owner["keep_source_audio"],
                "music_gain":0.06 if owner["dialogue_priority"] else (0.12 if owner["music_allowed"] else 0.0)},
       "captions":[]}

def compile_optional_presentation(evidence,proposal):
    """Non-semantic model-output compiler; preserve facts and owner constraints.

    The director may propose imaginative visual styling, but invalid optional
    transition/overlay tokens are NOT allowed to abort an otherwise source-safe
    timeline. Fail-closed constraints on timecodes, dialogue audio, permissions,
    music levels and source provenance are validated separately and never
    auto-corrected here. Receipt explicitly records every alteration.
    """
    if not isinstance(proposal,dict):
        raise CreativeBlocked("V8_DIRECTOR_NON_OBJECT")
    result=dict(proposal)
    segments=result.get("segments")
    if not isinstance(segments,list) or not 1<=len(segments)<=16:
        raise CreativeBlocked("V8_SEGMENT_COUNT")
    owner=evidence["owner_intent"];adjustments=[]
    clean=[]
    for index,original in enumerate(segments):
        if not isinstance(original,dict):
            raise CreativeBlocked("V8_SEGMENT_FIELDS")
        segment=dict(original)
        transition=segment.get("transition")
        if index==0 and transition!="cut":
            segment["transition"]="cut"
            adjustments.append({"segment":index,"field":"transition","reason":"first_boundary_has_no_previous_shot"})
        elif transition not in TRANSITIONS:
            segment["transition"]="cut"
            adjustments.append({"segment":index,"field":"transition","reason":"unimplemented_transition_rejected"})
        if index>0 and not owner["transitions_allowed"] and segment.get("transition")!="cut":
            # Owner explicitly requested no transitions. Do not render a
            # stylistic substitution, and record why this effect was discarded.
            segment["transition"]="cut"
            adjustments.append({"segment":index,"field":"transition","reason":"owner_explicitly_requested_no_transitions"})
        elif index>0 and segment.get("transition")=="dissolve" and owner["keep_source_audio"]:
            # Xfade changes source-video length. Do not retime continuous
            # dialogue/audio just to satisfy an optional transition style.
            segment["transition"]="dip-to-black"
            adjustments.append({"segment":index,"field":"transition","reason":"continuous_source_audio_takes_precedence"})
        text=segment.get("text")
        if text is not None and (
            not isinstance(text,str) or not 1<=len(text.strip())<=90
            or any(ord(c)<32 for c in text)
            or owner["dialogue_priority"]
        ):
            segment["text"]=None
            adjustments.append({"segment":index,"field":"text","reason":"unsafe_or_unverified_overlay_not_rendered"})
        if segment.get("grade") not in GRADES:
            segment["grade"]="natural"
            adjustments.append({"segment":index,"field":"grade","reason":"unimplemented_grade_rejected"})
        clean.append(segment)
    result["segments"]=clean
    return result,adjustments


def validate_plan(evidence,proposal):
    if not isinstance(proposal,dict) or set(proposal)-ALLOWED_KEYS:raise CreativeBlocked("V8_DIRECTOR_UNTRUSTED_FIELDS")
    if proposal.get("treatment") not in TREATMENTS:raise CreativeBlocked("V8_TREATMENT_INVALID")
    segments=proposal.get("segments")
    if not isinstance(segments,list) or not 1<=len(segments)<=16:raise CreativeBlocked("V8_SEGMENT_COUNT")
    owner=evidence["owner_intent"]; duration=evidence["source"]["duration"];last=0.0
    for i,s in enumerate(segments):
        if not isinstance(s,dict) or set(s)-{"start","end","transition","grade","text"}:
            raise CreativeBlocked("V8_SEGMENT_FIELDS")
        a,b=s.get("start"),s.get("end")
        if (type(a) not in (int,float) or type(b) not in (int,float) or
            not math.isfinite(a) or not math.isfinite(b) or a<0 or b-a<0.5 or b>duration+.05):
            raise CreativeBlocked("V8_SEGMENT_TIME")
        if a<last-.05:raise CreativeBlocked("V8_SEGMENT_OVERLAP")
        if (owner["dialogue_priority"] or owner["preserve_full_source"]) and abs(a-last)>.05:
            raise CreativeBlocked("V8_PROTECTED_DURATION_GAP")
        last=b
        if s.get("transition") not in TRANSITIONS or (not i and s.get("transition")!="cut"):
            raise CreativeBlocked("V8_TRANSITION_INVALID")
        if not owner["transitions_allowed"] and s["transition"]!="cut":
            raise CreativeBlocked("V8_TRANSITION_FORBIDDEN")
        if s.get("grade") not in GRADES:raise CreativeBlocked("V8_GRADE_INVALID")
        txt=s.get("text")
        if txt is not None and (not isinstance(txt,str) or len(txt)>90 or any(ord(c)<32 for c in txt)):
            raise CreativeBlocked("V8_TEXT_INVALID")
        if owner["dialogue_priority"] and s.get("text"):
            raise CreativeBlocked("V8_UNGROUNDED_DIALOGUE_TEXT")
    if (owner["dialogue_priority"] or owner["preserve_full_source"]) and abs(last-duration)>.1:
        raise CreativeBlocked("V8_PROTECTED_DURATION_SHORTENED")
    audio=proposal.get("audio")
    if not isinstance(audio,dict) or set(audio)!={"preserve_source","music_gain"}:
        raise CreativeBlocked("V8_AUDIO_SCHEMA")
    gain=audio["music_gain"]
    if type(gain) not in (float,int) or not 0<=gain<=.25:raise CreativeBlocked("V8_MUSIC_GAIN_INVALID")
    if owner["keep_source_audio"] and audio["preserve_source"] is not True:
        raise CreativeBlocked("V8_SOURCE_AUDIO_SUPPRESSED")
    if owner["dialogue_priority"] and gain>.08:raise CreativeBlocked("V8_MUSIC_MASKS_DIALOGUE")
    if not owner["music_allowed"] and gain!=0:raise CreativeBlocked("V8_UNWANTED_MUSIC")
    if not evidence["source"]["has_audio"] and audio["preserve_source"]:
        raise CreativeBlocked("V8_SOURCE_AUDIO_NOT_PRESENT")
    if not owner["transitions_allowed"] and any(s["transition"]!="cut" for s in segments):
        raise CreativeBlocked("V8_OWNER_TRANSITION_CONFLICT")
    if proposal.get("captions",[]) not in ([],None):raise CreativeBlocked("V8_UNGROUNDED_CAPTIONS")
    normalized={**proposal,"segments":segments,"audio":audio,"captions":[]}
    normalized["source_sha256"]=evidence["source"]["sha256"]
    normalized["creative_plan_sha256"]=hashlib.sha256(json.dumps(normalized,sort_keys=True).encode()).hexdigest()
    return normalized
