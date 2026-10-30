"""tests/test_intel_watchman_watch.py -- OS-122: who watches the watchman.

OS-122 treats a dead watchman as a first-class failure:
crew-dark means the machine's agents are asleep and its
jobs are invisible to them. A revivable watchman earns
a restart and a recovery and no Dale contact; a
watchman killed beyond the restart's power earns
exactly one blocked push naming the machine; the
board's group for a dark machine reads watchman-dead
while it lasts. These tests pin the judgement, journal,
brief, board, and zero-send halves on fixtures:

- A killed watchman yields crew-dark plus a restart
  record in one tick, and no escalation when the
  restart succeeds.
- A revived watchman yields a recovered record on the
  next tick, and still no escalation.
- A watchman killed beyond repair yields exactly one
  escalation whose push validates and names the
  machine, and re-ticks stay silent.
- A machine that recovers and dies again earns a
  fresh crew-dark record and a fresh escalation.
- A stale bell reads dead at the thresholds window,
  and a fresh bell reads alive.
- An unknown machine yields no records, and the board
  line says unknown, never dead and never alive.
- Malformed snapshots and machine records yield no
  records and no crash.
- The tick never mutates its snapshot or journal.
- The brief lines name machine and outcome for every
  record kind, and other records render nothing.
- The board lines read dead, alive, and unknown for
  the matching states.
- The escalation payload is built, never sent: the
  module imports no socket, bus, or network module.
- The drill script exists and passes; the eval note
  names OS-122.
- None of the new OS-122 files carries an em dash
  (the new-doc rule).

No bus post, no live Redis, no network, no systemd:
the restart is simulated, the push is built only.
"""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import push as push_module  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchman_watch as ww  # noqa: E402

T0 = 100000
NEW_FILES = [
    "intel/watchman_watch.py",
    "intel/drills/watchman_watch.py",
    "intel/evals/watchman_watch.md",
    "intel/evals/watchman_watch.log",
    "tests/test_intel_watchman_watch.py",
]


def dead_machine(restart_ok):
    return {"watchman_alive": False, "last_bell": T0 - 600,
            "last_wake": T0 - 600, "restart_ok": restart_ok}


class TestWatchmanWatch(unittest.TestCase):
    def test_killed_watchman_flags_crew_dark_in_one_tick(self):
        snap = {"machines": {"milo-box": dead_machine(True)}}
        new = ww.watchman_watch_tick(snap, [], T0)
        self.assertEqual([r["kind"] for r in new],
                         ["crew-dark", "watchman-restart"])
        self.assertFalse(any("push" in r for r in new))

    def test_revival_yields_recovered_and_still_no_escalation(self):
        snap = {"machines": {"milo-box": dead_machine(True)}}
        journal = ww.watchman_watch_tick(snap, [], T0)
        snap["machines"]["milo-box"] = {
            "watchman_alive": True, "last_bell": T0,
            "last_wake": T0, "restart_ok": True}
        new = ww.watchman_watch_tick(snap, journal, T0 + 60)
        self.assertEqual([r["kind"] for r in new],
                         ["watchman-recovered"])
        self.assertFalse(any("push" in r for r in journal + new))

    def test_beyond_repair_yields_exactly_one_valid_escalation(self):
        snap = {"machines": {"rowan-box": dead_machine(False)}}
        journal = ww.watchman_watch_tick(snap, [], T0)
        self.assertEqual([r["kind"] for r in journal],
                         ["crew-dark", "watchman-restart",
                          "escalation"])
        escalation = journal[2]
        self.assertTrue(push_module.validate_push(
            escalation.get("push")))
        self.assertIn("rowan-box", escalation.get("question", ""))
        for tick in (T0 + 60, T0 + 120):
            self.assertEqual(
                ww.watchman_watch_tick(snap, journal, tick), [])
        self.assertEqual(
            len([r for r in journal if r["kind"] == "escalation"]),
            1)

    def test_second_death_after_recovery_realerts(self):
        snap = {"machines": {"milo-box": dead_machine(True)}}
        journal = ww.watchman_watch_tick(snap, [], T0)
        snap["machines"]["milo-box"] = {
            "watchman_alive": True, "last_bell": T0,
            "last_wake": T0, "restart_ok": False}
        journal += ww.watchman_watch_tick(snap, journal, T0 + 60)
        snap["machines"]["milo-box"] = dead_machine(False)
        new = ww.watchman_watch_tick(snap, journal, T0 + 120)
        self.assertEqual([r["kind"] for r in new],
                         ["crew-dark", "watchman-restart",
                          "escalation"])

    def test_stale_bell_reads_dead_and_fresh_bell_reads_alive(self):
        stale = {"watchman_alive": True, "last_bell": T0 - 301,
                 "last_wake": T0 - 301}
        fresh = {"watchman_alive": True, "last_bell": T0 - 60,
                 "last_wake": T0 - 60}
        self.assertEqual(ww.machine_state(stale, T0,
                                          stale_minutes=5), ww.DEAD)
        self.assertEqual(ww.machine_state(fresh, T0,
                                          stale_minutes=5), ww.ALIVE)
        self.assertEqual(thresholds.WATCHMAN_STALE_MINUTES, 5)

    def test_unknown_machine_yields_nothing_and_reads_unknown(self):
        snap = {"machines": {"quiet-box": {"last_bell": None}}}
        self.assertEqual(ww.watchman_watch_tick(snap, [], T0), [])
        states = ww.current_states(snap, T0)
        self.assertEqual(states[0]["state"], ww.UNKNOWN)
        self.assertEqual(
            ww.board_lines(states),
            ["Machine quiet-box: watchman state unknown."])

    def test_malformed_inputs_never_crash(self):
        self.assertEqual(ww.watchman_watch_tick({}, [], T0), [])
        self.assertEqual(ww.watchman_watch_tick(
            {"machines": "not a mapping"}, [], T0), [])
        self.assertEqual(ww.watchman_watch_tick(
            {"machines": {"x": "not a record"}}, [], T0), [])
        self.assertEqual(ww.machine_state(None, T0), ww.UNKNOWN)

    def test_tick_never_mutates_inputs(self):
        snap = {"machines": {"rowan-box": dead_machine(False)}}
        journal = [{"kind": "crew-dark", "machine": "other-box"}]
        snap_copy = {"machines": {"rowan-box": dict(
            snap["machines"]["rowan-box"])}}
        journal_copy = [dict(journal[0])]
        ww.watchman_watch_tick(snap, journal, T0)
        self.assertEqual(snap, snap_copy)
        self.assertEqual(journal, journal_copy)

    def test_brief_and_board_lines(self):
        records = [
            {"kind": "crew-dark", "machine": "m-box"},
            {"kind": "watchman-restart", "machine": "m-box",
             "restart_ok": False},
            {"kind": "escalation", "machine": "m-box"},
            {"kind": "watchman-recovered", "machine": "m-box"},
            {"kind": "unrelated", "machine": "m-box"},
        ]
        lines = ww.watchman_brief_lines(records)
        self.assertEqual(len(lines), 4)
        self.assertTrue(all("m-box" in line for line in lines))
        self.assertEqual(
            ww.board_lines([
                {"machine": "a", "state": ww.DEAD},
                {"machine": "b", "state": ww.ALIVE},
                {"machine": "c", "state": ww.UNKNOWN}]),
            ["Machine a: watchman dead (crew-dark).",
             "Machine b: watchman alive.",
             "Machine c: watchman state unknown."])

    def test_escalation_is_built_never_sent(self):
        with open("intel/watchman_watch.py") as handle:
            source = handle.read()
        for banned in ("import socket", "import urllib",
                       "import requests", "bus_post"):
            self.assertNotIn(banned, source)
        self.assertNotIn("redis", source.lower().replace(
            "muse-relay-push", ""))

    def test_drill_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/watchman_watch.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("6/6 phases PASS", result.stdout)

    def test_eval_note_names_os122(self):
        with open("intel/evals/watchman_watch.md") as handle:
            text = handle.read()
        self.assertIn("OS-122", text)
        self.assertIn("crew-dark", text)

    def test_new_files_carry_no_em_dash(self):
        for path in NEW_FILES:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)

    def test_new_files_exist(self):
        for path in NEW_FILES:
            self.assertTrue(os.path.exists(path), path)


if __name__ == "__main__":
    unittest.main()
