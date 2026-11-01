#!/usr/bin/env python3
"""MAD public CI smoke: Groq edit plan -> FilmCraft MCP -> MP4 QA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
INPUT = OUT / "synthetic.mp4"
VIDEO = OUT / "filmcraft_groq_pilot.mp4"
PROJECT = OUT / "filmcraft_groq_pilot.fcproj"
LOG = OUT / "filmcraft_stderr.log"
RECEIPT = OUT / "receipt.json"

def shell(argv, timeout=30):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout)

def make_synthetic():
    shell(["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", "testsrc2=size=480x270:rate=24",
           "-t", "2", "-c:v", "libx264", "-preset", "ultrafast",
           "-threads", "1", "-pix_fmt", "yuv420p", str(INPUT)], timeout=35)
    print("SYNTHETIC_INPUT_OK", INPUT.stat().st_size, flush=True)

def plan_fixture():
    return json.loads((HERE / "plan.json").read_text())

def plan_live():
    from groq import Groq
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        raise RuntimeError("GROQ_API_KEY secret is required for live mode")
    instructions = (
        "Return only valid JSON with keys sequence, placement, export, creative_intent. "
        "For sequence use name MAD_Reel_Intro, width 480, height 270, fps 24. "
        "For placement use track V1, seconds 0, duration 2, matchSequence false. "
        "For export use format h264, width 480, height 270, range custom, "
        "startSeconds 0, endSeconds 2, wait true, hardwareEncoding off. "
        "Make the creative_intent a short phrase. No other actions."
    )
    with Groq(api_key=key, timeout=25, max_retries=1) as client:
        result = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": instructions},
                      {"role": "user", "content": "Plan the 2 second synthetic FilmCraft edit."}],
            response_format={"type": "json_object"},
            temperature=0, max_completion_tokens=1400)
    raw = result.choices[0].message.content or ""
    if not raw.strip():
        raise RuntimeError("Groq returned an empty edit plan")
    return json.loads(raw)

def validate_plan(plan):
    s, p, e = (plan[k] for k in ("sequence", "placement", "export"))
    if (s.get("width"), s.get("height"), s.get("fps")) != (480, 270, 24):
        raise ValueError("Unexpected sequence profile")
    if (p.get("track"), p.get("seconds"), p.get("duration")) != ("V1", 0, 2):
        raise ValueError("Unexpected placement")
    if (e.get("format"), e.get("width"), e.get("height"),
        e.get("endSeconds"), e.get("hardwareEncoding"), e.get("wait")) != (
        "h264", 480, 270, 2, "off", True):
        raise ValueError("Unexpected export parameters")
    return str(s.get("name") or "MAD Pilot")[:65]

class MCP:
    def __init__(self):
        cli = os.environ["FILMCRAFT_CLI"]
        self.stderr = LOG.open("w")
        self.process = subprocess.Popen(
            [cli, "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.stderr, text=True, bufsize=1,
            cwd=str(HERE), env={**os.environ, "RUST_BACKTRACE": "0"})
        self.next_id = 0
        result = self.request("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "mad-groq-gh-actions", "version": "0.1"}})
        assert result.get("result"), "FilmCraft initialize failed"
        self.process.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")
        self.process.stdin.flush()
        self.tools = {t["name"] for t in
                      self.request("tools/list", {}).get("result", {}).get("tools", [])}
        print("MCP_CONNECTED", len(self.tools), "tools", flush=True)

    def request(self, method, params, timeout=120):
        self.next_id += 1
        requested_id = self.next_id
        self.process.stdin.write(json.dumps(
            {"jsonrpc": "2.0", "id": requested_id, "method": method, "params": params}) + "\n")
        self.process.stdin.flush()
        selector = selectors.DefaultSelector()
        selector.register(self.process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                if not selector.select(min(1, max(0, deadline - time.monotonic()))):
                    continue
                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError("FilmCraft MCP closed its stdout")
                try:
                    response = json.loads(line)
                except ValueError:
                    continue
                if response.get("id") == requested_id:
                    if response.get("error"):
                        raise RuntimeError("MCP error: " + str(response["error"])[:400])
                    return response
            raise TimeoutError("MCP timed out: " + method)
        finally:
            selector.close()

    def tool(self, name, args, timeout=120):
        if name not in self.tools:
            raise RuntimeError("Missing MCP tool: " + name)
        response = self.request("tools/call", {"name": name, "arguments": args}, timeout)
        result = response.get("result", {})
        text = "\n".join(x.get("text", "") for x in result.get("content", [])
                         if x.get("type") == "text")
        if result.get("isError"):
            raise RuntimeError("MCP " + name + ": " + text[:750])
        print("MCP_OK", name, text[:240].replace("\n", " "), flush=True)
        return text

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.stderr.close()

def find_item(tree, basename):
    if isinstance(tree, dict):
        if tree.get("name") == basename and isinstance(tree.get("item"), int):
            return tree["item"]
        for value in tree.values():
            found = find_item(value, basename)
            if found is not None:
                return found
    elif isinstance(tree, list):
        for value in tree:
            found = find_item(value, basename)
            if found is not None:
                return found
    return None

def edit(plan):
    m = MCP()
    try:
        name = validate_plan(plan)
        m.tool("command_run", {"id": "file.newSequence",
            "params": {"name": name, "width": 480, "height": 270,
                       "fps": 24, "video": 1, "audio": 1}})
        m.tool("media_import", {"paths": [str(INPUT)]})
        tree = json.loads(m.tool("project_inspect", {}))
        item = find_item(tree, INPUT.name)
        if item is None:
            raise RuntimeError("Could not verify imported media item ID")
        m.tool("command_run", {"id": "timeline.place",
            "params": {"item": item, "track": "V1", "seconds": 0,
                       "duration": {"seconds": 2}, "audio": False,
                       "matchSequence": False}})
        m.tool("sequence_inspect", {})
        m.tool("command_run", {"id": "file.saveAs", "params": {"path": str(PROJECT)}})
        m.tool("command_run", {"id": "file.exportMedia", "params": {
            "path": str(VIDEO), "format": "h264", "width": 480, "height": 270,
            "range": "custom", "startSeconds": 0, "endSeconds": 2,
            "wait": True, "hardwareEncoding": "off", "audio": False}}, timeout=180)
    finally:
        m.close()

def verify():
    if not VIDEO.is_file() or VIDEO.stat().st_size == 0:
        raise RuntimeError("FilmCraft did not create an MP4 file")
    probe = json.loads(shell(["ffprobe", "-v", "error",
        "-show_entries", "format=duration,size",
        "-show_entries", "stream=codec_name,width,height",
        "-of", "json", str(VIDEO)], timeout=15).stdout)
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    duration = float(fmt["duration"])
    if not (1.5 <= duration <= 2.5):
        raise RuntimeError("Unexpected duration: " + str(duration))
    if not any(s.get("codec_name") == "h264" and
               (s.get("width"), s.get("height")) == (480, 270) for s in streams):
        raise RuntimeError("Wrong video codec or dimensions")
    shell(["ffmpeg", "-v", "error", "-i", str(VIDEO),
           "-f", "null", "-"], timeout=25)
    return {"duration_seconds": duration, "bytes": VIDEO.stat().st_size,
            "sha256": hashlib.sha256(VIDEO.read_bytes()).hexdigest(),
            "video": str(VIDEO.relative_to(HERE))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fixture", "live"), default="fixture")
    args = parser.parse_args()
    status = {"mode": args.mode, "filmcraft_version": "0.16.0",
              "groq_model": "openai/gpt-oss-20b" if args.mode == "live" else "fixture",
              "success": False}
    try:
        make_synthetic()
        plan = plan_live() if args.mode == "live" else plan_fixture()
        name = validate_plan(plan)
        print("PLAN_VALIDATED", args.mode, name, flush=True)
        edit(plan)
        status.update(verify())
        status["success"] = True
        print("PILOT_PASS", status["sha256"], flush=True)
    except Exception as exc:
        status["error"] = type(exc).__name__ + ": " + str(exc)[:400]
        print("PILOT_FAIL", status["error"], flush=True)
        traceback.print_exc()
        raise
    finally:
        RECEIPT.write_text(json.dumps(status, indent=2) + "\n")

if __name__ == "__main__":
    main()
