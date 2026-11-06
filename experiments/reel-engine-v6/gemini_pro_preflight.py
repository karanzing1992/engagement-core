#!/usr/bin/env python3
"""V6 free Gemini Flash read-only API preflight. No inference, media transfer or billing changes.

Reuses the existing V4.2 authenticated REST transport without its video sampler.
Online discovery must be explicitly requested; no API key is ever printed.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
V42 = HERE.parent / "reel-engine-v4_2" / "gemini_adapter.py"
from v6_contract import V6Blocked, read_config, free_flash_models, select_free_flash_model


def adapter():
    if not V42.is_file():
        raise V6Blocked("Existing V4.2 Gemini adapter unavailable")
    spec = importlib.util.spec_from_file_location("v6_reused_gemini_v42", V42)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_models(key: str, v42_module) -> dict:
    """GET-only, bounded pages, allowlisted Google endpoint, no model inference."""
    if not key:
        raise V6Blocked("GEMINI_API_KEY missing; cannot verify this account")
    all_models = []
    token = ""
    for page in range(4):
        url = v42_module.BASE_URL + "/models?pageSize=100"
        if token:
            url += "&pageToken=" + quote(token, safe="")
        result = v42_module.make_request(url, key, timeout=25)
        models = result.get("models", [])
        if not isinstance(models, list):
            raise V6Blocked("Unexpected Gemini model-list response")
        all_models.extend(models)
        token = result.get("nextPageToken") or ""
        if not token:
            break
        if page == 3:
            raise V6Blocked("Gemini model list truncated; refuse unsupported selection")
    return {"models": all_models}


def preflight(*, online: bool, accept_api_terms: bool, model: str | None = None) -> dict:
    c = read_config()
    if not online:
        return {
            "stage": "offline_policy_contract",
            "v6_policy": c["provider_policy"]["mode"],
            "gemini_model_selection": c["model_roles"]["research"]["model"],
            "gemini_api_key_verified": False,
            "gemini_project_free_tier": "unverified_must_be_confirmed_before_inference",
            "api_billing_and_privacy_tier_verified": False,
            "model_inference_performed": False,
            "external_media_sent": False,
            "production_changed": False,
        }
    if not accept_api_terms:
        raise V6Blocked("Online Gemini API model lookup requires explicit API-terms acknowledgement")
    v42 = adapter()
    key = v42.key_from_environment()
    available = discover_models(key, v42)
    selected = select_free_flash_model(available, approved_model=model)
    return {
        "stage": "authenticated_model_list_only",
        "gemini_free_generation_model_candidate": selected,
        "free_candidate_count": len(free_flash_models(available)),
        "gemini_api_key_verified": True,
        "gemini_project_free_tier": "not_verified_by_model_discovery",
        "api_billing_and_privacy_tier_verified": False,
        "model_inference_performed": False,
        "external_media_sent": False,
        "production_changed": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--online-model-discovery", action="store_true")
    ap.add_argument("--acknowledge-api-terms", action="store_true")
    ap.add_argument("--model", help="Optional exact free-tier Flash model from live available list")
    args = ap.parse_args(argv)
    try:
        result = preflight(online=args.online_model_discovery,
                           accept_api_terms=args.acknowledge_api_terms,
                           model=args.model)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (V6Blocked, OSError, ValueError, RuntimeError) as exc:
        # Provider bodies, key strings and private source never printed.
        print(json.dumps({"stage": "BLOCKED", "reason": type(exc).__name__,
                          "source_only": True}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
