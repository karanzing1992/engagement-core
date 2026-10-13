"""Private CPU-only local Reel draft runner. No cloud or publishing dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

LIMIT_BYTES = 48 * 1024 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.mp4\Z")
REQUEST_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.json\Z")
JOB_ID = re.compile(r"[a-z0-9][a-z0-9-]{7,49}\Z")


def _member(directory: Path, name: str, pattern: re.Pattern[str]) -> Path:
    if not isinstance(name, str) or not pattern.fullmatch(name) or Path(name).name != name:
        raise ValueError("Invalid basename in local job manifest")
    candidate = directory / name
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("Missing file or prohibited symlink")
    if candidate.resolve(strict=True).parent != directory.resolve(strict=True):
        raise ValueError("File outside dedicated workspace")
    return candidate


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _workspace(root: Path) -> dict[str, Path]:
    if root.is_symlink():
        raise ValueError("Workspace may not be a symlink")
    root = root.resolve(strict=True)
    result = {}
    for name in ("approved", "requests", "drafts", "work"):
        path = root / name
        if path.is_symlink() or not path.is_dir():
            raise ValueError(f"Missing or unsafe workspace directory: {name}")
        if path.resolve(strict=True).parent != root:
            raise ValueError("Workspace directory escape")
        result[name] = path
    return result


def setup(root: Path) -> None:
    if root.exists() or root.is_symlink():
        raise ValueError("Refusing to initialize over an existing directory")
    root.mkdir(parents=True, mode=0o700)
    for name in ("approved", "requests", "drafts", "work"):
        (root / name).mkdir(mode=0o700)
    print("Initialized separate private Reel workspace:", root)


def validate_request(spec: dict, folders: dict[str, Path]) -> tuple[str, list[Path], dict]:
    from geo_policy import validate_render_config

    if not isinstance(spec, dict) or spec.get("schema_version") != 1:
        raise ValueError("Unsupported local request schema")
    identifier = spec.get("job_id")
    if not isinstance(identifier, str) or not JOB_ID.fullmatch(identifier):
        raise ValueError("Invalid job_id")
    if spec.get("brand") != "generic":
        raise ValueError("Only unbranded drafts permitted until logo authorization")
    config = spec.get("config")
    if not isinstance(config, dict) or config.get("brand") != "generic":
        raise ValueError("Config brand mismatch")
    if any(k in config for k in ("geography_override", "regional_override")):
        raise ValueError("Geography override blocked")
    if (int(config.get("width", 720)), int(config.get("height", 1280)),
            int(config.get("fps", 25)), float(config.get("target_seconds", 30))) != (720, 1280, 25, 30.0):
        raise ValueError("Pilot expects 30s 720x1280 25fps")
    assets = spec.get("source_files")
    if not isinstance(assets, list) or not 1 <= len(assets) <= 4:
        raise ValueError("One to four approved source files required")
    if len(config.get("source_provenance", [])) != len(assets):
        raise ValueError("A provenance record is required per source")
    validate_render_config(config)

    total = 0
    seen = set()
    paths = []
    for item in assets:
        if not isinstance(item, dict):
            raise ValueError("Invalid source entry")
        path = _member(folders["approved"], item.get("file"), FILENAME)
        if path.name in seen:
            raise ValueError("Duplicate input file")
        seen.add(path.name)
        expected = item.get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError("Source SHA-256 required")
        total += path.stat().st_size
        if not 1024 <= path.stat().st_size or total > LIMIT_BYTES:
            raise ValueError("Source file size outside pilot bounds")
        if _hash(path) != expected:
            raise ValueError("Source SHA-256 mismatch")
        paths.append(path)
    if (folders["drafts"] / (identifier + ".mp4")).exists():
        raise FileExistsError("Refusing to overwrite existing draft")
    if (folders["drafts"] / (identifier + ".json")).exists():
        raise FileExistsError("Refusing to overwrite existing report")
    return identifier, paths, config


def run(root: Path, request_name: str, *, check_only: bool = False) -> dict:
    folders = _workspace(root)
    request_path = _member(folders["requests"], request_name, REQUEST_NAME)
    if request_path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Manifest too large")
    spec = json.loads(request_path.read_text(encoding="utf-8"))
    identifier, inputs, config = validate_request(spec, folders)
    if check_only:
        return {"checked": True, "job_id": identifier, "private": True, "published": False}
    from multi_renderer import render_multiple
    working = folders["work"] / identifier
    working.mkdir(mode=0o700, exist_ok=False)
    spool = working / "video.mp4"
    rendered = render_multiple(inputs, spool, config, working / "ffmpeg")
    target = folders["drafts"] / (identifier + ".mp4")
    report = folders["drafts"] / (identifier + ".json")
    try:
        with spool.open("rb") as reader, target.open("xb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(target, 0o600)
        with report.open("x", encoding="utf-8") as writer:
            json.dump({
                "job_id": identifier,
                "private": True,
                "published": False,
                "duration": rendered["duration"],
                "width": rendered["width"],
                "height": rendered["height"],
                "sha256": _hash(target),
            }, writer, indent=2)
        os.chmod(report, 0o600)
    except BaseException:
        target.unlink(missing_ok=True)
        report.unlink(missing_ok=True)
        raise
    return {"checked": True, "rendered": True, "job_id": identifier,
            "private": True, "published": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline private Reel batch runner")
    parser.add_argument("--workspace", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true")
    group.add_argument("--manifest", type=str)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    if args.init:
        setup(args.workspace.expanduser())
    else:
        print(json.dumps(run(args.workspace.expanduser(), args.manifest,
                             check_only=args.check), indent=2))


if __name__ == "__main__":
    main()
