"""Read-only negative regressions; genuine Playwright/Lighthouse evidence is separate."""
import hashlib
import json
import pathlib
import unittest
from unittest.mock import patch

from brand_guard import prioritized_context,validate_html
from qa_repair import relative_luminance,fix_contrast
from performance_repair import improve_image_dimensions
from core import gate

BASE=pathlib.Path.home()/'.local/share/dev-design-rag-v1/certification'
ORIGINAL=BASE/'andaz-v8-minimal-autonomous-20261111'
PASSED=BASE/'andaz-v8-autorepair-e2e-20261112'

class AutonomousRepairSafety(unittest.TestCase):
 def test_brand_phone_in_writer_context(self):
  ctx=prioritized_context(ORIGINAL)
  self.assertIn('wa.me/918999541081',ctx)
  self.assertIn('andaz-official-cropped.webp',ctx)
  self.assertLessEqual(len(ctx),1800)
 def test_initial_fake_whatsapp_denied(self):
  with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ROOM_OR_CONTACT_CLAIM'):
   validate_html(ORIGINAL,'andaz-v8.html',(ORIGINAL/'site/andaz-v8.html').read_text())
 def test_real_final_page_accepted(self):
  s=(PASSED/'site/andaz-v8.html').read_text()
  self.assertTrue(validate_html(PASSED,'andaz-v8.html',s)['pass'])
 def test_missing_whatsapp_rejected(self):
  s=(PASSED/'site/andaz-v8.html').read_text().replace('wa.me/918999541081','wa.me/1234567890')
  with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ROOM_OR_CONTACT_CLAIM'):
   validate_html(PASSED,'andaz-v8.html',s)
 def test_untrusted_page_no_main_rejected(self):
  s=(PASSED/'site/andaz-v8.html').read_text().replace('<main>','<div>').replace('</main>','</div>')
  with self.assertRaisesRegex(ValueError,'SEMANTIC_HTML_INVALID'):
   validate_html(PASSED,'andaz-v8.html',s)
 def test_contrast_math(self):
  self.assertGreater(relative_luminance('ffffff'),relative_luminance('000000'))
  self.assertGreater(relative_luminance('fff9f2'),.8)
 def test_repair_replay_denied(self):
  with self.assertRaises(ValueError):
   fix_contrast(PASSED,'andaz-v8.html',1)
 def test_performance_repair_is_bounded(self):
  with self.assertRaises(ValueError):
   improve_image_dimensions(PASSED,'other.html')
 def test_artistic_release_still_blocked(self):
  g=gate(PASSED,'preview')
  self.assertEqual(g['status'],'BLOCKED')
  self.assertIn('ARTISTIC_95_NOT_APPROVED',g['missing'])
  self.assertFalse(g['production_release_allowed'])
 def test_original_workspace_not_mutated(self):
  self.assertFalse((ORIGINAL/'reports/qa-repairs').exists())

if __name__=='__main__':unittest.main()
