#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
TASKS = BASE / "queue" / "tasks"
RESULTS = BASE / "queue" / "results"
PYTHON = BASE / ".venv" / "bin" / "python"
AGENT = BASE / "agent.py"

POLL_SECONDS = max(10, int(os.getenv("TELEGRAM_QUEUE_POLL_SECONDS", "15")))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        cwd=REPO,
        text=True,
        capture_output=True,
        check=check,
    )


def git_sync() -> None:
    run("git", "pull", "--ff-only", "origin", "main")


def load_task(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Task must be a JSON object.")
    return data


def safe_command(task: dict) -> list[str]:
    action = str(task.get("action", "")).strip()
    if action == "status":
        return [str(PYTHON), str(AGENT), "status"]

    if action == "preview":
        limit = min(max(int(task.get("limit", 50)), 1), 100)
        return [str(PYTHON), str(AGENT), "preview", "--limit", str(limit)]

    if action == "invite":
        if task.get("confirmed") is not True:
            raise ValueError("Invite task requires confirmed=true.")
        limit = min(max(int(task.get("limit", 20)), 1), 20)
        language = str(task.get("language", "ru"))
        if language not in {"ru", "en"}:
            raise ValueError("language must be ru or en.")
        return [
            str(PYTHON), str(AGENT), "invite",
            "--limit", str(limit),
            "--language", language,
            "--send",
            "--confirm", "MOKSHA",
        ]

    raise ValueError("Unsupported action. Allowed: status, preview, invite.")


def process(path: Path) -> None:
    task_id = path.stem
    result_path = RESULTS / f"{task_id}.json"
    if result_path.exists():
        return

    started = datetime.now(timezone.utc).isoformat()
    result = {
        "task_id": task_id,
        "started_at": started,
        "ok": False,
    }

    try:
        task = load_task(path)
        command = safe_command(task)
        cp = subprocess.run(
            command,
            cwd=BASE,
            text=True,
            capture_output=True,
            timeout=900,
        )
        result.update(
            {
                "ok": cp.returncode == 0,
                "returncode": cp.returncode,
                "stdout": cp.stdout[-20000:],
                "stderr": cp.stderr[-10000:],
                "action": task.get("action"),
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    RESULTS.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    run("git", "add", str(result_path.relative_to(REPO)))
    cp = run("git", "diff", "--cached", "--quiet", check=False)
    if cp.returncode != 0:
        run("git", "commit", "-m", f"Telegram user agent result {task_id}")
        run("git", "push", "origin", "main")


def tick() -> None:
    git_sync()
    TASKS.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    for task in sorted(TASKS.glob("*.json")):
        process(task)


def main() -> None:
    if not PYTHON.exists():
        raise SystemExit("Run ./bootstrap-mac.sh first.")
    print(f"Telegram queue worker running from {REPO}; poll={POLL_SECONDS}s")
    while True:
        try:
            tick()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print(f"worker error: {type(exc).__name__}: {exc}", file=sys.stderr)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
