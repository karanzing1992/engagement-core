import unittest
from agent import normalize_trusted_script_defer
class TrustedScriptTest(unittest.TestCase):
 def test_one_approved_script_fixed(self):
  x='<html><script src="assets/site.js"></script></html>'
  y,changed=normalize_trusted_script_defer(x)
  self.assertTrue(changed)
  self.assertIn('src="assets/site.js" defer',y)
 def test_multiple_scripts_no_repair(self):
  x='<script src="assets/site.js"></script><script>alert(1)</script>'
  self.assertEqual(normalize_trusted_script_defer(x),(x,False))
 def test_unknown_script_never_repaired(self):
  x='<script src="https://bad.invalid/x.js"></script>'
  self.assertEqual(normalize_trusted_script_defer(x),(x,False))
 def test_script_with_extra_attribute_not_repaired(self):
  x='<script src="assets/site.js" async></script>'
  self.assertEqual(normalize_trusted_script_defer(x),(x,False))
 def test_correct_script_unchanged(self):
  x='<script src="assets/site.js" defer></script>'
  self.assertEqual(normalize_trusted_script_defer(x),(x,False))
if __name__=='__main__':unittest.main()
