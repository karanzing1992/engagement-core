import unittest
from browser_r2_repair import transform,MARKER,BAD_LINK
class R2BrowserRepair(unittest.TestCase):
 def test_allowed_source_edit(self):
  css='--color-gold: #b8860b;.nav-list{}.cta{}'
  nxt,h=transform(css,BAD_LINK+'<main>real</main>')
  self.assertIn(MARKER,nxt)
  self.assertNotIn('about.html',h)
  self.assertIn('real',h)
  self.assertIn('max-width:10rem',nxt)
 def test_multiple_links_denied(self):
  with self.assertRaisesRegex(ValueError,'UNEXPECTED_BAD_LINK_SHAPE'):
   transform('--color-gold: #b8860b;.nav-list{}.cta{}',BAD_LINK*2)
 def test_patch_replay_denied(self):
  with self.assertRaisesRegex(ValueError,'CHROME_PATCH_REPLAY'):
   transform('--color-gold: #b8860b;.nav-list{}.cta{}'+MARKER,BAD_LINK)
if __name__=='__main__':unittest.main()
