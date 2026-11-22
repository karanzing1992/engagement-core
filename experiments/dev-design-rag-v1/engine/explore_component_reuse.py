"""Isolated reuse of previously browser-and-functionally verified Explore component."""
import re,json,fcntl,os
from pathlib import Path
from core import sha,treehash,write,require,state
from site_builder import ROOT
from interactive_contract import inspect_explore
from editorial_contract import check_editorial
from design_contract import validate_html
CANONICAL='349fd09fb35b9b85f196a535fb9d12fa32d6630462df4916ceb5f430605c916f'
OLD_NAME='andaz-v9-sixpage-engine214-20261112'
NEW_HEADER='''<header class="site-header container">
  <a href="index.html" class="logo-link"><img src="assets/andaz-official-cropped.webp" class="logo" alt="Andaz Vibe Stay logo"></a>
  <nav class="nav" aria-label="Primary navigation"><ul class="nav-list">
    <li><a href="index.html">Home</a></li><li><a href="rooms.html">Rooms</a></li>
    <li><a href="experiences.html">Experiences</a></li><li><a href="food.html">Food</a></li>
    <li><a href="explore.html">Explore</a></li><li><a href="contact.html">Contact</a></li>
  </ul></nav>
</header>'''
def adapt(old):
 header=re.compile(r'<header class="site-header">.*?</header>',re.S)
 require(len(header.findall(old))==1,'UNRECOGNIZED_OLD_HEADER')
 out=header.sub(NEW_HEADER,old,count=1)
 require(out.count('<main class="container" data-explore-guide>')==1,'OLD_GUIDE_SCOPE_MISSING')
 out=out.replace('<main class="container" data-explore-guide>','<main class="main container" data-explore-guide>',1)
 require(out.count('<a href="https://wa.me/918999541081">WhatsApp enquiry</a>')==1,'WHATSAPP_CTA_SCOPE_MISSING')
 out=out.replace('<a href="https://wa.me/918999541081">WhatsApp enquiry</a>',
   '<a class="cta" href="https://wa.me/918999541081">WhatsApp enquiry</a>',1)
 require(out.count('<div class="grid">')==1 and out.count('<p id="explore-empty" hidden>')==1,'EXPLORE_GRID_SCOPE_MISMATCH')
 out=out.replace('<div class="grid">','<section aria-label="Explore Arambol places"><div class="grid">',1)
 out=out.replace('<p id="explore-empty" hidden>','</section><p id="explore-empty" hidden>',1)
 return out
def apply(w):
 w=w.expanduser().resolve()
 require(w.is_relative_to(ROOT) and w.is_dir() and (w/'site').is_dir(),'ISOLATED_WORKSPACE_REQUIRED')
 old=ROOT/OLD_NAME
 require(old.is_dir(),'TRUSTED_BASE_NOT_PRESENT')
 oldstate=state(old)
 oldqa=json.loads((old/'reports/browser-qa.json').read_text())
 oldfunctional=json.loads((old/'reports/functional-e2e.json').read_text())
 require(oldstate['site_sha256']==treehash(old/'site') and oldqa.get('pass') is True and
   oldqa.get('source_hash')==oldstate['site_sha256'] and oldfunctional.get('pass') is True and
   oldfunctional.get('count')==10 and oldfunctional.get('source_sha256')==oldstate['site_sha256'],
   'CANONICAL_PREVIOUS_BROWSER_FUNCTIONAL_PROVENANCE_INVALID')
 canonical=old/'site/explore.html'
 require(sha(canonical)==CANONICAL,'EXPLORE_SOURCE_SHA_MISMATCH')
 source_text=canonical.read_text()
 require(inspect_explore(source_text)['status']=='PASS','PREVIOUS_INTERACTION_CONTRACT_UNVERIFIED')
 revised=adapt(source_text)
 require(inspect_explore(revised)['status']=='PASS','NEW_INTERACTION_CONTRACT_FAILED')
 require(check_editorial(revised,'explore.html','andaz-vibe-stay')['status']=='PASS','EDITORIAL_GATE_FAILED')
 report=w/'reports/explore-tested-component-reuse-v1.json'
 require(not report.exists(),'COMPONENT_REPLAY')
 with (w/'.full-site.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  state_current=state(w);page=w/'site/explore.html'
  require(state_current['site_sha256']==treehash(w/'site'),'CURRENT_SOURCE_HASH_DRIFT')
  validate_html(revised,state_current['project'],w/'site',page='explore.html')
  before=page.read_bytes()
  backup=w/'evidence'/('explore-before-trusted-component-'+sha(page)[:16]+'.html')
  require(not backup.exists(),'BACKUP_COLLISION')
  with backup.open('xb') as f:f.write(before)
  backup.chmod(0o600)
  evidence={'schema':'andaz-isolated-verified-explore-reuse-v1',
    'trusted_old_source_site_sha256':oldstate['site_sha256'],'trusted_explore_html_sha256':CANONICAL,
    'trusted_browser_receipt_sha256':sha(old/'reports/browser-qa.json'),
    'trusted_functional_receipt_sha256':sha(old/'reports/functional-e2e.json'),
    'new_source_before':state_current['site_sha256'],'new_page_before':sha(page),
    'new_page_after':None,'status':'PREPARED','artistic_score':None,'production_approved':False}
  write(report,evidence)
  temp=page.with_suffix('.html.explore-temp')
  try:
   require(not temp.exists(),'TMP_COLLISION')
   temp.write_text(revised)
   os.replace(temp,page)
   state_current['site_sha256']=treehash(w/'site')
   for stage in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):
    state_current['stage_status'][stage]='PENDING'
   state_current['artistic_score']=None;state_current['independent_verdict']=None
   write(w/'engine-state.json',state_current)
   evidence.update(status='PASS',new_source_after=state_current['site_sha256'],new_page_after=sha(page))
   write(report,evidence)
   return evidence
  except BaseException:
   page.write_bytes(before)
   state_current['site_sha256']=evidence['new_source_before']
   write(w/'engine-state.json',state_current)
   evidence['status']='BLOCKED';write(report,evidence);raise
