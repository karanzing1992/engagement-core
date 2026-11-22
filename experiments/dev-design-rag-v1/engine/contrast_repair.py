"""Evidence-bound deterministic WCAG color-contrast repair. Never certifies art.

Only exact same-build Chromium/axe four-width, single-selector contrast defects.
Writes a *new* immutable variant and reruns actual Chromium/axe before acceptance.
"""
import hashlib,json,os,re,shutil
from pathlib import Path
from core import state,treehash,sha,write,require
from qa_repair import validated_failure
from cli import qa
from design_contract import validate_html

RGB=re.compile(r'#[0-9a-fA-F]{6}')
FG=re.compile(r'foreground color:\s*(#[0-9a-fA-F]{6})',re.I)
BG=re.compile(r'background color:\s*(#[0-9a-fA-F]{6})',re.I)
SELECTOR=re.compile(r'[.#]?[a-zA-Z][a-zA-Z0-9_-]{0,80}')

def _luminance(hexcolor):
    rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
    linear=[(v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4) for v in rgb]
    return .2126*linear[0]+.7152*linear[1]+.0722*linear[2]

def ratio(fg,bg):
    x,y=sorted((_luminance(fg),_luminance(bg)),reverse=True)
    return (x+.05)/(y+.05)

def safe_background(foreground,background,threshold=4.75):
    if not RGB.fullmatch(foreground) or not RGB.fullmatch(background):
        raise ValueError('INVALID_AXE_COLOR')
    if ratio(foreground,background)>=threshold:raise ValueError('NO_CONTRAST_CHANGE_REQUIRED')
    orig=[int(background[i:i+2],16) for i in (1,3,5)]
    choices=[]
    for goal in (0,255):
        for step in range(1,101):
            factor=step/100
            trial=[round(v+(goal-v)*factor) for v in orig]
            value='#'+''.join(f'{n:02x}' for n in trial)
            if ratio(foreground,value)>=threshold:
                dist=sum((a-b)**2 for a,b in zip(orig,trial))
                choices.append((dist,step,value));break
    if not choices:raise ValueError('CONTRAST_SOLVER_NO_CANDIDATE')
    _,_,result=min(choices)
    return result

def candidate(w,page):
    q=validated_failure(w,page)
    if q.get('missing_links'):raise ValueError('NON_CONTRAST_LINK_FAILURE')
    targets=[]
    for row in q['rows']:
        if row.get('status')!=200 or row.get('errors') or row.get('dom',{}).get('brokenImages'):
            raise ValueError('NON_CONTRAST_RUNTIME_FAILURE')
        violations=row.get('axe',[])
        if len(violations)!=1 or violations[0].get('id')!='color-contrast':
            raise ValueError('NON_CONTRAST_AXE_FAILURE')
        v=violations[0]
        if v.get('nodes')!=1 or len(v.get('targets',[]))!=1:
            raise ValueError('MULTIPLE_CONTRAST_TARGETS_NOT_SUPPORTED')
        target=v['targets'][0];selector=target.get('selector','')
        if not SELECTOR.fullmatch(selector):raise ValueError('UNSAFE_CONTRAST_SELECTOR')
        summary=target.get('failure_summary','')
        fg=FG.search(summary);bg=BG.search(summary)
        if not fg or not bg:raise ValueError('MISSING_AXE_COLORS')
        targets.append((selector,fg.group(1).lower(),bg.group(1).lower()))
    if len(set(targets))!=1:raise ValueError('VIEWPORT_CONTRAST_VARIATION')
    return targets[0],sha(w/'reports/browser-qa.json')

def run(w,page,checkpoint):
    (selector,fg,bg),prior_hash=candidate(w,page)
    history=w/'reports/qa-attempts'
    history.mkdir(exist_ok=True)
    input_path=history/('contrast-source-'+prior_hash[:16]+'.json')
    if input_path.exists():
        require(sha(input_path)==prior_hash,'CONTRAST_SOURCE_RECEIPT_DRIFT')
    else:shutil.copy2(w/'reports/browser-qa.json',input_path)
    color=safe_background(fg,bg)
    after=ratio(fg,color)
    old=w/'site'/page
    require(old.is_file() and not old.is_symlink(),'UNSAFE_CONTRAST_SOURCE')
    target=Path(page).stem+'-a11y.html'
    new=w/'site'/target
    require(not new.exists() and not new.is_symlink(),'CONTRAST_VARIANT_EXISTS')
    content=old.read_text(encoding='utf-8')
    require('</head>' in content.lower() and 'id="qa-contrast-patch"' not in content,
            'CONTRAST_PATCH_SOURCE_INVALID')
    override=('\n<style id="qa-contrast-patch">'+selector+
      '{background-color:'+color+' !important;color:'+fg+' !important;}</style>\n')
    import re as regex
    patched=regex.sub(r'</head>',lambda m:override+m.group(0),content,count=1,flags=regex.I)
    validation=validate_html(patched,state(w)['project'],w/'site')
    before=state(w)
    old_site=treehash(w/'site')
    require(old_site==before['site_sha256'],'CONTRAST_BUILD_DRIFT')
    fd=os.open(new,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(patched)
    update=state(w)
    update['site_sha256']=treehash(w/'site')
    update['stage_status']['actual_render_and_screenshot']='PENDING'
    update['stage_status']['technical_qa']='PENDING'
    update['deterministic_qa_patch_source_sha256']=old_site
    write(w/'engine-state.json',update)
    receipt={'schema':'design-rag-2.1.1-deterministic-contrast-v1','source_page':page,
      'output_page':target,'initial_site_sha256':old_site,'patched_site_sha256':update['site_sha256'],
      'original_page_sha256':hashlib.sha256(content.encode()).hexdigest(),
      'patched_page_sha256':sha(new),'input_browser_qa_sha256':prior_hash,
      'axe_selector':selector,'axe_foreground':fg,'axe_background':bg,'new_background':color,
      'measured_color_contrast_before':round(ratio(fg,bg),3),
      'calculated_color_contrast_after':round(after,3),'semantic_guard':validation,
      'status':'PATCHED_PENDING_REAL_QA','independent_artistic_score':None,
      'release_authorized':False}
    report=w/'reports/contrast-repair.json'
    write(report,receipt)
    checkpoint('contrast_repair','RUNNING',selector+' '+bg+' → '+color)
    try:
        qa(w,target)
    except Exception as e:
        receipt['status']='FAILED_REAL_QA';receipt['failure']=str(e)[:160]
        write(report,receipt)
        checkpoint('contrast_repair','BLOCKED',receipt['failure'])
        raise ValueError('CONTRAST_REPAIR_FAILED_REAL_QA') from e
    receipt['status']='PASS_REAL_QA'
    receipt['qa_receipt_sha256']=state(w).get('qa_receipt_sha256')
    write(report,receipt)
    checkpoint('contrast_repair','PASS','Chromium/axe all widths verified '+target)
    return target
