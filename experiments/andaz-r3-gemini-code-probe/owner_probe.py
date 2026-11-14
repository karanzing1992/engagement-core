#!/usr/bin/env python3
"""One owner-only Gemini coding candidate; no site writes, scores, deploys or secrets in artifacts."""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

MODEL = "gemini-3.5-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
OUT = Path("out/andaz-r3-owner-code-probe")
PAGES = ("index.html", "rooms.html", "experiences.html", "food.html", "explore.html", "contact.html")
WA = "https://wa.me/918999541081"
MAP = "https://maps.app.goo.gl/CrzfATU3QnmNoMZcA"
LOGO = "assets/andaz-official-cropped.webp"
PHOTO = "media/andaz_room_01_wide.webp"
CSS = "assets/v9-fresh.css"
JS = "assets/site.js"
FORBIDDEN = re.compile(r"\b(suites?|balcon(y|ies)|swimming pool|free wifi|breakfast included|sea views?|ocean views?|guided tours?|luxury resort|private two.bed dorm|well[- ]maintained dormitories|common social areas?|communal seating zones?|spontaneous gatherings?|music and shared experiences|shared lounge areas?|common lounge areas?)\b", re.I)
STYLE_CLASSES = {"site-header", "site-footer", "container", "logo", "nav-list", "hero", "grid", "card", "btn", "cta"}

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

class PageInspector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.images = []
        self.links = []
        self.sections = []
        self.active_section = None
        self.section_depth = 0
        self.words = []
        self.scripts = []
        self.classes = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        self.classes.update(a.get("class", "").split())
        if tag == "section":
            self.sections.append({"text": [], "links": [], "images": []})
            self.active_section = self.sections[-1]
            self.section_depth += 1
        if tag == "img":
            self.images.append(a.get("src", ""))
            if self.active_section is not None:
                self.active_section["images"].append(a.get("src", ""))
        if tag == "a":
            href = a.get("href", "")
            self.links.append(href)
            if self.active_section is not None:
                self.active_section["links"].append(href)
        if tag == "script":
            self.scripts.append(a)
    def handle_endtag(self, tag):
        if tag == "section" and self.section_depth:
            self.section_depth -= 1
            if self.section_depth == 0:
                self.active_section = None
    def handle_data(self, data):
        if data.strip():
            self.words.append(data)
            if self.active_section is not None:
                self.active_section["text"].append(data)

def validate(html):
    if not isinstance(html, str) or not 1200 <= len(html.encode()) <= 30000:
        raise ValueError("CANDIDATE_LENGTH")
    if not html.strip().lower().startswith("<!doctype html>"):
        raise ValueError("DOCTYPE_REQUIRED")
    p = PageInspector()
    p.feed(html)
    if p.tags.count("main") != 1 or p.tags.count("h1") != 1:
        raise ValueError("MAIN_H1_REQUIRED")
    if len(p.sections) < 4 or len(" ".join(p.words).split()) < 185:
        raise ValueError("EDITORIAL_COPY_TOO_THIN")
    if FORBIDDEN.search(" ".join(p.words)):
        raise ValueError("UNVERIFIED_PROPERTY_CLAIM")
    if p.images.count(LOGO) < 1 or p.images.count(PHOTO) != 1:
        raise ValueError("OFFICIAL_BRAND_ASSET_POLICY")
    if any(img not in (LOGO, PHOTO) for img in p.images):
        raise ValueError("UNAPPROVED_IMAGE")
    if any(x not in set(PAGES) | {WA, MAP, "#rooms", "#food", "#explore", "#top", "#contact"} for x in p.links):
        raise ValueError("UNAPPROVED_LINK")
    if not set(PAGES[1:]).issubset(set(p.links)) or WA not in p.links:
        raise ValueError("NAV_OR_WHATSAPP_MISSING")
    food = [s for s in p.sections if "Andaz Table" in " ".join(s["text"])]
    if not food or not any("food.html" in s["links"] and PHOTO not in s["images"] for s in food):
        raise ValueError("FOOD_TEASER_WRONG_DESTINATION")
    if len(p.scripts) != 1 or p.scripts[0].get("src") != JS or "defer" not in p.scripts[0]:
        raise ValueError("TRUSTED_SCRIPT_REQUIRED")
    if CSS not in re.findall(r'href=["\']([^"\']+)["\']', html):
        raise ValueError("SHARED_CSS_REQUIRED")
    if not {"site-header", "container", "nav-list", "hero"}.issubset(p.classes) or len(STYLE_CLASSES & p.classes) < 6:
        raise ValueError("STYLE_CLASS_CONTRACT")
    if "<iframe" in html.lower() or "javascript:" in html.lower() or "onerror=" in html.lower():
        raise ValueError("UNSAFE_ACTIVE_CONTENT")
    return {"sections": len(p.sections), "visible_words": len(" ".join(p.words).split()),
            "images": len(p.images), "internal_nav": len(set(PAGES[1:]) & set(p.links))}

PROMPT = (
    "You are a guarded code-writing agent creating a SINGLE HTML5 candidate for Andaz Vibe Stay, "
    "an authentic social hostel in Arambol, Goa, India, never a luxury resort. "
    "Return a JSON object with one field html containing valid complete index.html; no Markdown, no explanations. "
    "Include at least 215 visible English words of genuine grounded hospitable copy in 5 or more sections. "
    "Use doctype html, lang=en, viewport meta, exactly one main and h1, 6-page navigation links "
    "to index.html, rooms.html, experiences.html, food.html, explore.html, contact.html, "
    "and visible WhatsApp enquiry link " + WA + ". "
    "Use official logo image " + LOGO + " and exactly ONE authentic bedroom photo " + PHOTO +
    " in home/stay hero ONLY, never in food or destination sections, alt exactly 'Andaz room interior'. "
    "Use shared stylesheet " + CSS + " and ONLY <script src=\"" + JS + "\" defer></script>. "
    "A separate photo-free section titled The Andaz Table MUST contain visible food.html link, "
    "with true owner prices: fresh homestyle Indian meals Rs 180 dine-in, Rs 220 delivered inside Arambol "
    "with free delivery; outside Arambol a minimal additional delivery fee by enquiry. "
    "Rooms: six-bed non-AC dorm, six-bed AC dorm, two-bed non-AC SHARED dorm, private AC rooms. "
    "Keep Moksha Wellness optional independent wellness partner. "
    "Separate Explore section must link explore.html. Do not invent amenities, photographs, chefs, "
    "tours, sea views, balconies, pool, breakfast, parking, Wi-Fi, desk, location details or room prices. "
    "Match the actual verified stylesheet vocabulary: site-header with inner container, "
    "logo image class logo, nav ul class nav-list, hero section class hero, "
    "grid and card for content listings, btn for clickable WhatsApp enquiry, "
    "cta for focused booking prompt and site-footer for footer. "
    "Use at least six distinct classes from site-header, site-footer, container, logo, "
    "nav-list, hero, grid, card, btn, cta; never invent unsupported CSS class names. "
    "A social-hostel identity DOES NOT prove shared seating zones, a lounge, music, "
    "hosted gatherings, maintained quality ratings or organized entertainment. "
    "Mention none of those claims, including as negative/disclaimer statements. "
    "Mobile nav must be visibly discoverable and spacious. Semantic headings, good body contrast. "
    "NEVER mention even as a disclaimer or negative claim: suites, suite, balcony, balconies, "
    "swimming pool, free wifi, breakfast included, sea view, sea views, ocean views, "
    "guided tours, luxury resort, private two-bed dorm. Use only the supplied facts. "
    "No extra external URLs, no remote fonts, scripts, embeds, buttons without destinations, "
    "JavaScript handlers or additional image assets."
)

def self_test():
    for bad in ("<script>alert(1)</script>", "<!doctype html><html><main><h1>Wrong</h1></main></html>"):
        try: validate(bad)
        except ValueError: pass
        else: raise AssertionError("UNSAFE_HTML_WAS_ACCEPTED")
    assert digest(PROMPT) == digest(PROMPT.encode())
    assert "GEMINI_API_KEY" not in PROMPT
    print("LOCAL_VALIDATOR_NEGATIVE_TEST_PASS; no provider call or website write")

def run():
    if os.getenv("GITHUB_REPOSITORY") != "karanzing1992/engagement-core" or os.getenv("GITHUB_ACTOR") != "karanzing1992" or os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        raise RuntimeError("OWNER_PR_CONTEXT_REQUIRED")
    key = os.getenv("GEMINI_API_KEY", "")
    if len(key) < 20:
        raise RuntimeError("EXISTING_OWNER_SECRET_UNAVAILABLE")
    OUT.mkdir(parents=True, exist_ok=True)
    body = {"contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 4500,
                                 "responseMimeType": "application/json"}}
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=50) as res:
            payload = res.read(100000)
        reply = json.loads(payload)
        first = (reply.get("candidates") or [{}])[0]
        if first.get("finishReason") != "STOP":
            raise RuntimeError("MODEL_FINISH_UNSAFE")
        text = "".join(z.get("text", "") for z in first.get("content", {}).get("parts", []) if isinstance(z, dict))
        obj = json.loads(text)
        if not isinstance(obj, dict) or set(obj) != {"html"}:
            raise RuntimeError("UNEXPECTED_MODEL_JSON")
        html = obj["html"]
        metrics = validate(html)
        (OUT / "index.html").write_text(html, encoding="utf-8")
        result = {"schema": "andaz-r3-owner-gemini-code-probe-v1", "status": "CANDIDATE_ONLY",
                  "model": MODEL, "prompt_sha256": digest(PROMPT),
                  "html_sha256": digest(html), "metrics": metrics,
                  "owner_verified_source": False, "independent_artistic_score": None,
                  "release_authorized": False, "production_writes": False}
        (OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        print("GEMINI_OWNER_ONLY_CODE_CANDIDATE_SUCCESS sha256=" + digest(html))
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GEMINI_HTTP_" + str(exc.code)) from None
    except (TimeoutError, urllib.error.URLError):
        raise RuntimeError("GEMINI_NETWORK_OR_TIMEOUT") from None

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
    else:
        try: run()
        except Exception as e:
            OUT.mkdir(parents=True, exist_ok=True)
            reason = str(e)
            safe_failures = {
                "CANDIDATE_LENGTH", "DOCTYPE_REQUIRED", "MAIN_H1_REQUIRED",
                "EDITORIAL_COPY_TOO_THIN", "UNVERIFIED_PROPERTY_CLAIM",
                "OFFICIAL_BRAND_ASSET_POLICY", "UNAPPROVED_IMAGE", "UNAPPROVED_LINK",
                "NAV_OR_WHATSAPP_MISSING", "FOOD_TEASER_WRONG_DESTINATION",
                "TRUSTED_SCRIPT_REQUIRED", "SHARED_CSS_REQUIRED", "UNSAFE_ACTIVE_CONTENT", "STYLE_CLASS_CONTRACT"
            }
            if isinstance(e, json.JSONDecodeError):
                reason = "GEMINI_MODEL_JSON_INVALID"
            elif isinstance(e, ValueError) and reason in safe_failures:
                reason = "VALIDATION_" + reason
            elif not reason.startswith(("GEMINI_HTTP_", "GEMINI_NETWORK_", "OWNER_", "EXISTING_OWNER_")):
                reason = type(e).__name__ + ":VALIDATION_OR_PROVIDER_REJECTED"
            (OUT / "failed.json").write_text(json.dumps({
                "status": "BLOCKED", "reason": reason[:110], "artistic_score": None,
                "release_authorized": False, "production_writes": False}, indent=2) + "\n")
            print("OWNER_CODE_PROBE_BLOCKED " + reason[:100], file=sys.stderr)
            sys.exit(4)
