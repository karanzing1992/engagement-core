"""Owner-fact-bound isolated food copy repair; no creative or release authority."""
from pathlib import Path
import fcntl,json,os
from core import state,treehash,sha,write,require
from site_builder import ROOT
from editorial_contract import check_editorial
from design_contract import validate_html

UNVERIFIED='Each dish is crafted from locally sourced ingredients, ensuring authentic flavor profiles and seasonal freshness.'
REPLACEMENT='Meals are prepared fresh in an Indian home-style manner, with familiar flavours and simple, comforting food.'
# Exact textual unit only. No regex replacement or structural rewrite.
def corrected(text):
 require(text.count(UNVERIFIED)==1,'EXPECTED_SINGLE_UNVERIFIED_CLAIM')
 require('₹180' in text and '₹220' in text,'OWNER_PRICE_FACTS_MISSING')
 require('https://wa.me/918999541081' in text,'OWNER_WHATSAPP_MISSING')
 return text.replace(UNVERIFIED,REPLACEMENT,1)

def apply(w):
 w=w.expanduser().resolve()
 require(w.is_relative_to(ROOT) and (w/'site').is_dir(),'ISOLATION_REQUIRED')
 p=w/'site/food.html';report=w/'reports/food-fact-repair-v1.json'
 require(not report.exists(),'REPAIR_ALREADY_RUN')
 with (w/'.full-site.lock').open('a+') as lock:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('ALREADY_RUNNING')
  s=state(w)
  require(s['project']=='andaz-vibe-stay' and s['site_sha256']==treehash(w/'site'),'SOURCE_HASH_DRIFT')
  original=p.read_bytes();text=original.decode('utf-8')
  result=check_editorial(text,'food.html',s['project'])
  require(result['issues']==['UNVERIFIED_HOSPITALITY_OR_MENU_CLAIM'],'UNEXPECTED_FACTUAL_FAILURE')
  fixed=corrected(text)
  require(check_editorial(fixed,'food.html',s['project'])['status']=='PASS','FACTUAL_REPAIR_DID_NOT_PASS')
  require(validate_html(fixed,s['project'],w/'site',page='food.html')['status']=='PASS','HTML_REVALIDATION_FAILED')
  backup=w/'evidence/factual-source-backups'/('food.html-'+sha(p)[:16]+'.bak')
  backup.parent.mkdir(parents=True,exist_ok=True)
  if backup.exists():require(backup.read_bytes()==original,'BACKUP_DRIFT')
  else:
   with backup.open('xb') as f:f.write(original)
   backup.chmod(0o600)
  evidence={'schema':'source-bound-owner-food-fact-repair-v1','status':'PREPARED',
    'source_before':s['site_sha256'],'original_page_sha256':sha(p),
    'exact_replacement':{'removed':UNVERIFIED,'added':REPLACEMENT},
    'validated':True,'artistic_score':None,'production_approved':False}
  write(report,evidence);saved=json.loads(json.dumps(s))
  temp=p.with_suffix('.html.fact-temp')
  try:
   require(not temp.exists(),'TEMP_REPLAY')
   temp.write_text(fixed,encoding='utf-8');os.replace(temp,p)
   s['site_sha256']=treehash(w/'site')
   for stage in ('actual_render_and_screenshot','technical_qa','independent_artistic_review'):
    s['stage_status'][stage]='PENDING'
   s['artistic_score']=None;s['independent_verdict']=None
   write(w/'engine-state.json',s)
   evidence.update({'status':'PASS','source_after':s['site_sha256'],'page_sha256_after':sha(p)})
   write(report,evidence)
   return evidence
  except BaseException:
   p.write_bytes(original);write(w/'engine-state.json',saved)
   evidence['status']='BLOCKED';write(report,evidence);raise
