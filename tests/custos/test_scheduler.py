"""Patrol-scheduler tests for META CUSTOS (RW-007).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The scheduler's cadence logic is pinned on injected signals and a
fake clock — no network, no live hosts. The claims pinned here are
the RW-007 checkable results:

  * a per-source cadence config decides what runs each cycle, and
    a source fires exactly when its interval has elapsed;
  * the subdomain sweep pulls the CT source in with it (it grades
    this cycle's CT entries, so it cannot run on a stale cycle);
  * a cycle where nothing is due calls no patrol and still leaves
    a cycle record proving the scheduler decided;
  * a bad cadence (unknown source, unparseable or non-positive
    interval) fails before anything runs;
  * a full unattended cycle — every source firing on its own
    cadence across a simulated window — leaves its proof in the
    records, with no human step between cycles.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402
import scheduler  # noqa: E402

T0 = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)


def at(hours=0, minutes=0):
    from datetime import timedelta
    return T0 + timedelta(hours=hours, minutes=minutes)


def fake_config(cadence=None):
    config = {
        "hosts": [],
        "inventory": ["openssl"],
        "ct_domains": ["example.org"],
        "dns_domains": ["example.org"],
        "ct_since": "2026-01-01",
    }
    if cadence is not None:
        config["cadence"] = cadence
    return config


def fake_signals(calls):
    """Injectable patrol signals that record which source ran.

    The kev feed matches the inventory once; the CT feed carries
    one fresh cert; DNS returns one snapshot; the subdomain map is
    empty so the sweep grades nothing. Any signal the test does not
    expect is a failure, not a silent pass.
    """
    def fetch_kev(_url):
        calls.append("kev")
        return [{"cveID": "CVE-2024-0001", "vendorProject": "OpenSSL",
                 "product": "OpenSSL", "dateAdded": "2024-05-01"}]

    def fetch_ct(_domain, _template):
        calls.append("ct")
        return [{"id": 7, "common_name": "example.org",
                 "issuer_name": "Test CA", "not_before": "2026-10-01",
                 "not_after": "2027-10-01"}]

    def fetch_dns(_domain):
        calls.append("dns")
        return {"A": ["203.0.113.1"], "AAAA": [], "MX": [], "TXT": []}

    return fetch_kev, fetch_ct, fetch_dns


class TestParseDuration(unittest.TestCase):
    def test_units(self):
        self.assertEqual(scheduler.parse_duration(90), 90)
        self.assertEqual(scheduler.parse_duration("90"), 90)
        self.assertEqual(scheduler.parse_duration("30s"), 30)
        self.assertEqual(scheduler.parse_duration("15m"), 900)
        self.assertEqual(scheduler.parse_duration("1h"), 3600)
        self.assertEqual(scheduler.parse_duration("7d"), 604800)
        self.assertEqual(scheduler.parse_duration(" 2H "), 7200)

    def test_rejects(self):
        for bad in (0, -5, "0", "0h", "-1h", "15x", "hour", "", "1.5h",
                    None, 1.5, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                scheduler.parse_duration(bad)


class TestCadenceValidation(unittest.TestCase):
    def test_absent_cadence_runs_everything_every_cycle(self):
        cadence = scheduler.validate_cadence(fake_config())
        self.assertEqual(cadence, {s: 0 for s in scheduler.SOURCES})

    def test_unlisted_source_defaults_to_every_cycle(self):
        cadence = scheduler.validate_cadence(
            fake_config({"kev": "24h"}))
        self.assertEqual(cadence["kev"], 86400)
        self.assertEqual(cadence["ct"], 0)

    def test_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            scheduler.validate_cadence(fake_config({"bogus": "1h"}))

    def test_bad_interval_rejected(self):
        with self.assertRaises(ValueError):
            scheduler.validate_cadence(fake_config({"kev": "soon"}))

    def test_non_object_cadence_rejected(self):
        with self.assertRaises(ValueError):
            scheduler.validate_cadence({"cadence": ["kev"]})


class TestDueSources(unittest.TestCase):
    def test_never_run_is_due(self):
        cadence = {"kev": 86400, "ct": 3600, "dns": 21600,
                   "subdomain": 21600, "hosts": 900}
        self.assertEqual(scheduler.due_sources(at(), {}, cadence),
                         set(scheduler.SOURCES))

    def test_interval_boundary_is_due(self):
        last = {"kev": "2026-11-01T00:00:00Z"}
        cadence = {"kev": 3600, "ct": 0, "dns": 0,
                   "subdomain": 0, "hosts": 0}
        self.assertIn("kev", scheduler.due_sources(at(hours=1),
                                                   last, cadence))
        self.assertNotIn("kev", scheduler.due_sources(at(minutes=59),
                                                      last, cadence))

    def test_unparseable_stamp_is_due_and_repaired(self):
        last = {"kev": "not-a-time"}
        cadence = {"kev": 3600, "ct": 0, "dns": 0,
                   "subdomain": 0, "hosts": 0}
        self.assertIn("kev", scheduler.due_sources(at(), last, cadence))


class TestPatrolSourceFilter(unittest.TestCase):
    def test_hosts_only_skips_every_other_signal(self):
        calls = []

        def boom(_x):
            raise AssertionError("skipped source must not be fetched")

        records, _s, _c = patrol.run_patrol(
            fake_config(), "2026-11-01T03:00:00Z", boom,
            lambda h, p: False, lambda h, p: False,
            sources={"hosts"})
        summary = records[-1]
        self.assertEqual(summary["sources_run"], ["hosts"])
        self.assertEqual(summary["sources_skipped"],
                         ["kev", "ct", "dns", "subdomain"])
        self.assertEqual(summary["hosts_checked"], 0)
        self.assertEqual(summary["kev_entries_seen"], 0)
        self.assertEqual(summary["ct_entries_seen"], 0)

    def test_unknown_source_raises_before_any_fetch(self):
        calls = []

        def boom(_x):
            calls.append("fetched")
            return []

        with self.assertRaises(ValueError):
            patrol.run_patrol(fake_config(), "2026-11-01T03:00:00Z",
                              boom, lambda h, p: False,
                              lambda h, p: False, sources={"bogus"})
        self.assertEqual(calls, [])


class TestRunCycle(unittest.TestCase):
    def run_one(self, config, now, sched, state, calls):
        fetch_kev, fetch_ct, fetch_dns = fake_signals(calls)
        return scheduler.run_cycle(
            config, now, sched, state,
            fetch_kev_fn=fetch_kev, fetch_ct_fn=fetch_ct,
            fetch_dns_fn=fetch_dns,
            probe_cert_fn=lambda h, p: None,
            probe_port_fn=lambda h, p: False)

    def test_first_cycle_runs_everything(self):
        calls, sched, state = [], {}, {"seen_cve": set(),
                                       "seen_ct": set(), "seen_dns": {}}
        records, sched, _st = self.run_one(
            fake_config({"kev": "24h", "ct": "1h", "dns": "6h",
                         "subdomain": "6h", "hosts": "15m"}),
            at(), sched, state, calls)
        cycle = records[-1]
        self.assertEqual(cycle["record_type"], "scheduler-cycle")
        self.assertEqual(cycle["sources_run"], list(scheduler.SOURCES))
        self.assertEqual(cycle["sources_skipped"], [])
        self.assertEqual(sorted(calls), ["ct", "dns", "kev"])
        self.assertIsNotNone(cycle["patrol_summary"])
        self.assertEqual(cycle["patrol_summary"]["sources_run"],
                         list(scheduler.SOURCES))

    def test_nothing_due_calls_no_patrol(self):
        calls, sched, state = [], {}, {"seen_cve": set(),
                                       "seen_ct": set(), "seen_dns": {}}
        self.run_one(fake_config({"kev": "24h", "ct": "1h", "dns": "6h",
                                  "subdomain": "6h", "hosts": "15m"}),
                     at(), sched, state, calls)
        calls.clear()
        records, _sched, _st = self.run_one(
            fake_config({"kev": "24h", "ct": "1h", "dns": "6h",
                         "subdomain": "6h", "hosts": "15m"}),
            at(minutes=1), sched, state, calls)
        self.assertEqual(calls, [])
        self.assertEqual(len(records), 1)
        cycle = records[0]
        self.assertEqual(cycle["sources_run"], [])
        self.assertIsNone(cycle["patrol_summary"])
        self.assertEqual(cycle["sources_skipped"],
                         list(scheduler.SOURCES))

    def test_subdomain_due_pulls_ct_in(self):
        calls, sched, state = [], {}, {"seen_cve": set(),
                                       "seen_ct": set(), "seen_dns": {}}
        config = fake_config({"kev": "24h", "ct": "24h", "dns": "24h",
                              "subdomain": "1h", "hosts": "24h"})
        self.run_one(config, at(), sched, state, calls)
        calls.clear()
        records, _sched, _st = self.run_one(config, at(hours=1),
                                            sched, state, calls)
        cycle = records[-1]
        self.assertEqual(cycle["sources_due"], ["subdomain"])
        self.assertEqual(cycle["sources_run"], ["ct", "subdomain"])
        self.assertIn("ct", calls)

    def test_full_unattended_cycle_on_fake_clock(self):
        """Every source fires on its own cadence across 24 hours,
        with no human step between cycles: the unattended proof."""
        config = fake_config({"kev": "24h", "ct": "1h", "dns": "6h",
                              "subdomain": "6h", "hosts": "15m"})
        sched, state = {}, {"seen_cve": set(), "seen_ct": set(),
                            "seen_dns": {}}
        fired = {s: 0 for s in scheduler.SOURCES}
        cycles = []
        for step in range(0, 24 * 4 + 1):
            now = at(minutes=15 * step)
            calls = []
            records, sched, state = self.run_one(config, now, sched,
                                                 state, calls)
            cycle = records[-1]
            cycles.append(cycle)
            for source in cycle["sources_run"]:
                fired[source] += 1
        # Hosts every 15m across 24h + the t0 cycle: 97 runs.
        self.assertEqual(fired["hosts"], 97)
        # CT hourly: 25 runs. DNS/subdomain every 6h: 5 runs each.
        self.assertEqual(fired["ct"], 25)
        self.assertEqual(fired["dns"], 5)
        self.assertEqual(fired["subdomain"], 5)
        # KEV daily: t0 and t24h only.
        self.assertEqual(fired["kev"], 2)
        # Every cycle left exactly one cycle record, in order.
        self.assertEqual(len(cycles), 97)
        self.assertTrue(all(c["record_type"] == "scheduler-cycle"
                            for c in cycles))

    def test_bad_cadence_fails_before_any_fetch(self):
        calls, sched, state = [], {}, {"seen_cve": set(),
                                       "seen_ct": set(), "seen_dns": {}}
        with self.assertRaises(ValueError):
            self.run_one(fake_config({"kev": "soon"}), at(), sched,
                         state, calls)
        self.assertEqual(calls, [])
        self.assertEqual(sched, {})


class TestSchedulerCli(unittest.TestCase):
    def test_two_offline_cycles_prove_idle(self):
        """Real CLI, fixture feeds, no network: cycle 1 runs the
        due sources, cycle 2 (immediately after) runs nothing but
        still records the decision. The scheduler state defaults
        to scheduler.json next to the patrol state file."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "hosts.json")
            kev_path = os.path.join(tmp, "kev.json")
            ct_path = os.path.join(tmp, "ct.json")
            dns_path = os.path.join(tmp, "dns.json")
            records_path = os.path.join(tmp, "records.jsonl")
            state_path = os.path.join(tmp, "seen.json")
            with open(config_path, "w") as f:
                json.dump(fake_config({"kev": "24h", "ct": "24h",
                                       "dns": "24h", "subdomain": "24h",
                                       "hosts": "24h"}), f)
            with open(kev_path, "w") as f:
                json.dump({"vulnerabilities": [
                    {"cveID": "CVE-2024-0001",
                     "vendorProject": "OpenSSL", "product": "OpenSSL",
                     "dateAdded": "2024-05-01"}]}, f)
            with open(ct_path, "w") as f:
                json.dump([{"id": 7, "common_name": "example.org",
                            "issuer_name": "Test CA",
                            "not_before": "2026-10-01",
                            "not_after": "2027-10-01"}], f)
            with open(dns_path, "w") as f:
                json.dump({"example.org": {"A": ["203.0.113.1"],
                                           "AAAA": [], "MX": [],
                                           "TXT": []}}, f)
            script = os.path.join(REPO, "os", "worlds", "custos",
                                  "runtime", "scheduler.py")
            cmd = [sys.executable, script, "run", "--config",
                   config_path, "--records", records_path, "--state",
                   state_path, "--kev-file", kev_path, "--ct-file",
                   ct_path, "--dns-file", dns_path]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("scheduler cycle complete", first.stderr)
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("ran nothing", second.stderr)
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, "scheduler.json")))
            with open(records_path) as f:
                rows = [json.loads(line) for line in f if line.strip()]
            cycles = [r for r in rows
                      if r["record_type"] == "scheduler-cycle"]
            self.assertEqual(len(cycles), 2)
            self.assertEqual(cycles[0]["sources_run"],
                             list(scheduler.SOURCES))
            self.assertEqual(cycles[1]["sources_run"], [])
            self.assertEqual(cycles[1]["sources_skipped"],
                             list(scheduler.SOURCES))

    def test_bad_cadence_cli_exits_nonzero_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "hosts.json")
            records_path = os.path.join(tmp, "records.jsonl")
            state_path = os.path.join(tmp, "seen.json")
            with open(config_path, "w") as f:
                json.dump(fake_config({"kev": "soon"}), f)
            script = os.path.join(REPO, "os", "worlds", "custos",
                                  "runtime", "scheduler.py")
            proc = subprocess.run(
                [sys.executable, script, "run", "--config",
                 config_path, "--records", records_path, "--state",
                 state_path], capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(os.path.exists(records_path))
            self.assertFalse(os.path.exists(state_path))


if __name__ == "__main__":
    unittest.main()
