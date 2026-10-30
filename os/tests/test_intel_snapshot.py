"""tests/test_intel_snapshot.py — intel/ingest.py snapshot (FND-014).

Snapshot is read-only: it returns {room, messages, jobs, presence,
caps} assembled from the real bus list, the real jobs queue, the
real presence keys, and the real capability registry — all on the
fake Redis surface, no network. Nothing here invents state: every
section is seeded first through the repo's own functions, and the
empty-room case returns four empty sections, not fabricated data.
"""

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
import relay_common as rc  # noqa: E402
from intel import ingest  # noqa: E402
from mos import capabilities  # noqa: E402


class SnapshotTest(RelayTestCase):
    def _seed(self):
        for line in ("pax: hello", "milo: working on it"):
            self.fake.bus_push(line, key="muse-bus:room:build")
        self.run_cli(jobs.main, [
            "post", "--title", "Add endpoint", "--spec", "build it",
            "--files", "src/app.py", "--max-attempts", "3"])
        self.run_cli(jobs.main, [
            "post", "--title", "Write tests", "--spec", "test it",
            "--deps", "1"])
        self.run_cli(jobs.main, ["claim", "1"])
        rc.presence_beat()
        capabilities.register("milo", ["python", "testing"])

    def test_snapshot_has_all_four_sections(self):
        self._seed()
        snap = ingest.snapshot("build")
        self.assertEqual(snap["room"], "build")
        self.assertEqual(snap["messages"],
                         ["pax: hello", "milo: working on it"])
        self.assertEqual(len(snap["jobs"]), 2)
        by_id = {j["id"]: j for j in snap["jobs"]}
        self.assertEqual(by_id["1"]["title"], "Add endpoint")
        self.assertEqual(by_id["1"]["status"], "claimed")
        self.assertEqual(by_id["1"]["claim"], "tester")
        self.assertEqual(by_id["1"]["files"], "src/app.py")
        self.assertEqual(by_id["1"]["attempts"], 0)
        self.assertEqual(by_id["2"]["status"], "open")
        self.assertEqual(by_id["2"]["deps"], "1")
        self.assertEqual(by_id["2"]["claim"], None)
        self.assertIn("tester", snap["presence"])
        self.assertIn("milo", snap["caps"])
        self.assertIn("python", snap["caps"]["milo"]["caps"])

    def test_snapshot_matches_list_json_shape(self):
        # Dashboard and watchdog consume list --json; snapshot jobs
        # must carry exactly the same fields so the two never drift.
        self._seed()
        snap = ingest.snapshot("build")
        expected = {"id", "title", "status", "claim", "files", "deps",
                    "attempts", "lease_until", "last_progress_at"}
        for row in snap["jobs"]:
            self.assertEqual(set(row), expected)

    def test_snapshot_is_room_scoped_for_messages(self):
        self.fake.bus_push("pax: main room", key="muse-bus")
        self.fake.bus_push("pax: build room",
                           key="muse-bus:room:build")
        snap = ingest.snapshot("build")
        self.assertEqual(snap["messages"], ["pax: build room"])

    def test_empty_room_returns_empty_sections(self):
        snap = ingest.snapshot("quiet")
        self.assertEqual(snap["room"], "quiet")
        self.assertEqual(snap["messages"], [])
        self.assertEqual(snap["jobs"], [])
        self.assertEqual(snap["presence"], [])
        self.assertEqual(snap["caps"], {})

    def test_snapshot_writes_nothing(self):
        self._seed()
        before = (dict(self.fake.strings), dict(self.fake.hashes),
                  dict(self.fake.sets), dict(self.fake.lists),
                  dict(self.fake.zsets))
        ingest.snapshot("build")
        after = (dict(self.fake.strings), dict(self.fake.hashes),
                 dict(self.fake.sets), dict(self.fake.lists),
                 dict(self.fake.zsets))
        self.assertEqual(before, after)


if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
