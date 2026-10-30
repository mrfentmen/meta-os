"""tests/test_intel_capability.py -- OS-081: capability refusal.

OS-081 puts a grant gate in front of every process action:
a process that attempts an action outside its grant is
refused, the refusal is written as an alert record with a
plain-English explanation, and the watchdog surfaces it
like any other alert. These tests pin the decision, the
tick, the alert record, and the no-push half on fixtures:

- An inside-grant bus post, network reach, and file write
  are allowed and journal nothing.
- A bus post, spend, and network reach with the flag off
  are refused, reason capability not granted.
- A file write outside the grant paths is refused, reason
  write path outside grant, naming write:<path>.
- A dot-dot write escaping the grant is refused, and a
  segment-prefix trick (crew/milo2) never matches
  crew/milo/.
- A write with no path, a process with no grant, and an
  unknown action are all refused, never silently allowed.
- A tick journals one refusal per refused attempt and
  nothing else, and a second tick journals nothing new.
- A tick never mutates its inputs.
- The refusal alert names identity, action, and missing
  capability, and builds a valid open alert record.
- Brief lines render the refusal.
- The capability module carries no push path.
- The drill script exists and passes; the eval note
  names OS-081.
- None of the new OS-081 files carries an em dash
  (the new-doc rule).

No bus post, no live Redis, no network, no systemd:
pure fixture calls plus file reads. Grants here are
plain dicts in the OS-080 shape, supplied by the caller;
no capability file is read, because OS-080 has not
landed yet.
"""

import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import capability  # noqa: E402
from intel import store  # noqa: E402

NOW = 100000
GRANTS = {
    "milo": {"identity": "milo", "bus_post": False,
             "spend": False, "network": True,
             "write_paths": ["crew/milo/"]},
    "pax": {"identity": "pax", "bus_post": True,
            "spend": True, "network": True,
            "write_paths": ["crew/pax/", "plan/"]},
}
NEW_FILES = [
    "intel/capability.py",
    "intel/drills/capability_refusal.py",
    "intel/evals/capability_refusal.md",
    "intel/evals/capability_refusal.log",
    "tests/test_intel_capability.py",
]


class DecisionTest(unittest.TestCase):
    def test_allowed_actions_journal_nothing(self):
        for identity, action, subject in [
                ("pax", "bus_post", None),
                ("milo", "network", None),
                ("pax", "write_file", "plan/lanes/PAX.md")]:
            decision = capability.check_action(
                GRANTS[identity], action, subject)
            self.assertTrue(decision["allowed"])
            self.assertIsNone(decision["missing_capability"])
            self.assertIsNone(capability.refusal_alert(decision))

    def test_flag_off_refused(self):
        for identity, action in [("milo", "bus_post"),
                                 ("milo", "spend")]:
            decision = capability.check_action(GRANTS[identity],
                                               action)
            self.assertFalse(decision["allowed"])
            self.assertEqual(decision["missing_capability"],
                             action)
            self.assertEqual(decision["reason"],
                             "capability not granted")

    def test_write_outside_grant_refused(self):
        decision = capability.check_action(
            GRANTS["pax"], "write_file", "crew/milo/notes.md")
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["missing_capability"],
                         "write:crew/milo/notes.md")
        self.assertEqual(decision["reason"],
                         "write path outside grant")

    def test_dotdot_escape_and_prefix_trick_refused(self):
        escaped = capability.check_action(
            GRANTS["milo"], "write_file", "crew/milo/../pax/x.md")
        self.assertFalse(escaped["allowed"])
        self.assertEqual(escaped["missing_capability"],
                         "write:crew/pax/x.md")
        trick = capability.check_action(
            GRANTS["milo"], "write_file", "crew/milo2/x.md")
        self.assertFalse(trick["allowed"])

    def test_no_path_no_grant_unknown_action_refused(self):
        no_path = capability.check_action(GRANTS["milo"],
                                          "write_file", None)
        self.assertEqual(no_path["reason"], "no file path given")
        no_grant = capability.check_action(None, "bus_post",
                                           None, identity="ghost")
        self.assertEqual(no_grant["reason"],
                         "no capability grant on file")
        self.assertEqual(no_grant["identity"], "ghost")
        unknown = capability.check_action(GRANTS["milo"],
                                          "teleport")
        self.assertEqual(unknown["reason"], "unknown action")
        self.assertIsNone(capability.check_action(
            GRANTS["milo"], ""))


class TickTest(unittest.TestCase):
    def test_tick_journals_refusals_only_once(self):
        attempts = [
            {"identity": "milo", "action": "bus_post",
             "subject": None},
            {"identity": "milo", "action": "spend",
             "subject": None},
            {"identity": "pax", "action": "bus_post",
             "subject": None},
            {"identity": "milo", "action": "bus_post",
             "subject": None},
        ]
        journal = []
        first = capability.capability_tick(attempts, GRANTS,
                                           journal, NOW)
        journal.extend(first)
        second = capability.capability_tick(attempts, GRANTS,
                                            journal, NOW + 60)
        self.assertEqual(len(first), 2)
        self.assertEqual(second, [])

    def test_tick_never_mutates_inputs(self):
        attempts = [{"identity": "milo", "action": "bus_post",
                     "subject": None}]
        snapshot_attempts = copy.deepcopy(attempts)
        snapshot_grants = copy.deepcopy(GRANTS)
        capability.capability_tick(attempts, GRANTS, [], NOW)
        self.assertEqual(attempts, snapshot_attempts)
        self.assertEqual(GRANTS, snapshot_grants)

    def test_tick_skips_malformed_attempts(self):
        records = capability.capability_tick(
            ["not-a-dict", {"identity": "milo", "action": ""}],
            GRANTS, [], NOW)
        self.assertEqual(records, [])


class RecordTest(unittest.TestCase):
    def test_alert_names_identity_action_capability(self):
        decision = capability.check_action(GRANTS["milo"],
                                          "bus_post")
        alert = capability.refusal_alert(decision, now=NOW)
        self.assertEqual(alert["kind"], "capability-refusal")
        self.assertEqual(alert["severity"], "warning")
        for name in ("milo", "bus_post"):
            self.assertIn(name, alert["explanation"])
        record = store.build_alert_record(alert,
                                          room="fixture-room",
                                          now=NOW)
        self.assertEqual(record["status"], "open")
        self.assertEqual(record["id"], alert["dedupe_key"])
        note = capability.refusal_note(decision)
        self.assertIn("milo", note)
        self.assertIn("bus_post", note)

    def test_brief_lines_render_refusal(self):
        records = capability.capability_tick(
            [{"identity": "milo", "action": "spend",
              "subject": None}], GRANTS, [], NOW)
        lines = capability.brief_lines(records)
        self.assertEqual(len(lines), 1)
        self.assertIn("milo", lines[0])
        self.assertIn("spend", lines[0])


class HygieneTest(unittest.TestCase):
    def test_no_push_path(self):
        with open("intel/capability.py") as handle:
            text = handle.read()
        for word in ("push.py", "post_to_bus", "redis",
                     "socket"):
            self.assertNotIn(word, text)

    def test_drill_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/capability_refusal.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("5/5 phases PASS", result.stdout)

    def test_eval_note_names_task(self):
        with open("intel/evals/capability_refusal.md") as handle:
            text = handle.read()
        self.assertIn("OS-081", text)

    def test_no_em_dash_in_new_files(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
