import tempfile,unittest
from pathlib import Path
from multipage_contract import layout_preflight

CSS=':root{--ink:#213345;--sand:#f7f2e9}body{color:var(--ink)}.hero{padding:3rem}.hero img{width:100%;max-height:35rem;object-fit:cover}.container{max-width:72rem}.site-header{display:flex}.nav-list{display:flex}.grid{display:grid}.card{padding:1rem}.btn{padding:.7rem}.title{font-weight:700}@media(max-width:767px){.grid{display:block}}'+'/* design tokens */'*75
class MultipageGuardTests(unittest.TestCase):
 def make(self,n=5):
  tmp=tempfile.TemporaryDirectory();root=Path(tmp.name);(root/'assets').mkdir()
  (root/'assets/site.css').write_text(CSS)
  names=['index.html']+['page'+str(i)+'.html' for i in range(1,n)]
  for page in names:
   nav=''.join('<a href="'+p+'">'+p+'</a>' for p in names)
   (root/page).write_text('<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/site.css"></head><body><header class="site-header">'+nav+'</header><main class="container"><h1 class="title">Real page</h1><section class="hero"><img src="photo.jpg" alt="Room" /></section><div class="grid"><article class="card"><a class="btn" href="index.html">Home</a></article></div></main></body></html>')
  return tmp,root,names
 def test_full_sitemap_5_12_64(self):
  for n in (5,12,64):
   t,root,names=self.make(n)
   with t:
    r=layout_preflight(root,names,'assets/site.css')
    self.assertEqual(r['status'],'PASS',r)
    self.assertEqual(r['reachable'],n)
 def test_missing_component_styles_rejected(self):
  t,root,names=self.make()
  with t:
   css=root/'assets/site.css';css.write_text(css.read_text().replace('.hero{padding:3rem}','').replace('.hero img{width:100%;max-height:35rem;object-fit:cover}',''))
   r=layout_preflight(root,names,'assets/site.css')
   self.assertIn('UNSTYLED_COMPONENT_CLASSES:hero',r['issues'])
 def test_disconnected_route_rejected(self):
  t,root,names=self.make()
  with t:
   for p in names:
    f=root/p;f.write_text(f.read_text().replace('href="page4.html"','href="index.html"'))
   r=layout_preflight(root,names,'assets/site.css')
   self.assertTrue(any('DISCONNECTED_PAGES:page4.html' in x for x in r['issues']))
 def test_unbounded_portrait_hero_rejected(self):
  t,root,names=self.make()
  with t:
   css=root/'assets/site.css';css.write_text(css.read_text().replace('max-height:35rem;object-fit:cover','object-fit:cover'))
   r=layout_preflight(root,names,'assets/site.css')
   self.assertIn('UNCONSTRAINED_HERO_IMAGE:index.html',r['issues'])
 def test_missing_css_link_rejected(self):
  t,root,names=self.make()
  with t:
   f=root/'index.html';f.write_text(f.read_text().replace('href="assets/site.css"','href="wrong.css"'))
   r=layout_preflight(root,names,'assets/site.css')
   self.assertIn('SHARED_CSS_NOT_LINKED:index.html',r['issues'])
if __name__=='__main__':unittest.main()
