"""Static security regression checks for Linux SRT canary scripts (no host execution)."""
import pathlib
import re
import subprocess
import unittest

BASE = pathlib.Path(__file__).resolve().parents[1]


class SeccompCanaryPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installer = (BASE / "install-srt-and-canary.sh").read_text()
        cls.retest = (BASE / "retest-srt-helper-visibility.sh").read_text()

    def test_bash_parsing(self):
        for path in ["install-srt-and-canary.sh", "retest-srt-helper-visibility.sh"]:
            with self.subTest(path=path):
                subprocess.run(["bash", "-n", str(BASE / path)], check=True)

    def test_install_is_pinned_and_user_scoped(self):
        self.assertIn('SRT_VERSION="0.0.79"', self.installer)
        self.assertIn('npm install --prefix', self.installer)
        self.assertIn('"$HELPER_DIR/apply-seccomp"', self.installer)

    def test_helper_read_only_carveout_both_scripts(self):
        self.assertIn("'allowRead': [sys.argv[2], sys.argv[4]]", self.installer)
        self.assertIn("'denyWrite': [sys.argv[3], sys.argv[4]]", self.installer)
        self.assertIn('"allowRead": [sys.argv[2], sys.argv[4]]', self.retest)
        self.assertIn('"denyWrite": [sys.argv[3], sys.argv[4]]', self.retest)

    def test_neither_disables_seccomp_or_home_guard(self):
        for script in (self.installer, self.retest):
            self.assertIn('/home', script)
            self.assertIn('enableWeakerNestedSandbox', script)
            self.assertNotIn('allowAllUnixSockets', script)
            self.assertNotIn('sudo sysctl', script)
            self.assertNotIn('apparmor_restrict_unprivileged_userns=0', script)

    def test_write_canary_checks_host_not_tmpfs_return_code(self):
        # Linux SRT may accept writes in a disposable tmpfs overlay mounted
        # over denyRead; that does not mean the actual host path changed.
        self.assertIn("if [ -e \"$FAKE_PRIVATE/forbidden.txt\" ]", self.retest)
        self.assertIn("CANARY_FAKE_SECRET", self.retest)
        self.assertIn('READABLE_ONLY="$ROOT/readable-only"', self.retest)
        self.assertIn('write outside allowWrite', self.retest)
        self.assertIn("if [ -e \"$PRIVATE_DIR/unexpected.txt\" ]", self.installer)
        self.assertIn("FAKE_SECRET_DO_NOT_DISCLOSE", self.installer)
        self.assertIn('READABLE_ONLY="$TMP_ROOT/readable-only"', self.installer)
        self.assertIn('write outside explicit allowWrite', self.installer)
        self.assertNotIn('FAIL: fake private path was writable', self.retest)

    def test_retest_does_not_reinstall_or_change_runners(self):
        self.assertNotRegex(self.retest, r'(?m)^\s*(sudo|npm install|systemctl|gh auth)\b')
        self.assertIn('CROSS_PROJECT_RUNNERS: NOT_ENROLLED', self.retest)
        self.assertIn('FAKE_PRIVATE', self.retest)
        self.assertIn('escape-link', self.retest)


if __name__ == "__main__":
    unittest.main()
