"""Single-pass, source-bound Andaz V9 R2 repair for measured browser defects."""
import fcntl,json,os
from pathlib import Path
from core import require,state,treehash,sha,write
from site_builder import ROOT
from design_contract import validate_html
from editorial_contract import check_editorial
from multipage_contract import layout_preflight
MARKER='/* VERIFIED R2 CHROMIUM 24-CASE ACCESSIBILITY AND MOBILE-LOGO REPAIR */'
BAD_LINK='<li><a href="about.html">About</a></li>'
RULES='''
/* VERIFIED R2 CHROMIUM 24-CASE ACCESSIBILITY AND MOBILE-LOGO REPAIR */
.site-header{display:flex;flex-wrap:wrap;align-items:center;gap:.65rem;max-width:100%;}
.site-header > .container{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;min-width:0;}
.site-header a.logo{display:inline-flex;align-items:center;max-width:10rem;max-height:7rem;flex:0 0 auto;}
.site-header img[src="assets/andaz-official-cropped.webp"]{display:block;width:auto;max-width:10rem;max-height:7rem;height:auto;object-fit:contain;}
.site-header nav{min-width:0;max-width:100%;flex:1 1 15rem;}
.site-header .nav-list{display:flex;max-width:100%;min-width:0;overflow-x:auto;scrollbar-width:thin;gap:.65rem;}
.site-header .nav-list li{flex:0 0 auto;min-width:0;}
.site-header .nav-list a{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:.5rem 1rem;white-space:nowrap;}
a.cta,.cta,.btn,a[href^="https://wa.me/918999541081"]{background-color:#443019;color:#ffffff;font-weight:650;text-decoration:none;border-color:#443019;}
a.cta,.cta,a[href^="https://wa.me/918999541081"]{display:inline-flex;min-height:48px;align-items:center;padding:.65rem 1.1rem;border-radius:.35rem;}
a.cta:hover,a.cta:focus-visible,.btn:hover,.btn:focus-visible,a[href^="https://wa.me/918999541081"]:hover{background-color:#2a2115;color:#ffffff;}
.site-header .nav-list a:hover,.site-header .nav-list a:focus-visible{background-color:#443019;color:#ffffff;border-color:#443019;}
.chip-group button,.explore-controls button{min-height:48px;min-width:44px;}
'''
def transform(css,exp):
 require(MARKER not in css,'CHROME_PATCH_REPLAY')
 require(exp.count(BAD_LINK)==1,'UNEXPECTED_BAD_LINK_SHAPE')
 require('--color-gold: #b8860b' in css and '.nav-list' in css and '.cta' in css,'STYLESHEET_SCOPE_MISMATCH')
 return css+'\n'+RULES,exp.replace(BAD_LINK,'',1)
def run(w):
 w=w.expanduser().resolve();require(w.is_relative_to(ROOT) and (w/'site').is_dir(),'ISOLATION_REQUIRED')
 receipt=w/'reports/browser-r2-verified-repair.json';require(not receipt.exists(),'REPLAY_DENIED')
 with (w/'.full-site.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  s=state(w);require(s['site_sha256']==treehash(w/'site'),'SOURCE_DRIFT')
  qp=w/'reports/browser-qa.json';require(qp.is_file(),'REAL_BROWSER_QA_REQUIRED')
  q=json.loads(qp.read_text());rows=q['rows']
  require(q['pass'] is False and q['source_hash']==s['site_sha256'] and
   len(rows)==24 and len({r['page'] for r in rows})==6 and
   q.get('missing_links')==['about.html'],'BROWSER_EVIDENCE_MISMATCH')
  require(all({v['id'] for v in r['axe']}.issubset({'color-contrast','target-size'}) for r in rows)
   and any(r['width']==320 and r['dom'].get('overflow')==388 for r in rows),
   'UNEXPECTED_BROWSER_FAILURES')
  css=w/'site/assets/v9-fresh.css';experiences=w/'site/experiences.html'
  require(all(p.is_file() and not p.is_symlink() for p in (css,experiences)),'UNSAFE_FILES')
  original_css=css.read_bytes();original_exp=experiences.read_bytes()
  updated_css,updated_exp=transform(original_css.decode(),original_exp.decode())
  require(validate_html(updated_exp,s['project'],w/'site',page='experiences.html')['status']=='PASS',
    'REVISED_EXPERIENCES_HTML_INVALID')
  require(check_editorial(updated_exp,'experiences.html',s['project'])['status']=='PASS',
    'REVISED_EXPERIENCES_EDITORIAL_FAILED')
  backup=w/'evidence'/('browser-r2-before-'+sha(css)[:16]);require(not backup.exists(),'BACKUP_COLLISION')
  backup.mkdir(mode=0o700)
  (backup/'site.css').write_bytes(original_css)
  (backup/'experiences.html').write_bytes(original_exp)
  evidence={'schema':'andaz-browser-evidence-bounded-repair-v1','status':'PREPARED',
   'browser_failure_receipt_sha256':sha(qp),'source_before':s['site_sha256'],
   'css_before':sha(css),'experiences_before':sha(experiences),
   'repairs':['BOUND_OFFICIAL_LOGO_692px','FIX_WCAG_CONTRAST','ENSURE_NAV_48px','REMOVE_BROKEN_ABOUT_LINK'],
   'artistic_score':None,'production_approved':False}
  write(receipt,evidence)
  original_state=json.loads(json.dumps(s));tmp_css=css.with_suffix('.css.r2-tmp');tmp_exp=experiences.with_suffix('.html.r2-tmp')
  try:
   require(not tmp_css.exists() and not tmp_exp.exists(),'TEMP_CONFLICT')
   tmp_css.write_text(updated_css);tmp_exp.write_text(updated_exp)
   os.replace(tmp_css,css);os.replace(tmp_exp,experiences)
   names=['index.html','rooms.html','experiences.html','food.html','explore.html','contact.html']
   require(layout_preflight(w/'site',names,'assets/v9-fresh.css')['status']=='PASS','LAYOUT_REGRESSION')
   s['site_sha256']=treehash(w/'site')
   for k in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):s['stage_status'][k]='PENDING'
   s['artistic_score']=None;s['independent_verdict']=None;write(w/'engine-state.json',s)
   evidence.update({'status':'PASS','source_after':s['site_sha256'],
    'css_after':sha(css),'experiences_after':sha(experiences)})
   write(receipt,evidence)
   return evidence
  except BaseException:
   css.write_bytes(original_css);experiences.write_bytes(original_exp)
   write(w/'engine-state.json',original_state)
   evidence['status']='BLOCKED';write(receipt,evidence)
   raise
