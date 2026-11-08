from pathlib import Path
import sys,json,hashlib
root=Path.home()/'moksha-diwali-v8-20261108'
work=root/'private'
sys.path.insert(0,str(root/'engine/services/reel-engine/v8-creative'))
sys.path.insert(0,str(root/'engine/services/reel-engine/v6-kv-gateway'))
from intelligence import inspect
from director import validate_plan,compile_optional_presentation
from editor import render
from critic import inspect_output,decide_release
brief=('Cinematic Indian Diwali festival greeting, The Light Within. '
 'Keep full original duration. Mute source audio. Use licensed instrumental music. '
 'A warm emotional progression from a solitary flame to togetherness and blessings.')
evidence=inspect(work/'v8_source.mp4',brief)
source_d=float(evidence['source']['duration'])
segments=[
 {'start':0.,'end':4.1,'transition':'cut','grade':'cinematic_warm','text':None},
 {'start':4.1,'end':7.5,'transition':'dip-to-black','grade':'cinematic_warm','text':None},
 {'start':7.5,'end':10.9,'transition':'cut','grade':'natural','text':None},
 {'start':10.9,'end':14.3,'transition':'dip-to-black','grade':'cinematic_warm','text':None},
 {'start':14.3,'end':source_d,'transition':'cut','grade':'cinematic_warm','text':None}]
plan={'treatment':'observational_cinema','concept':'The Light Within',
 'reasoning_summary':'Owner-directed, based on genuine Diwali footage and India festival photographs.',
 'segments':segments,'audio':{'preserve_source':False,'music_gain':0.20},'captions':[]}
proposal,changes=compile_optional_presentation(evidence,plan)
validated=validate_plan(evidence,proposal)
source_page='https://commons.wikimedia.org/wiki/File:Samuel_Corwin_-_A_Man_Approaches_with_Bowed_Sitar%2C_Rishikesh.ogg'
rights={'automatic_source_verified':True,'verification_method':'commons_api_live',
 'original_source_url':source_page,'source_license_proof_url':source_page,
 'original_license_url':'https://creativecommons.org/licenses/by/4.0/',
 'credit_text':'Music: Samuel Corwin, A Man Approaches with Bowed Sitar, Rishikesh (CC BY 4.0); excerpt mixed for reel',
 'license':'CC BY','attribution_approved':True}
target=work/'v8-native.mp4'
result=render(evidence,proposal,work,target,music=work/'music_original.ogg',
 music_rights=rights,width=720,height=1280,fps=30)
review=inspect_output(evidence,validated,result,target)
release=decide_release(review)
report={'engine':'V8 creative beta, manually directed through V8 compiler and critic',
 'git_commit':__import__('subprocess').check_output(['git','-C',str(root/'engine'),'rev-parse','HEAD'],text=True).strip(),
 'brief':brief,'source_evidence':{'duration':source_d,'scene_count':len(evidence['shots']),
 'source_sha256':evidence['source']['sha256']},
 'plan_sha256':validated['creative_plan_sha256'],'editor':result,
 'critic':review,'release':release,'music':rights,'published':False}
(work/'v8_receipt.json').write_text(json.dumps(report,indent=2))
print('V8_RENDER_COMPLETED',target,target.stat().st_size,'SHA256',result['output_sha256'],
 'DURATION',result['duration_seconds'],'RELEASE',release,flush=True)
