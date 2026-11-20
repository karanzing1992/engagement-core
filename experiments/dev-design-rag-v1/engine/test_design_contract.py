"""Source-grounded V8 engineering regression; no external inference or deployment."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import design_contract as dc
import qa_repair

ROOT=Path.home()/'.local/share/dev-design-rag-v1'
ORIGINAL=ROOT/'certification/andaz-v8-minimal-autonomous-20261111'
REVISED=ROOT/'certification/andaz-v8-minimal-autonomous-iter4-20261111'
VALID='''<!doctype html><html lang="en"><head><title>Andaz Vibe Stay</title></head>
<body><header><img src="assets/andaz-official-cropped.webp" alt="Andaz official logo" />
<nav><a href="rooms.html">Rooms</a><a href="experiences.html">Experiences</a>
<a href="explore.html">Explore</a><a href="contact.html">Contact</a></nav></header>
<main><h1>Andaz Vibe Stay – Arambol</h1><p>An easygoing hostel in Goa.</p>
<img src="media/andaz_room_01_wide.webp" alt="Actual Andaz interior" />
<a href="https://wa.me/918999541081">Enquire on WhatsApp</a></main></body></html>'''
class DesignContractTests(unittest.TestCase):
 def test_brand_policy_pinned(self):
  p=dc.policy_for('andaz-vibe-stay')
  self.assertEqual(p['official_whatsapp'],'https://wa.me/918999541081')
 def test_real_8400_character_packet_packed_with_phone(self):
  packet=(ORIGINAL/'evidence/rag-packet.txt').read_text()
  result=dc.writer_context(packet,'andaz-vibe-stay')
  self.assertLessEqual(len(result),4600)
  self.assertIn('https://wa.me/918999541081',result[:1500])
  self.assertIn('Andaz Vibe Stay',result)
  self.assertIn('PROJECT SOURCE',result)
  self.assertIn('BRAND SOURCE',result)
 def test_cross_project_packet_denied(self):
  with self.assertRaisesRegex(ValueError,'RAG_PROJECT_SCOPE_MISMATCH'):
   dc.writer_context((ORIGINAL/'evidence/rag-packet.txt').read_text(),'moksha-wellness')
 def test_valid_owner_facts(self):
  self.assertEqual(dc.validate_html(VALID,'andaz-vibe-stay',ORIGINAL/'site')['status'],'PASS')
 def test_original_fake_whatsapp_rejected(self):
  with self.assertRaises(ValueError):
   dc.validate_html((ORIGINAL/'site/andaz-v8.html').read_text(),'andaz-vibe-stay',ORIGINAL/'site')
 def test_wrong_number(self):
  with self.assertRaisesRegex(ValueError,'UNAPPROVED_WHATSAPP_CONTACT'):
   dc.validate_html(VALID.replace('918999541081','1234567890'),'andaz-vibe-stay')
 def test_missing_navigation(self):
  with self.assertRaisesRegex(ValueError,'REQUIRED_NAV_MISSING'):
   dc.validate_html(VALID.replace('explore.html','fake.html'),'andaz-vibe-stay')
 def test_fabricated_suite(self):
  with self.assertRaisesRegex(ValueError,'UNSUPPORTED_PROPERTY_CLAIM'):
   dc.validate_html(VALID.replace('easygoing hostel','king-size ensuite room and easygoing hostel'),'andaz-vibe-stay')
 def test_fabricated_photo_alt(self):
  with self.assertRaisesRegex(ValueError,'INTERIOR_PHOTO_MISLABELLED'):
   dc.validate_html(VALID.replace('Actual Andaz interior','sea view private AC room'),'andaz-vibe-stay')
 def test_logo_removed(self):
  with self.assertRaisesRegex(ValueError,'OFFICIAL_LOGO_AND_INTERIOR_REQUIRED'):
   dc.validate_html(VALID.replace('andaz-official-cropped.webp','fabricated.svg'),'andaz-vibe-stay')
 def test_script_not_reviewed(self):
  with self.assertRaisesRegex(ValueError,'UNREVIEWED_SCRIPT'):
   dc.validate_html(VALID.replace('</main>','<script>alert(1)</script></main>'),'andaz-vibe-stay')
 def test_remote_link_denied(self):
  with self.assertRaisesRegex(ValueError,'UNAPPROVED_EXTERNAL_LINK'):
   dc.validate_html(VALID.replace('</main>','<a href="https://example.com/tracker">Track</a></main>'),'andaz-vibe-stay')
 def test_unverified_image_denied(self):
  with self.assertRaisesRegex(ValueError,'UNVERIFIED_IMAGE_ASSET'):
   dc.validate_html(VALID.replace('Actual Andaz interior"','Actual Andaz interior"'), 'andaz-vibe-stay', Path('/tmp/does-not-exist'))
 def test_actual_failed_browser_receipt_is_genuine(self):
  data=qa_repair.validated_failure(ORIGINAL,'andaz-v8.html')
  self.assertFalse(data['pass'])
  self.assertEqual({row['width'] for row in data['rows']},{320,390,768,1440})
 def test_actual_revision_defects_reduced(self):
  data=qa_repair.validated_failure(REVISED,'andaz-v8.html')
  self.assertEqual(sum(z['nodes'] for row in data['rows'] for z in row['axe']),4)
 def test_repair_requires_one_or_two(self):
  with self.assertRaisesRegex(ValueError,'REPAIR_BUDGET_LIMIT'):
   qa_repair.run(ORIGINAL,'andaz-v8.html','minimal',3,lambda *_:None)
 def test_revision_task_bounded_and_grounded(self):
  prompt=qa_repair.revision_task(ORIGINAL,'A minimal Goa hostel website')
  self.assertLessEqual(len(prompt),650)
  self.assertIn('918999541081',prompt)
 def test_unknown_brand_generic_only(self):
  self.assertEqual(dc.policy_for('another-project'),None)
  self.assertEqual(dc.validate_html('<html lang="en"><main><h1>Test</h1><p>'+'text'*80+'</p></main></html>','another-project')['policy'],'generic-only')
if __name__=='__main__':unittest.main(verbosity=2)
