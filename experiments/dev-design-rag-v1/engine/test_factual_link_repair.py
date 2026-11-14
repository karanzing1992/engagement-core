import unittest
from factual_link_repair import corrected
class StrictLinkRepairTests(unittest.TestCase):
 def test_specific_page_fix(self):
  h='<section><h2>Andaz Table</h2><p>Home meals</p></section>'
  t=corrected(h)
  self.assertEqual(t.count('href="food.html"'),1)
  self.assertIn('Home meals',t)
 def test_missing_table_denied(self):
  with self.assertRaisesRegex(ValueError,'SINGLE_TABLE_SECTION_REQUIRED'):
   corrected('<section><h2>Rooms</h2></section>')
 def test_duplicate_tables_denied(self):
  with self.assertRaisesRegex(ValueError,'SINGLE_TABLE_SECTION_REQUIRED'):
   corrected('<section><h2>Andaz Table</h2></section>'*2)
 def test_existing_link_denied(self):
  with self.assertRaisesRegex(ValueError,'LINK_ALREADY_PRESENT'):
   corrected('<section><h2>Andaz Table</h2><a href="food.html">See</a></section>')
if __name__=='__main__':unittest.main()
