#!/usr/bin/env python3
"""Allow only attested, hash-verified Vercel preview; no production mode."""
import argparse,json,os,re,shutil,subprocess,sys,tempfile,urllib.parse,urllib.request
from pathlib import Path
from core import gate,sha,state,treehash,workspace,write,require
def deploy(w,publish=False):
    decision=gate(w,'preview')
    require(decision['status']=='PASS','PREVIEW_GATE_BLOCKED:'+','.join(decision['missing']))
    s=state(w)
    require(s.get('site_sha256')==treehash(w/'site'),'SOURCE_HASH_DRIFT')
    if not publish:
        return {'status':'PREFLIGHT_PASS','site_sha256':s['site_sha256'],
          'deployed':False,'production_release_allowed':False}
    require(os.environ.get('UIUX_VERIFIED_ZERO_COST_PREVIEW')=='1','NO_ZERO_COST_PREVIEW_ATTESTATION')
    binary=shutil.which('vercel')
    require(binary is not None,'VERCEL_CLI_MISSING')
    with tempfile.TemporaryDirectory(prefix='uiux-checked-preview-') as temp:
        build=Path(temp)/'site'
        shutil.copytree(w/'site',build,symlinks=False)
        require(treehash(build)==s['site_sha256'],'PREVIEW_COPY_HASH_DRIFT')
        manifest={'protocol':'uiux-v2-preview','job_id':s['job_id'],
          'site_sha256':s['site_sha256'],'qa_receipt_sha256':s['qa_receipt_sha256'],
          'artistic_receipt_sha256':s['artistic_receipt_sha256'],
          'lighthouse_summary_sha256':s['lighthouse_summary_sha256']}
        write(build/'uiux-v2-integrity.json',manifest)
        result=subprocess.run([binary,'deploy','--yes','--cwd',str(build)],
            capture_output=True,text=True,timeout=180)
        require(result.returncode==0,'VERCEL_PREVIEW_FAILED:'+result.stderr[-200:])
        urls=re.findall(r'https://[A-Za-z0-9.-]+\.vercel\.app',result.stdout)
        require(bool(urls),'VERCEL_PREVIEW_URL_MISSING')
        url=urls[-1];host=urllib.parse.urlsplit(url).hostname
        require(host and host.endswith('.vercel.app'),'UNTRUSTED_PREVIEW_HOST')
        with urllib.request.urlopen(url+'/uiux-v2-integrity.json',timeout=20) as response:
            require(response.status==200,'PREVIEW_REMOTE_MANIFEST_UNAVAILABLE')
            served=json.load(response)
        require(served==manifest,'PREVIEW_REMOTE_HASH_MISMATCH')
        require(treehash(w/'site')==s['site_sha256'],'SOURCE_CHANGED_DURING_DEPLOY')
        receipt={'status':'PASS','url':url,'source_sha256':s['site_sha256'],
          'remote_manifest_verified':True,'production_deployed':False}
        write(w/'reports/verified-preview-deploy.json',receipt)
        s=state(w);s['preview_url']=url
        s['preview_receipt_sha256']=sha(w/'reports/verified-preview-deploy.json')
        s['stage_status']['isolated_preview']='PASS'
        write(w/'engine-state.json',s)
        return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--workspace',required=True,type=Path)
    p.add_argument('--deploy-preview',action='store_true')
    a=p.parse_args()
    try:print(json.dumps(deploy(workspace(a.workspace),a.deploy_preview),indent=2))
    except Exception as e:
        print(json.dumps({'status':'BLOCKED','deployed':False,
          'reason':type(e).__name__+':'+str(e)[:270]}));sys.exit(4)
