"""Synthetic negative cases for deterministic WCAG fixes; no bypass of browser QA."""
import hashlib,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from contrast_repair import candidate,ratio,safe_background
class ContrastTests(unittest.TestCase):
 def test_measured_and_solved_contrast(self):
  self.assertAlmostEqual(ratio('#ffffff','#3b8797'),4.119,places=2)
  self.assertGreaterEqual(ratio('#ffffff',safe_background('#ffffff','#3b8797')),4.75)
 def test_keep_approved_hue_small_shift(self):
  self.assertEqual(safe_background('#ffffff','#3b8797'),'#367c8b')
 def test_reject_invalid_hex(self):
  with self.assertRaisesRegex(ValueError,'INVALID_AXE_COLOR'):
   safe_background('#ff','blue')
 def test_reject_already_accessible(self):
  with self.assertRaisesRegex(ValueError,'NO_CONTRAST_CHANGE_REQUIRED'):
   safe_background('#ffffff','#111111')
 def rows(self,violations):
  return {'missing_links':[],'rows':[{'width':n,'page':'demo.html','status':200,
    'errors':[],'dom':{'brokenImages':[]},'axe':violations} for n in (320,390,768,1440)]}
 def test_targets_across_four_widths_are_exact(self):
  violation={'id':'color-contrast','nodes':1,'targets':[{'selector':'.cta',
    'failure_summary':'foreground color: #ffffff, background color: #3b8797'}]}
  with patch('contrast_repair.validated_failure',return_value=self.rows([violation])):
   with patch('contrast_repair.sha',return_value='9'*64):
    self.assertEqual(candidate(Path('/tmp'), 'demo.html')[0],('.cta','#ffffff','#3b8797'))
 def test_refuse_noncontrast_defect(self):
  violation={'id':'aria-valid-attr','nodes':1,'targets':[{'selector':'.cta','failure_summary':'bad'}]}
  with patch('contrast_repair.validated_failure',return_value=self.rows([violation])):
   with self.assertRaisesRegex(ValueError,'NON_CONTRAST_AXE_FAILURE'):
    candidate(Path('/tmp'),'demo.html')
 def test_refuse_selector_injection(self):
  violation={'id':'color-contrast','nodes':1,'targets':[{'selector':'.cta};body{display:none}',
    'failure_summary':'foreground color: #ffffff, background color: #3b8797'}]}
  with patch('contrast_repair.validated_failure',return_value=self.rows([violation])):
   with self.assertRaisesRegex(ValueError,'UNSAFE_CONTRAST_SELECTOR'):
    candidate(Path('/tmp'),'demo.html')
 def test_refuse_disagreeing_color_by_viewport(self):
  v={'id':'color-contrast','nodes':1,'targets':[{'selector':'.cta',
    'failure_summary':'foreground color: #ffffff, background color: #3b8797'}]}
  rows=self.rows([v])
  rows['rows'][3]['axe']=[{'id':'color-contrast','nodes':1,'targets':[{'selector':'.cta',
    'failure_summary':'foreground color: #ffffff, background color: #556677'}]}]
  with patch('contrast_repair.validated_failure',return_value=rows):
   with self.assertRaisesRegex(ValueError,'VIEWPORT_CONTRAST_VARIATION'):
    candidate(Path('/tmp'),'demo.html')
if __name__=='__main__':unittest.main(verbosity=2)
