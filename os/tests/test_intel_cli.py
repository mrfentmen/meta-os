#!/usr/bin/env python3
"""tests/test_intel_cli.py — intel.py CLI surface (FND-016).

Covers exactly what FND-016 accepts: --help lists all five
subcommands (brief, dispatch, watch, alerts, snapshot); a bad
subcommand exits 2 with usage; the subcommand whose engine is
not yet landed (watch routing to Milo's loop) fails loudly
with RELAY_ERROR + UNIMPLEMENTED and exit 2 — it prints no
alert, because inventing one would be fake output. Dispatch
dry-run (DSP-006), the approval gate (DSP-007), the poster
(DSP-008), and signing with the crew-mode rule (DSP-009)
are landed and covered in test_intel_dispatch.py;
their --help surface is pinned here.
Snapshot (FND-014) is landed: with no live relay it
fails loudly with RELAY_ERROR and exit 2 instead of inventing a
snapshot, and its real output is covered by test_intel_snapshot.py
on the fake Redis surface.

These tests run intel.py as a subprocess so the CLI's own argparse
and exit codes are what get asserted. They write no files and use
no test helpers, so they run even where the sandbox blocks writes.
The live alerts --show read path (intel.store.get_alert) is covered
by the store tests, not here: it needs a Redis surface, and this
file must not invent one.
"""

import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTEL_PY = os.path.join(REPO, "intel.py")


def run_cli(*argv):
    """Run intel.py with argv; return (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, INTEL_PY, *argv],
        cwd=REPO, capture_output=True, text=True, timeout=60,
    )
    return proc.returncode, proc.stdout, proc.stderr


class IntelCliTest(unittest.TestCase):
    def test_help_lists_all_five_subcommands(self):
        code, out, _err = run_cli("--help")
        self.assertEqual(code, 0)
        for name in ("brief", "dispatch", "watch", "alerts", "snapshot"):
            self.assertIn(name, out)

    def test_bad_subcommand_exits_2_with_usage(self):
        code, _out, err = run_cli("frobnicate")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_no_subcommand_exits_2(self):
        code, _out, err = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("required", err)

    def test_brief_help_still_works(self):
        # Hana's brief subcommand must survive the FND-016 extension.
        code, out, _err = run_cli("brief", "--help")
        self.assertEqual(code, 0)
        self.assertIn("--list", out)
        self.assertIn("--show", out)

    def test_dispatch_posting_without_plan_fails_loudly(self):
        # DSP-007: posting needs the plan under review; no plan
        # is invented from the goal alone, so a posting run
        # without --plan fails loudly before any approval gate.
        code, out, err = run_cli("dispatch", "--goal", "add a test")
        self.assertEqual(code, 2)
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("--plan", err)
        self.assertNotIn("jobs", out)

    def test_dispatch_without_goal_is_usage_error(self):
        code, _out, err = run_cli("dispatch")
        self.assertEqual(code, 2)
        self.assertIn("--goal", err)

    def test_dispatch_help_lists_dry_run_options(self):
        code, out, _err = run_cli("dispatch", "--help")
        self.assertEqual(code, 0)
        self.assertIn("--dry-run", out)
        self.assertIn("--plan", out)
        self.assertIn("--approve", out)

    def test_watch_without_engine_fails_loudly(self):
        code, out, err = run_cli("watch")
        self.assertEqual(code, 2)
        self.assertIn("RELAY_ERROR", err)
        self.assertIn("UNIMPLEMENTED", err)
        self.assertEqual(out, "")

    def test_snapshot_without_live_relay_fails_loudly(self):
        # FND-014 landed: the engine exists, so the failure here is
        # the missing live backend, not a missing engine — and no
        # invented snapshot may appear on stdout.
        code, out, err = run_cli("snapshot")
        self.assertEqual(code, 2)
        self.assertIn("RELAY_ERROR", err)
        self.assertNotIn("UNIMPLEMENTED", err)
        self.assertEqual(out, "")

    def test_alerts_show_needs_id(self):
        code, _out, err = run_cli("alerts", "--show")
        self.assertEqual(code, 2)
        self.assertIn("--id", err)

    def test_alerts_needs_a_flag(self):
        code, _out, err = run_cli("alerts")
        self.assertEqual(code, 2)
        self.assertIn("--show", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
