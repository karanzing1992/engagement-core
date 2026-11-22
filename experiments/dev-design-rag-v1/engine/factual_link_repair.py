"""Provenance-bound engine correction for one narrowly defined AI page defect."""
import fcntl,json,re,os,hashlib
from pathlib import Path
from core import state,treehash,sha,write,require
from site_builder import ROOT
from design_contract import validate_html
from editorial_contract import check_editorial
WHY='ValueError:EDITORIAL_GATE:FOOD_TEASER_WRONG_DESTINATION'
LINK='<a href="food.html" class="btn">Explore The Andaz Table</a>'

def corrected(text):
 matches=[m for m in re.finditer(r'<section\b[^>]*>.*?</section>',text,re.I|re.S)
          if re.search(r'<h2[^>]*>[^<]*Andaz Table',m.group(0),re.I)]
 require(len(matches)==1,'SINGLE_TABLE_SECTION_REQUIRED')
 m=matches[0]
 require('href="food.html"' not in m.group(0),'LINK_ALREADY_PRESENT')
 at=m.end()-len('</section>')
 require(text[at:m.end()]=='</section>','UNSAFE_SECTION_BOUNDARY')
 return text[:at]+LINK+'\n'+text[at:]

def treehash_without_home(site):
 h=hashlib.sha256()
 for f in sorted(site.rglob('*')):
  require(not f.is_symlink(),'SITE_SYMLINK_DENIED')
  if f.is_file() and f.relative_to(site).as_posix()!='index.html':
   h.update(f.relative_to(site).as_posix().encode()+b'\0')
   h.update(bytes.fromhex(sha(f)))
 return h.hexdigest()

def run(w,task):
 w=w.expanduser().resolve()
 require(w.is_relative_to(ROOT) and (w/'site').is_dir(),'ISOLATED_ROOT_REQUIRED')
 require(bool(re.fullmatch(r'fact-[a-f0-9]{23}',task)),'TASK_ID_DENIED')
 t=w/'tasks'/task
 report=w/'reports/deterministic-food-link-repair-v1.json'
 require(not report.exists(),'REPLAY_DENIED')
 with (w/'.full-site.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  s=state(w)
  require(s['project']=='andaz-vibe-stay' and s['site_sha256']==treehash(w/'site'),'SOURCE_DRIFT')
  page=w/'site/index.html';old=page.read_bytes()
  rec=t/'receipt.json';candidate=t/'index.html'
  require(rec.is_file() and candidate.is_file() and not rec.is_symlink() and not candidate.is_symlink(),'CANDIDATE_MISSING')
  r=json.loads(rec.read_text())
  require(r.get('status')=='BLOCKED' and r.get('target')=='index.html' and
    r.get('validation_failure')==WHY and 'write' in r.get('tool_types',[]) and
    r.get('output_site_sha256')==treehash_without_home(w/'site'),'CANDIDATE_PROVENANCE_DENIED')
  body=candidate.read_text()
  require(validate_html(body,s['project'],w/'site',page='index.html')['status']=='PASS','UNTRUSTED_CANDIDATE')
  require(check_editorial(body,'index.html',s['project'])['issues']==['FOOD_TEASER_WRONG_DESTINATION'],'UNEXPECTED_DEFECT')
  revised=corrected(body)
  require(validate_html(revised,s['project'],w/'site',page='index.html')['status']=='PASS'
    and check_editorial(revised,'index.html',s['project'])['status']=='PASS','CORRECTION_UNVERIFIED')
  backup=w/'evidence/factual-source-backups'/('index.html-'+sha(page)[:16]+'.bak')
  require(backup.is_file() and backup.read_bytes()==old,'BACKUP_REQUIRED')
  evidence={'schema':'source-bound-foodlink-repair-v1','status':'PREPARED',
    'task':task,'task_receipt_sha256':sha(rec),'model_output_sha256':sha(candidate),
    'source_sha256_before':s['site_sha256'],'original_page_sha256':sha(page),
    'repair':'INSERT_VERIFIED_DINING_SECTION_LINK_TO_FOOD_HTML',
    'artistic_score':None,'production':False}
  write(report,evidence)
  state_snapshot=json.loads(json.dumps(s))
  state_snapshot=json.loads(json.dumps(s))
  tmp=page.with_suffix('.html.repair-tmp')
  try:
   require(not tmp.exists(),'TMP_EXISTS')
   tmp.write_text(revised)
   os.replace(tmp,page)
   s['site_sha256']=treehash(w/'site')
   for k in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):s['stage_status'][k]='PENDING'
   s['artistic_score']=None;s['independent_verdict']=None
   write(w/'engine-state.json',s)
   evidence.update(status='PASS',source_sha256_after=s['site_sha256'],page_sha256_after=sha(page))
   write(report,evidence)
   return evidence
  except BaseException:
   page.write_bytes(old);write(w/'engine-state.json',state_snapshot)
   evidence['status']='BLOCKED';write(report,evidence)
   raise
