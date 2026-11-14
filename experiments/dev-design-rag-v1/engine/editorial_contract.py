"""Source-bound Andaz editorial fact preflight, NOT an artistic score.

Rejects known unsupported claims; full factual truth still requires owner source review.
"""
import re
from html.parser import HTMLParser

class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.sections=0;self.images=[];self.words=[];self.main=False;self.forms=0
  self.section_stack=[];self.section_details=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='section':
   self.sections+=1
   item={'words':[],'images':[],'links':[]}
   self.section_details.append(item);self.section_stack.append(item)
  if tag=='img':
   self.images.append(a.get('src',''))
   for section in self.section_stack:section['images'].append(a.get('src',''))
  if tag=='a':
   for section in self.section_stack:section['links'].append(a.get('href',''))
  if tag=='main':self.main=True
  if tag=='form':self.forms+=1
 def handle_endtag(self,tag):
  if tag=='section' and self.section_stack:self.section_stack.pop()
 def handle_data(self,data):
  words=re.findall(r"\b[\w'-]+\b",data)
  self.words.extend(words)
  for section in self.section_stack:section['words'].extend(words)

def check_editorial(html,page,project,room_photo='media/andaz_room_01_wide.webp'):
 if project!='andaz-vibe-stay':return {'status':'PASS','scope':'generic-no-editorial-claim'}
 p=Page();p.feed(html);issues=[]
 minimum={'index.html':3,'rooms.html':2,'experiences.html':3,'food.html':2,'explore.html':1,'contact.html':2}
 if p.sections<minimum.get(page,1):issues.append('INSUFFICIENT_EDITORIAL_SECTIONS')
 minwords={'index.html':145,'rooms.html':110,'experiences.html':125,'food.html':95,'explore.html':65,'contact.html':110}
 if len(p.words)<minwords.get(page,60):issues.append('THIN_PAGE_CONTENT')
 if page in ('food.html','experiences.html') and room_photo in p.images:
  issues.append('UNSUPPORTED_CONTEXTUAL_ROOM_PHOTOGRAPH')
 if page=='index.html' and room_photo not in p.images:issues.append('VERIFIED_ROOM_IMAGE_MISSING_ON_HOME')
 if page=='index.html' and p.images.count(room_photo)>2:issues.append('REPEATED_ROOM_IMAGE_OVERUSE')
 if page=='contact.html' and p.forms<1:issues.append('CONTACT_FORM_REQUIRED')
 if re.search(r'additional editorial content could go here|lorem ipsum|placeholder|coming soon',html,re.I):
  issues.append('UNFINISHED_PLACEHOLDER')
 prose=' '.join(p.words)
 # Claims neither present in the owner-approved inventory nor independently verified.
 unsupported=(r'\b(?:suites?|balcon(?:y|ies)|king size|sea views?|guided (?:walks?|tours?)|'
  r'sunrise yoga|luxury resort|global twists|wi\W*fi|flat\W*screen|televisions?|'
  r'workspaces?|sustainab\w*|chefs?|locally\W+sourced|shared kitchens?|common lounges?|'
  r'nightly gatherings?|weekly flea market|staff provide|short walk)\b')
 if re.search(unsupported,prose,re.I):issues.append('UNVERIFIED_HOSPITALITY_OR_MENU_CLAIM')
 if page=='index.html':
  table=[s for s in p.section_details if re.search(r'\bAndaz Table\b',' '.join(s['words']),re.I)]
  if table and not any('food.html' in s['links'] for s in table):
   issues.append('FOOD_TEASER_WRONG_DESTINATION')
  if any(room_photo in s['images'] for s in table):issues.append('ROOM_PHOTO_MISUSED_AS_FOOD')
  if any(room_photo in s['images'] and re.search(r'\bExplore\b',' '.join(s['words']),re.I)
         for s in p.section_details):issues.append('ROOM_PHOTO_MISUSED_AS_DESTINATION')
 if page=='rooms.html':
  for s in p.section_details:
   text=' '.join(s['words'])
   if re.search(r'2\W*bed\W*non\W*ac',text,re.I) and re.search(r'\bprivate\b',text,re.I):
    issues.append('TWO_BED_DORM_MISREPRESENTED_AS_PRIVATE');break
 if page=='food.html':
  if not re.search(r'(?:₹|Rs\.?\s*)\s*180\b',html) or not re.search(r'(?:₹|Rs\.?\s*)\s*220\b',html):
   issues.append('OWNER_PRICE_FACTS_MISSING')
 return {'status':'PASS' if not issues else 'BLOCKED','page':page,'section_count':p.sections,'word_count':len(p.words),
  'issues':sorted(set(issues)),'artistic_score':None,'independent_certification':False}
