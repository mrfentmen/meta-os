#!/usr/bin/env python3
"""labs/check_assets.py — fail on missing assets for Section C (science lab + 3D) pages.

Covers: labs/molecules/index.html, design/meta-scientia-molecules.html,
labs/science-lab-review/index.html, labs/review/*.html.

Checks per page:
  1. Every local <script src> / fetch("...") / fetch('...') target resolves
     to a file in the repo (relative to the page's directory).
  2. No <script src> or <link href> points at an http(s) CDN (fonts,
     shaders, libraries). The molecule viewer's *runtime* PubChem
     load-by-CID fetch is documented and allowlisted — it is a user-
     triggered API call, not a page asset, and the page works offline
     without it.
  3. Every data file referenced by data/meta.json (labs/molecules) and
     design/molecules/meta.json exists and parses.

Run: python3 labs/check_assets.py (exit 0 = all present, 1 = failures).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = [
    "labs/molecules/index.html",
    "design/meta-scientia-molecules.html",
    "labs/science-lab-review/index.html",
    "labs/review/bolo.html",
    "labs/review/timeline.html",
    "labs/review/cannot-do.html",
]
# Runtime-only remote call, not a page asset: user clicks "Load CID".
ALLOW_REMOTE = ("https://pubchem.ncbi.nlm.nih.gov/rest/pug/",)

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL:", msg)


def page_dir(page):
    return (ROOT / page).parent


def resolve(page, url):
    """Where an asset URL points on disk.

    A leading slash is site-absolute: the server hands /vendor/fonts/fonts.css
    out of the repo root, not out of the page's folder. Pathlib's `/` operator
    lets an absolute right-hand side win, so `page_dir(page) / '/vendor/x'`
    became the host filesystem path /vendor/x and the file "did not exist"
    even though the repo ships it. Absolute URLs resolve against the root.
    """
    return (ROOT / url.lstrip("/")) if url.startswith("/") else (page_dir(page) / url)


def check_page(page):
    text = (ROOT / page).read_text()
    d = page_dir(page)
    # 1+2. script/link tags
    for m in re.finditer(r'<(?:script[^>]*src|link[^>]*href)\s*=\s*["\']([^"\']+)["\']', text):
        url = m.group(1)
        if url.startswith("data:"):
            continue
        if url.startswith(("http://", "https://")):
            fail(f"{page}: CDN/remote asset in tag: {url}")
            continue
        if not resolve(page, url).exists():
            fail(f"{page}: missing tag asset: {url} (resolved {resolve(page, url)})")
    # 1. fetch("...") targets (template-local only; skip http and dynamic concat)
    for m in re.finditer(r'fetch\(\s*["\']([^"\']+)["\']', text):
        url = m.group(1)
        if url.startswith(("http://", "https://")):
            if not url.startswith(ALLOW_REMOTE):
                fail(f"{page}: non-allowlisted remote fetch: {url}")
            continue
        if not resolve(page, url).exists():
            fail(f"{page}: missing fetch asset: {url}")
    # 2b. @import / @font-face / ShaderMaterial from CDN
    for pat in (r"@import\s+url\(['\"]?https?://", r"fonts\.googleapis\.com",
                r"unpkg\.com", r"cdnjs\.cloudflare\.com", r"cdn\.jsdelivr\.net"):
        if re.search(pat, text):
            fail(f"{page}: CDN reference matching {pat!r}")


def check_meta(meta_rel, data_dir_rel):
    meta = json.loads((ROOT / meta_rel).read_text())
    comps = meta["compounds"]
    if not comps:
        fail(f"{meta_rel}: compound list is empty")
    data_dir = ROOT / data_dir_rel
    key = "file" if "file" in comps[0] else "id"
    for c in comps:
        fname = c["file"] if key == "file" else c["id"] + ".json"
        p = data_dir / fname
        if not p.exists():
            fail(f"{meta_rel}: missing data file {fname}")
            continue
        try:
            mol = json.loads(p.read_text()) if p.suffix == ".json" else None
        except json.JSONDecodeError as e:
            fail(f"{meta_rel}: {fname} is not valid JSON: {e}")
            continue
        if mol is not None and (not mol.get("atoms") or "bonds" not in mol):
            fail(f"{meta_rel}: {fname} has no atoms/bonds")


for page in PAGES:
    if not (ROOT / page).exists():
        fail(f"page missing: {page}")
    else:
        check_page(page)
check_meta("labs/molecules/data/meta.json", "labs/molecules/data")
check_meta("design/molecules/meta.json", "design/molecules")

if failures:
    print(f"\n{len(failures)} failure(s).")
    sys.exit(1)
print(f"OK: {len(PAGES)} pages, all local assets resolve, no CDN tag assets.")
