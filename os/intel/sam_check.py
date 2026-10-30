#!/usr/bin/env python3
"""STR-003 check: validate the SAM eval set in intel/evals/sam/.

Checks, all must pass (exit 0):
1. pairs.json parses; every pair has one good (build-ok) and one bad
   (build-broken) half, distinct files, no file reused across pairs.
2. Every listed file exists in this directory and is a real PNG
   (magic bytes).
3. Every bad half's alert_ids equal exactly the open critical alert
   ids in the DSH-037 dev-pack payload (intel/devpack/alerts.json),
   which is what the firing shots render.
4. The firing files are byte-identical to the DSH-030 submission
   shots they were copied from (no silent drift from the pinned set).
5. The quiet files are the sam_render.py outputs (name convention
   + non-trivial PNG size); the render script itself asserts the
   panel text and snapshot at render time.

Usage: python3 intel/sam_check.py
"""

import hashlib
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAM_DIR = os.path.join(REPO, "intel", "evals", "sam")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def fail(msg):
    print("FAIL: " + msg)
    return 1


def main():
    with open(os.path.join(SAM_DIR, "pairs.json")) as fh:
        manifest = json.load(fh)
    if manifest.get("set") != "sam-eval-alerts-panel-v1":
        return fail("unexpected set id: %r" % manifest.get("set"))
    labels = set(manifest.get("labels", []))
    if labels != {"build-ok", "build-broken"}:
        return fail("labels must be exactly build-ok/build-broken: %r" % labels)

    with open(os.path.join(REPO, "intel", "devpack", "alerts.json")) as fh:
        pack = json.load(fh)

    def alert_ids(node):
        ids = []
        if isinstance(node, dict):
            if "id" in node and "kind" in node:
                ids.append(node["id"])
            for value in node.values():
                ids.extend(alert_ids(value))
        elif isinstance(node, list):
            for value in node:
                ids.extend(alert_ids(value))
        return ids

    pack_ids = sorted(alert_ids(pack))
    if len(pack_ids) != 5:
        return fail("dev-pack alerts payload no longer has 5 alerts: %r"
                    % pack_ids)

    seen_files = set()
    for pair in manifest["pairs"]:
        good, bad = pair["good"], pair["bad"]
        if good["label"] != "build-ok" or bad["label"] != "build-broken":
            return fail("pair %s has wrong labels" % pair["id"])
        for half in (good, bad):
            path = os.path.join(SAM_DIR, half["file"])
            if half["file"] in seen_files:
                return fail("file reused across pairs: %s" % half["file"])
            seen_files.add(half["file"])
            if not os.path.isfile(path):
                return fail("missing file: %s" % half["file"])
            with open(path, "rb") as fh:
                head = fh.read(8)
            if head != PNG_MAGIC:
                return fail("not a PNG: %s" % half["file"])
            if os.path.getsize(path) < 1000:
                return fail("suspiciously small PNG: %s" % half["file"])
        if sorted(bad["alert_ids"]) != pack_ids:
            return fail("pair %s bad alert_ids != dev-pack payload: %r"
                        % (pair["id"], bad["alert_ids"]))
        # Firing halves must match the pinned DSH-030 submission shots.
        orig = os.path.join(
            REPO, "hackathon", "relay-intelligence", "submission-assets",
            bad["file"])
        if not os.path.isfile(orig):
            return fail("submission original missing: %s" % orig)
        digest = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
        if digest(os.path.join(SAM_DIR, bad["file"])) != digest(orig):
            return fail("firing shot drifted from submission original: %s"
                        % bad["file"])
        if not good["file"].startswith("alerts-quiet-"):
            return fail("good half is not a sam_render.py output: %s"
                        % good["file"])
    print("SAM eval set OK: %d pairs, %d files, bad halves match the "
          "5-alert dev-pack payload" % (len(manifest["pairs"]), len(seen_files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
