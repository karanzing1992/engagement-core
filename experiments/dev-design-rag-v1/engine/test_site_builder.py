import json, tempfile, unittest
from pathlib import Path
from site_builder import plan
from design_contract import validate_html
from core import ROOT

class SiteBuilderSafetyTests(unittest.TestCase):
 def make(self,paths):
  data={'project':'andaz-vibe-stay','brand_prompt':'editorial Goa stay',
        'css_task':'Brand new design-system CSS, correct responsiveness, accessible contrast, responsive editorial grid, keyboard focus and original palette',
        'full_brief':'AND AZ canonical stay with full five page plan, approved real photos and contact facts. ' *3,
        'pages':[{'file':path,'task':'Build a substantial editorial landing page using verified brand facts only.'} for path in paths]}
  folder=tempfile.TemporaryDirectory();p=Path(folder.name)/'plan.json'
  p.write_text(json.dumps(data));return folder,p
 def test_variable_length_routes(self):
  for n in (1,5,12,32,64):
   t,p=self.make(['route'+str(i)+'.html' for i in range(n)])
   with t:self.assertEqual(len(plan(p)['pages']),n)
 def test_page_cap_fail_closed(self):
  t,p=self.make(['route'+str(i)+'.html' for i in range(65)])
  with t,self.assertRaises(ValueError):plan(p)
 def test_traversal_rejected(self):
  t,p=self.make(['../../index.html'])
  with t,self.assertRaises(ValueError):plan(p)
 def test_duplicate_rejected(self):
  t,p=self.make(['rooms.html','rooms.html'])
  with t,self.assertRaises(ValueError):plan(p)
 def test_inner_page_original_photo_not_forced(self):
  base=Path.home()/'.local/share/dev-design-rag-v1/certification/andaz-v9-fresh-asset-baseline-20261112'
  self.assertTrue((base/'assets/site.js').is_file())
  h='<html lang="en"><head><title>Andaz Vibe Stay</title></head><body><main><h1>Andaz Vibe Stay Rooms</h1><img src="assets/andaz-official-cropped.webp" alt="official gold Andaz logo"/><nav>'+''.join(f'<a href="{x}">{x}</a>' for x in ['rooms.html','explore.html','experiences.html','contact.html'])+'</nav><a href="https://wa.me/918999541081">Enquire</a><script src="assets/site.js" defer></script></main></body></html>'
  self.assertEqual(validate_html(h,'andaz-vibe-stay',base,page='rooms.html')['status'],'PASS')
  with self.assertRaisesRegex(ValueError,'OFFICIAL_LOGO_AND_INTERIOR_REQUIRED'):
   validate_html(h,'andaz-vibe-stay',base,page='index.html')
 def test_inline_script_rejected(self):
  base=Path.home()/'.local/share/dev-design-rag-v1/certification/andaz-v9-fresh-asset-baseline-20261112'
  h='<html lang="en"><body><main><h1>Andaz Vibe Stay</h1><img src="assets/andaz-official-cropped.webp" alt="logo">'+''.join('<a href="'+x+'">Link</a>' for x in ['rooms.html','explore.html','experiences.html','contact.html'])+'<a href="https://wa.me/918999541081">Book</a><script>evil()</script></main></body></html>'
  with self.assertRaisesRegex(ValueError,'UNREVIEWED_SCRIPT'):
   validate_html(h,'andaz-vibe-stay',base,page='rooms.html')
if __name__=='__main__': unittest.main()
