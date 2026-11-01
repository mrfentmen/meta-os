#!/usr/bin/env python3
"""DSH-020 performance pass: no new panel timers, job reads capped.

Acceptance: the intel panels reuse the core 2s poll cycle (no
setInterval/setTimeout anywhere in the intel module) and the job
read is bounded — ZRANGE over the newest JOB_READ_CAP ids, never
the whole index. The index is a created_at zset (jobs.py), so the
tail holds every live job in any crew this viewer serves, and one
poll cycle costs at most 1 ZRANGE + JOB_READ_CAP HGETALLs.

The node driver stubs U.api with a 250-id index and emulates
ZRANGE range semantics, so the harness proves the requested range
— not just the constant — is what bounds the hash fetches.
"""
import json
import os
import re
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")
SPEC = os.path.join(REPO, "docs", "DASHBOARD_SPEC.md")

NODE_DRIVER = r"""
const fs = require("fs");
const assert = require("assert");
const bodies = {};
const calls = { zrange: [], hgetall: 0 };
const IDS = [];
for (var i = 1; i <= 250; i++) IDS.push(String(i));
global.window = {
  busUtil: {
    panel: (id) => (bodies[id] || (bodies[id] = { innerHTML: "" })),
    esc: (s) => String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;"),
    myNick: () => "rowan",
    api: async (path) => {
      if (path.indexOf("/zrange/") === 0) {
        calls.zrange.push(path);
        // Emulate ZRANGE range semantics over the 250-id index.
        var parts = path.split("/");
        var start = parseInt(parts[parts.length - 2], 10);
        var stop = parseInt(parts[parts.length - 1], 10);
        var n = IDS.length;
        var s = start < 0 ? n + start : start;
        var e = stop < 0 ? n + stop + 1 : stop + 1;
        return { result: IDS.slice(s, e) };
      }
      if (path.indexOf("/hgetall/") === 0) {
        calls.hgetall++;
        return { result: ["title", "T", "status", "claimed",
                          "claim", "rowan"] };
      }
      throw new Error("unexpected api path " + path);
    },
  },
  busHooks: { connect: [], poll: [] },
};
global.document = { getElementById: () => null, createElement: () => ({}) };
eval(fs.readFileSync(__MODULE_PATH__, "utf8"));
const ip = global.window.__busTest.intelPanel;
assert(ip, "intelPanel test hook missing");
assert(ip.collectJobsForTest, "collectJobsForTest hook missing");
(async () => {
  await ip.collectJobsForTest();
  const out = {};
  out.zrangeUrls = calls.zrange;
  out.hgetallCalls = calls.hgetall;
  out.jobs = ip.snapshot().jobs;
  out.jobRows = ip.snapshot().jobRows.length;
  console.log(JSON.stringify(out));
})();
"""


def _intel_module(html):
    parts = html.split("// === feature: intelPanel ===")
    assert len(parts) == 3, (
        "bus.html must carry exactly two intelPanel markers, found %d"
        % len(parts))
    return parts[1]


def _run_node(module):
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        mod_path = f.name
        f.write(module)
    driver = NODE_DRIVER.replace("__MODULE_PATH__",
                                 json.dumps(mod_path))
    with tempfile.NamedTemporaryFile("w", suffix=".js",
                                     delete=False) as f:
        drv_path = f.name
        f.write(driver)
    try:
        r = subprocess.run(["node", drv_path], capture_output=True,
                           text=True, timeout=60)
    finally:
        os.unlink(mod_path)
        os.unlink(drv_path)
    assert r.returncode == 0, "node failed: %s" % r.stderr
    return json.loads(r.stdout)


class DashboardPerformanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(BUS, encoding="utf-8") as f:
            cls.bus = f.read()
        with open(INDEX, encoding="utf-8") as f:
            cls.index = f.read()
        cls.intel = _intel_module(cls.bus)
        cls.js = _run_node(cls.intel)

    def test_bus_and_index_identical(self):
        # DSH-026 invariant: the performance checks on bus.html cover
        # index.html only if the two files are the same file.
        self.assertEqual(self.bus, self.index,
                         "bus.html and index.html differ")

    def test_no_new_timers_in_intel_module(self):
        # DSH-020, first half: panels ride the core 2s poll. The core
        # setInterval lives outside the intel module; any timer
        # inside it would be a panel running its own clock.
        self.assertNotIn("setInterval", self.intel,
                         "intel module must not set its own interval")
        self.assertNotIn("setTimeout", self.intel,
                         "intel module must not set its own timeout")

    def test_job_index_read_is_capped(self):
        # DSH-020, second half: no unbounded index read remains.
        self.assertNotIn("/0/-1", self.intel,
                          "unbounded ZRANGE 0/-1 must not survive")
        m = re.search(r"JOB_READ_CAP\s*=\s*(\d+)", self.intel)
        self.assertIsNotNone(m, "JOB_READ_CAP constant missing")
        self.assertEqual(int(m.group(1)), 200)
        self.assertIn('"/-" + JOB_READ_CAP + "/-1"', self.intel,
                      "collectJobs must request the capped tail range")

    def test_capped_range_bounds_hash_fetches(self):
        # A 250-id index under the requested range yields exactly
        # the newest 200 jobs and 200 HGETALLs — no more.
        self.assertEqual(len(self.js["zrangeUrls"]), 1)
        self.assertTrue(self.js["zrangeUrls"][0].endswith("/-200/-1"),
                        self.js["zrangeUrls"][0])
        self.assertEqual(self.js["hgetallCalls"], 200)
        self.assertEqual(self.js["jobRows"], 200)
        self.assertEqual(self.js["jobs"], 200)

    def test_spec_documents_the_cap(self):
        with open(SPEC, encoding="utf-8") as f:
            spec = f.read()
        self.assertIn("newest 200", spec,
                      "spec must state the 200-job read cap")


if __name__ == "__main__":
    unittest.main()
