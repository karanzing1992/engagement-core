import unittest
from factual_repair import bounded_task
class BoundedFactualRepairTests(unittest.TestCase):
 def test_only_expected_failing_pages_permitted(self):
  for p in ('index.html','rooms.html','experiences.html','food.html'):
   self.assertTrue(40<=len(bounded_task(p))<=650)
 def test_approved_explore_and_contact_untouched(self):
  for p in ('contact.html','explore.html','../../index.html','assets/v9-fresh.css'):
   with self.assertRaisesRegex(ValueError,'UNAPPROVED_REPAIR_PAGE'):bounded_task(p)
if __name__=='__main__':unittest.main()
