"""Source-only regression checks for restricted Moksha Claude Unix worker setup.

These do not create users or modify the host; live checks run only on owner PC.
"""
import pathlib
import subprocess
import unittest

BASE=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=BASE/'setup-moksha-isolated-user.sh'

class WorkerIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SCRIPT.read_text()

    def test_bash_syntax(self):
        subprocess.run(['bash','-n',str(SCRIPT)],check=True)

    def test_pilot_is_exact_repo_and_os_account(self):
        self.assertIn('ACCOUNT="claude-moksha"',self.source)
        self.assertIn('HOME_DIR="/home/claude-moksha"',self.source)
        self.assertIn('OWNER_REPO="karanzing1992/moksha_wordpress"',self.source)

    def test_no_login_privileged_shell_or_group(self):
        self.assertIn('--system --user-group --create-home',self.source)
        self.assertIn('--shell /usr/sbin/nologin',self.source)
        self.assertIn('chmod 0700 "$HOME_DIR"',self.source)
        self.assertIn('sudo docker lxd adm root wheel',self.source)

    def test_no_credential_migration_or_runner_changes(self):
        for token in ('gh auth login','gh auth switch','ssh-keygen',
                      'cp "$HOME/.claude"','cp -r ~/.config','systemctl enable',
                      'actions/runners/registration-token','claude -p',
                      'ANTHROPIC_API_KEY='):
            self.assertNotIn(token,self.source)

    def test_synthetic_two_way_boundary(self):
        self.assertIn('SYNTHETIC_OWNER_PRIVATE_CANARY',self.source)
        self.assertIn('sudo -u "$ACCOUNT" /usr/bin/cat "$MARKER"',self.source)
        self.assertIn('if [ -r "$HOME_DIR" ]',self.source)
        self.assertIn('env -i HOME="$HOME_DIR"',self.source)
        self.assertIn('ACCOUNT_BASELINE_PASS',self.source)
        self.assertIn('NOT_ENROLLED',self.source)

if __name__ == '__main__':
    unittest.main()
