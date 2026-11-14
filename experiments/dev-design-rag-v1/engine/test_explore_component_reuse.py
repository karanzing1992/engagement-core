import unittest
from explore_component_reuse import adapt
class CanonicalExploreTests(unittest.TestCase):
 def test_adapt_scoped_header_and_guides(self):
  src='<header class="site-header"><p>Old nav</p></header><a href="https://wa.me/918999541081">WhatsApp enquiry</a><main class="container" data-explore-guide><div class="grid"><p>Guide</p></div><p id="explore-empty" hidden>None</p></main>'
  out=adapt(src)
  self.assertIn('href="food.html"',out)
  self.assertIn('data-explore-guide',out)
  self.assertIn('class="main container"',out)
  self.assertNotIn('Old nav',out)
 def test_canonical_cards_wrapped_in_section(self):
  base='<header class="site-header"></header><a href="https://wa.me/918999541081">WhatsApp enquiry</a><main class="container" data-explore-guide><div class="grid"><div class="card">A</div></div><p id="explore-empty" hidden>None</p></main>'
  out=adapt(base)
  self.assertIn('<section aria-label="Explore Arambol places">',out)
  self.assertIn('</section><p id="explore-empty" hidden>',out)
 def test_missing_guide_rejected(self):
  with self.assertRaisesRegex(ValueError,'OLD_GUIDE_SCOPE_MISSING'):
   adapt('<header class="site-header"></header>')
 def test_duplicate_header_rejected(self):
  with self.assertRaisesRegex(ValueError,'UNRECOGNIZED_OLD_HEADER'):
   adapt('<header class="site-header"></header>'*2)
if __name__=='__main__':unittest.main()
