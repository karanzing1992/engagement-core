import unittest
from agent import page_scoped_verified_context
class PageScopedEvidenceTests(unittest.TestCase):
 def test_non_photo_pages_do_not_receive_room_photo_path(self):
  t='verified room media/andaz_room_01_wide.webp'
  for p in ('experiences.html','food.html','explore.html','contact.html'):
   x=page_scoped_verified_context(t,p,'andaz-vibe-stay')
   self.assertNotIn('media/andaz_room_01_wide.webp',x)
 def test_home_rooms_original_photo_authorized(self):
  t='media/andaz_room_01_wide.webp'
  for p in ('index.html','rooms.html'):
   self.assertEqual(page_scoped_verified_context(t,p,'andaz-vibe-stay'),t)
 def test_other_brand_isolated(self):
  t='media/andaz_room_01_wide.webp'
  self.assertEqual(page_scoped_verified_context(t,'food.html','another-brand'),t)
if __name__=='__main__':unittest.main()
