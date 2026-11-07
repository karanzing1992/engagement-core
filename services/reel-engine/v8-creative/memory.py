"""Owner-confirmed, brand-scoped V8 feedback index. Optional local dev storage only.

No original footage, audio, credentials, emails, user identities, or private media blobs.
Production feedback custody must use the existing authenticated project service.
"""
from __future__ import annotations
import os,re,sqlite3
from pathlib import Path
from director import CreativeBlocked

ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
TAGS=frozenset(("dialogue","audio_mix","rhythm","story_arc","transitions",
                 "typography","framing","grade","authenticity","other"))
VERDICTS=frozenset(("accepted","rejected","needs_revision"))

def identity(*parts):
    if any(not isinstance(s,str) or not ID.fullmatch(s) for s in parts):
        raise CreativeBlocked("V8_FEEDBACK_SCOPE_INVALID")

class FeedbackStore:
    def __init__(self,path):
        self.path=Path(path).resolve()
        if self.path.suffix!=".sqlite3" or not self.path.parent.is_dir():
            raise CreativeBlocked("V8_FEEDBACK_PATH_INVALID")
        if self.path.is_symlink():raise CreativeBlocked("V8_FEEDBACK_PATH_UNSAFE")
        if not self.path.exists():
            f=os.open(str(self.path),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(f)
        if self.path.stat().st_mode & 0o077:
            raise CreativeBlocked("V8_FEEDBACK_PERMISSIONS")
        with self.db() as d:
            d.execute("CREATE TABLE IF NOT EXISTS feedback(tenant TEXT,brand TEXT,receipt_sha TEXT,tag TEXT,verdict TEXT,lesson TEXT,approved INTEGER CHECK(approved=1),PRIMARY KEY(tenant,brand,receipt_sha,tag))")
    def db(self):return sqlite3.connect(self.path,timeout=5)
    def add(self,tenant,brand,receipt_sha,tag,verdict,lesson,*,owner_approved=False):
        identity(tenant,brand)
        if (not isinstance(receipt_sha,str) or not re.fullmatch(r"[a-f0-9]{64}",receipt_sha)
            or tag not in TAGS or verdict not in VERDICTS or owner_approved is not True
            or not isinstance(lesson,str) or not 15<=len(lesson)<=500
            or any(ord(ch)<32 for ch in lesson)):
            raise CreativeBlocked("V8_FEEDBACK_OWNER_APPROVAL_REQUIRED")
        with self.db() as d:
            d.execute("INSERT INTO feedback VALUES(?,?,?,?,?,?,1) ON CONFLICT(tenant,brand,receipt_sha,tag) DO UPDATE SET verdict=excluded.verdict, lesson=excluded.lesson",
                      (tenant,brand,receipt_sha,tag,verdict,lesson))
    def context(self,tenant,brand,limit=6):
        identity(tenant,brand)
        if not isinstance(limit,int) or not 1<=limit<=12:raise CreativeBlocked("V8_FEEDBACK_LIMIT_INVALID")
        with self.db() as d:
            rows=d.execute("SELECT tag,verdict,lesson FROM feedback WHERE tenant=? AND brand=? AND approved=1 ORDER BY rowid DESC LIMIT ?",
                           (tenant,brand,limit)).fetchall()
        return "\n".join(f"[{tag}/{verdict}] {lesson}" for tag,verdict,lesson in rows)
