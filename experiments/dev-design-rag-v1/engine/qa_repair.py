"""Bounded, auditable contrast correction from real axe browser evidence.

No speculative rendering claims, no release approvals, no hidden QA bypasses.
"""
import hashlib
import json
import re
from pathlib import Path
from core import require,sha,state,treehash,write

def relative_luminance(rgb):
 c=[int(rgb[i:i+2],16)/255 for i in (0,2,4)]
 c=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in c]
 return .2126*c[0]+.7152*c[1]+.0722*c[2]

def fix_contrast(w,page,iteration=1):
 require(iteration in (1,2),'REPAIR_LIMIT')
 s=state(w)
 require(s['site_sha256']==treehash(w/'site'),'SOURCE_DRIFT')
 report=w/'reports/browser-qa.json'
 require(report.is_file() and not report.is_symlink(),'QA_EVIDENCE_REQUIRED')
 qa=json.loads(report.read_text())
 require(qa.get('pass') is False and qa.get('source_hash')==s['site_sha256'],'WRONG_BUILD_QA')
 require(len(qa.get('rows',[]))==4,'EXPECTED_FOUR_VIEWPORTS')
 require(all(x.get('page')==page and not x.get('pass') for x in qa['rows']),'WRONG_ROUTE')
 require(not qa.get('missing_links') and not qa.get('critical_violations'),'NON_CONTRAST_FAILURE')
 for row in qa['rows']:
  require(row['status']==200 and not row['errors'] and row['dom'].get('brokenImages')==[]
   and row['dom'].get('overflow')==0 and row['dom'].get('main') is True,'OTHER_QA_DEFECTS')
  require(row['axe'] and all(x['id']=='color-contrast' for x in row['axe']),'NON_CONTRAST_VIOLATIONS')
 p=w/'site'/page
 require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to((w/'site').resolve()),'UNSAFE_ROUTE')
 original=p.read_text()
 selectors={}
 for row in qa['rows']:
  for violation in row['axe']:
   require(violation.get('targets'),'MISSING_AXE_TARGETS')
   for n in violation['targets']:
    for selector in n['target']:
     if re.fullmatch(r'[.#][a-zA-Z][a-zA-Z0-9_-]{0,65}',selector) or re.fullmatch(r'a\[href\$="[a-z0-9_.-]+\.html"\]',selector):
      bgmatch=re.search(r'background color: #([0-9a-fA-F]{6})',n.get('summary',''))
      require(bgmatch is not None,'NO_GROUNDED_BACKGROUND')
      old=selectors.get(selector)
      require(old is None or old==bgmatch.group(1).lower(),'INCONSISTENT_BACKGROUND')
      selectors[selector]=bgmatch.group(1).lower()
 require(0<len(selectors)<=5,'UNSUPPORTED_SELECTOR_SET')
 css=[]
 for sel,bg in sorted(selectors.items()):
  lum=relative_luminance(bg)
  foreground='#101010' if (lum+.05)/.05>=4.5 else '#ffffff'
  ratio=((lum+.05)/(.0516) if foreground=='#101010' else 1.05/(lum+.05))
  require(ratio>=4.5,'CONTRAST_CALCULATION_FAILED')
  css.append(sel+'{color:'+foreground+' !important}')
 inject='\n<style data-engine-contrast-repair="'+str(iteration)+'">'+' '.join(css)+'</style>\n'
 require('</head>' in original,'HEAD_REQUIRED')
 revised=original.replace('</head>',inject+'</head>',1)
 from brand_guard import validate_html
 validate_html(w,page,revised)
 ledger=w/'reports/qa-repairs'
 ledger.mkdir(exist_ok=True)
 before=ledger/('attempt-'+str(iteration)+'-before.html')
 qa_snapshot=ledger/('attempt-'+str(iteration)+'-before-qa.json')
 receipt=ledger/('attempt-'+str(iteration)+'.json')
 require(not before.exists() and not receipt.exists() and not qa_snapshot.exists(),'REPAIR_REPLAY_DENIED')
 before.write_text(original);before.chmod(0o600)
 qa_snapshot.write_bytes(report.read_bytes());qa_snapshot.chmod(0o600)
 p.write_text(revised)
 newhash=treehash(w/'site')
 s['site_sha256']=newhash
 s['stage_status']['actual_render_and_screenshot']='PENDING'
 s['stage_status']['technical_qa']='PENDING'
 s['stage_status']['independent_artistic_review']='PENDING'
 s['artistic_score']=None;s['independent_verdict']=None
 write(w/'engine-state.json',s)
 result={'status':'AUTO_CONTRAST_PATCH_APPLIED_RECHECK_REQUIRED','iteration':iteration,
  'old_site_sha256':qa['source_hash'],'new_site_sha256':newhash,
  'prior_qa_sha256':sha(report),'selectors':sorted(selectors),
  'style_rules':css,'artistic_score':None,'release_authorized':False}
 write(receipt,result);receipt.chmod(0o600)
 s['repair_chain']=s.get('repair_chain',[])+[{'kind':'contrast','iteration':iteration,
  'receipt_sha256':sha(receipt),'old_site_sha256':qa['source_hash'],
  'new_site_sha256':newhash}]
 write(w/'engine-state.json',s)
 return result
