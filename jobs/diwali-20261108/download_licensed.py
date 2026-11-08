import urllib.request,urllib.parse,urllib.error,json,hashlib,time,pathlib,sys
W=pathlib.Path.home()/'moksha-diwali-v8-20261108'/'private'
UA='MokshaReelBot/1.0 (https://github.com/karanzing1992/engagement-core)'
files={'festive_motion.webm':'Happy Diwali.webm','diya_closeup.jpg':'Diwali deep.jpg','diya_rangoli.jpg':'Rangoli in diwali 2025.jpg','diya_group.jpg':'Diwali k deepak.jpg','music_original.ogg':'Samuel Corwin - A Man Approaches with Bowed Sitar, Rishikesh.ogg'}
for path,title in files.items():
 q=urllib.parse.urlencode({'action':'query','format':'json','prop':'imageinfo','iiprop':'url|sha1|size|extmetadata','titles':'File:'+title})
 req=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+q,headers={'User-Agent':UA})
 pages=json.load(urllib.request.urlopen(req,timeout=20))['query']['pages']
 meta=next(iter(pages.values()))['imageinfo'][0]
 assert 0<meta['size']<=25000000
 license=meta['extmetadata']['LicenseShortName']['value']
 assert license in ('CC BY 4.0','CC BY-SA 4.0','CC BY-SA 3.0')
 dest=W/path
 if dest.exists() and dest.stat().st_size==meta['size'] and hashlib.sha1(dest.read_bytes()).hexdigest()==meta['sha1']:
  print('CACHED_VERIFIED',path,dest.stat().st_size,flush=True);continue
 tmp=dest.with_suffix(dest.suffix+'.part')
 tmp.unlink(missing_ok=True)
 total=meta['size']
 try:
  with open(tmp,'wb') as out:
   pos=0
   while pos<total:
    end=min(total-1,pos+4194303)
    r=urllib.request.Request(meta['url'],headers={'User-Agent':UA,'Range':f'bytes={pos}-{end}'})
    for retry in range(3):
     try:
      resp=urllib.request.urlopen(r,timeout=50)
      break
     except urllib.error.HTTPError as e:
      if e.code not in (429,503) or retry>=2:raise
      wait=int(e.headers.get('Retry-After','10'))
      if wait>30:raise RuntimeError('WIKIMEDIA_RATE_LIMIT_WAIT_TOO_LONG')
      time.sleep(max(1,wait))
    code=resp.status; data=resp.read()
    if code==200 and pos==0 and len(data)==total:out.write(data);pos=total;break
    content_range=resp.headers.get('Content-Range','')
    assert code==206 and content_range==f'bytes {pos}-{end}/{total}' and len(data)==end-pos+1,(code,content_range,len(data))
    out.write(data);pos=end+1
    print('RANGE',path,pos,'/',total,flush=True)
  assert tmp.stat().st_size==total and hashlib.sha1(tmp.read_bytes()).hexdigest()==meta['sha1']
  tmp.replace(dest)
 except Exception:
  tmp.unlink(missing_ok=True);raise
 print('DOWNLOADED_SHA1_VERIFIED',path,license,total,hashlib.sha256(dest.read_bytes()).hexdigest(),flush=True)
