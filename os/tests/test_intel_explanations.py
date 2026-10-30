"""tests/test_intel_explanations.py — WDG-011 template tests (Milo).

Every detector's fixture alert must carry a filled explanation
and suggested fix rendered from intel/explanations.py — not a
second copy of the wording inline in the detector. These tests
prove that by re-rendering the template with the fixture's
subjects and comparing it to what the detector actually
produced: if a detector drifts back to its own string, the
comparison fails. Pure-function tests: no Redis, no bus.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import explanations  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

NOW = 100000

# Sample fields for every template key: render must fill them
# all with no placeholder braces left behind.
SAMPLES = {
    "presence-stall": {"nick": "pax", "job": "7",
                       "stall_minutes": 10, "age_minutes": 20},
    "progress-stall": {"nick": "pax", "job": "7",
                       "age_minutes": 20, "window_minutes": 10},
    "lease-risk": {"job": "7", "nick": "pax",
                   "minutes_to_expiry": 2, "quiet_minutes": 2},
    "dead-dep": {"job": "1", "dep": "2", "dep_status": "blocked",
                 "blocking_note": " Blocking reason: waiting on review"},
    "missing-dep": {"job": "1", "dep": "9"},
    "file-collision": {"job": "1", "other_job": "2",
                       "shared_path": "intel/store.py"},
    "file-collision-done": {"job": "1", "other_job": "2",
                            "shared_path": "intel/store.py",
                            "branch": "worker/1"},
    "attempt-warning": {"job": "7", "attempts": 2, "max_attempts": 3},
    "attempt-exhaustion": {"job": "7", "attempts": 3,
                           "max_attempts": 3},
    "silent-room": {"claimed_ids": "1, 2", "age_minutes": 90,
                    "window_minutes": 60},
}


class TemplateRenderTest(unittest.TestCase):
    def test_every_template_fills_completely(self):
        for key, fields in SAMPLES.items():
            explanation, fix = explanations.render(key, **fields)
            self.assertTrue(explanation, key)
            self.assertTrue(fix, key)
            self.assertNotIn("{", explanation, key)
            self.assertNotIn("}", explanation, key)
            self.assertNotIn("{", fix, key)
            self.assertNotIn("}", fix, key)

    def test_template_text_is_plain_english_one_liner(self):
        # One line each: no newlines smuggled into a record, and
        # the silent-room template never reads as an ALERT.
        for key, fields in SAMPLES.items():
            explanation, fix = explanations.render(key, **fields)
            self.assertNotIn("\n", explanation, key)
            self.assertNotIn("\n", fix, key)
        self.assertNotIn("ALERT", SAMPLES and explanations.render(
            "silent-room", **SAMPLES["silent-room"])[0])

    def test_unknown_template_key_raises(self):
        with self.assertRaises(ValueError):
            explanations.render("no-such-detector", job="1")

    def test_missing_placeholder_raises_not_half_filled(self):
        with self.assertRaises(KeyError):
            explanations.render("presence-stall", nick="pax")


class DetectorUsesTemplateTest(unittest.TestCase):
    def test_presence_stall_alert_matches_template(self):
        snap = {"caps": {"pax": 1}, "presence": [],
                "jobs": [{"id": "7", "status": "claimed",
                          "claim": "pax", "claimed_at": NOW - 20 * 60}]}
        got = watchdog.detect_presence_stall(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, fix = explanations.render(
            "presence-stall", nick="pax", job="7",
            stall_minutes=thresholds.STALL_MINUTES, age_minutes=20)
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)

    def test_progress_stall_alert_matches_template(self):
        snap = {"caps": {"pax": 1}, "presence": ["pax"],
                "jobs": [{"id": "7", "status": "claimed",
                          "claim": "pax", "claimed_at": NOW - 20 * 60}]}
        got = watchdog.detect_progress_stall(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, fix = explanations.render(
            "progress-stall", nick="pax", job="7", age_minutes=20,
            window_minutes=thresholds.PROGRESS_STALL_MINUTES)
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)

    def test_lease_risk_alert_matches_template(self):
        snap = {"jobs": [{"id": "7", "status": "claimed",
                          "claim": "pax",
                          "lease_until": NOW + 2 * 60,
                          "lease": 1800}]}
        got = watchdog.detect_lease_risk(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, fix = explanations.render(
            "lease-risk", job="7", nick="pax", minutes_to_expiry=2,
            quiet_minutes=thresholds.LEASE_RISK_QUIET_MINUTES)
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)

    def test_dead_dep_alert_carries_note_verbatim(self):
        snap = {"jobs": [
            {"id": "1", "status": "open", "deps": "2"},
            {"id": "2", "status": "blocked",
             "note": "waiting on review"}]}
        got = watchdog.detect_dead_dep(snap, NOW)
        self.assertEqual(len(got), 1)
        self.assertIn("waiting on review", got[0]["explanation"])
        exp, fix = explanations.render(
            "dead-dep", job="1", dep="2", dep_status="blocked",
            blocking_note=" Blocking reason: waiting on review")
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)

    def test_dead_dep_without_note_matches_template(self):
        snap = {"jobs": [
            {"id": "1", "status": "open", "deps": "2"},
            {"id": "2", "status": "failed-final"}]}
        got = watchdog.detect_dead_dep(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, _ = explanations.render(
            "dead-dep", job="1", dep="2", dep_status="failed-final",
            blocking_note="")
        self.assertEqual(got[0]["explanation"], exp)

    def test_missing_dep_alert_matches_template(self):
        snap = {"jobs": [{"id": "1", "status": "open", "deps": "9"}]}
        got = watchdog.detect_missing_dep(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, fix = explanations.render("missing-dep", job="1", dep="9")
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)

    def test_collision_alerts_match_both_templates(self):
        snap = {"jobs": [
            {"id": "1", "status": "claimed", "claim": "pax",
             "files": "intel/store.py"},
            {"id": "2", "status": "claimed", "claim": "hana",
             "files": "intel/store.py"},
            {"id": "3", "status": "done", "branch": "worker/3",
             "files": "intel/store.py"}]}
        got = watchdog.detect_file_collision(snap, NOW)
        kinds = [(a["job"], a["other_job"]) for a in got]
        self.assertIn(("1", "2"), kinds)
        self.assertIn(("1", "3"), kinds)
        claimed = [a for a in got if a["other_job"] == "2"][0]
        exp, fix = explanations.render(
            "file-collision", job="1", other_job="2",
            shared_path="intel/store.py")
        self.assertEqual(claimed["explanation"], exp)
        self.assertEqual(claimed["suggested_fix"], fix)
        done = [a for a in got if a["other_job"] == "3"][0]
        exp, _ = explanations.render(
            "file-collision-done", job="1", other_job="3",
            shared_path="intel/store.py", branch="worker/3")
        self.assertEqual(done["explanation"], exp)

    def test_attempt_alerts_match_templates(self):
        warn = watchdog.detect_attempt_exhaustion(
            {"jobs": [{"id": "7", "status": "claimed",
                       "attempts": 2, "max_attempts": 3}]}, NOW)
        self.assertEqual(len(warn), 1)
        exp, fix = explanations.render(
            "attempt-warning", job="7", attempts=2, max_attempts=3)
        self.assertEqual(warn[0]["explanation"], exp)
        self.assertEqual(warn[0]["suggested_fix"], fix)
        self.assertIn("one attempt", exp)
        spent = watchdog.detect_attempt_exhaustion(
            {"jobs": [{"id": "7", "status": "failed-final",
                       "attempts": 3, "max_attempts": 3}]}, NOW)
        self.assertEqual(len(spent), 1)
        exp, fix = explanations.render(
            "attempt-exhaustion", job="7", attempts=3, max_attempts=3)
        self.assertEqual(spent[0]["explanation"], exp)
        self.assertEqual(spent[0]["suggested_fix"], fix)
        self.assertIn("failed-final", exp)

    def test_silent_room_record_matches_template(self):
        snap = {"room": "build", "jobs": [
            {"id": "1", "status": "claimed"},
            {"id": "2", "status": "claimed"}],
            "messages": [{"ts": NOW - 90 * 60}]}
        got = watchdog.detect_silent_room(snap, NOW)
        self.assertEqual(len(got), 1)
        exp, fix = explanations.render(
            "silent-room", claimed_ids="1, 2", age_minutes=90,
            window_minutes=thresholds.SILENT_ROOM_MINUTES)
        self.assertEqual(got[0]["explanation"], exp)
        self.assertEqual(got[0]["suggested_fix"], fix)
        self.assertNotIn("ALERT", exp)


if __name__ == "__main__":
    unittest.main()
