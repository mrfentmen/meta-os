#!/usr/bin/env python3
"""STR-003: render the all-quiet Alerts panel (known-good half of the
SAM eval pairs) with Playwright + the repo's own Chromium build.

Method (same as DSH-030/DSH-035): headless render of bus.html at this
commit in demo mode (?demo=1), feed the panel through the
__busTest.intelPanel harness — zero alerts plus a live beat 30s old —
and screenshot the DETAILS#panel-intel-alerts element. The panel must
read "All quiet — watchdog alive" and the snapshot must report
alerts 0 and beat alive, or the script exits non-zero and writes
nothing.

The known-bad half (alerts-firing-*.png) is NOT re-rendered here:
those are the DSH-030 submission shots of the same panel fed the
DSH-037 dev-pack alerts payload (one watchdog.tick on a
stall/collision/dead-dep fixture), copied verbatim into
intel/evals/sam/ by the check's companion step. Re-rendering them
would risk silent drift from the pinned submission set.

Usage: python3 intel/sam_render.py [outdir]
Default outdir: intel/evals/sam
"""

import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.path.expanduser(
    "~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome")


def render(outdir):
    from playwright.sync_api import sync_playwright

    os.makedirs(outdir, exist_ok=True)
    url = "file://%s/bus.html?demo=1" % REPO
    shots = [
        ("alerts-quiet-desktop.png", 1280, 900),
        ("alerts-quiet-phone.png", 390, 844),
    ]
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        for name, width, height in shots:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            page.wait_for_timeout(800)
            snap = page.evaluate(
                "() => window.__busTest.intelPanel.snapshot()")
            assert snap["demoMode"] is True, "demo mode not on: %r" % snap
            page.evaluate(
                "() => { const ip = window.__busTest.intelPanel;"
                " const now = Date.now();"
                " ip.setAlerts([], now);"
                " ip.setBeat({ts: Math.floor(now/1000) - 30}, now); }")
            page.wait_for_timeout(400)
            snap = page.evaluate(
                "() => window.__busTest.intelPanel.snapshot()")
            assert snap["alerts"] == 0, "alerts not zero: %r" % snap
            assert snap["beat"] is True, "beat missing: %r" % snap
            panel_text = page.evaluate(
                "() => document.querySelector("
                "'#panel-intel-alerts').innerText")
            assert "All quiet" in panel_text, "quiet text absent: %r" % panel_text
            assert "watchdog alive" in panel_text, (
                "beat not alive in render: %r" % panel_text)
            assert not errors, "page errors: %r" % errors
            path = os.path.join(outdir, name)
            page.locator("#panel-intel-alerts").screenshot(path=path)
            assert os.path.getsize(path) > 1000, "tiny screenshot: %s" % path
            results[name] = {
                "viewport": [width, height],
                "panel_text": panel_text.strip().split("\n")[0],
                "bytes": os.path.getsize(path),
            }
            page.close()
        browser.close()
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(render(sys.argv[1] if len(sys.argv) > 1 else
                     os.path.join(REPO, "intel", "evals", "sam")))
