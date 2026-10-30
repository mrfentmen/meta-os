"""tests/test_os_watchman.py -- OS-118: the watchman (relay-watchman).

OS-118 ships os/watchman/relay_watchman.py, the resident CLI
program that rings the bell for one Meta OS machine, plus
os/services/relay-watchman.service under relay.target. These
tests pin the program's decisions and the unit wiring, not a
live boot: a booted test image, a live queue reader, and the
mechanical restart/reassign rungs are still owed (see the
os/README.md OS-118 section).

- One tick over a newly posted open job addressed to a local
  sleeping agent yields exactly one wake event naming job +
  agent; the same tick with the job addressed elsewhere, to
  an awake agent, unaddressed, done, or malformed yields none.
- A claimed job whose local claimer heartbeat went stale
  yields one nudge on the same tick; a fresh heartbeat, or
  no heartbeat at all, yields none (a never-seen worker is
  not nudged into existence).
- No counter anywhere: varying a stray bus_message_count
  field carried on the job records yields identical events,
  and tick() takes no counter argument at all.
- Dedupe: a second tick with the merged rung ledger yields
  no repeat wake or nudge; a nudge re-fires only when the
  heartbeat value itself changed (the worker came back and
  stalled again).
- tick() never mutates its inputs.
- The CLI --once path prints events as JSON lines, writes
  the rung ledger to the state file, prints nothing on a
  second run over the same state, and exits 2 on malformed
  input without printing an event.
- The unit file orders after relay-jobs, belongs to
  relay.target, carries the OS-012 secrets gate, puts no
  secret on its command line, and is wanted by relay.target
  and enabled on all three image routes.

No bus post, no live Redis, no network, no systemd, no model
call: pure functions plus temp-file CLI runs.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAM = os.path.join(ROOT, "os", "watchman", "relay_watchman.py")
UNIT = os.path.join(ROOT, "os", "services", "relay-watchman.service")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
README = os.path.join(ROOT, "os", "README.md")
BUILD_IMAGE = os.path.join(ROOT, "os", "build-image.sh")
PACKER = os.path.join(ROOT, "os", "packer", "metaos.pkr.hcl")
HOOK = os.path.join(
    ROOT, "os", "live-build", "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")

sys.path.insert(0, os.path.join(ROOT, "os", "watchman"))
import relay_watchman  # noqa: E402

NOW = 1000000
STALE = 300


def job(job_id, status="open", **fields):
    record = {"id": job_id, "status": status}
    record.update(fields)
    return record


class WakeTest(unittest.TestCase):
    def test_open_job_wakes_sleeping_local_agent(self):
        events, keys = relay_watchman.tick(
            [job("7", addressed_to="hana", title="Write the brief")],
            {"hana": {"heartbeat_at": None}},
            set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "wake")
        self.assertEqual(events[0]["job_id"], "7")
        self.assertEqual(events[0]["agent"], "hana")
        self.assertEqual(keys, ["wake:7"])

    def test_wake_via_legacy_to_field(self):
        events, _ = relay_watchman.tick(
            [job("8", to="milo")],
            {"milo": {}}, set(), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["agent"], "milo")

    def test_no_wake_for_other_agent_awake_or_unaddressed(self):
        jobs = [
            job("1", addressed_to="ghost"),
            job("2", addressed_to="hana"),
            job("3"),
        ]
        agents = {
            "hana": {"heartbeat_at": NOW},
        }
        events, _ = relay_watchman.tick(
            jobs, agents, set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])

    def test_no_wake_for_done_or_malformed_or_unknown(self):
        jobs = [
            job("1", status="done", addressed_to="hana"),
            job("2", status="cancelled", addressed_to="hana"),
            {"status": "open", "addressed_to": "hana"},
            "not-a-record",
            job("3", addressed_to="ghost"),
        ]
        events, _ = relay_watchman.tick(
            jobs, {"hana": {"heartbeat_at": None}}, set(), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])

    def test_unregistered_agent_is_not_local(self):
        events, _ = relay_watchman.tick(
            [job("9", addressed_to="buffy")],
            {"buffy": {"heartbeat_at": None, "registered": False}},
            set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])


class NudgeTest(unittest.TestCase):
    def test_stale_heartbeat_nudges_on_same_cycle(self):
        events, keys = relay_watchman.tick(
            [job("4", status="claimed", claim="milo",
                 title="Run the drill")],
            {"milo": {"heartbeat_at": NOW - 1000}},
            set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "nudge")
        self.assertEqual(events[0]["job_id"], "4")
        self.assertEqual(events[0]["agent"], "milo")
        self.assertEqual(events[0]["heartbeat_age_seconds"], 1000)
        self.assertEqual(keys, ["nudge:4:%s" % (NOW - 1000)])

    def test_fresh_or_missing_heartbeat_never_nudges(self):
        jobs = [
            job("5", status="claimed", claim="milo"),
            job("6", status="claimed", claim="hana"),
        ]
        agents = {
            "milo": {"heartbeat_at": NOW - 10},
            "hana": {"heartbeat_at": None},
        }
        events, _ = relay_watchman.tick(
            jobs, agents, set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])

    def test_claim_by_nonlocal_agent_never_nudges(self):
        events, _ = relay_watchman.tick(
            [job("5", status="claimed", claim="rowan")],
            {"milo": {"heartbeat_at": NOW - 1000}},
            set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])


class CounterAndDedupeTest(unittest.TestCase):
    def test_counter_field_variation_changes_nothing(self):
        base = [job("7", addressed_to="hana")]
        agents = {"hana": {"heartbeat_at": None}}
        first, _ = relay_watchman.tick(
            base, agents, set(), NOW, heartbeat_stale_seconds=STALE)
        drifted = [dict(base[0], bus_message_count=999,
                        seen=12345)]
        second, _ = relay_watchman.tick(
            drifted, agents, set(), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(first, second)
        # And tick takes no counter argument at all.
        params = relay_watchman.tick.__code__.co_varnames
        self.assertNotIn("counter", params)
        self.assertNotIn("message_count", params)

    def test_second_tick_with_merged_ledger_is_silent(self):
        jobs = [job("7", addressed_to="hana"),
                job("4", status="claimed", claim="milo")]
        agents = {"hana": {"heartbeat_at": None},
                  "milo": {"heartbeat_at": NOW - 1000}}
        events, keys = relay_watchman.tick(
            jobs, agents, set(), NOW, heartbeat_stale_seconds=STALE)
        self.assertEqual(len(events), 2)
        again, _ = relay_watchman.tick(
            jobs, agents, set(keys), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(again, [])

    def test_nudge_refires_only_when_heartbeat_refreshes(self):
        jobs = [job("4", status="claimed", claim="milo")]
        old = {"milo": {"heartbeat_at": NOW - 1000}}
        _, keys = relay_watchman.tick(
            jobs, old, set(), NOW, heartbeat_stale_seconds=STALE)
        fresh = {"milo": {"heartbeat_at": NOW - 900}}
        events, _ = relay_watchman.tick(
            jobs, fresh, set(keys), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "nudge")

    def test_inputs_never_mutated(self):
        jobs = [job("7", addressed_to="hana")]
        agents = {"hana": {"heartbeat_at": None}}
        ledger = set()
        snapshot_jobs = json.loads(json.dumps(jobs))
        snapshot_agents = json.loads(json.dumps(agents))
        relay_watchman.tick(jobs, agents, ledger, NOW,
                            heartbeat_stale_seconds=STALE)
        self.assertEqual(jobs, snapshot_jobs)
        self.assertEqual(agents, snapshot_agents)
        self.assertEqual(ledger, set())


class CliTest(unittest.TestCase):
    def _run_once(self, jobs, agents, state_exists=True):
        tmp = tempfile.mkdtemp()
        jobs_path = os.path.join(tmp, "jobs.json")
        agents_path = os.path.join(tmp, "agents.json")
        state_path = os.path.join(tmp, "state.json")
        with open(jobs_path, "w") as handle:
            json.dump(jobs, handle)
        with open(agents_path, "w") as handle:
            json.dump(agents, handle)
        if state_exists:
            with open(state_path, "w") as handle:
                json.dump({"rung": []}, handle)
        proc = subprocess.run(
            [sys.executable, PROGRAM, "--once",
             "--jobs-file", jobs_path,
             "--agents-file", agents_path,
             "--state-file", state_path,
             "--now", str(NOW)],
            capture_output=True, text=True)
        return proc, state_path

    def test_once_prints_event_and_second_run_is_silent(self):
        jobs = [job("7", addressed_to="hana", title="Write it")]
        proc, state_path = self._run_once(
            jobs, {"hana": {"heartbeat_at": None}})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [json.loads(line) for line in
                 proc.stdout.strip().splitlines()]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["kind"], "wake")
        self.assertEqual(lines[0]["job_id"], "7")
        with open(state_path) as handle:
            state = json.load(handle)
        self.assertEqual(state["rung"], ["wake:7"])

    def test_once_reusing_state_file_is_silent(self):
        tmp = tempfile.mkdtemp()
        jobs_path = os.path.join(tmp, "jobs.json")
        agents_path = os.path.join(tmp, "agents.json")
        state_path = os.path.join(tmp, "state.json")
        with open(jobs_path, "w") as handle:
            json.dump([job("7", addressed_to="hana")], handle)
        with open(agents_path, "w") as handle:
            json.dump({"hana": {"heartbeat_at": None}}, handle)
        argv = [sys.executable, PROGRAM, "--once",
                "--jobs-file", jobs_path,
                "--agents-file", agents_path,
                "--state-file", state_path,
                "--now", str(NOW)]
        first = subprocess.run(argv, capture_output=True, text=True)
        second = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(len(first.stdout.strip().splitlines()), 1)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout.strip(), "")

    def test_once_malformed_input_exits_2_with_no_event(self):
        tmp = tempfile.mkdtemp()
        jobs_path = os.path.join(tmp, "jobs.json")
        agents_path = os.path.join(tmp, "agents.json")
        with open(jobs_path, "w") as handle:
            handle.write("{not json")
        with open(agents_path, "w") as handle:
            json.dump({}, handle)
        proc = subprocess.run(
            [sys.executable, PROGRAM, "--once",
             "--jobs-file", jobs_path,
             "--agents-file", agents_path,
             "--now", str(NOW)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout.strip(), "")

    def test_once_missing_files_read_as_empty(self):
        tmp = tempfile.mkdtemp()
        proc = subprocess.run(
            [sys.executable, PROGRAM, "--once",
             "--jobs-file", os.path.join(tmp, "no-jobs.json"),
             "--agents-file", os.path.join(tmp, "no-agents.json"),
             "--now", str(NOW)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")


class UnitWiringTest(unittest.TestCase):
    def _read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()

    def test_unit_file_shape(self):
        text = self._read(UNIT)
        self.assertIn("After=relay-jobs.service", text)
        self.assertIn("PartOf=relay.target", text)
        self.assertIn("WantedBy=relay.target", text)
        self.assertIn("ConditionPathExists=/etc/metaos/secrets.env",
                      text)
        self.assertIn("relay_watchman.py --loop", text)
        self.assertIn("User=relay", text)
        self.assertNotIn("--dm", text)
        self.assertNotIn("--token", text)
        self.assertNotIn("MUSE_RELAY_TOKEN", text)

    def test_target_wants_watchman_and_all_routes_enable_it(self):
        self.assertIn("relay-watchman.service", self._read(TARGET))
        for path in (BUILD_IMAGE, PACKER, HOOK):
            self.assertIn("relay-watchman.service",
                          self._read(path), path)

    def test_readme_carries_os118_section(self):
        self.assertIn("OS-118", self._read(README))
        self.assertIn("relay_watchman", self._read(README))
