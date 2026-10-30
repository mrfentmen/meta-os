"""Restart-ownership contract (Milo lane, OS-034).

systemd's Restart= owns process death, the watchdog owns
silent-but-alive stalls, and neither double-acts on the
other's case. Pinned here: the restart event note's shape
and validation, the zero-alert post-restart tick, the
control proving that zero comes from the restart (an
un-restarted death past threshold still stalls), and the
SIGSTOP case (progress-stall only, no restart note).
"""

import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402

NICK = "pax"
JOB_ID = "7"
T0 = 100000


def _snapshot(present, last_activity):
    return {
        "caps": {NICK: ["python"]},
        "presence": [NICK] if present else [],
        "jobs": [{
            "id": JOB_ID, "title": "demo job", "status": "claimed",
            "claim": NICK, "claimed_at": T0,
            "last_progress": last_activity,
            "lease": thresholds.LEASE_DEFAULT_SECONDS,
            "lease_until": T0 + thresholds.LEASE_DEFAULT_SECONDS,
        }],
        "messages": [],
    }


class RestartContractTest(unittest.TestCase):
    def test_restart_note_shape(self):
        note = watchdog.restart_event_note(NICK, JOB_ID, T0 + 310,
                                           downtime_seconds=10)
        self.assertEqual(note["kind"], "worker-restart")
        self.assertEqual(note["severity"], "info")
        self.assertEqual(note["dedupe_key"],
                         f"worker-restart:{NICK}:{JOB_ID}")
        self.assertIn("systemd", note["explanation"])
        self.assertIn(NICK, note["explanation"])
        self.assertIn(JOB_ID, note["explanation"])
        self.assertIn("no stall alert", note["explanation"])

    def test_restart_note_validates_and_never_announces(self):
        note = watchdog.restart_event_note(NICK, JOB_ID, T0 + 310,
                                           downtime_seconds=10)
        record = istore.build_alert_record(note)
        self.assertEqual(record["severity"], "info")
        self.assertEqual(record["id"], f"worker-restart:{NICK}:{JOB_ID}")
        self.assertEqual(watchdog.announcements_for([record]), [])

    def test_restart_note_without_downtime_invents_nothing(self):
        note = watchdog.restart_event_note(NICK, JOB_ID, T0 + 310)
        self.assertIsNone(note["downtime_seconds"])
        self.assertNotIn("None", note["explanation"])
        self.assertIn("brief absence", note["explanation"])

    def test_restart_note_needs_nick_and_job(self):
        with self.assertRaises(ValueError):
            watchdog.restart_event_note("", JOB_ID, T0)
        with self.assertRaises(ValueError):
            watchdog.restart_event_note(NICK, "", T0)

    def test_post_restart_tick_yields_zero_alerts(self):
        # Killed at T0+300, back at T0+310 with a fresh heartbeat.
        tick = watchdog.tick(_snapshot(True, T0 + 310), now=T0 + 310)
        self.assertEqual(tick, [])

    def test_unrestarted_death_past_threshold_still_stalls(self):
        # Control: the zero above comes from the restart, not
        # from a blind detector — the same death with no
        # restart yields exactly one presence-stall alert.
        tick = watchdog.tick(
            _snapshot(False, T0 + 300),
            now=T0 + 300 + thresholds.STALL_MINUTES * 60 + 60)
        self.assertEqual([a["kind"] for a in tick], ["presence-stall"])

    def test_wedged_worker_yields_progress_stall_only(self):
        # SIGSTOP: process alive (present) but last activity
        # frozen at T0 — a stall alert, no presence-stall, and
        # no restart note anywhere in the tick output.
        tick = watchdog.tick(
            _snapshot(True, T0),
            now=T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 60)
        self.assertEqual([a["kind"] for a in tick], ["progress-stall"])
        self.assertEqual(tick[0]["nick"], NICK)
        self.assertEqual(tick[0]["job"], JOB_ID)


if __name__ == "__main__":
    unittest.main()
