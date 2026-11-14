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
  r=check_editorial(fixture(3,photo=True),'index.html','andaz-vibe-stay')
  self.assertEqual(r['status'],'PASS',r)
  self.assertIsNone(r['artistic_score'])
 def test_rejects_invented_private_balcony_and_suite(self):
  r=check_editorial(fixture(4,extra='Room suites with private balcony',photo=True),'index.html','andaz-vibe-stay')
  self.assertIn('UNVERIFIED_HOSPITALITY_OR_MENU_CLAIM',r['issues'])
 def test_food_must_preserve_owner_pricing(self):
  r=check_editorial(fixture(3), 'food.html','andaz-vibe-stay')
  self.assertIn('OWNER_PRICE_FACTS_MISSING',r['issues'])
 def test_other_tenant_not_styled_as_andaz(self):
  self.assertEqual(check_editorial('','index.html','other-approved-brand')['status'],'PASS')
if __name__=='__main__':unittest.main()
