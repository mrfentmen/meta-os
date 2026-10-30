#!/usr/bin/env python3
"""tests/test_intel_redis_down.py: INT-009 Redis-outage CLI surface.

Pins the INT-009 fix: with the store dead, every Redis-dependent
intel.py command exits 2 with RELAY_ERROR and no traceback, and
the store-free commands still succeed. The store is killed by
patching relay_common.api_get/api_post to raise RuntimeError at
once (the real retry loop is proved by the drill script, not
re-run here: it waits out 4 curl attempts per call).

The CLI is loaded under a distinct module name because the
intel/ package shadows a plain `import intel` of root intel.py,
the same way the spark-down CLI stage does.
"""

import importlib.util
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _load_cli():
    path = os.path.join(REPO, "intel.py")
    spec = importlib.util.spec_from_file_location(
        "intel_cli_redis_down", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(cli, argv):
    """Run cli.main in-process; return (code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
    except SystemExit as exc:
        code = exc.code
    return code, out.getvalue(), err.getvalue()


class RedisDownCliTest(unittest.TestCase):
    def setUp(self):
        import relay_common as rc
        self.cli = _load_cli()
        self.rc = rc
        self.dead = mock.Mock(
            side_effect=RuntimeError(
                "request failed after 4 attempts: curl rc=7"))
        self.get_patch = mock.patch.object(rc, "api_get", self.dead)
        self.post_patch = mock.patch.object(rc, "api_post", self.dead)
        self.get_patch.start()
        self.post_patch.start()

    def tearDown(self):
        self.post_patch.stop()
        self.get_patch.stop()

    def assert_loud_failure(self, argv):
        code, out, err = _run(self.cli, argv)
        self.assertEqual(code, 2, f"{argv} exited {code}: {out!r} {err!r}")
        self.assertIn("RELAY_ERROR", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(out, "")

    def test_brief_morning_fails_loudly(self):
        # INT-009 fix: the generation block used to let the store
        # failure escape as a traceback.
        self.assert_loud_failure(
            ["brief", "--morning", "--room", "drill-room"])

    def test_brief_list_fails_loudly(self):
        self.assert_loud_failure(
            ["brief", "--list", "--room", "drill-room"])

    def test_brief_show_fails_loudly(self):
        self.assert_loud_failure(
            ["brief", "--show", "--room", "drill-room", "--ts", "10000"])

    def test_dispatch_show_fails_loudly(self):
        self.assert_loud_failure(["dispatch", "--show", "drill-missing"])

    def test_dispatch_undo_fails_loudly(self):
        self.assert_loud_failure(["dispatch", "--undo", "drill-missing"])

    def test_brief_dry_run_still_succeeds(self):
        # A dry-run brief stores nothing and the BRF-028 guard
        # fails open, so it is store-free in effect: exit 0 with
        # a template brief even with the store dead.
        code, out, err = _run(
            self.cli, ["brief", "--morning", "--room", "drill-room",
                       "--now", "10000", "--dry-run"])
        self.assertEqual(code, 0, f"dry-run exited {code}: {out!r} {err!r}")
        self.assertTrue(out.startswith("TEMPLATE"),
                        f"dry-run brief is not TEMPLATE: {out[:80]!r}")
        self.assertNotIn("Traceback", err)

    def test_snapshot_and_alerts_still_loud(self):
        # Already clean before INT-009; pinned so the drill's
        # already-clean rows cannot regress silently.
        self.assert_loud_failure(["snapshot", "--room", "drill-room"])
        self.assert_loud_failure(
            ["alerts", "--show", "--id", "drill-missing"])


if __name__ == "__main__":
    unittest.main()
