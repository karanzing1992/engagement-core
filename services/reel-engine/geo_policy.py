"""Fail-closed Goa/India footage policy for Reel Engine.

This is a provenance/eligibility gate, not proof of a clip's actual location.
A person must check the source evidence before marking it human_verified.
Foreign visuals are never legitimized by merely writing "Goa" in captions.
"""
from __future__ import annotations

from urllib.parse import urlsplit

TARGET_BRANDS = frozenset({"moksha", "andaz", "andaz-vibe-stay", "default", "generic"})
INDIA = frozenset({"india", "in"})
REGIONS = frozenset({"goa", "india"})
ACTUAL_ORIGINS = frozenset({"owned", "licensed_stock", "original"})
MEDIA_KINDS = frozenset({"video", "visual"})


class GeoPolicyError(ValueError):
    """A video must not be reviewed or delivered as local brand creative."""


def _https(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or value.startswith("REPLACE_"):
        return False
    p = urlsplit(value)
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password


def validate_asset(asset: dict, *, scene: str = "source") -> dict:
    """Validate a human-audited footage provenance record for a single clip."""
    if not isinstance(asset, dict):
        raise GeoPolicyError(f"{scene}: video provenance must be an object")
    origin = str(asset.get("origin", "")).strip().lower()
    status = str(asset.get("verification_status", "")).strip().lower()
    reviewer = str(asset.get("verified_by", "")).strip()
    if status != "human_verified" or len(reviewer) < 3:
        raise GeoPolicyError(f"{scene}: independent human verification is required")
    if not _https(asset.get("source_url")) or not _https(asset.get("location_evidence_url")):
        raise GeoPolicyError(f"{scene}: exact HTTPS source and location-evidence URLs are required")
    if origin in ACTUAL_ORIGINS:
        if str(asset.get("capture_country", "")).strip().casefold() not in INDIA:
            raise GeoPolicyError(f"{scene}: only verified footage filmed in Goa or India is eligible")
        return {"eligibility": "india_verified", "capture_country": "India",
                "capture_region": str(asset.get("capture_region", "")).strip(),
                "source_url": asset["source_url"], "verified_by": reviewer}
    if origin == "generated":
        # AI video cannot claim it was filmed in Goa or elsewhere.
        if str(asset.get("subject_region", "")).strip().casefold() not in REGIONS:
            raise GeoPolicyError(f"{scene}: generated footage must depict a Goa/India-specific subject")
        if asset.get("is_illustrative") is not True or asset.get("claims_real_footage") is not False:
            raise GeoPolicyError(f"{scene}: generated images must be labelled illustrative, not authentic local footage")
        return {"eligibility": "india_illustrative", "subject_region": asset["subject_region"],
                "source_url": asset["source_url"], "verified_by": reviewer}
    raise GeoPolicyError(f"{scene}: unverified media origin")


def validate_render_config(config: dict) -> dict:
    """Reject source media unrelated to Goa/India before copying or rendering."""
    if not isinstance(config, dict):
        raise GeoPolicyError("Video configuration must be a JSON object")
    brand = str(config.get("brand", "moksha")).strip().lower() or "moksha"
    if brand not in TARGET_BRANDS:
        raise GeoPolicyError("Unknown brand requires a configured geographic policy")
    editorial_region = str(config.get("editorial_region", "")).strip().casefold()
    if editorial_region not in REGIONS:
        raise GeoPolicyError("Video brief must explicitly target Goa or India")
    if config.get("regional_override") or config.get("geography_override"):
        # Explicit user exceptions require a separately audited admin authorization.
        # A render-request field cannot assert the user's approval.
        raise GeoPolicyError("Geography override is not supported in unattended render requests")
    assets = config.get("source_provenance")
    if not isinstance(assets, list) or not assets:
        raise GeoPolicyError("Provide source_provenance for every visual source")
    results = [validate_asset(asset, scene=f"clip {i+1}") for i, asset in enumerate(assets)]
    if not any(x["eligibility"] in ("india_verified", "india_illustrative") for x in results):
        raise GeoPolicyError("No Goa/India visual sources verified")
    return {"editorial_region": "Goa" if editorial_region == "goa" else "India",
            "clips_verified": len(results), "geography_gate": "passed",
            "publishing_enabled": False}
