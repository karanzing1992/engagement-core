#!/usr/bin/env python3
"""Public Andaz screenshots to owner's authorized free Gemini API; no website writes."""
import os,json,base64,hashlib,urllib.request,urllib.error,sys,datetime,time
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='https://andaz-vibe-home-v3-review.vercel.app/'
API='https://generativelanguage.googleapis.com/v1beta'
OUT=Path(__file__).resolve().parent/'output'
SNAPS=[('home_desktop','index.html',1440,900),('home_mobile','index.html',390,844),('home_mobile_320','index.html',320,720)]
PROMPT="""Independent senior creative-director artistic review of Andaz Vibe Stay HOMEPAGE V3 ONLY.
Inspect 3 ACTUAL deployed browser screenshots in order: HOME desktop 1440x900, HOME mobile 390x844, HOME small mobile 320x720.
Andaz is a youth-oriented social hostel/coliving stay in Arambol Goa. The goal is a distinctive globally recognizable warm Goa/community aesthetic, not a corporate graphic. Andaz is NOT Moksha Wellness.
Historical Gemini V1 reviewed 54/100 REJECT and V2 reviewed 68/100 REVISE. Main V2 failures: desktop half hero empty, muted generic boutique retreat energy, mobile chip 'Illustrative artwork' looked like developer metadata, mixed CTA semantics.
This iteration targets artistic readiness >=95/100 but DO NOT INFLATE SCORES or APPROVE merely due to user's desired number.
Genuine Arambol street/beach atmosphere visuals are CC BY 4.0 editorial stock photos by Vyacheslav Argenberg, NOT photos of Andaz actual guests or the property. Copyright/credit is supplied on page. Do not treat these as proof of the property amenities, guest experiences or guaranteed bookings.
Inspect original artistic direction, headline legibility/copy, immediately recognizable destination, genuine editorial narrative, page frame continuity, image/crop quality, visual balance at 1440, hierarchy/legibility/button visibility at 390 and 320, CTA honest WhatsApp enquiry wording, and proof of physical hostel's identity via truthful media and copy.
Do not audit Rooms, Explore, Contact, Experiences. Do not infer the other pages' appearance.
Prior independent automation found zero critical axe violations and excellent Lighthouse scores, but your job is artistic critique on screenshots not accessibility compliance.
Return JSON ONLY with EXACT keys:
{
"verdict":"APPROVE|REVISE|REJECT",
"overall_artistic_score_100":0,
"subscores":{"identity":0,"typography":0,"palette":0,"layout":0,"mobile":0,"originality":0,"conversion":0},
"strengths":["up to 5 specific screenshot facts"],
"findings":[{"id":"F01","priority":"CRITICAL|HIGH|MEDIUM|LOW","screenshot":"home_desktop|home_mobile|home_mobile_320","visual_evidence":"what is visible, not a guess","guest_impact":"why it matters","precise_creative_fix":"bounded homepage-only improvement"}],
"proposed_hero_composition":"specific next hero art direction",
"proposed_design_system":{"typography":"...","palette":"...","visual_motifs":["..."],"layout_rules":"..."},
"final_release_conditions":["..."],
"confidence_limitations":["photos are Arambol atmosphere not Andaz property; screenshot-only"]
}
Evidence-first grading. Scores >=95 should be exceptional, not automatic. If 95 is not deserved, score accordingly and recommend precise refinements. No markdown fences, only JSON."""


def request(key,url,payload=None,timeout=22):
    if not url.startswith(API+'/'):raise RuntimeError('API_POLICY_DENIED')
    raw=None if payload is None else json.dumps(payload,separators=(',',':')).encode()
    h={'x-goog-api-key':key,'Accept':'application/json'}
    if raw is not None:h['Content-Type']='application/json'
    r=urllib.request.Request(url,data=raw,headers=h,method='POST' if raw else 'GET')
    try:
        with urllib.request.urlopen(r,timeout=timeout) as x:return json.loads(x.read(750000))
    except urllib.error.HTTPError as x:raise RuntimeError('GEMINI_HTTP_'+str(x.code)) from None
    except urllib.error.URLError:raise RuntimeError('GEMINI_TRANSPORT_ERROR') from None
def run():
    if os.getenv('GITHUB_REPOSITORY')!='karanzing1992/engagement-core' or os.getenv('GITHUB_REF')!='refs/heads/audit/andaz-gemini-vision-20261107':raise RuntimeError('REPO_BRANCH_BOUNDARY')
    if os.getenv('GEMINI_OWNER_FREE_ATTESTED')!='true' or os.getenv('GEMINI_OWNER_INFERENCE_APPROVED')!='true':raise RuntimeError('FREE_OWNER_POLICY')
    key=os.getenv('GEMINI_API_KEY','')
    if not key:raise RuntimeError('GEMINI_GITHUB_SECRET_ABSENT')
    OUT.mkdir(exist_ok=True)
    images=[]
    with sync_playwright() as pw:
        chrome=pw.chromium.launch(channel='chrome',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            for name,page,width,height in SNAPS:
                ctx=chrome.new_context(viewport={'width':width,'height':height},device_scale_factor=1,is_mobile=width<600,has_touch=width<600,reduced_motion='reduce')
                tab=ctx.new_page()
                response=tab.goto(BASE+page,wait_until='domcontentloaded',timeout=20000)
                if response is None or response.status!=200:raise RuntimeError('PUBLIC_PREVIEW_HTTP_FAILED')
                tab.wait_for_timeout(450)
                blob=tab.screenshot(type='jpeg',quality=78,full_page=False)
                if len(blob)>2000000:raise RuntimeError('SCREENSHOT_SIZE_LIMIT')
                (OUT/(name+'.jpg')).write_bytes(blob)
                images.append((name,blob,hashlib.sha256(blob).hexdigest()))
                ctx.close()
        finally:chrome.close()
    offered=request(key,API+'/models?pageSize=100',timeout=18)
    allowed=('gemini-3.6-flash','gemini-2.5-flash-lite')
    available={x.get('name','').split('/')[-1] for x in offered.get('models',[]) if 'generateContent' in x.get('supportedGenerationMethods',[])}
    model=next((x for x in allowed if x in available),None)
    if not model:raise RuntimeError('NO_APPROVED_FREE_FLASH_MODEL')
    print('GEMINI_ALLOWED_MODEL_SELECTED',model,'candidate_count',sum(x in available for x in allowed),flush=True)
    parts=[{'text':PROMPT}]
    for name,blob,_ in images:
        parts.extend([{'text':name},{'inline_data':{'mime_type':'image/jpeg','data':base64.b64encode(blob).decode()}}])
    req={'contents':[{'role':'user','parts':parts}],'generationConfig':{'temperature':0.2,'maxOutputTokens':7000,'responseMimeType':'application/json'}}
    if len(json.dumps(req))>12000000:raise RuntimeError('REQUEST_SIZE_LIMIT')
    response=None
    error_states=[]
    for candidate in allowed:
        if candidate not in available:continue
        print('GEMINI_AUTHORIZED_FLASH_TRY',candidate,flush=True)
        for attempt in range(2 if candidate=='gemini-3.8-flash' else 1):
            try:
                response=request(key,API+'/models/'+candidate+':generateContent',req,timeout=85)
                model=candidate
                break
            except RuntimeError as exc:
                code=str(exc)
                error_states.append({'model':candidate,'error':code})
                print('GEMINI_INFERENCE_ATTEMPT_BLOCKED',candidate,code,flush=True)
                if code not in ('GEMINI_HTTP_503','GEMINI_HTTP_404','GEMINI_HTTP_429'):raise
                if code=='GEMINI_HTTP_429':continue
                if code=='GEMINI_HTTP_503' and attempt==0 and candidate=='gemini-3.8-flash':time.sleep(5)
        if response is not None:break
    if response is None:raise RuntimeError('FREE_FLASH_UNAVAILABLE')
    text=''.join(p.get('text','') for p in (response.get('candidates') or [{}])[0].get('content',{}).get('parts',[]))
    (OUT/'gemini_raw_response.txt').write_text(text)
    print('GEMINI_OUTPUT_RECEIPT',json.dumps({'model':model,'response_chars':len(text),'finish_reason':(response.get('candidates') or [{}])[0].get('finishReason'),'usage':response.get('usageMetadata',{})}),flush=True)
    try:obj=json.loads(text)
    except json.JSONDecodeError as exc:raise RuntimeError('GEMINI_STRUCTURED_RESPONSE_INCOMPLETE') from None
    if obj.get('verdict') not in ('APPROVE','REVISE','REJECT') or not obj.get('findings'):raise RuntimeError('GEMINI_REVIEW_INVALID')
    receipt={'provider':'Google Gemini Developer API','model':model,'free_tier':'owner-attested','screenshots':[{'label':n,'sha256':sha} for n,_,sha in images],'usage':response.get('usageMetadata',{}),'response':obj,'website_changes':False,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (OUT/'gemini_review.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False))
    report='# Andaz — independent Gemini Vision artistic audit\n\nProvider: Google Gemini API / '+model+'\n\nVerdict: '+obj['verdict']+'\n\nScore: '+str(obj.get('overall_artistic_score_100'))+'/100\n\n'+json.dumps(obj,indent=2,ensure_ascii=False)
    (OUT/'GEMINI_ARTISTIC_REVIEW.md').write_text(report)
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(report[:19000])
    print('GEMINI_ARTISTIC_REVIEW_COMPLETE',json.dumps({'model':model,'verdict':obj['verdict'],'score':obj.get('overall_artistic_score_100'),'findings':len(obj['findings']),'images':len(images)}))
if __name__=='__main__':
    try:run()
    except Exception as exc:
        print('GEMINI_ART_AUDIT_FAILED',str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__,file=sys.stderr)
        sys.exit(2)
