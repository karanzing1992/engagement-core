import unittest
from site_builder import approved_free_model_for_task
class ModelRouteTests(unittest.TestCase):
 def test_initial_original_page_model(self):
  self.assertIsNone(approved_free_model_for_task('rooms.html',0))
 def test_initial_contact_approved_20b(self):
  self.assertEqual(approved_free_model_for_task('contact.html',0),'groq-oss20')
 def test_first_recovery_20b(self):
  self.assertEqual(approved_free_model_for_task('experiences.html',1),'groq-oss20')
  self.assertEqual(approved_free_model_for_task('index.html',1),'groq-oss20')
 def test_second_recovery_experiences_120b(self):
  self.assertEqual(approved_free_model_for_task('experiences.html',2),'groq-oss120')
  self.assertEqual(approved_free_model_for_task('food.html',2),'groq-oss20')
 def test_never_force_css_model(self):
  self.assertIsNone(approved_free_model_for_task('assets/v9-fresh.css',2))
if __name__=='__main__':unittest.main()
