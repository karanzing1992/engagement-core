"""Bounded, provenance-recorded CSS repairs; never an artistic-score substitute."""
import hashlib,re
from pathlib import Path
from core import write,require

# Accessible UI primitives with known semantics; unknown components must fail closed.
SAFE_COMPONENT_RULES={
 'whatsapp-link': '.whatsapp-link{display:inline-flex;gap:.5rem;align-items:center;color:var(--color-indigo);font-weight:700;text-decoration:underline;}',
 'btn-secondary': '.btn-secondary{background:#ffffff;color:var(--color-dark);border:2px solid var(--color-dark);}.btn-secondary:hover{background:var(--color-cream);}',
 'chip-group': '.chip-group{display:flex;flex-wrap:wrap;align-items:center;gap:.65rem;margin-block:1rem;}',
 'explore-controls': '.explore-controls{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr));align-items:end;margin-block:1rem;}',
 'form-error': '.form-error{color:#8b1717;font-weight:600;min-height:1.5rem;}'
}
# Classes established on the actual owner-approved Andaz six-page DOM.
# Each rule controls a specific UI component, not an invented model/art score.
R2_COMPONENT_RULES={
 'top-bar':'.top-bar{display:flex;flex-wrap:wrap;gap:1rem;align-items:center;justify-content:space-between;padding-block:.65rem;}',
 'site-nav':'.site-nav{display:block;min-width:0;max-width:100%;}',
 'logo-link':'.logo-link{display:inline-flex;align-items:center;max-width:12rem;flex-shrink:0;}.logo-link .logo{display:block;width:auto;height:auto;max-width:100%;max-height:5.8rem;}',
 'card-title':'.card-title{font-size:clamp(1.1rem,2vw,1.45rem);font-weight:700;line-height:1.25;margin-bottom:.5rem;}',
 'cards':'.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,16rem),1fr));gap:1.2rem;align-items:stretch;margin-block:1.2rem 2rem;}',
 'filters':'.filters{display:flex;max-width:100%;align-items:center;gap:.6rem;overflow-x:auto;padding-block:.7rem 1rem;scrollbar-width:thin;}',
 'main':'.main{max-width:1200px;margin-inline:auto;padding-block:clamp(1.25rem,3vw,3rem);}',
 'nav':'.nav{display:block;max-width:100%;min-width:0;}',
 'btn-primary':'.btn-primary{background:var(--color-charcoal);color:var(--color-white);}.btn-primary:hover,.btn-primary:focus-visible{background:#3a3a3a;color:#fff;}',
 'btn-secondary':'.btn-secondary{background:#fff;color:var(--color-charcoal);border:2px solid var(--color-charcoal);}.btn-secondary:hover,.btn-secondary:focus-visible{background:var(--color-cream);color:var(--color-charcoal);}',
 'chip-group':'.chip-group{display:flex;align-items:center;gap:.55rem;flex-wrap:wrap;margin-block:.8rem;}',
 'explore-controls':'.explore-controls{display:grid;gap:1rem;grid-template-columns:repeat(auto-fit,minmax(min(100%,14rem),1fr));align-items:center;margin-block:1rem 1.6rem;}',
 'form-control':'.form-control{display:block;max-width:100%;width:100%;min-height:44px;padding:.65rem .85rem;color:var(--color-charcoal);background:#fff;border:1px solid var(--color-charcoal);border-radius:.35rem;}',
 'mt-1':'.mt-1{margin-block-start:1rem;}',
 'text-center':'.text-center{text-align:center;}',

}
SAFE_COMPONENT_RULES.update(R2_COMPONENT_RULES)
R2_HERO_BOUNDING='''

/* V9 R2 source-bound hero: prevents viewport clipping and unconstrained photos */
.hero{height:auto;min-height:0;max-height:none;display:grid;grid-template-columns:1fr;gap:clamp(.9rem,2vw,1.7rem);padding-block:clamp(1rem,3vw,2.4rem);overflow:visible;}
.hero img{width:100%;height:auto;max-height:480px;aspect-ratio:16/9;object-fit:cover;object-position:center;display:block;}
@media(min-width:900px){.hero{grid-template-columns:minmax(0,1fr) minmax(0,1.25fr);align-items:center;}}
'''
def repair(w,css_file,report):
    issues=report.get('issues',[])
    require(issues and all(x.startswith('UNSTYLED_COMPONENT_CLASSES:') or x in ('INVALID_MEDIA_QUERY_VARIABLE','FULL_WIDTH_UNBOUNDED_IMAGE:index.html') for x in issues),'NONDETERMINISTIC_STYLE_REPAIR_REQUIRED')
    missing=set(v for entries in report.get('missing_classes',{}).values() for v in entries)
    require(missing.issubset(SAFE_COMPONENT_RULES),'UNRECOGNIZED_COMPONENT_NOT_PATCHED')
    css=Path(w)/'site'/css_file
    require(css.is_file() and not css.is_symlink() and css.resolve().is_relative_to((Path(w)/'site').resolve()),'UNSAFE_STYLESHEET')
    before=css.read_text();updated=before
    fix=[]
    if 'INVALID_MEDIA_QUERY_VARIABLE' in issues:
        variables=dict(re.findall(r'(--bp-[a-z]+):\s*([0-9]+px)\s*;',before))
        def resolve_token(match):
            token=match.group(1)
            require(token in variables,'UNDEFINED_MEDIA_BREAKPOINT')
            fix.append('MEDIA_QUERY_LITERAL:'+token)
            return variables[token]
        # Substitute only the header of an actual @media statement.
        def media_header(match):
            return re.sub(r'var\((--bp-[a-z]+)\)',resolve_token,match.group(0))
        updated=re.sub(r'@media\s*\([^{}]*?\)\s*\{',media_header,updated)
    if missing:
        updated+='\n/* SOURCE-GROUNDED V9 COMPONENT REPAIR — NOT AN ARTISTIC CERTIFICATE */\n'
        for c in sorted(missing):
            updated+=SAFE_COMPONENT_RULES[c]+'\n'
            fix.append('MISSING_CLASS:'+c)
    if 'FULL_WIDTH_UNBOUNDED_IMAGE:index.html' in issues:
        home=Path(w)/'site/index.html'
        require(home.is_file() and not home.is_symlink(),'HOME_FOR_IMAGE_REPAIR_REQUIRED')
        html=home.read_text()
        require(bool(re.search(r'\bclass=["\'][^"\']*\bhero\b',html)) and
                'width:100%;height:auto' in html.replace(' ',''),'UNVERIFIED_IMAGE_REPAIR_SCOPE')
        updated+=R2_HERO_BOUNDING
        fix.append('BOUND_REAL_HOME_HERO_IMAGE')
    require(updated!=before,'REPAIR_NO_CHANGE')
    original_hash=hashlib.sha256(before.encode()).hexdigest()
    backed=Path(w)/'evidence'/('layout-css-before-'+original_hash[:16]+'.css')
    require(not backed.exists(),'LAYOUT_BACKUP_ALREADY_EXISTS')
    backed.write_text(before)
    css.write_text(updated)
    result={'schema':'uiux-deterministic-layout-repair-v1','source_css':css_file,'original_sha256':original_hash,'updated_sha256':hashlib.sha256(updated.encode()).hexdigest(),'repairs':fix,'artistic_score':None,'review_certified':False,'production_modified':False}
    write(Path(w)/'reports/layout-repair.json',result)
    return result
