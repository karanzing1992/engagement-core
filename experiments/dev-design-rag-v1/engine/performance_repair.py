"""Evidence-bound image layout-shift repair, never overrides Lighthouse thresholds."""
import json
import re
import time
from pathlib import Path
from PIL import Image
from core import state,treehash,sha,write,require
from brand_guard import validate_html

def improve_image_dimensions(w,page):
 s=state(w)
 require(treehash(w/'site')==s['site_sha256'],'SOURCE_DRIFT')
 require(s['stage_status']['actual_render_and_screenshot']=='PASS','BROWSER_QA_REQUIRED')
 report=w/'reports'/('lighthouse-'+page.replace('.html','')+'-mobile.json')
 require(report.is_file() and not report.is_symlink(),'LIGHTHOUSE_RAW_REQUIRED')
 require(abs(time.time()-report.stat().st_mtime)<360,'STALE_LIGHTHOUSE')
 data=json.loads(report.read_text())
 categories=data.get('categories',{})
 pscore=categories.get('performance',{}).get('score')
 cls=data.get('audits',{}).get('cumulative-layout-shift',{}).get('numericValue')
 require(type(pscore) in (float,int) and pscore<.9,'NO_PERFORMANCE_DEFICIT')
 require(type(cls) in (float,int) and cls>.1,'CLS_NOT_DEMONSTRATED')
 require(str(data.get('finalUrl','')).split('?',1)[0].endswith('/'+page),'LIGHTHOUSE_WRONG_ROUTE')
 target=w/'site'/page
 require(target.is_file() and not target.is_symlink(),'BAD_PAGE')
 before=target.read_text()
 count=[0]
 def fix(match):
  raw=match.group(0)
  src=re.search(r'\bsrc=["\']([^"\']+)["\']',raw,re.I)
  if not src or 'width=' in raw.lower() or 'height=' in raw.lower():return raw
  val=src.group(1)
  if not re.fullmatch(r'(?:assets|media)/[a-zA-Z0-9_.-]+\.(?:webp|png|jpg|jpeg)',val):return raw
  image=w/'site'/val
  if not image.is_file() or image.is_symlink():return raw
  with Image.open(image) as im:width,height=im.size
  require(0<width<=6000 and 0<height<=6000,'BAD_DIMENSIONS')
  count[0]+=1
  return raw[:-1]+' width="'+str(width)+'" height="'+str(height)+'">'
 revised=re.sub(r'<img\b[^>]*>',fix,before,flags=re.I)
 require(count[0]>0,'NO_IMAGE_DIMENSIONS_TO_FIX')
 validate_html(w,page,revised)
 ledger=w/'reports/qa-repairs'
 ledger.mkdir(exist_ok=True)
 index=len(s.get('repair_chain',[]))+1
 receipt=ledger/('performance-'+str(index)+'.json')
 snap=ledger/('performance-'+str(index)+'-before.html')
 raw=ledger/('performance-'+str(index)+'-lighthouse.json')
 require(not receipt.exists() and not snap.exists() and not raw.exists(),'PERFORMANCE_REPAIR_REPLAY')
 snap.write_text(before);snap.chmod(0o600)
 raw.write_bytes(report.read_bytes());raw.chmod(0o600)
 target.write_text(revised)
 newhash=treehash(w/'site')
 r={'status':'IMAGE_LAYOUT_DIMENSIONS_APPLIED_RECHECK_REQUIRED',
    'old_site_sha256':s['site_sha256'],'new_site_sha256':newhash,
    'lighthouse_sha256':sha(raw),'prior_lighthouse_cls':cls,'prior_performance':pscore,
    'modified_img_tags':count[0],'artistic_score':None,'release_authorized':False}
 write(receipt,r);receipt.chmod(0o600)
 s['repair_chain']=s.get('repair_chain',[])+[{'kind':'image_dimensions',
    'old_site_sha256':s['site_sha256'],'new_site_sha256':newhash,
    'receipt_sha256':sha(receipt)}]
 s['site_sha256']=newhash
 s['artistic_score']=None;s['independent_verdict']=None
 s['stage_status']['actual_render_and_screenshot']='PENDING'
 s['stage_status']['technical_qa']='PENDING'
 s['stage_status']['independent_artistic_review']='PENDING'
 write(w/'engine-state.json',s)
 return r
