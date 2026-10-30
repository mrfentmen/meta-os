"""tests/test_intel_wake.py -- OS-119: Muse wake adapter.

OS-119 wakes a sleeping Muse instance with the job
already in its hands, so the agent's first act is
the job, never a poll. These tests pin the wake
rule, the bundle, the dedupe, and the zero-send
halves on fixtures:

- A sleeping Muse agent addressed by a posted job
  wakes, and the bundle carries goal, spec,
  acceptance checks, files, and mind image.
- A job addressed to a different agent wakes
  nobody, in both directions.
- An awake agent needs no wake, and a sleeping
  agent whose runtime is not muse is not this
  adapter's wake.
- A job with no id cannot wake anyone.
- A bundle with no mind image reference says the
  OS-102 loader is pending instead of inventing
  one, and still wakes.
- A goal from a spec Goal line fills the bundle
  when the job carries no goal key.
- Dedupe is per job and agent pair: a second tick
  is silent, a second job wakes again.
- The tick never mutates its inputs.
- Brief lines render wake records only.
- Malformed inputs yield no records and no crash.
- The module imports no socket, bus, or network
  module.
- The drill script exists and passes.
- None of the new OS-119 files carries an em dash.

No bus post, no live runtime, no network, no
systemd: the session start is simulated by the
drill's fake runtime.
"""

import ast
import copy
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

from intel import wake  # noqa: E402

T0 = 100000
NEW_FILES = [
    "intel/wake.py",
    "intel/drills/wake.py",
    "intel/evals/wake.md",
    "tests/test_intel_wake.py",
]


def hana_agent(asleep=True, runtime="muse"):
    return {"nick": "hana", "machine": "hana-box",
            "runtime": runtime, "asleep": asleep}


def job(job_id, addressed_to, mind_image=True):
    record = {"id": job_id, "addressed_to": addressed_to,
              "goal": "Write the watchdog brief line",
              "spec": "Goal: Write the watchdog brief line\n"
                      "Steps: draft, check, file",
              "acceptance_checks": ["brief line names the alert"],
              "files": ["intel/brief.py"]}
    if mind_image:
        record["mind_image_ref"] = "mind/hana-base-v3"
    return record


class TestWake(unittest.TestCase):
    def test_sleeping_addressed_agent_wakes_with_full_bundle(self):
        agent = hana_agent()
        posted = job("job-1", "hana")
        bundle = wake.compose_bundle(posted, agent)
        self.assertIsNotNone(bundle)
        self.assertEqual(bundle["job_id"], "job-1")
        self.assertEqual(bundle["agent"], "hana")
        self.assertEqual(bundle["goal"], "Write the watchdog brief line")
        self.assertIn("Goal:", bundle["spec"])
        self.assertEqual(bundle["acceptance_checks"],
                         ["brief line names the alert"])
        self.assertEqual(bundle["files"], ["intel/brief.py"])
        self.assertEqual(bundle["mind_image"], "mind/hana-base-v3")
        self.assertTrue(wake.should_wake(posted, agent))

    def test_wrong_addressee_wakes_nobody(self):
        self.assertFalse(wake.should_wake(job("job-1", "rowan"),
                                          hana_agent()))
        self.assertFalse(wake.should_wake(
            job("job-1", "hana"),
            {"nick": "rowan", "machine": "rowan-box",
             "runtime": "muse", "asleep": True}))
        self.assertEqual(wake.wake_tick([job("job-1", "rowan")],
                                        [hana_agent()], [], T0), [])

    def test_awake_agent_needs_no_wake(self):
        self.assertFalse(wake.should_wake(job("job-1", "hana"),
                                          hana_agent(asleep=False)))
        self.assertEqual(wake.wake_tick([job("job-1", "hana")],
                                        [hana_agent(asleep=False)],
                                        [], T0), [])

    def test_non_muse_runtime_is_not_this_adapter_wake(self):
        for runtime in ("freebuff", None):
            agent = hana_agent(runtime=runtime)
            self.assertFalse(wake.should_wake(job("job-1", "hana"),
                                              agent))
        self.assertEqual(wake.wake_tick([job("job-1", "hana")],
                                        [hana_agent(runtime="freebuff")],
                                        [], T0), [])

    def test_job_without_id_cannot_wake(self):
        posted = {"addressed_to": "hana", "goal": "Do a job"}
        self.assertFalse(wake.should_wake(posted, hana_agent()))
        self.assertEqual(wake.wake_tick([posted], [hana_agent()],
                                        [], T0), [])

    def test_bundle_without_mind_image_names_os102_pending(self):
        bundle = wake.compose_bundle(job("job-1", "hana",
                                          mind_image=False),
                                     hana_agent())
        self.assertIsNotNone(bundle)
        self.assertIsNone(bundle["mind_image"])
        self.assertIn("OS-102", bundle.get("mind_image_note", ""))
        self.assertIn("pending", bundle.get("mind_image_note", ""))

    def test_goal_from_spec_line_when_goal_key_missing(self):
        posted = {"id": "job-1", "addressed_to": "hana",
                  "spec": "Goal: File the brief\nSteps: draft"}
        bundle = wake.compose_bundle(posted, hana_agent())
        self.assertEqual(bundle["goal"], "File the brief")

    def test_dedupe_is_per_pair_not_per_agent(self):
        agent = hana_agent()
        first = job("job-1", "hana")
        journal = wake.wake_tick([first], [agent], [], T0)
        self.assertEqual(len(journal), 1)
        self.assertEqual(journal[0]["dedupe_key"], "wake:job-1:hana")
        self.assertEqual(wake.wake_tick([first], [agent], journal,
                                        T0), [])
        second = job("job-2", "hana")
        new = wake.wake_tick([first, second], [agent], journal, T0)
        self.assertEqual([record["job"] for record in new], ["job-2"])

    def test_tick_never_mutates_inputs(self):
        jobs = [job("job-1", "hana")]
        agents = [hana_agent()]
        journal = []
        jobs_before = copy.deepcopy(jobs)
        agents_before = copy.deepcopy(agents)
        wake.wake_tick(jobs, agents, journal, T0)
        self.assertEqual(jobs, jobs_before)
        self.assertEqual(agents, agents_before)
        self.assertEqual(journal, [])

    def test_brief_lines_render_wake_records_only(self):
        records = wake.wake_tick([job("job-1", "hana")],
                                 [hana_agent()], [], T0)
        records.append({"kind": "alert", "job": "job-9"})
        self.assertEqual(wake.brief_lines(records),
                         ["Wake: hana woken for job job-1 on hana-box"])

    def test_malformed_inputs_never_crash(self):
        jobs = [None, "not-a-job", {"id": "job-1"},
                {"addressed_to": "hana"}, job("job-1", "hana")]
        agents = [None, "not-an-agent", {"nick": "hana"},
                  hana_agent()]
        new = wake.wake_tick(jobs, agents, ["not-a-record"], T0)
        self.assertEqual([record["job"] for record in new], ["job-1"])
        self.assertEqual(wake.wake_tick(None, None, None, T0), [])
        self.assertEqual(wake.brief_lines(None), [])

    def test_module_imports_no_socket_bus_or_network(self):
        path = os.path.join("intel", "wake.py")
        with open(path) as handle:
            tree = ast.parse(handle.read())
        banned = {"socket", "urllib", "requests", "redis", "subprocess"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0]
                         for alias in node.names}
                self.assertFalse(names & banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], banned)

    def test_drill_exists_and_passes(self):
        result = subprocess.run(
            [sys.executable, "intel/drills/wake.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("6/6 phases PASS", result.stdout)

    def test_new_files_carry_no_em_dash(self):
        for path in NEW_FILES:
            with open(path) as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
