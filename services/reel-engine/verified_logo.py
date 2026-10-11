"""Approved Moksha logo resolver for in-house cloud video renderers.

Single Drive master is approved in ops/brand-assets/registry.json. This module
uses a signed WP Control lookup when credentials are available, then downloads
only the byte-identical WordPress attachment or the exact immutable Git mirror.
No fuzzy matching, AI reconstruction, dynamic hostnames, or publish actions.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DRIVE_ID = "1XwmlYRfjfkcnbEOlJLNJc8bGHm9uxkyv"
SHA256 = "76e89b83667827da4b5d89143fb267f4000a9392eff685129c838c3d0b24748c"
BYTES = 81501
DIMENSIONS = (737, 681)
MIRROR = (
    "https://raw.githubusercontent.com/karanzing1992/engagement-core/"
    "e7224f224ffa17bfa56bea7c946c2f7f8af45b8f/assets/brand/moksha-logo-source.jpg"
)
WP_ENDPOINT = "https://mokshagoa.com/wp-json/wp-control/v1/brand-assets/moksha/resolve"
PLACEMENTS = {"reel", "short", "story", "feed", "google-business", "whatsapp", "pinterest", "website", "print"}


class VerificationError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise VerificationError("Unapproved media redirect")


def _url_allowed(url: str, *, mirror: bool = False) -> bool:
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.query or p.fragment:
        return False
    if mirror:
        return url == MIRROR
    return p.hostname == "mokshagoa.com" and p.port is None and p.path.startswith("/wp-content/uploads/") and p.path.endswith(".jpg")


def _read_http(url: str, headers: dict[str, str] | None = None, opener=None, max_bytes: int = 1024 * 1024) -> bytes:
    opener = opener or urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "MokshaApprovedLogoRenderer/1.0"})
    with opener.open(request, timeout=20) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise VerificationError("Brand asset exceeds size cap")
        return data


def _verify_original(data: bytes) -> None:
    if len(data) != BYTES or not data.startswith(b"\xff\xd8\xff") or not data.endswith(b"\xff\xd9"):
        raise VerificationError("Official JPEG bytes missing or malformed")
    if not hashlib.sha256(data).hexdigest() == SHA256:
        raise VerificationError("Wrong logo: bytes differ from approved Google Drive master")


def resolve_verified_logo(
    output_path: Path,
    *,
    brand: str = "moksha",
    placement: str = "reel",
    wp_token: str | None = None,
    opener=None,
) -> dict:
    """Return exact approved JPEG on disk and provenance; never substitute.

    WordPress resolver token is optional. Offline/cold worker uses immutable Git mirror;
    cached correct bytes are accepted even if neither network route responds.
    """
    if brand != "moksha":
        raise VerificationError("Brand not approved. Separate Drive master required.")
    if placement not in PLACEMENTS:
        raise VerificationError("Unsupported logo placement; request human approval")
    output_path = Path(output_path)
    if output_path.is_file():
        try:
            _verify_original(output_path.read_bytes())
            return {"logo": str(output_path), "source": "previously_verified_cache", "drive_file_id": DRIVE_ID,
                    "sha256": SHA256, "placement": placement, "width": 737, "height": 681}
        except VerificationError:
            raise VerificationError("Existing logo cache is corrupt. Refusing to overwrite untrusted bytes silently.")
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)

    allowed_urls: list[tuple[str, str]] = []
    if wp_token:
        if len(wp_token) != 64 or any(c not in "0123456789abcdef" for c in wp_token):
            raise VerificationError("Brand resolver token format invalid")
        endpoint = WP_ENDPOINT + "?" + urllib.parse.urlencode({"placement": placement})
        try:
            payload = json.loads(_read_http(endpoint, {"X-WP-Control-Brand-Token": wp_token}, opener=opener))
            if not (
                payload.get("ready") is True and payload.get("brand") == "moksha" and
                payload.get("role") == "official_full_logo" and payload.get("drive_file_id") == DRIVE_ID and
                payload.get("approved_sha256") == SHA256 and payload.get("variant") == "original_gold_on_black" and
                payload.get("allow_ai_recreation") is False and payload.get("width") == 737 and
                payload.get("height") == 681 and payload.get("placement") == placement
            ):
                raise VerificationError("WordPress brand manifest conflicts with pinned approved logo")
            url = str(payload.get("asset_url", ""))
            if not _url_allowed(url):
                raise VerificationError("WordPress returned an untrusted media hostname or path")
            allowed_urls.append(("wordpress_verified", url))
        except VerificationError:
            # Manifest conflicts are security failures, not network failures. Never fall back.
            raise
        except (TimeoutError, OSError, urllib.error.URLError, ValueError, json.JSONDecodeError):
            # Temporary connection failure: immutable approved master is still eligible.
            pass
    allowed_urls.append(("approved_immutable_git_mirror", MIRROR))

    errors = []
    for source, url in allowed_urls:
        if not _url_allowed(url, mirror=source == "approved_immutable_git_mirror"):
            raise VerificationError("Unapproved source URL")
        try:
            data = _read_http(url, opener=opener)
            _verify_original(data)
            with tempfile.NamedTemporaryFile(dir=output_path.parent, prefix=".logo-", delete=False) as fh:
                path = Path(fh.name)
                fh.write(data)
            os.replace(path, output_path)
            return {"logo": str(output_path), "source": source, "drive_file_id": DRIVE_ID,
                    "sha256": SHA256, "placement": placement, "width": 737, "height": 681}
        except (VerificationError, TimeoutError, OSError, urllib.error.URLError) as exc:
            errors.append(f"{source}: {type(exc).__name__}")
    raise VerificationError("No verified approved logo could be retrieved (" + "; ".join(errors) + ")")


def overlay_verified_logo(
    video_input: Path,
    video_output: Path,
    *,
    brand: str = "moksha",
    placement: str = "reel",
    wp_token: str | None = None,
    cache_dir: Path | None = None,
) -> dict:
    """Burn original logo onto a finished MP4 AFTER the hook, preserve underlying audio.

    A full black-backed official logo is shown as a closing mark; no fake transparent logo.
    """
    if not Path(video_input).is_file():
        raise VerificationError("Video input is missing")
    video_input, video_output = Path(video_input), Path(video_output)
    if video_input.resolve() == video_output.resolve():
        raise VerificationError("Cannot overwrite master video in place")
    cache_dir = Path(cache_dir or (video_output.parent / ".verified-brand-assets"))
    logo_info = resolve_verified_logo(cache_dir / "moksha-approved-master.jpg", brand=brand, placement=placement, wp_token=wp_token)
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type", "-of", "json", str(video_input)
    ])
    meta = json.loads(raw)
    duration = float(meta.get("format", {}).get("duration") or 0)
    stream = next((x for x in meta.get("streams", []) if x.get("codec_type") == "video"), None)
    if stream is None or not 2 <= duration <= 180:
        raise VerificationError("Invalid finished MP4 dimensions/duration")
    width, height = int(stream["width"]), int(stream["height"])
    if min(width, height) < 360:
        raise VerificationError("Output too small for verified logo")
    mark_width = max(80, round(width * (0.28 if placement in ("reel", "short") else 0.18)))
    start = max(1.5, duration - 2.7) if placement in ("reel", "short") else 1.5
    if placement in ("reel", "short"):
        pos = "(main_w-overlay_w)/2:main_h-overlay_h-main_h*0.18"
    else:
        pos = "main_w-overlay_w-main_w*0.06:main_h-overlay_h-main_h*0.20"
    filter_graph = (
        f"[1:v]scale={mark_width}:-1,format=yuva420p[logo];"
        f"[0:v][logo]overlay={pos}:enable='gte(t,{start:.3f})':shortest=1,format=yuv420p[v]"
    )
    video_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_input), "-loop", "1", "-i", logo_info["logo"],
           "-filter_complex", filter_graph, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "21", "-c:a", "copy", "-movflags", "+faststart", "-shortest", str(video_output)]
    subprocess.run(cmd, check=True)
    return {"source_video": str(video_input), "output_video": str(video_output), "logo": logo_info,
            "applied_start_seconds": start, "publishing_enabled": False}


def main() -> None:
    """CLI for external FFmpeg workers: inspect, verify and brand one finished draft."""
    import argparse
    parser = argparse.ArgumentParser(description="Apply only SHA-256 verified official Drive-sourced branding to a draft")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--brand", default="moksha")
    parser.add_argument("--placement", choices=sorted(PLACEMENTS), default="reel")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    report = overlay_verified_logo(args.input, args.output, brand=args.brand, placement=args.placement,
                                  wp_token=os.environ.get("MRS_BRAND_ASSET_TOKEN") or None, cache_dir=args.cache_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()