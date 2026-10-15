import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from router import (Rejected, child_environment, sandbox_config, safe_relative_path,
                    validate_event, validate_policy, verify_paths)

POLICY={'repository':'KaranZi/shaadi-aunty-dodge', 'owner_id':11679700,
        'prefix':'[CLAUDE-DEV]', 'enabled':True, 'model':'opus',
        'allowed_paths':['godot/', 'docs/REUSE_LOG.md']}
EVENT={'action':'opened','repository':{'full_name':'KaranZi/shaadi-aunty-dodge','private':True},
       'issue':{'number':1,'title':'[CLAUDE-DEV] test', 'body':'safe valid task',
                'user':{'id':11679700,'login':'KaranZi'}}}

class RouterTests(unittest.TestCase):
    def ok(self, e=EVENT, p=POLICY):
        return validate_event(e, p, 'KaranZi','KaranZi/shaadi-aunty-dodge')
    def reject(self, e=EVENT, p=POLICY):
        with self.assertRaises(Rejected): self.ok(e, p)
    def test_valid(self): self.assertEqual(self.ok()['issue_number'],1)
    def test_disabled(self): self.reject(p={**POLICY,'enabled':False})
    def test_unauthorized(self):
        self.reject(e={**EVENT, 'issue':{**EVENT['issue'],'user':{'id':100,'login':'attacker'}}})
    def test_wrong_actor(self):
        with self.assertRaises(Rejected): validate_event(EVENT,POLICY,'attacker','KaranZi/shaadi-aunty-dodge')
    def test_wrong_repo(self): self.reject(e={**EVENT,'repository':{'full_name':'karanzing1992/engagement-core','private':True}})
    def test_not_private(self): self.reject(e={**EVENT,'repository':{**EVENT['repository'],'private':False}})
    def test_wrong_prefix(self): self.reject(e={**EVENT,'issue':{**EVENT['issue'],'title':'[SHAADI-CODE] oops'}})
    def test_not_opened(self): self.reject(e={**EVENT,'action':'edited'})
    def test_length(self): self.reject(e={**EVENT,'issue':{**EVENT['issue'],'body':'x'*6000}})
    def test_paid_model(self):
        with self.assertRaises(Rejected):validate_policy({**POLICY,'model':'best'})
    def test_path_traversal(self):
        for p in ('../etc/passwd','/etc/passwd','godot/../../oops','~/.ssh/id','godot/a\\b'):
            with self.subTest(p=p),self.assertRaises(Rejected):safe_relative_path(p)
    def test_path_enforcement(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'godot').mkdir();(root/'docs').mkdir()
            verify_paths(root,['godot/scene.gd','docs/REUSE_LOG.md'],POLICY['allowed_paths'])
            with self.assertRaises(Rejected): verify_paths(root,['scripts/other.sh'],POLICY['allowed_paths'])
            (root/'godot'/'escape').symlink_to('/etc/passwd')
            with self.assertRaises(Rejected): verify_paths(root,['godot/escape'],POLICY['allowed_paths'])
    def test_claude_child_environment_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            env=child_environment(root, {'PATH':'/usr/bin', 'LANG':'C.UTF-8',
                                         'GH_TOKEN':'synthetic-gh', 'ANTHROPIC_API_KEY':'synthetic-api',
                                         'UNKNOWN_PRIVATE_TOKEN':'synthetic-unknown',
                                         'GITHUB_WORKSPACE':'/other-project',
                                         'LD_PRELOAD':'/other-project/lib.so'})
            self.assertEqual(env['HOME'],str(root))
            self.assertEqual(env['PATH'],'/usr/bin')
            self.assertEqual(env['CLAUDE_CODE_SUBAGENT_MODEL'],'inherit')
            for name in ('GH_TOKEN','ANTHROPIC_API_KEY','UNKNOWN_PRIVATE_TOKEN',
                         'GITHUB_WORKSPACE','LD_PRELOAD'):
                self.assertNotIn(name,env)

    def test_sandbox_read_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/'repo').mkdir();(root/'auth').mkdir();(root/'seccomp').mkdir()
            (root/'seccomp'/'apply-seccomp').write_text('fake test helper only')
            c=sandbox_config(root/'repo',root/'auth',root/'seccomp')
            self.assertIn(str(root/'seccomp'), c['filesystem']['allowRead'])
            self.assertIn(str(root/'seccomp'), c['filesystem']['denyWrite'])
            self.assertIn('/home',c['filesystem']['denyRead'])
            self.assertNotIn('github.com',c['network']['allowedDomains'])
            self.assertEqual(c['network']['allowUnixSockets'],[])

if __name__=='__main__': unittest.main()
