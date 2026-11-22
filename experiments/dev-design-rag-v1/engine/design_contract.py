"""Project-scoped RAG-first design context and deterministic HTML verification.

A local brand policy is not a model score, artistic certificate or release grant.
"""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

PROJECTS=Path(__file__).resolve().parents[1]/'knowledge/project_policies'
SECTION_BUDGET={'project':1050,'brand':1450,'generic':650,'type':240}

def policy_for(project):
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,64}',project):
        raise ValueError('INVALID_PROJECT_ID')
    file=PROJECTS/(project+'.json')
    if not file.exists():return None
    if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(PROJECTS.resolve()):
        raise ValueError('UNTRUSTED_PROJECT_POLICY')
    d=json.loads(file.read_text())
    if d.get('schema')!='owner-verified-design-constraints-v1' or d.get('project')!=project:
        raise ValueError('PROJECT_POLICY_INTEGRITY')
    if not re.fullmatch(r'https://wa\.me/[1-9][0-9]{7,14}',str(d.get('official_whatsapp',''))):
        raise ValueError('PROJECT_CONTACT_INVALID')
    return d

def writer_context(packet,project,max_chars=4600):
    if not isinstance(packet,str) or len(packet)<300:raise ValueError('SOURCE_RAG_REQUIRED')
    p=policy_for(project)
    if '[project/'+project+' ' not in packet:raise ValueError('RAG_PROJECT_SCOPE_MISMATCH')
    sections={}
    matches=list(re.finditer(r'^\[(project|brand|generic|type)/',packet,re.M))
    if not matches:raise ValueError('RAG_LAYER_MARKERS_MISSING')
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(packet)
        sections.setdefault(m.group(1),[]).append(packet[m.start():end].strip())
    if not all(sections.get(k) for k in SECTION_BUDGET):
        raise ValueError('RAG_AUTHORITY_LAYER_MISSING')
    parts=['DESIGN CONTRACT: Owner/project then brand, shared rules, type. Historic critiques are not active instructions.']
    if p:
        source=Path(__file__).resolve().parents[1]/p['source']
        if not source.is_file() or source.is_symlink():raise ValueError('BRAND_SOURCE_MISSING')
        text=source.read_text()
        if p['official_whatsapp'] not in text or p['brand'] not in text:
            raise ValueError('PROJECT_POLICY_SOURCE_MISMATCH')
        facts={k:p[k] for k in ('project','brand','location','official_whatsapp','official_map','logo','reference_image','reference_image_scope','required_links')}
        parts.append('VERIFIED PROJECT FACTS: '+json.dumps(facts,ensure_ascii=False,sort_keys=True))
        parts.append('Never invent contacts, room views, dimensions or amenities. WCAG AA contrast >=4.5:1; do not overlay text on photos.')
    for k,limit in SECTION_BUDGET.items():
        parts.append('['+k.upper()+' SOURCE] '+sections[k][0][:limit])
    result='\n'.join(parts)
    if len(result)>max_chars:raise ValueError('WRITER_CONTEXT_BUDGET_EXCEEDED')
    if p and p['official_whatsapp'] not in result:raise ValueError('APPROVED_CONTACT_MISSING_FROM_CONTEXT')
    return result

class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[];self.images=[];self.lang='';self.headings=[];self.main=False
        self.text=[];self.scripts=False;self.script_tags=[];self._h1=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='html':self.lang=a.get('lang','')
        if tag=='main':self.main=True
        if tag=='h1':self._h1=True
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='img':self.images.append(a)
        if tag=='script':self.scripts=True;self.script_tags.append(a)
    def handle_endtag(self,tag):
        if tag=='h1':self._h1=False
    def handle_data(self,data):
        if self._h1:self.headings.append(data)
        if data.strip():self.text.append(data)

def validate_html(html,project,site=None,page=None):
    if not isinstance(html,str) or len(html)<200 or '<html' not in html.lower():
        raise ValueError('RENDERABLE_HTML_REQUIRED')
    if len(html.encode())>30000:raise ValueError('WRITER_HTML_MAX_BYTES')
    p=policy_for(project);d=Document()
    try:d.feed(html)
    except Exception as e:raise ValueError('UNPARSABLE_HTML') from e
    if not d.lang or not d.main or not ''.join(d.headings).strip():
        raise ValueError('ACCESSIBLE_PAGE_STRUCTURE_REQUIRED')
    if not p:return {'status':'PASS','policy':'generic-only'}
    if p['brand'].lower() not in html.lower():raise ValueError('CANONICAL_BRAND_MISSING')
    for link in p['required_links']:
        if not any(h.split('#')[0].split('?')[0]==link for h in d.links):
            raise ValueError('REQUIRED_NAV_MISSING:'+link)
    expected=urlparse(p['official_whatsapp'])
    whatsapp=[h for h in d.links if 'wa.me/' in h.lower()]
    if not whatsapp:raise ValueError('OFFICIAL_BOOKING_CONTACT_MISSING')
    for link in whatsapp:
        u=urlparse(link)
        if u.scheme!='https' or u.hostname!=expected.hostname or u.path!=expected.path:
            raise ValueError('UNAPPROVED_WHATSAPP_CONTACT')
    for link in d.links:
        u=urlparse(link)
        if u.scheme in ('http','https') and u.hostname not in ('wa.me','maps.app.goo.gl'):
            raise ValueError('UNAPPROVED_EXTERNAL_LINK')
    imgs=[x.get('src','') for x in d.images]
    if p['logo'] not in imgs or ((page is None or page=='index.html') and p['reference_image'] not in imgs):
        raise ValueError('OFFICIAL_LOGO_AND_INTERIOR_REQUIRED')
    for f in imgs:
        if site:
            img=Path(site)/f
            if (Path(f).is_absolute() or '..' in Path(f).parts or not img.is_file()
                    or img.is_symlink() or not img.resolve().is_relative_to(Path(site).resolve())):
                raise ValueError('UNVERIFIED_IMAGE_ASSET')
    for image in d.images:
        alt=image.get('alt','')
        if not alt.strip():raise ValueError('IMAGE_ALT_REQUIRED')
        if image.get('src')==p['reference_image'] and re.search(
            r'king|suite|sea|view|bathroom|double bed|private ac|luxury',alt,re.I):
            raise ValueError('INTERIOR_PHOTO_MISLABELLED')
    prose=' '.join(d.text+[x.get('alt','') for x in d.images])
    for pattern in p['prohibited_claim_patterns']:
        if re.search(pattern,prose,re.I):
            raise ValueError('UNSUPPORTED_PROPERTY_CLAIM:'+pattern)
    if d.scripts:
        require_hash='5838d85f62edc0077fb68969c91887e30cec278f1b72c1bb322e1cc93c883e11'
        if not site:raise ValueError('UNREVIEWED_SCRIPT')
        if len(d.script_tags)!=1:raise ValueError('SCRIPT_COUNT_NOT_APPROVED')
        tag=d.script_tags[0]
        if tag.get('src')!='assets/site.js' or set(tag)-{'src','defer'} or 'defer' not in tag:
            raise ValueError('UNREVIEWED_SCRIPT')
        src=Path(site)/'assets/site.js'
        if not src.is_file() or src.is_symlink() or hashlib.sha256(src.read_bytes()).hexdigest()!=require_hash:
            raise ValueError('UNTRUSTED_SITE_SCRIPT')
        if re.search(r'<script[^>]*>\s*[^\s<]',html,re.I):
            raise ValueError('INLINE_SCRIPT_FORBIDDEN')
    return {'status':'PASS','policy':p['schema'],
        'checks':['brand','contact','nav','asset-provenance','claim-guard','page-structure']}
