"""Journal watch (Milo lane, OS-037).

A relay unit's failure in journald becomes a SYSTEM alert
record in the same alert store the dashboard reads — kind
system-failure, subjects the unit name, no nick, no job — so
a unit failure can never be mistaken for a worker stall.
Pinned here: the failure rule (relay unit + systemd failure
message or err-or-worse priority), the grouping (one alert
per unit per window), the silence cases (healthy relay units,
non-relay failures, unparseable lines), the store round-trip
on the fake store (write + query within one journal_watch_tick),
and the CLI --journal flag. Live force-fail on a test image
is NOT proven here: there is no image in this repo, so the
drill and these tests prove the watchdog half on fixtures.
"""

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402

T0 = 100000
UNIT = "relay-jobs.service"


def _entry(unit, message, priority):
    return {"_SYSTEMD_UNIT": unit, "MESSAGE": message,
            "PRIORITY": str(priority)}


def _json_lines(entries):
    return "\n".join(json.dumps(e) for e in entries)


class JournalFailureRuleTest(unittest.TestCase):
    def test_systemd_failure_message_fires(self):
        alerts = watchdog.detect_journal_failures(
            [_entry(UNIT, "relay-jobs.service: Failed with result "
                          "'exit-code'.", 6)], T0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["kind"], "system-failure")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_err_priority_fires_without_failure_phrasing(self):
        alerts = watchdog.detect_journal_failures(
            [_entry(UNIT, "worker thread wedged, no progress", 3)], T0)
        self.assertEqual(len(alerts), 1)

    def test_healthy_relay_unit_stays_silent(self):
        alerts = watchdog.detect_journal_failures(
            [_entry("relay-bus.service", "Started relay-bus.service.", 6),
             _entry(UNIT, "relay-jobs.service: Started.", 6)], T0)
        self.assertEqual(alerts, [])

    def test_gateway_unit_failure_fires_system_alert(self):
        # OS-059: relay-mcp-gateway.service joins relay.target, so
        # the OS-037 prefix rule must catch it by name, not just
        # the units pinned when the watch first landed.
        alert = watchdog.detect_journal_failures(
            [_entry("relay-mcp-gateway.service",
                    "relay-mcp-gateway.service: Failed with result "
                    "'exit-code'.", 6)], T0)[0]
        self.assertEqual(alert["kind"], "system-failure")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["subjects"],
                         ["relay-mcp-gateway.service"])
        self.assertIs(alert["system_alert"], True)
        self.assertNotIn("nick", alert)
        self.assertNotIn("job", alert)
        quiet = watchdog.detect_journal_failures(
            [_entry("relay-mcp-gateway.service",
                    "Started relay-mcp-gateway.service.", 6)], T0)
        self.assertEqual(quiet, [])

    def test_memory_unit_failure_fires_system_alert(self):
        # OS-078: relay-memory.service joins relay.target, so
        # the OS-037 prefix rule must catch it by name, not just
        # the units pinned when the watch first landed. The unit
        # is a oneshot ensure step, but a failure line is still a
        # relay unit failure and gets the same SYSTEM record.
        alert = watchdog.detect_journal_failures(
            [_entry("relay-memory.service",
                    "relay-memory.service: Failed with result "
                    "'exit-code'.", 6)], T0)[0]
        self.assertEqual(alert["kind"], "system-failure")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["subjects"],
                         ["relay-memory.service"])
        self.assertIs(alert["system_alert"], True)
        self.assertNotIn("nick", alert)
        self.assertNotIn("job", alert)
        quiet = watchdog.detect_journal_failures(
            [_entry("relay-memory.service",
                    "Started relay-memory.service.", 6)], T0)
        self.assertEqual(quiet, [])

    def test_non_relay_failure_stays_silent(self):
        alerts = watchdog.detect_journal_failures(
            [_entry("sshd.service", "sshd.service: Failed with result "
                                   "'exit-code'.", 3)], T0)
        self.assertEqual(alerts, [])

    def test_unparseable_and_unitless_lines_skipped_not_fatal(self):
        text = "\n".join([
            "not json at all",
            json.dumps({"MESSAGE": "Failed with result 'exit-code'.",
                        "PRIORITY": "3"}),
            json.dumps(_entry(UNIT, "relay-jobs.service: Failed with "
                                    "result 'exit-code'.", 3)),
        ])
        alerts = watchdog.detect_journal_failures(text, T0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["unit"], UNIT)

    def test_plain_keyed_entries_accepted(self):
        alerts = watchdog.detect_journal_failures(
            [{"unit": UNIT, "message": "Failed to start relay jobs", "priority": 6}],
            T0)
        self.assertEqual(len(alerts), 1)

    def test_failures_group_by_unit_with_count(self):
        alerts = watchdog.detect_journal_failures(
            [_entry(UNIT, "Failed with result 'exit-code'.", 3),
             _entry(UNIT, "Main process exited, code=exited.", 3),
             _entry("relay-bus.service", "Failed with result 'signal'.", 3)],
            T0)
        self.assertEqual(len(alerts), 2)
        jobs_alert = [a for a in alerts if a["unit"] == UNIT][0]
        self.assertEqual(jobs_alert["failure_count"], 2)
        self.assertEqual(jobs_alert["dedupe_key"], "system-failure:" + UNIT)

    def test_system_alert_has_no_nick_or_job(self):
        alert = watchdog.detect_journal_failures(
            [_entry(UNIT, "Failed with result 'exit-code'.", 3)], T0)[0]
        self.assertEqual(alert["subjects"], [UNIT])
        self.assertIs(alert["system_alert"], True)
        self.assertNotIn("nick", alert)
        self.assertNotIn("job", alert)
        self.assertIn("journalctl -u " + UNIT,
                      alert["suggested_fix"])

    def test_system_failure_severity_is_critical(self):
        # Locked here, not in SEVERITY_BY_KIND: that table is
        # locked by SeverityMappingTest to exactly the snapshot
        # detectors' kinds, and journal watch is deliberately
        # not a snapshot detector.
        alert = watchdog.detect_journal_failures(
            [_entry(UNIT, "Failed with result 'exit-code'.", 3)], T0)[0]
        self.assertEqual(alert["severity"], "critical")

    def test_journal_watch_is_not_a_snapshot_detector(self):
        # Journal entries are not snapshot data: tick() must never
        # consult them, and DETECTORS must not gain a journal entry.
        self.assertNotIn(watchdog.detect_journal_failures,
                         watchdog.DETECTORS)
        self.assertEqual(watchdog.tick({"jobs": [], "messages": []},
                                       now=T0), [])


class JournalStoreRoundTripTest(RelayTestCase):
    def test_one_tick_writes_and_queries_the_system_alert(self):
        fixture = _json_lines([
            _entry(UNIT, "relay-jobs.service: Failed with result "
                          "'exit-code'.", 3),
            _entry("relay-bus.service", "Started.", 6),
        ])
        alerts = watchdog.journal_watch_tick(fixture, now=T0,
                                             emit=istore.write_alert)
        self.assertEqual(len(alerts), 1)
        record = istore.get_alert("system-failure:" + UNIT)
        self.assertIsNotNone(record)
        self.assertEqual(record["kind"], "system-failure")
        self.assertEqual(record["subjects"], [UNIT])
        found = istore.query_alerts(kind="system-failure")
        self.assertEqual([r["id"] for r in found],
                         ["system-failure:" + UNIT])

    def test_retick_inside_cooldown_advances_last_seen_only(self):
        fixture = _json_lines([
            _entry(UNIT, "relay-jobs.service: Failed with result "
                          "'exit-code'.", 3)])
        watchdog.journal_watch_tick(fixture, now=T0,
                                    emit=istore.write_alert)
        watchdog.journal_watch_tick(fixture, now=T0 + 60,
                                    emit=istore.write_alert)
        record = istore.get_alert("system-failure:" + UNIT)
        self.assertEqual(record["created_at"], T0)
        self.assertEqual(record["last_seen"], T0 + 60)


class JournalCliTest(unittest.TestCase):
    def _run_cli(self, journal_text=None):
        args = ["python3", "-m", "intel.watchdog", "--once"]
        path = None
        if journal_text is not None:
            path = os.path.join(self._tmp, "journal.jsonl")
            with open(path, "w") as handle:
                handle.write(journal_text)
            args += ["--journal", path]
        proc = subprocess.run(args, capture_output=True, text=True,
                              cwd=os.path.dirname(
                                  os.path.dirname(
                                      os.path.abspath(__file__))))
        return proc

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="journal-cli-")

    def test_cli_once_with_journal_reports_one_alert(self):
        fixture = _json_lines([
            _entry(UNIT, "relay-jobs.service: Failed with result "
                          "'exit-code'.", 3)])
        proc = self._run_cli(fixture)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("watchdog: 1 alert(s)", proc.stdout)

    def test_cli_once_with_quiet_journal_reports_zero(self):
        fixture = _json_lines([
            _entry("relay-bus.service", "Started.", 6)])
        proc = self._run_cli(fixture)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("watchdog: 0 alert(s)", proc.stdout)

    def test_cli_missing_journal_file_exits_1(self):
        proc = subprocess.run(
            ["python3", "-m", "intel.watchdog", "--once",
             "--journal", "/nonexistent/journal.jsonl"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("cannot load journal", proc.stderr)


if __name__ == "__main__":
    unittest.main()
