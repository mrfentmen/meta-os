#!/usr/bin/env python3
"""DSH-024 crew-board Attempts badge (dashboard spec section 7).

Acceptance: job cards show an attempts/max_attempts badge that is
neutral below max-1, amber at max-1, and red at max; badge states are
verified against fixture jobs at 0, max-1, and max. The badge is
absent when the fields are absent, blank, or non-numeric. The detail
drawer shows the badge and an attempts row too. The node driver stubs
document like the other board harness tests; cardHTML / detailHTML are
pure renderers, so the driver calls them directly with fixture hashes
— no Upstash, no DOM. The badge text always reads "attempts a/m", so
the state is never carried by color alone.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "crew-board.html")

NODE_DRIVER = r"""
function elStub() {
  return { addEventListener: function () {}, hidden: false,
    textContent: "", innerHTML: "", value: "", className: "",
    focus: function () {}, querySelector: function () { return null; },
    querySelectorAll: function () { return []; } };
}
global.document = { getElementById: function () { return elStub(); },
  addEventListener: function () {}, querySelectorAll: function () { return []; } };
const out = {};
out.zero = cardHTML("1", { title: "Fresh", status: "open",
  created_at: 1700000000, attempts: "0", max_attempts: "3" });
out.one = cardHTML("2", { title: "One used", status: "claimed",
  created_at: 1700000000, attempts: 1, max_attempts: 3 });
out.warn = cardHTML("3", { title: "One left", status: "claimed",
  created_at: 1700000000, attempts: "2", max_attempts: "3" });
out.maxed = cardHTML("4", { title: "Spent", status: "blocked",
  created_at: 1700000000, attempts: "3", max_attempts: "3" });
out.over = cardHTML("5", { title: "Over", status: "blocked",
  created_at: 1700000000, attempts: "5", max_attempts: "3" });
out.oldJob = cardHTML("9", { title: "Old job", status: "open",
  created_at: 1700000000 });
out.blankJob = cardHTML("10", { title: "Blank fields", status: "open",
  created_at: 1700000000, attempts: "", max_attempts: "" });
out.junkJob = cardHTML("11", { title: "Junk fields", status: "open",
  created_at: 1700000000, attempts: "two", max_attempts: "three" });
out.noMaxJob = cardHTML("12", { title: "No max", status: "open",
  created_at: 1700000000, attempts: "1" });
out.detailWarn = detailHTML("3", { title: "One left", status: "claimed",
  attempts: "2", max_attempts: "3" }, "(spec)");
out.detailOld = detailHTML("9", { title: "Old job", status: "open" }, "(spec)");
console.log(JSON.stringify(out));
"""


def _script():
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    assert m, "no script block in crew-board.html"
    return m.group(1)


def _run_node():
    script = _script()
    # The page script runs DOM lookups at load; the driver stubs document
    # BEFORE those lookups run, so the stub must precede the script.
    prelude = NODE_DRIVER.split("const out = {};")[0]
    driver = NODE_DRIVER.split("const out = {};")[1]
    src = prelude + script + "\nconst out = {};" + driver
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        f.write(src)
        path = f.name
    try:
        res = subprocess.run(["node", path], capture_output=True,
                             text=True, timeout=30)
    finally:
        os.unlink(path)
    assert res.returncode == 0, f"node failed: {res.stderr}"
    return json.loads(res.stdout)


class TestCrewboardAttempts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = _run_node()

    def test_zero_attempts_neutral_badge(self):
        card = self.out["zero"]
        self.assertIn("attempts 0/3", card)
        self.assertIn('class="pill attempts"', card)
        self.assertNotIn("attempts warn", card)
        self.assertNotIn("attempts danger", card)

    def test_below_max_minus_one_neutral_badge(self):
        card = self.out["one"]
        self.assertIn("attempts 1/3", card)
        self.assertNotIn("attempts warn", card)
        self.assertNotIn("attempts danger", card)

    def test_max_minus_one_amber_badge(self):
        card = self.out["warn"]
        self.assertIn("attempts 2/3", card)
        self.assertIn('class="pill attempts warn"', card)

    def test_at_max_red_badge(self):
        card = self.out["maxed"]
        self.assertIn("attempts 3/3", card)
        self.assertIn('class="pill attempts danger"', card)

    def test_over_max_stays_red(self):
        card = self.out["over"]
        self.assertIn("attempts 5/3", card)
        self.assertIn('class="pill attempts danger"', card)

    def test_old_job_has_no_badge(self):
        card = self.out["oldJob"]
        self.assertNotIn("attempts", card)
        self.assertIn("Old job", card)

    def test_blank_and_junk_fields_render_no_badge(self):
        self.assertNotIn("attempts", self.out["blankJob"])
        self.assertNotIn("attempts", self.out["junkJob"])
        self.assertNotIn("attempts", self.out["noMaxJob"])

    def test_detail_shows_badge_and_row(self):
        detail = self.out["detailWarn"]
        self.assertIn("attempts 2/3", detail)
        self.assertIn('class="pill attempts warn"', detail)
        self.assertIn(">attempts<", detail)

    def test_detail_old_job_has_no_attempts(self):
        detail = self.out["detailOld"]
        self.assertNotIn("attempts", detail)


if __name__ == "__main__":
    unittest.main()
