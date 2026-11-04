#!/usr/bin/env python3
"""Headless tests: second launch focuses instead of duplicating (lane R2-T2,
E/86; implements section B task 43).

Honest option chosen: (a) — direct tests against the importable single-
instance logic. Sections A/B factored the lock/id policy into pure helpers
(slug_app_id, lock_path_for, pid_alive, acquire/release_app_lock) that load
with gi absent, and main() runs the whole second-launch path — lock check,
"already running" message, named exit 6 — before touching GTK. On this macOS
box GTK_AVAILABLE is False, so every assertion below executes the shipped
code headless with zero stubs.

What this proves headless (real logic, real files in a temp HOME):
  * App-id derivation: explicit --app-id wins, else slug of --title.
  * First launch acquires; a second acquire reports ("held", holder pid);
    stale locks (dead pid) are stolen; foreign live locks are respected;
    release drops only our own lock.
  * main() with a pre-held lock returns EXIT_ALREADY_RUNNING (6) with an
    "already running" message and opens no window; main() with a free lock
    and no backend returns EXIT_NO_BACKEND (5), never a traceback.
What still needs a booted guest: the wmctrl focus raise actually moving
focus to the existing window (focus_existing_window returns False here —
no wmctrl on this box), and the one-window-per-app-id pixel check.
See GUEST_STEPS / --guest.

Usage: python3 test-single-instance.py            (unittest, exit != 0 on fail)
       python3 test-single-instance.py --guest    (print the guest test only)
"""
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_PATH = os.path.join(_HERE, "meta-app.py")


def load_app_module():
    spec = importlib.util.spec_from_file_location("meta_app_live", _APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_app_module()
if app.GTK_AVAILABLE:
    raise SystemExit("unexpected: GTK importable on the headless prover")

GUEST_STEPS = """Guest proof for single-instance focus (needs a booted MetaOS guest):
  Pre: ensure meta-app is installed at /usr/local/bin/meta-app and the Board
       backend answers on 127.0.0.1:18900 (or use file:///usr/share/metaos
       pages if the backend is down — single-instance must not depend on it).
  S1. Launch once:
       meta-app --title Board --url http://127.0.0.1:18900/board.html &
       echo $! > /tmp/t2-first.pid; sleep 2
      Expect: one Board window, focused. Record its id:
       wmctrl -l | grep -i board | tee /tmp/t2-first-win.txt
  S2. Launch the SAME app again (same --title / same app id):
       meta-app --title Board --url http://127.0.0.1:18900/board.html &
       sleep 2
      Expect: NO second window. Window count is unchanged:
       wmctrl -l | grep -ci board        # must still be 1
      and the existing window is focused/raised (check _NET_ACTIVE_WINDOW):
       xdotool getactivewindow; xdotool getwindowname $(xdotool getactivewindow)
       # must name the Board window from S1.
      Second process exits 6 (already running, focused).
  S3. Launch a DIFFERENT app (e.g. --title Notes): expect a second window —
      grouping is per app id, never per page title (section C task 49).
  S4. Kill the first instance (close its window or kill $(cat /tmp/t2-first.pid)),
      relaunch: expect a fresh window (stale lock must not block relaunch).
  S5. Two rapid launches in the same second (`cmd & cmd &`): still one window.
  Cleanup: kill any meta-app PIDs you started; remove /tmp/t2-first.pid.
  Tools needed in guest: wmctrl + xdotool (apt install if absent).
"""


class _HomeEnv(object):
    """Run a block with HOME pointed at a temp dir (locks/config go there)."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="t2-single-home-")
        self.old = os.environ.get("HOME")

    def __enter__(self):
        os.environ["HOME"] = self.tmp.name
        return self.tmp.name

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.old
        self.tmp.cleanup()
        return False


class TestAppId(unittest.TestCase):
    def test_slug_from_title(self):
        self.assertEqual(app.slug_app_id("Board"), "board")
        self.assertEqual(app.slug_app_id("Meta Notes"), "meta-notes")

    def test_explicit_app_id_wins(self):
        self.assertEqual(
            app.slug_app_id("Board", explicit="my-board"), "my-board")
        self.assertEqual(
            app.slug_app_id("Board", explicit="My_Board!"), "my-board-")

    def test_empty_title_degrades(self):
        self.assertEqual(app.slug_app_id(""), "app")
        self.assertEqual(app.slug_app_id(None), "app")


class TestLockLifecycle(unittest.TestCase):
    def test_first_acquire_wins_second_is_held(self):
        with _HomeEnv():
            status, holder = app.acquire_app_lock("board")
            self.assertEqual(status, "acquired")
            self.assertEqual(holder, os.getpid())
            status2, holder2 = app.acquire_app_lock("board")
            self.assertEqual(status2, "held")
            self.assertEqual(holder2, os.getpid())

    def test_release_drops_only_own_lock(self):
        with _HomeEnv():
            app.acquire_app_lock("board")
            self.assertTrue(app.release_app_lock("board"))
            # Re-acquire after release: proves the hold file is gone.
            status, _ = app.acquire_app_lock("board")
            self.assertEqual(status, "acquired")

    def test_stale_lock_is_stolen(self):
        with _HomeEnv():
            path = app.lock_path_for("board")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="ascii") as fh:
                fh.write("42424242")  # no such pid: dead holder
            self.assertFalse(app.pid_alive(42424242))
            status, holder = app.acquire_app_lock("board")
            self.assertEqual(status, "acquired")
            self.assertEqual(holder, os.getpid())

    def test_foreign_live_lock_is_respected(self):
        with _HomeEnv():
            path = app.lock_path_for("board")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="ascii") as fh:
                fh.write("1")  # pid 1 (launchd/init): alive, not us
            self.assertTrue(app.pid_alive(1))
            status, holder = app.acquire_app_lock("board")
            self.assertEqual(status, "held")
            self.assertEqual(holder, 1)
            self.assertFalse(app.release_app_lock("board"))

    def test_lock_paths_are_per_app_per_user(self):
        with _HomeEnv():
            self.assertNotEqual(app.lock_path_for("board"),
                                app.lock_path_for("notes"))
            self.assertTrue(app.lock_path_for("board").endswith(".lock"))
            self.assertTrue(app.config_file_path().endswith("meta-app.json"))


class TestSecondLaunchMain(unittest.TestCase):
    def _run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_second_launch_returns_already_running(self):
        # The real second-launch path: lock pre-held (as a running instance
        # would hold it), main() must report and exit 6 — no window, no
        # traceback. Focus raise itself needs wmctrl, hence the guest test.
        with _HomeEnv():
            status, _ = app.acquire_app_lock("board")
            self.assertEqual(status, "acquired")
            rc, out, err = self._run_main(
                ["--title", "Board",
                 "--url", "http://127.0.0.1:19999/board.html"])
            self.assertEqual(rc, app.EXIT_ALREADY_RUNNING)
            self.assertIn("already running", out + err)
            self.assertNotIn("Traceback", out + err)

    def test_first_launch_without_backend_is_named(self):
        # No lock held, no GTK here: named exit 5, lock released behind us.
        with _HomeEnv() as home:
            rc, out, err = self._run_main(
                ["--title", "Board",
                 "--url", "http://127.0.0.1:19999/board.html"])
            self.assertEqual(rc, app.EXIT_NO_BACKEND)
            self.assertIn("backend missing", err)
            self.assertNotIn("Traceback", out + err)
            # Lock released: a fresh acquire must succeed.
            status, _ = app.acquire_app_lock("board", home=home)
            self.assertEqual(status, "acquired")

    def test_focus_helper_never_raises(self):
        self.assertIsInstance(app.focus_existing_window("Board"), bool)

    def test_guest_steps_documented(self):
        self.assertIn("wmctrl -l", GUEST_STEPS)
        self.assertIn("must still be 1", GUEST_STEPS)
        self.assertIn("S5", GUEST_STEPS)


if __name__ == "__main__":
    if "--guest" in sys.argv:
        sys.stdout.write(GUEST_STEPS)
    else:
        unittest.main()
