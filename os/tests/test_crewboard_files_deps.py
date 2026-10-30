#!/usr/bin/env python3
"""DSH-023 crew-board Files and Deps columns (dashboard spec section 7).

Acceptance: job cards show files/deps when the job hash carries them,
and cards for old jobs without those fields render unchanged (no
files/deps lines at all). The detail drawer lists them too. The node
driver stubs document like the other board harness tests; cardHTML /
detailHTML are pure renderers, so the driver calls them directly with
fixture hashes — no Upstash, no DOM.
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
out.withBoth = cardHTML("42", { title: "Build it", status: "open",
  created_at: 1700000000, files: "intel/a.py, intel/b.py", deps: "3, 7" });
out.oldJob = cardHTML("9", { title: "Old job", status: "open",
  created_at: 1700000000 });
out.blankJob = cardHTML("10", { title: "Blank fields", status: "open",
  created_at: 1700000000, files: " , ", deps: "" });
out.escaped = cardHTML("11", { title: "XSS", status: "open",
  created_at: 1700000000, files: "<b>&amp;</b>" });
out.detailBoth = detailHTML("42", { title: "Build it", status: "open",
  files: "intel/a.py", deps: "3" }, "(spec)");
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


class TestCrewboardFilesDeps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = _run_node()

    def test_card_shows_files_and_deps(self):
        card = self.out["withBoth"]
        self.assertIn("files: intel/a.py, intel/b.py", card)
        self.assertIn("deps: #3, #7", card)

    def test_old_job_card_unchanged(self):
        card = self.out["oldJob"]
        self.assertNotIn("files:", card)
        self.assertNotIn("deps:", card)
        self.assertIn("Old job", card)
        self.assertIn("#9", card)

    def test_blank_fields_render_nothing(self):
        card = self.out["blankJob"]
        self.assertNotIn("files:", card)
        self.assertNotIn("deps:", card)

    def test_file_names_escaped(self):
        card = self.out["escaped"]
        self.assertIn("files: &lt;b&gt;&amp;amp;&lt;/b&gt;", card)
        self.assertNotIn("<b>", card)

    def test_detail_lists_files_and_deps(self):
        detail = self.out["detailBoth"]
        self.assertIn("files", detail)
        self.assertIn("intel/a.py", detail)
        self.assertIn("deps", detail)
        self.assertIn("#3", detail)

    def test_detail_old_job_has_no_rows(self):
        detail = self.out["detailOld"]
        self.assertNotIn(">files<", detail)
        self.assertNotIn(">deps<", detail)


if __name__ == "__main__":
    unittest.main()
