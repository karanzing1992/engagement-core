import subprocess,pathlib,json,hashlib
W=pathlib.Path.home()/'moksha-diwali-v8-20261108'/'private'
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=115)
 if p.returncode:raise RuntimeError(p.stderr[-1400:])
def photo(name,output,seconds,focus):
 frames=round(seconds*30)
 # Licensed original photograph gets a subtle camera push without synthetic art.
 vf=(f"scale=900:1600:force_original_aspect_ratio=increase,"
 f"crop=900:1600:x=(iw-900)*{focus}:y=(ih-1600)/2,"
 f"zoompan=z='min(zoom+0.00045,1.065)':d={frames}:"
 f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=30,"
 f"setsar=1,format=yuv420p")
 run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-i',str(W/name),
  '-vf',vf,'-frames:v',str(frames),'-an','-c:v','libx264','-preset','ultrafast',
  '-crf','20','-r','30',str(W/output)])
def motion():
 run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','7.1','-t','3.4',
  '-i',str(W/'festive_motion.webm'),'-vf',
  'scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=30',
  '-an','-c:v','libx264','-preset','ultrafast','-crf','20','-r','30',str(W/'shot03.mp4')])
timeline=[('diya_closeup.jpg','shot01.mp4',4.1,.35),
          ('diya_group.jpg','shot02.mp4',3.4,.65),
          ('festive_motion.webm','shot03.mp4',3.4,.5),
          ('diya_rangoli.jpg','shot04.mp4',3.4,.5),
          ('diya_closeup.jpg','shot05.mp4',4.1,.22)]
for f,out,seconds,focus in timeline:
 if f.endswith('.webm'):motion()
 else:photo(f,out,seconds,focus)
concat=W/'base_concat.txt'
concat.write_text(''.join("file '"+x[1]+"'\n" for x in timeline))
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
 '-i',str(concat),'-c','copy',str(W/'v8_source.mp4')])
meta={'project':'Moksha Diwali The Light Within','editorial_region':'India',
  'source_status':'originals SHA1 and SHA256 verified from Wikimedia Commons API',
  'clips':timeline,'clip_source_licenses':[
    {'source':'https://commons.wikimedia.org/wiki/File:Diwali_deep.jpg','author':'Shantanoo','license':'CC BY 4.0','modified':True},
    {'source':'https://commons.wikimedia.org/wiki/File:Diwali_k_deepak.jpg','author':'Abhimeena3213','license':'CC BY 4.0','modified':True},
    {'source':'https://commons.wikimedia.org/wiki/File:Happy_Diwali.webm','author':'Pratiksha','license':'CC BY-SA 3.0','modified':True},
    {'source':'https://commons.wikimedia.org/wiki/File:Rangoli_in_diwali_2025.jpg','author':'Anushka10patel','license':'CC BY 4.0','modified':True}],
  'source_sha256':hashlib.sha256((W/'v8_source.mp4').read_bytes()).hexdigest()}
(W/'source_manifest.json').write_text(json.dumps(meta,indent=2))
print('MONTAGE_DONE', (W/'v8_source.mp4').stat().st_size,meta['source_sha256'])
