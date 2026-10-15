"""Offline validation for the non-destructive host SRT network/security canary."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HostCanarySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'host-network-socket-env-canary.py').read_text(encoding='utf-8')
        ast.parse(cls.source)

    def test_deny_all_network_and_unix_socket(self):
        for token in ('"allowedDomains": []','"deniedDomains": ["*"]',
                      '"allowAllUnixSockets": False','"allowLocalBinding": False',
                      '"enableWeakerNestedSandbox": False',
                      '"enableWeakerNetworkIsolation": False'):
            self.assertIn(token, self.source)

    def test_live_localhost_negative_and_positive_control(self):
        self.assertIn('host_listener.bind(("127.0.0.1", 0))', self.source)
        self.assertIn('socket.create_connection', self.source)
        self.assertIn('loopback_connected', self.source)
        self.assertIn('unix_socket_created', self.source)
        self.assertIn('with socket.create_connection', self.source)

    def test_explicit_clean_environment_for_model_child(self):
        self.assertIn('safe_env = {', self.source)
        self.assertIn('env=safe_env', self.source)
        self.assertIn('MOKSHA_FAKE_TOKEN_FOR_CANARY', self.source)
        self.assertIn('unexpected_api_key_in_child', self.source)
        self.assertNotIn('env=parent', self.source)
        self.assertNotIn('os.system', self.source)

    def test_no_external_tokens_runner_registration_or_real_data(self):
        for forbidden in ('gh auth login','systemctl enable','sudo ',
                          'ANTHROPIC_API_KEY=','SUPABASE_SERVICE_ROLE_KEY='):
            self.assertNotIn(forbidden, self.source)

if __name__ == '__main__':
    unittest.main()
