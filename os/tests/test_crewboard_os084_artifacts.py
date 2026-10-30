#!/usr/bin/env python3
"""OS-084 artifact links on the crew board (artifact part only).

Acceptance, artifact part: a job record carrying the OS-083
attach() shape — an "artifacts" list of {path, reference,
version, sha256} — renders artifact links on its job card and in
its detail drawer: the link target is the store-relative path
("jobs/<id>/<name>", META_OS.md section 3: the dashboard links
straight to the store path), the label is the file name plus its
version, the reference rides as the title. Jobs without artifacts
render unchanged (no artifacts line at all), exactly like the
DSH-023 files/deps rule for old jobs. A job-hash field arriving
as a JSON string (Redis hashes deliver strings) parses the same
way. Entries with an absolute, escaping, or empty-segment path
are dropped, never rendered as links.

The live check feeds the renderer the output of the real
mos/artifact_store.attach() after two real deposits (v1 then v2),
so the shape asserted is the shape the store actually produces,
not a hand-built fixture. Nothing here posts: the board only
reads job records.

Not shipped here: per-process capability summaries (the OS-080
grant files are on-disk JSON with no dashboard-readable record
for the static viewer to read — that publisher is still owed).
Not proven here: artifact links from live job hashes (jobs.py
does not yet carry artifacts on the hash — OS-094 still owed)
or on a booted image (no test image in repo) — integration-day
work (INT-028).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(REPO, "crew-board.html")

sys.path.insert(0, REPO)
from mos import artifact_store  # noqa: E402

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
out.withArtifacts = cardHTML("42", { title: "Build it", status: "done",
  created_at: 1700000000, artifacts: [
    { path: "jobs/42/report.md", reference: "artifact:42/report.md@v2",
      version: 2, sha256: "aa" },
    { path: "jobs/42/notes/out.txt", reference: "artifact:42/notes/out.txt@v1",
      version: 1, sha256: "bb" }] });
out.liveAttached = cardHTML("42", { title: "Live job", status: "done",
  created_at: 1700000000, artifacts: __LIVE__ });
out.oldJob = cardHTML("9", { title: "Old job", status: "open",
  created_at: 1700000000 });
out.jsonString = cardHTML("10", { title: "JSON job", status: "done",
  created_at: 1700000000, artifacts: JSON.stringify([
    { path: "jobs/10/plan.md", reference: "artifact:10/plan.md@v1",
      version: 1, sha256: "cc" }]) });
out.badPaths = cardHTML("11", { title: "Bad paths", status: "done",
  created_at: 1700000000, artifacts: [
    { path: "../escape.txt", reference: "artifact:11/escape.txt@v1",
      version: 1, sha256: "dd" },
    { path: "/abs.txt", reference: "artifact:11/abs.txt@v1",
      version: 1, sha256: "ee" },
    { path: "jobs/11/ok.txt", reference: "artifact:11/ok.txt@v1",
      version: 1, sha256: "ff" },
    { reference: "artifact:11/nopath@v1", version: 1, sha256: "gg" }] });
out.escaped = cardHTML("12", { title: "XSS", status: "done",
  created_at: 1700000000, artifacts: [
    { path: "jobs/12/<b>.txt", reference: "artifact:12/<b>.txt@v1",
      version: 1, sha256: "hh" }] });
out.detailBoth = detailHTML("42", { title: "Build it", status: "done",
  artifacts: [
    { path: "jobs/42/report.md", reference: "artifact:42/report.md@v2",
      version: 2, sha256: "aa" }] }, "(spec)");
out.detailOld = detailHTML("9", { title: "Old job", status: "open" },
  "(spec)");
console.log(JSON.stringify(out));
"""


def _script():
    with open(HTML, encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    assert m, "no script block in crew-board.html"
    return m.group(1)


def _live_artifacts():
    """Real attach() output: two deposits of one artifact -> v2."""
    with tempfile.TemporaryDirectory() as root:
        artifact_store.deposit(root, "42", "report.md", "v1 bytes",
                               author="rowan")
        artifact_store.deposit(root, "42", "report.md", "v2 bytes",
                               author="rowan")
        return artifact_store.attach(root, "42", {"title": "Live job"})


def _run_node():
    script = _script()
    prelude = NODE_DRIVER.split("const out = {};")[0]
    driver = NODE_DRIVER.split("const out = {};")[1]
    driver = driver.replace("__LIVE__",
                            json.dumps(_live_artifacts()["artifacts"]))
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


class TestCrewboardOs084Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = _run_node()

    def test_card_links_store_paths(self):
        card = self.out["withArtifacts"]
        self.assertIn('href="jobs/42/report.md"', card)
        self.assertIn('title="artifact:42/report.md@v2"', card)
        self.assertIn("report.md v2", card)
        self.assertIn('href="jobs/42/notes/out.txt"', card)
        self.assertIn("out.txt v1", card)

    def test_live_attach_shape_renders(self):
        card = self.out["liveAttached"]
        self.assertIn('href="jobs/42/report.md"', card)
        self.assertIn('title="artifact:42/report.md@v2"', card)
        self.assertIn("report.md v2", card)

    def test_old_job_card_unchanged(self):
        card = self.out["oldJob"]
        self.assertNotIn("artifacts:", card)
        self.assertNotIn("class=\"artifact\"", card)

    def test_json_string_field_parses(self):
        card = self.out["jsonString"]
        self.assertIn('href="jobs/10/plan.md"', card)
        self.assertIn("plan.md v1", card)

    def test_bad_paths_dropped(self):
        card = self.out["badPaths"]
        self.assertNotIn("escape.txt", card)
        self.assertNotIn("abs.txt", card)
        self.assertIn('href="jobs/11/ok.txt"', card)
        self.assertIn("ok.txt v1", card)

    def test_paths_escaped(self):
        card = self.out["escaped"]
        self.assertIn("jobs/12/&lt;b&gt;.txt", card)
        self.assertNotIn("<b>", card)

    def test_detail_lists_artifacts(self):
        detail = self.out["detailBoth"]
        self.assertIn(">artifacts<", detail)
        self.assertIn('href="jobs/42/report.md"', detail)
        self.assertIn("report.md v2", detail)

    def test_detail_old_job_has_no_row(self):
        detail = self.out["detailOld"]
        self.assertNotIn(">artifacts<", detail)


if __name__ == "__main__":
    unittest.main()
