"""tests/test_intel_integration.py: the INT-001 integration environment.

The environment is one room (build-int), one job namespace
(muse-bus:int-job), and one capability namespace (muse-bus:int-cap),
all disjoint from production defaults and from the unit-test
prefixes. These tests pin three things a second crew member depends
on when reproducing the environment from the README alone:

1. env_for/export_lines/apply_env agree on the exact values.
2. The namespaces are read at import time: a process that sets the
   variables before importing jobs/mos.capabilities gets the
   integration prefixes, and one that does not gets the defaults.
3. State written under the integration prefixes is invisible under
   the production prefixes, and integration room announcements never
   land on the main bus.
4. The README section reproduces the export block verbatim, so the
   documented steps and the code cannot drift apart silently.
"""

import os
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import RelayTestCase  # noqa: E402
import jobs  # noqa: E402
from mos import capabilities  # noqa: E402
from intel import integration  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "intel", "README.md")
IMPORT_PROBE = (
    "import jobs; from mos import capabilities; "
    "print(jobs.NS); print(capabilities.CAPNS)"
)


class EnvForTest(unittest.TestCase):
    def test_defaults_are_the_int_constants(self):
        self.assertEqual(integration.env_for(), {
            "MUSE_RELAY_JOBNS": "muse-bus:int-job",
            "MUSE_RELAY_CAPNS": "muse-bus:int-cap",
            "MUSE_RELAY_INTEL_ROOM": "build-int",
        })
        self.assertEqual(integration.INT_ROOM, "build-int")
        self.assertEqual(integration.INT_JOBNS, "muse-bus:int-job")
        self.assertEqual(integration.INT_CAPNS, "muse-bus:int-cap")

    def test_explicit_values_override_defaults(self):
        env = integration.env_for(room="build-two",
                                  jobns="muse-bus:two-job",
                                  capns="muse-bus:two-cap")
        self.assertEqual(env["MUSE_RELAY_INTEL_ROOM"], "build-two")
        self.assertEqual(env["MUSE_RELAY_JOBNS"], "muse-bus:two-job")
        self.assertEqual(env["MUSE_RELAY_CAPNS"], "muse-bus:two-cap")

    def test_export_lines_cover_all_three_vars(self):
        lines = integration.export_lines()
        self.assertEqual(len(lines), 3)
        self.assertIn("export MUSE_RELAY_JOBNS=muse-bus:int-job", lines)
        self.assertIn("export MUSE_RELAY_CAPNS=muse-bus:int-cap", lines)
        self.assertIn("export MUSE_RELAY_INTEL_ROOM=build-int", lines)

    def test_apply_env_sets_and_returns_mapping(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for var in integration.INT_ENV_VARS:
                os.environ.pop(var, None)
            applied = integration.apply_env()
            self.assertEqual(os.environ["MUSE_RELAY_JOBNS"],
                             "muse-bus:int-job")
            self.assertEqual(os.environ["MUSE_RELAY_CAPNS"],
                             "muse-bus:int-cap")
            self.assertEqual(os.environ["MUSE_RELAY_INTEL_ROOM"],
                             "build-int")
            self.assertEqual(applied, integration.env_for())

    def test_room_bus_key_is_the_build_int_room(self):
        self.assertEqual(integration.room_bus_key(),
                         "muse-bus:room:build-int")


class ImportOrderTest(unittest.TestCase):
    def _probe(self, with_int_env):
        env = dict(os.environ)
        for var in integration.INT_ENV_VARS:
            env.pop(var, None)
        if with_int_env:
            env.update(integration.env_for())
        proc = subprocess.run(
            [sys.executable, "-c", IMPORT_PROBE],
            cwd=ROOT, env=env, capture_output=True, text=True,
            timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.split()

    def test_env_before_import_yields_int_prefixes(self):
        self.assertEqual(self._probe(True),
                         ["muse-bus:int-job", "muse-bus:int-cap"])

    def test_no_env_yields_production_defaults(self):
        self.assertEqual(self._probe(False),
                         ["muse-bus:job", "muse-bus:cap"])


class IsolationTest(RelayTestCase):
    def test_job_written_under_int_ns_invisible_under_default_ns(self):
        jobs.NS = integration.INT_JOBNS
        try:
            rc, out, _ = self.run_cli(
                jobs.main, ["post", "--title", "Int job",
                            "--spec", "s", "--room", "build-int"])
            self.assertEqual(rc, 0)
            h, _ = jobs.job_get("1")
            self.assertEqual(h["title"], "Int job")
            jobs.NS = "muse-bus:job"
            self.assertEqual(jobs.job_get("1"), (None, None))
        finally:
            jobs.NS = "muse-bus:tjob"

    def test_cap_written_under_int_ns_invisible_under_default_ns(self):
        capabilities.CAPNS = integration.INT_CAPNS
        try:
            self.assertTrue(capabilities.register("w-int", ["python"]))
            rec = capabilities.get("w-int")
            self.assertEqual(rec["caps"], "python")
            capabilities.CAPNS = "muse-bus:cap"
            self.assertIsNone(capabilities.get("w-int"))
        finally:
            capabilities.CAPNS = "muse-bus:tcap"

    def test_int_room_announcement_never_lands_on_main_bus(self):
        jobs.NS = integration.INT_JOBNS
        try:
            rc, _, _ = self.run_cli(
                jobs.main, ["post", "--title", "Int job",
                            "--spec", "s", "--room", "build-int"])
            self.assertEqual(rc, 0)
            self.assertIn("tester: JOB:1 Int job",
                          self.pushes_to("muse-bus:room:build-int"))
            self.assertEqual(self.pushes_to("muse-bus"), [])
        finally:
            jobs.NS = "muse-bus:tjob"


class ReadmePinTest(unittest.TestCase):
    def test_readme_section_reproduces_the_export_block(self):
        with open(README, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Integration environment: INT-001", text)
        self.assertIn("build-int", text)
        self.assertIn("muse-bus:int-job", text)
        self.assertIn("muse-bus:int-cap", text)
        # The import-order rule is the load-bearing warning; the
        # section must state it in plain words.
        self.assertIn("at import time", text)
        for line in integration.export_lines():
            self.assertIn(line, text)
