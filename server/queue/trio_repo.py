"""trio_repo.py — repo-relative anchors for the queue service.

The queue service lives at server/queue/ inside the meta-sentinel
repo; the shared web/server code it must never drift from lives two
levels up:

  js/schema.js    the v2 contract validator (validateAssessment)
  js/products.js  the per-product configs (ids, categories, prompt
                  profile fields) the server prompt profiles derive
                  from in server/model.mjs

Products are loaded by having node import the real js/products.js and
dump it as JSON — the file itself is the source of truth, never a
Python-side copy of its values.
"""
import json
import os
import subprocess

QUEUE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(QUEUE_DIR, "..", ".."))
SCHEMA_PATH = os.path.join(REPO_ROOT, "js", "schema.js")
PRODUCTS_PATH = os.path.join(REPO_ROOT, "js", "products.js")

_cache = {}


def products():
    """The PRODUCTS array from js/products.js (list of dicts)."""
    if "products" not in _cache:
        script = (
            f'import {{ PRODUCTS }} from '
            f'"file://{PRODUCTS_PATH}";\n'
            "console.log(JSON.stringify(PRODUCTS));\n"
        )
        p = subprocess.run(["node", "--input-type=module", "-e", script],
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise RuntimeError(
                f"could not load js/products.js: {p.stderr.strip()[:300]}")
        _cache["products"] = json.loads(p.stdout)
    return _cache["products"]


def product_ids():
    return {p["id"] for p in products()}


def product_profile(product):
    for p in products():
        if p["id"] == product:
            return p
    raise KeyError(f"no product profile for {product!r} in js/products.js")
