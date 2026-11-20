"""Multi-page visual preflight: structural evidence only, never artistic scoring."""
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from core import require

class Scan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=set();self.classes=set();self.styles=[];self.viewport=False;self.stylesheets=set()
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('class'):self.classes.update(a['class'].split())
        if tag=='a':
            link=a.get('href','').split('#')[0].split('?')[0]
            if link and not urlsplit(link).scheme and not link.startswith('//'):
                self.links.add(link.lstrip('./'))
        if tag=='link' and 'stylesheet' in a.get('rel','').split():
            self.stylesheets.add(a.get('href',''))
        if tag=='meta' and a.get('name','').lower()=='viewport':self.viewport=True
        if tag=='img' and a.get('style'):self.styles.append(a['style'].lower())

def layout_preflight(site,pages,css_file):
    root=Path(site)
    require(root.is_dir() and not root.is_symlink(),'SITE_REQUIRED')
    css=root/css_file
    require(css.is_file() and not css.is_symlink(),'SHARED_STYLE_MISSING')
    style=css.read_text()
    require(len(style)>1200 and ':root' in style and '@media' in style,'RESPONSIVE_DESIGN_SYSTEM_MISSING')
    selectors=set(re.findall(r'\.([a-zA-Z][\w-]*)',style))
    graph={};missing={};issues=[]
    names=set(pages)
    require('index.html' in names,'HOMEPAGE_REQUIRED')
    for page in pages:
        f=root/page
        require(f.is_file() and not f.is_symlink() and f.resolve().is_relative_to(root.resolve()),'PAGE_MISSING:'+page)
        html=f.read_text()
        s=Scan();s.feed(html)
        if not s.viewport:issues.append('VIEWPORT_MISSING:'+page)
        if css_file not in s.stylesheets:issues.append('SHARED_CSS_NOT_LINKED:'+page)
        graph[page]={x for x in s.links if x in names}
        page_missing={x for x in s.classes if x not in selectors and x not in {'open','active','is-active','hidden'}}
        if page_missing:missing[page]=sorted(page_missing)
        if ('class="hero"' in html or "class='hero'" in html):
            controlled=('max-height' in style or 'aspect-ratio' in style or
              bool(re.search(r'\.hero(?:\s+[\w.>-]+)*\s*img\s*\{[^}]*(height|aspect-ratio)',style,re.S)))
            if not controlled:issues.append('UNCONSTRAINED_HERO_IMAGE:'+page)
        if any('width:100%' in x.replace(' ','') and 'height:auto' in x.replace(' ','') and 'max-height' not in x
               for x in s.styles) and 'max-height' not in style:
            issues.append('FULL_WIDTH_UNBOUNDED_IMAGE:'+page)
    reached={'index.html'};pending=['index.html']
    while pending:
        current=pending.pop()
        for child in graph[current]-reached:reached.add(child);pending.append(child)
    if reached!=names:issues.append('DISCONNECTED_PAGES:'+','.join(sorted(names-reached)))
    if missing:issues.append('UNSTYLED_COMPONENT_CLASSES:'+','.join(sorted(set(x for xs in missing.values() for x in xs))[:20]))
    return {'status':'PASS' if not issues else 'BLOCKED','pages':len(pages),
        'reachable':len(reached),'shared_css':css_file,'missing_classes':missing,
        'issues':issues,'artistic_score':None,'independent_artistic_certified':False}
