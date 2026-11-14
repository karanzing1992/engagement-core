import unittest,tempfile
from pathlib import Path
from layout_repair import repair
from multipage_contract import layout_preflight
class R2LayoutTests(unittest.TestCase):
 def test_only_genuine_home_image_and_known_classes(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);site=w/'site';(site/'assets').mkdir(parents=True);(w/'evidence').mkdir();(w/'reports').mkdir()
   (site/'assets/v9-fresh.css').write_text(':root{--color-cream:#fafafa;--color-charcoal:#222;} .hero{height:50vh;}@media(max-width:390px){.hero{height:40vh;}}'+'.x{color:#333;}'*120)
   (site/'index.html').write_text('<html><meta name="viewport"><link rel="stylesheet" href="assets/v9-fresh.css"><div class="hero top-bar"><img style="width:100%;height:auto" src="photo.webp"></div></html>')
   before=layout_preflight(site,['index.html'],'assets/v9-fresh.css')
   self.assertEqual(before['status'],'BLOCKED')
   r=repair(w,'assets/v9-fresh.css',before)
   self.assertIn('BOUND_REAL_HOME_HERO_IMAGE',r['repairs'])
   self.assertIn('MISSING_CLASS:top-bar',r['repairs'])
   after=layout_preflight(site,['index.html'],'assets/v9-fresh.css')
   self.assertEqual(after['status'],'PASS',after)
 def test_unknown_classes_remain_blocked(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);(w/'site/assets').mkdir(parents=True);(w/'evidence').mkdir();(w/'reports').mkdir()
   (w/'site/assets/v9-fresh.css').write_text(':root{}')
   with self.assertRaisesRegex(ValueError,'UNRECOGNIZED_COMPONENT_NOT_PATCHED'):
    repair(w,'assets/v9-fresh.css',{'issues':['UNSTYLED_COMPONENT_CLASSES:madeup'],'missing_classes':{'index.html':['madeup']}})
 def test_unknown_image_page_blocked(self):
  with tempfile.TemporaryDirectory() as t:
   w=Path(t);(w/'site/assets').mkdir(parents=True);(w/'evidence').mkdir();(w/'reports').mkdir()
   (w/'site/assets/v9-fresh.css').write_text(':root{}')
   with self.assertRaisesRegex(ValueError,'NONDETERMINISTIC_STYLE_REPAIR_REQUIRED'):
    repair(w,'assets/v9-fresh.css',{'issues':['FULL_WIDTH_UNBOUNDED_IMAGE:unknown.html'],'missing_classes':{}})
if __name__=='__main__':unittest.main()
