import tempfile,unittest
from pathlib import Path
from director import CreativeBlocked
from memory import FeedbackStore
class FeedbackTests(unittest.TestCase):
 def test_authority_and_brand_isolation(self):
  with tempfile.TemporaryDirectory() as p:
   db=FeedbackStore(Path(p)/"feedback.sqlite3")
   sha="a"*64
   with self.assertRaises(CreativeBlocked):db.add("owner1","moksha",sha,"dialogue","accepted","Do not attenuate original spoken words")
   db.add("owner1","moksha",sha,"dialogue","accepted","Keep dialogue audible above music",owner_approved=True)
   self.assertIn("dialogue",db.context("owner1","moksha"))
   self.assertEqual(db.context("owner1","andaz"),"")
   self.assertEqual(db.context("owner2","moksha"),"")
   with self.assertRaises(CreativeBlocked):db.context("../owner","moksha")
 def test_no_raw_media_or_pii_policy(self):
  with tempfile.TemporaryDirectory() as p:
   db=FeedbackStore(Path(p)/"feedback.sqlite3")
   with self.assertRaises(CreativeBlocked):
    db.add("t1","brand","a"*64,"story_arc","accepted","short",owner_approved=True)
if __name__=="__main__":unittest.main()
