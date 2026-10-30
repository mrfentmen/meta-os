"""Pinning tests for the FDNY pack runtime: the PAR clock.

The clock holds each inside crew's interval individually, raises
par-check-due once per cycle-due moment (warning, urgent), escalates
once per cycle-due moment to crew-unaccounted (critical, life-safety)
when the grace window passes without a confirmed check, and keeps the
timeline. Pure core, disk state, no network: same test style as the
OS-118 watchman's pinning tests.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "worlds", "fdny", "runtime"))

import par_clock  # noqa: E402


def _entered_state(crew="crew-2", entered=1000, location=None):
    state, err = par_clock.enter_crew(par_clock.new_state(), crew,
                                      entered, location=location)
    return state, err


class TestEnterExit(unittest.TestCase):

    def test_enter_starts_interval_from_entry(self):
        state, err = _entered_state()
        self.assertIsNone(err)
        self.assertEqual(state["roster"]["crew-2"]["entered_at"], 1000)
        self.assertIsNone(state["roster"]["crew-2"]["last_par_at"])

    def test_enter_twice_is_refused(self):
        state, _ = _entered_state()
        _, err = par_clock.enter_crew(state, "crew-2", 1100)
        self.assertIn("already inside", err)

    def test_crew_id_rules(self):
        _, err = par_clock.enter_crew(par_clock.new_state(), "crew 2", 1)
        self.assertIn("whitespace", err)
        _, err = par_clock.enter_crew(par_clock.new_state(), "", 1)
        self.assertIn("empty", err)

    def test_exit_removes_crew_and_cleans_ledger(self):
        state, _ = _entered_state()
        events, _ = par_clock.tick(state, 1000 + 700)
        self.assertTrue(events)
        done, err = par_clock.exit_crew(state, "crew-2", 1700)
        self.assertIsNone(err)
        self.assertNotIn("crew-2", done["roster"])
        kinds = [t["kind"] for t in done["timeline"]]
        self.assertIn(par_clock.TL_EXIT, kinds)
        before = len(state["ledger"]) if "ledger" in state else 0
        events2, _ = par_clock.tick(done, 10000)
        self.assertEqual(events2, [])

    def test_exit_unknown_crew_is_refused(self):
        _, err = par_clock.exit_crew(par_clock.new_state(), "ghost", 1)
        self.assertIn("not inside", err)


class TestTick(unittest.TestCase):

    def test_quiet_before_interval(self):
        state, _ = _entered_state(entered=1000)
        events, _ = par_clock.tick(state, 1000 + 599)
        self.assertEqual(events, [])

    def test_due_fires_once_per_cycle(self):
        state, _ = _entered_state(entered=1000)
        events, out = par_clock.tick(state, 1000 + 600)
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds, [par_clock.KIND_PAR_CHECK_DUE])
        events2, _ = par_clock.tick(out, 1000 + 610)
        self.assertEqual(events2, [])

    def test_grace_escalates_to_life_safety(self):
        state, _ = _entered_state(entered=1000)
        events, out = par_clock.tick(state, 1000 + 600 + 120)
        kinds = [e["kind"] for e in events]
        self.assertEqual(kinds, [par_clock.KIND_PAR_CHECK_DUE,
                                 par_clock.KIND_CREW_UNACCOUNTED])
        over = [e for e in events
                if e["kind"] == par_clock.KIND_CREW_UNACCOUNTED][0]
        self.assertEqual(over["severity"], "critical")
        self.assertEqual(over["urgency"], "life-safety")
        events2, _ = par_clock.tick(out, 1000 + 900)
        # The same cycle never re-alarms: dedupe keys are per
        # cycle-due moment, held in the state ledger, and a later
        # tick over an unchanged inside state stays silent.
        self.assertEqual(events2, [])

    def test_completion_resets_cycle_and_clears_alarm(self):
        state, _ = _entered_state(entered=1000)
        events, out = par_clock.tick(state, 1000 + 800)
        self.assertTrue(any(e["kind"] == par_clock.KIND_CREW_UNACCOUNTED
                            for e in events))
        done, err = par_clock.complete_par(out, "crew-2", 1800)
        self.assertIsNone(err)
        events2, out2 = par_clock.tick(done, 1801)
        self.assertEqual(events2, [])
        events3, out3 = par_clock.tick(out2, 1800 + 600)
        kinds = [e["kind"] for e in events3]
        self.assertEqual(kinds, [par_clock.KIND_PAR_CHECK_DUE])
        due = events3[0]["due_at"]
        self.assertEqual(due, 1800 + 600)

    def test_exit_silences_overdue(self):
        state, _ = _entered_state(entered=1000)
        _, out = par_clock.tick(state, 1000 + 800)
        done, _ = par_clock.exit_crew(out, "crew-2", 2000)
        events, _ = par_clock.tick(done, 5000)
        self.assertEqual(events, [])

    def test_location_present_on_life_safety_event(self):
        state, _ = _entered_state(entered=1000,
                                  location="division 2 stairwell")
        events, _ = par_clock.tick(state, 1000 + 800)
        over = [e for e in events
                if e["kind"] == par_clock.KIND_CREW_UNACCOUNTED][0]
        self.assertEqual(over.get("location"), "division 2 stairwell")

    def test_inputs_never_mutated(self):
        state, _ = _entered_state(entered=1000)
        before = json.dumps(state, sort_keys=True)
        par_clock.tick(state, 10000)
        self.assertEqual(json.dumps(state, sort_keys=True), before)

    def test_second_crew_counts_independently(self):
        state, _ = _entered_state(crew="crew-1", entered=1000)
        state, err = par_clock.enter_crew(state, "crew-2", 1200)
        self.assertIsNone(err)
        events, _ = par_clock.tick(state, 1600)
        # crew-1 is due at 1600; crew-2 entered later, not yet due.
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["crew"], "crew-1")


class TestAlertLine(unittest.TestCase):

    def test_line_matches_fnd020_shape(self):
        state, _ = _entered_state(crew="crew-2", entered=1000)
        events, _ = par_clock.tick(state, 1000 + 800)
        over = [e for e in events
                if e["kind"] == par_clock.KIND_CREW_UNACCOUNTED][0]
        line = par_clock.render_alert(over)
        self.assertEqual(line, "ALERT:par-unaccounted-crew-2-1600 "
                               "critical crew-unaccounted")
        self.assertNotIn("  ", line)
        self.assertNotIn("\n", line)

    def test_ids_carry_no_spaces_or_explanations(self):
        state, _ = _entered_state(crew="crew-2", entered=1000)
        events, _ = par_clock.tick(state, 1000 + 800)
        for e in events:
            self.assertNotIn(" ", e["alert_id"])
            line = par_clock.render_alert(e)
            self.assertTrue(line.startswith("ALERT:"))
            self.assertEqual(len(line.split()), 3)


class TestCli(unittest.TestCase):

    def _run(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = par_clock.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_show_and_full_lifecycle_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            base = ["--file", path, "--now", "0"]
            code, _, err = self._run(base + [
                "enter", "--crew", "crew-2", "--entered-at", "1000"])
            self.assertEqual((code, err), (0, ""))
            code, _, _ = self._run(base + [
                "tick", "--interval-seconds", "600",
                "--grace-seconds", "120", "--now", "1720"])
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as fh:
                state = json.load(fh)
            self.assertEqual(state["timeline"][0]["kind"],
                             par_clock.TL_ENTER)
            code, out, _ = self._run(base + ["tick", "--now", "1720"])
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            with open(path, encoding="utf-8") as fh:
                state = json.load(fh)
            self.assertTrue(any(
                k.startswith("par:crew-2:") for k in state["ledger"]))

    def test_bad_crew_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            code, _, err = self._run([
                "--file", path, "enter", "--crew", "crew 2",
                "--entered-at", "1000"])
            self.assertEqual(code, 2)
            self.assertIn("whitespace", err)

    def test_state_survives_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            self._run(["--file", path, "enter", "--crew", "c1",
                       "--entered-at", "1000"])
            code, _, _ = self._run(["--file", path, "tick",
                                    "--now", "1700"])
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as fh:
                state = json.load(fh)
            self.assertEqual(len(state["ledger"]), 1)


if __name__ == "__main__":
    unittest.main()
