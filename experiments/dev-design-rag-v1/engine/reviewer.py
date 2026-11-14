#!/usr/bin/env python3
"""Evidence-only Ollama vision reviewer. This process NEVER signs or approves releases.

Trusted Ed25519 attestation is a separate, owner-provisioned reviewer service.
"""
import argparse,base64,hashlib,io,json,sys,time,urllib.error,urllib.request
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from core import workspace,state,sha,write,require
def one_page(w, s, q, page, model, timeout):
    pair=sorted((x for x in q['screenshots'] if x['page']==page and x['width'] in (390,1440)),key=lambda x:x['width'])
    require(len(pair)==2 and [x['width'] for x in pair]==[390,1440],'MOBILE_DESKTOP_PAIR_REQUIRED')
    images=[]
    for x in pair:
        f=w/'evidence/screenshots'/x['name']
        require(f.is_file() and not f.is_symlink() and sha(f)==x['sha256'],'VISUAL_SOURCE_HASH_INVALID')
        with Image.open(f) as source:
            im=source.convert('RGB')
            im.thumbnail((640,960))
            out=io.BytesIO();im.save(out,'JPEG',quality=60,optimize=True)
            images.append(base64.b64encode(out.getvalue()).decode())
    prompt=('Independent critical design review: compare actual mobile and desktop FULL-PAGE website screenshots. '
      'Evaluate visual hierarchy, typographic consistency, spacing, originality, authenticity, trust, CTA clarity and '
      'mobile usability. Score 0 to 100 conservatively, with 95+ reserved for exceptional professional design. '
      'Do not infer unseen features. JSON ONLY with fields score (number), issues (array of factual concerns), '
      'visual_evidence (at least one specific visible observation), verdict ("APPROVE" or "REVISE").')
    payload={'model':model,'prompt':prompt,'images':images,'stream':False,
      'options':{'num_predict':240,'num_ctx':4096,'temperature':0.1,'num_thread':2,'num_gpu':0}}
    request=urllib.request.Request('http://127.0.0.1:11434/api/generate',
      data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request,timeout=timeout) as response:
                result=json.load(response)
            break
        except urllib.error.HTTPError as e:
            detail=e.read(350).decode(errors='replace')
            if e.code in (429,503) and attempt==0:
                time.sleep(3);continue
            raise ValueError('VISUAL_MODEL_HTTP_'+str(e.code)+':'+detail[:200]) from e
        except Exception as e:raise ValueError('VISUAL_MODEL_UNAVAILABLE:'+type(e).__name__) from e
    raw=result.get('response','').strip()
    a=raw.find('{');b=raw.rfind('}')
    require(a>=0 and b>a,'VISUAL_MODEL_NOT_JSON')
    try:
        clean=raw[a:b+1];obj=json.loads(clean)
    except ValueError:raise ValueError('VISUAL_MODEL_JSON_INVALID')
    score=obj.get('score')
    require(type(score) in (int,float) and 0<=score<=100,'VISUAL_SCORE_INVALID')
    require(isinstance(obj.get('issues'),list) and
       all(isinstance(x,str) for x in obj['issues']),'VISUAL_ISSUES_INVALID')
    require(len(str(obj.get('visual_evidence','')).strip())>=12,'VISUAL_EVIDENCE_INSUFFICIENT')
    return {'page':page,'raw':clean,'site_sha256':s['site_sha256'],
      'qa_sha256':s['qa_receipt_sha256'],'model':model,
      'mobile_sha256':pair[0]['sha256'],'desktop_sha256':pair[1]['sha256'],
      'score':score,'issues':obj['issues'],'visual_evidence':obj['visual_evidence']}
def review(w,limit,model,timeout):
    s=state(w);q=json.loads((w/'reports/browser-qa.json').read_text())
    require(q.get('pass') is True and q.get('source_hash')==s['site_sha256'] and
      sha(w/'reports/browser-qa.json')==s.get('qa_receipt_sha256'),'REVIEW_QA_UNTRUSTED')
    pages=sorted({x['page'] for x in q['screenshots']})
    if limit:pages=pages[:limit]
    records=[]
    for page in pages:
        path=w/'reports/visual'/('vision-'+page.replace('.html','')+'.json')
        prior=json.loads(path.read_text()) if path.is_file() else None
        pair=sorted((x for x in q['screenshots'] if x['page']==page and x['width'] in (390,1440)),key=lambda x:x['width'])
        valid=(prior and prior.get('site_sha256')==s['site_sha256'] and
          prior.get('qa_sha256')==s['qa_receipt_sha256'] and prior.get('model')==model and
          prior.get('mobile_sha256')==pair[0]['sha256'] and
          prior.get('desktop_sha256')==pair[1]['sha256'] and
          hashlib.sha256(prior.get('raw','').encode()).hexdigest()==prior.get('raw_sha256'))
        if valid:
            try:
                parsed=json.loads(prior['raw'])
                valid=parsed.get('score')==prior.get('score') and len(str(parsed.get('visual_evidence','')))>11
            except Exception:valid=False
        entry=prior if valid else one_page(w,s,q,page,model,timeout)
        if not valid:
            entry['raw_sha256']=hashlib.sha256(entry['raw'].encode()).hexdigest()
            write(path,entry)
        records.append(entry)
        print('ACTUAL_VISION_RESULT',page,entry['score'],flush=True)
    all_pages=set(pages)=={x['page'] for x in q['screenshots']}
    score=min(r['score'] for r in records)
    reviewed=[x for x in q['screenshots'] if x['page'] in pages and x['width'] in (390,1440)]
    result={'reviewer_kind':'local_independent_model_unattested',
      'reviewer_id':'ollama-'+model,'key_id':None,'signature_scheme':None,
      'assessment_method':'actual_screenshots','evidence_source':'independent_visual_model',
      'signed_or_verifiable_receipt':False,'job_id':s.get('job_id'),'project_id':s.get('project'),
      'site_sha256':s['site_sha256'],'qa_receipt_sha256':s['qa_receipt_sha256'],
      'score':score,'verdict':'APPROVE' if all_pages and score>=95 else 'REVISE',
      'screenshots':q['screenshots'],'reviewed_screenshots':reviewed,
      'raw_model_outputs':[{'page':r['page'],'raw':r['raw']} for r in records],
      'model_response_sha256':hashlib.sha256('\n'.join(r['raw'] for r in records).encode()).hexdigest(),
      'issues':[v for r in records for v in r['issues']],
      'scope_complete':all_pages,'model':model}
    write(w/'reports/artistic-model-review.json',result)
    return {'status':'EVIDENCE_ONLY_UNATTESTED','actual_model_score':score,
       'pages_reviewed':len(records),'total_pages':len({x['page'] for x in q['screenshots']}),
       'scope_complete':all_pages,'artistic_gate':'BLOCKED'}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--max-pages',type=int,default=0)
    p.add_argument('--model',default='qwen3-vl:2b-instruct')
    p.add_argument('--timeout',type=int,default=110)
    a=p.parse_args()
    try:
        x=review(workspace(a.workspace),a.max_pages,a.model,a.timeout)
        print(json.dumps(x));sys.exit(4)
    except Exception as e:
        print(json.dumps({'status':'BLOCKED','error':type(e).__name__+':'+str(e)[:200]}))
        sys.exit(5)
