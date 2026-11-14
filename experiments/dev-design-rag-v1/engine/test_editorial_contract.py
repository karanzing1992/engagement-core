"""Portable synthetic fixtures; never depend on private Dell screenshots or actual site assets."""
import unittest
from editorial_contract import check_editorial

def fixture(sections,words=180,extra='',photo=False):
 blocks=''.join('<section><h2>Arambol Stay</h2><p>'+('Fresh Indian home style food, verified local rooms, contact and community. '*((words//11)+1))+'</p></section>' for _ in range(sections))
 return '<html><main>'+blocks+('<img src="media/andaz_room_01_wide.webp" alt="Real room interior">' if photo else '')+extra+'</main></html>'

class EditorialTests(unittest.TestCase):
 def test_rejects_sparse_home_and_placeholder(self):
  h=fixture(1,words=35,extra='Additional editorial content could go here',photo=True)
  r=check_editorial(h,'index.html','andaz-vibe-stay')
  self.assertEqual(r['status'],'BLOCKED')
  self.assertIn('UNFINISHED_PLACEHOLDER',r['issues'])
  self.assertIn('INSUFFICIENT_EDITORIAL_SECTIONS',r['issues'])
 def test_rejects_room_photo_on_food_and_experiences(self):
  for page in ('food.html','experiences.html'):
   with self.subTest(page=page):
    r=check_editorial(fixture(4,photo=True)+' ₹180 ₹220',page,'andaz-vibe-stay')
    self.assertIn('UNSUPPORTED_CONTEXTUAL_ROOM_PHOTOGRAPH',r['issues'])
 def test_accepts_substantial_home_without_score(self):
  r=check_editorial(fixture(3,photo=True,extra='<section><h2>Andaz Table</h2><a href="food.html">Meals</a></section>'),'index.html','andaz-vibe-stay')
  self.assertEqual(r['status'],'PASS',r)
  self.assertIsNone(r['artistic_score'])
 def test_rejects_invented_private_balcony_and_suite(self):
  r=check_editorial(fixture(4,extra='Room suites with private balcony',photo=True),'index.html','andaz-vibe-stay')
  self.assertIn('UNVERIFIED_HOSPITALITY_OR_MENU_CLAIM',r['issues'])
 def test_unsupported_amenities_are_blocked(self):
  for claim in ('free Wi-Fi','flat-screen TV','comfortable workspace','locally sourced ingredients','staff provide guided tours','common lounge','nightly gatherings'):
   with self.subTest(claim=claim):
    d=check_editorial(fixture(3,extra=claim,photo=True),'index.html','andaz-vibe-stay')
    self.assertIn('UNVERIFIED_HOSPITALITY_OR_MENU_CLAIM',d['issues'])
 def test_food_section_cannot_misuse_room_photo_or_wrong_route(self):
  text=fixture(3,photo=True,extra='<section><h2>The Andaz Table</h2><img src="media/andaz_room_01_wide.webp"><a href="experiences.html">Eat</a></section>')
  d=check_editorial(text,'index.html','andaz-vibe-stay')
  self.assertIn('ROOM_PHOTO_MISUSED_AS_FOOD',d['issues'])
  self.assertIn('FOOD_TEASER_WRONG_DESTINATION',d['issues'])
 def test_two_bed_shared_dorm_not_private(self):
  text=fixture(3,extra='<section>2-Bed Non-AC Dorm in a private setting</section>')
  d=check_editorial(text,'rooms.html','andaz-vibe-stay')
  self.assertIn('TWO_BED_DORM_MISREPRESENTED_AS_PRIVATE',d['issues'])
 def test_food_must_preserve_owner_pricing(self):
  r=check_editorial(fixture(3), 'food.html','andaz-vibe-stay')
  self.assertIn('OWNER_PRICE_FACTS_MISSING',r['issues'])
 def test_search_placeholder_attribute_not_unfinished_copy(self):
  r=check_editorial(fixture(3,extra='<input placeholder="Search places" />'),'explore.html','andaz-vibe-stay')
  self.assertNotIn('UNFINISHED_PLACEHOLDER',r['issues'])
 def test_other_tenant_not_styled_as_andaz(self):
  self.assertEqual(check_editorial('','index.html','other-approved-brand')['status'],'PASS')
if __name__=='__main__':unittest.main()
