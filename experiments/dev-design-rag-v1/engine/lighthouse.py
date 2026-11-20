"""Per-route, per-device real Chromium Lighthouse checks for isolated sites."""
import hashlib,json,os,subprocess
from pathlib import Path
NODE=Path.home()/'.local/share/andaz-autonomous-website-pilot-20261106/audit-engine/node_modules/lighthouse/cli/index.js'
def audit(base,site,folder,page):
    if not NODE.is_file():raise ValueError('LIGHTHOUSE_BINARY_MISSING')
    if page!=Path(page).name or not page.endswith('.html') or not (site/page).is_file():
        raise ValueError('UNSAFE_OR_MISSING_ROUTE')
    results={}
    for mode in ('mobile','desktop'):
        output=folder/('lighthouse-'+page.removesuffix('.html')+'-'+mode+'.json')
        command=['node',str(NODE),base+'/'+page,'--output=json','--output-path='+str(output),
            '--only-categories=performance,accessibility,best-practices,seo','--quiet',
            '--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage --disable-gpu',
            '--no-enable-error-reporting']
        if mode=='desktop':command+=['--preset=desktop']
        env=os.environ.copy();env['CHROME_PATH']='/usr/bin/google-chrome'
        p=subprocess.run(command,text=True,capture_output=True,timeout=110,env=env)
        if p.returncode or not output.is_file():
            raise ValueError('LIGHTHOUSE_'+page+'_'+mode+'_FAILED:'+p.stderr[-160:])
        raw=output.read_bytes();x=json.loads(raw)
        categories=x.get('categories') or {}
        scores={k:round(v['score']*100) if type(v.get('score')) in (int,float) else None
            for k,v in categories.items()}
        results[mode]={'scores':scores,'report_sha256':hashlib.sha256(raw).hexdigest()}
        for key,minimum in (('performance',90),('accessibility',95),('best-practices',90)):
            if scores.get(key) is None or scores[key]<minimum:
                raise ValueError('LIGHTHOUSE_'+page+'_'+mode+'_'+key+'_BELOW_'+str(minimum)+':'+str(scores.get(key)))
    return results
