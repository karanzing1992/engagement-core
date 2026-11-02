import copy
import unittest
from v5_issue_gate import GateRejected, authorize

BASE = {"repository": {"owner": {"login": "repo-owner"}},
 "issue": {"number": 42, "state": "open", "title": "[MAD-V5] synthetic certification",
 "user": {"login": "repo-owner"}, "labels": [{"name": "reel-v5-run"}],
 "body": '{"schema_version":1,"operation":"synthetic_certification","project_id":"moksha_wellness","job_type":"instagram_reel","mode":"fixture","profile":"synthetic_test"}'}}

class TestGate(unittest.TestCase):
    def test_owner_fixture(self):
        accepted = authorize(copy.deepcopy(BASE))
        self.assertEqual(accepted["status"], "ACCEPTED_SYNTHETIC_ONLY")
        self.assertFalse(accepted["publishing"])
        self.assertFalse(accepted["private_media"])

    def test_other_user_rejected(self):
        e = copy.deepcopy(BASE); e["issue"]["user"]["login"] = "attacker"
        with self.assertRaises(GateRejected): authorize(e)

    def test_unlabeled_rejected(self):
        e = copy.deepcopy(BASE); e["issue"]["labels"] = []
        with self.assertRaises(GateRejected): authorize(e)

    def test_no_private_footage_urls_or_tokens_in_issue(self):
        for key, value in [("video_url", "https://secret.example/guest.mp4"),
                           ("token", "secret"), ("source_path", "/private/a")]:
            e = copy.deepcopy(BASE)
            payload = __import__("json").loads(e["issue"]["body"])
            payload[key] = value
            e["issue"]["body"] = __import__("json").dumps(payload)
            with self.assertRaises(GateRejected): authorize(e)

    def test_wrong_mode_project_or_operation(self):
        for key, value in [("mode", "publish"), ("project_id", "unknown_project"),
                           ("operation", "private_upload"), ("profile", "arbitrary")]:
            e = copy.deepcopy(BASE)
            payload = __import__("json").loads(e["issue"]["body"])
            payload[key] = value
            e["issue"]["body"] = __import__("json").dumps(payload)
            with self.assertRaises((GateRejected, ValueError)): authorize(e)

    def test_duplicate_open_edit_is_same_safe_receipt(self):
        first = authorize(copy.deepcopy(BASE))
        second = authorize(copy.deepcopy(BASE))
        self.assertEqual(first, second)

if __name__ == "__main__":
    unittest.main()
