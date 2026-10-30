"""intel/store.py key shapes: FND-029 watchdog state + dedupe keys.

FND-029 acceptance: key shapes written into intel/store.py's
docstring, and Milo and Pax both reference the same names in
code. Pax's FND-004 defined the layout (store.wd_key, the
docstring's wd:<nick> entry with last_seen / last_progress /
claimed_jobs); the second half of FND-029 — the alert dedupe
key shape — was only implicit in the detector code. These
tests pin both halves: the docstring names the wd hash
fields, wd_key builds the key Pax defined, and one tick per
detector family yields exactly the documented dedupe key.
Pure-function tests: no network, no Redis, no bus posts.
Fixtures mirror tests/test_intel_watchdog.py's own shapes.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import store as istore  # noqa: E402
from intel import watchdog  # noqa: E402


def _only_tick(snapshot, now=10000):
    got = watchdog.tick(snapshot, now=now)
    assert len(got) == 1, got
    return got[0]


class WdKeyTest(unittest.TestCase):
    def test_wd_key_shape_matches_pax_fnd004_layout(self):
        # Pax's FND-004 key, Milo's watchdog reference, same name.
        self.assertEqual(istore.wd_key("milo"),
                         "muse-bus:intel:wd:milo")
        self.assertEqual(istore.wd_key("pax"),
                         "muse-bus:intel:wd:pax")

    def test_docstring_names_the_wd_hash_fields(self):
        doc = istore.__doc__
        for field in ("last_seen", "last_progress", "claimed_jobs"):
            self.assertIn(field, doc,
                          f"wd hash field {field} must be documented")

    def test_docstring_names_every_detector_dedupe_shape(self):
        doc = istore.__doc__
        for shape in ("presence-stall:<nick>:<job>",
                      "progress-stall:<nick>:<job>",
                      "lease-risk:<nick>:<job>",
                      "dead-dep:<job>:<dep>",
                      "missing-dep:<job>:<dep>",
                      "file-collision:<job>:<job>:<path>",
                      "attempt-warning:<job>",
                      "attempt-exhaustion:<job>",
                      "silent-room[:<room>]",
                      "budget-warning:<lane>",
                      "system-failure:<unit>",
                      "worker-restart:<nick>:<job>"):
            self.assertIn(shape, doc,
                          f"dedupe shape {shape} must be documented")


class DedupeKeyTest(unittest.TestCase):
    def test_presence_stall_key(self):
        alert = _only_tick({
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        })
        self.assertEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["dedupe_key"], "presence-stall:pax:7")

    def test_progress_stall_key(self):
        alert = _only_tick({
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9000, "last_progress": 9340}],
            "presence": ["pax", "hana"],
            "caps": {"pax": {"caps": "build"}},
        })
        self.assertEqual(alert["kind"], "progress-stall")
        self.assertEqual(alert["dedupe_key"], "progress-stall:pax:7")

    def test_lease_risk_key(self):
        alert = _only_tick({
            "jobs": [{"id": "9", "title": "lease job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9900, "lease_until": 10240}],
            "presence": ["pax"],
            "caps": {"pax": {"caps": "build"}},
        })
        self.assertEqual(alert["kind"], "lease-risk")
        self.assertEqual(alert["dedupe_key"], "lease-risk:pax:9")

    def test_dead_dep_key(self):
        alert = _only_tick({
            "jobs": [{"id": "2", "title": "blocked job", "status": "open",
                      "deps": "1"},
                     {"id": "1", "title": "dep job", "status": "blocked",
                      "note": "waiting on vendor API key"}],
        })
        self.assertEqual(alert["kind"], "dead-dep")
        self.assertEqual(alert["dedupe_key"], "dead-dep:2:1")

    def test_missing_dep_key(self):
        alert = _only_tick({
            "jobs": [{"id": "2", "title": "dangling job", "status": "open",
                      "deps": "9"}],
        })
        self.assertEqual(alert["kind"], "missing-dep")
        self.assertEqual(alert["dedupe_key"], "missing-dep:2:9")

    def test_file_collision_key(self):
        alert = _only_tick({
            "jobs": [
                {"id": "1", "title": "job 1", "status": "claimed",
                 "claim": "pax", "claimed_at": 9990,
                 "files": "intel/watchdog.py, intel/store.py"},
                {"id": "2", "title": "job 2", "status": "claimed",
                 "claim": "rowan", "claimed_at": 9990,
                 "files": "intel/store.py, intel/brief.py"}],
            "presence": ["pax", "rowan"],
            "caps": {"pax": {"caps": "build"},
                     "rowan": {"caps": "build"}},
        })
        self.assertEqual(alert["kind"], "file-collision")
        self.assertEqual(alert["dedupe_key"],
                         "file-collision:1:2:intel/store.py")

    def test_attempt_warning_then_exhaustion_keys(self):
        def _job(attempts):
            return {"id": "7", "title": "flaky job", "status": "open",
                    "claim": "pax", "attempts": attempts,
                    "max_attempts": 3}

        alert = _only_tick({"jobs": [_job(2)]})
        self.assertEqual(alert["kind"], "attempt-warning")
        self.assertEqual(alert["dedupe_key"], "attempt-warning:7")
        alert = _only_tick({"jobs": [_job(3)]})
        self.assertEqual(alert["kind"], "attempt-exhaustion")
        self.assertEqual(alert["dedupe_key"], "attempt-exhaustion:7")

    def test_silent_room_key_without_room(self):
        alert = _only_tick({
            "jobs": [{"id": "1", "title": "claimed job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 1000}],
            "messages": [{"nick": "pax", "text": "starting",
                        "ts": 1000}],
        })
        self.assertEqual(alert["kind"], "silent-room")
        self.assertEqual(alert["dedupe_key"], "silent-room")

    def test_silent_room_key_with_room(self):
        alert = _only_tick({
            "jobs": [{"id": "1", "title": "claimed job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 1000}],
            "messages": [{"nick": "pax", "text": "starting",
                        "ts": 1000}],
            "room": "build",
        })
        self.assertEqual(alert["kind"], "silent-room")
        self.assertEqual(alert["dedupe_key"], "silent-room:build")

    def test_budget_warning_key(self):
        alert = _only_tick({
            "budgets": [{"lane": "milo", "spent": 80, "cap": 100}],
        })
        self.assertEqual(alert["kind"], "budget-warning")
        self.assertEqual(alert["dedupe_key"], "budget-warning:milo")


if __name__ == "__main__":
    unittest.main()
