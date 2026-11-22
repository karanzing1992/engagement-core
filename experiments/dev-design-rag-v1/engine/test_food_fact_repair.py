import unittest
from food_fact_repair import corrected,UNVERIFIED,REPLACEMENT
class FoodFactTests(unittest.TestCase):
 def test_owner_fact_fix(self):
  x='<a href="https://wa.me/918999541081">Order</a><p>₹180 ₹220 '+UNVERIFIED+'</p>'
  y=corrected(x)
  self.assertNotIn(UNVERIFIED,y)
  self.assertIn(REPLACEMENT,y)
  self.assertIn('₹180 ₹220',y)
 def test_multiple_claims_denied(self):
  with self.assertRaisesRegex(ValueError,'EXPECTED_SINGLE_UNVERIFIED_CLAIM'):
   corrected('₹180 ₹220 https://wa.me/918999541081 '+UNVERIFIED*2)
 def test_owner_facts_required(self):
  with self.assertRaisesRegex(ValueError,'OWNER_PRICE_FACTS_MISSING'):
   corrected('https://wa.me/918999541081 '+UNVERIFIED)
 def test_absent_claim_denied(self):
  with self.assertRaisesRegex(ValueError,'EXPECTED_SINGLE_UNVERIFIED_CLAIM'):
   corrected('₹180 ₹220 https://wa.me/918999541081')
if __name__=='__main__':unittest.main()
