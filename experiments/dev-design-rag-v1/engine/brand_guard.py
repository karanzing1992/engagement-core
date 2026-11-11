"""Fail-closed project-specific factual guard and concise source-grounded agent context."""
import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

class TextAndLinks(HTMLParser):
 def __init__(self):
  super().__init__();self.links=[];self.images=[];self.text=[];self.title=0
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if tag=='a':self.links.append(d.get('href',''))
  if tag=='img':self.images.append((d.get('src',''),d.get('alt','')))
  if tag=='h1':self.title+=1
 def handle_data(self,data):self.text.append(data)

def approved_facts(w):
 source=(w/'evidence/rag-packet.txt').read_text()
 state=__import__('json').loads((w/'engine-state.json').read_text())
 if hashlib.sha256(source.encode()).hexdigest()!=state['rag_sha256']:
  raise ValueError('UNTRUSTED_RAG')
 if state['project']!='andaz-vibe-stay':
  return {'project':state['project'],'source_hash':state['rag_sha256']}
 # Project-specific immutable facts, cross-verified against source-grounded RAG.
 base=(w/'site/index.html').read_text()
 phone='918999541081'
 if phone not in source or phone not in base or 'andaz-official-cropped.webp' not in base:
  raise ValueError('AND AZ_AUTHORITATIVE_FACTS_NOT_AVAILABLE')
 return {'project':state['project'],'phone':phone,'logo':'assets/andaz-official-cropped.webp',
         'image':'media/andaz_room_01_wide.webp',
         'brand':'Andaz Vibe Stay','source_hash':state['rag_sha256']}

def prioritized_context(w,max_len=1800):
 facts=approved_facts(w)
 raw=(w/'evidence/rag-packet.txt').read_text()
 if facts['project']=='andaz-vibe-stay':
  critical=('PROJECT: Andaz Vibe Stay, Temple Road, Arambol, Goa. Canonical WhatsApp '
   'https://wa.me/'+facts['phone']+'. ORIGINAL logo '+facts['logo']+
   '. Authentic single-interior photo '+facts['image']+
   '. Not an image of pool or a specific room category; no invented specifications. '
   'Only owner-backed facts. Do not publish. WCAG text contrast >=4.5:1.\n')
  layers=[]
  for name in ('[project/andaz-vibe-stay','[brand/andaz','[generic/shared','[type/hospitality'):
   at=raw.find(name)
   if at>=0:layers.append(raw[at:at+420].split('\n')[0:2][-1])
  return (critical+'\n'.join(layers))[:max_len]
 return raw[:max_len]

def validate_html(w,filename,content):
 if not filename.endswith('.html'):return {'pass':True,'checks':[]}
 facts=approved_facts(w);parser=TextAndLinks();parser.feed(content)
 if parser.title!=1 or not re.search(r'<main(?:\s|>)',content,re.I):raise ValueError('SEMANTIC_HTML_INVALID')
 if facts['project']!='andaz-vibe-stay':return {'pass':True,'checks':['semantic_html']}
 forbidden=('1234567890','en-suite','king-size','ocean view','sea view','mountain view')
 normalized=content.lower()
 if any(token in normalized for token in forbidden):
  raise ValueError('UNSUPPORTED_ROOM_OR_CONTACT_CLAIM')
 whatsapp=[x for x in parser.links if 'wa.me/' in x]
 if not whatsapp or any(not re.match(r'^https://wa\.me/'+facts['phone']+r'(?:\?|$)',x) for x in whatsapp):
  raise ValueError('WHATSAPP_CONTACT_MISMATCH')
 if not any(facts['logo']==src for src,_ in parser.images):
  raise ValueError('OFFICIAL_LOGO_REQUIRED')
 if not any(facts['image']==src for src,_ in parser.images):
  raise ValueError('REAL_ROOM_IMAGE_REQUIRED')
 if not all(any(x.startswith(page) for x in parser.links) for page in ('rooms.html','experiences.html','explore.html','contact.html')):
  raise ValueError('REQUIRED_NAV_MISSING')
 return {'pass':True,'checks':['source_grounded_phone','official_logo','real_photo','all_site_links','unsupported_claims']}
