#!/usr/bin/env python3
"""Headless tests: dead port shows the named error and Retry works (lane R2-T2,
E/87; implements section B tasks 24, 25, 30, 31).

Honest option chosen: (a) — direct tests against the importable --check path
and error-screen builder. Sections A/B factored both into pure helpers
(split_target, fail_context, fail_html, check_port_reachable,
check_page_reachable, build_arg_parser, run_check) that load with gi absent;
main() serves --check before touching GTK. On this macOS box GTK_AVAILABLE is
False, so every assertion below executes the shipped code headless — real
sockets against real loopback listeners, no stubs, no tracebacks.

What this proves headless (real logic):
  * --check exists with binary/port/page modes and documented named exit
    codes (task 30): 0 ok, 3 port down, 4 page unreachable, 5 backend
    missing (this box), 2 usage. Missing ports exit named, never traceback
    (task 31).
  * fail_context/fail_html name the host, the port AND the failing URL
    (task 24); the dead screen's copy names Retry.
  * Retry re-requests only the failed page: the GTK wiring
    (deadbar "Retry" -> web.load_uri(self.url)) is verified present in the
    AppWindow source; the live click needs a display, hence guest D2.
What still needs a booted guest: the visible Retry click, the Copy URL
button paste, the named exit code from a real dead-port process launch, and
the error-screen screenshot. See GUEST_STEPS / --guest.

Usage: python3 test-dead-port.py            (unittest, exit != 0 on fail)
       python3 test-dead-port.py --guest    (print the guest test only)
"""
import importlib.util
import io
import os
import socket
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP_PATH = os.path.join(_HERE, "meta-app.py")

DEAD_HOST = "127.0.0.1"
DEAD_URL = "http://127.0.0.1:19999/board.html"  # nothing listens here


def load_app_module():
    spec = importlib.util.spec_from_file_location("meta_app_live", _APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_app_module()
if app.GTK_AVAILABLE:
    raise SystemExit("unexpected: GTK importable on the headless prover")


def _free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((DEAD_HOST, 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _QuietHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>board</body></html>")

    def log_message(self, *args):
        pass


GUEST_STEPS = """Guest proof for dead-port error + Retry (needs a booted MetaOS guest):
  D1. With NO backend on 19999 (verify: `ss -ltn | grep 19999` prints
      nothing), run:
       meta-app --title Board --url http://127.0.0.1:19999/board.html &
      Expect the window to show a Meta-styled error naming host (127.0.0.1),
      port (19999), and the failing URL — never a WebKit error page and never
      a raw traceback on screen.
  D2. The error screen shows a Retry button. Start the backend, click Retry.
      Expect: ONLY the failed page is re-requested (no new window — record
      `xdotool getactivewindow` before/after, must be identical) and the app
      content appears.
  D3. --check modes with the backend down and up (documented exit codes):
       meta-app --check binary; echo $?                # 0: backend present
       meta-app --check port --url URL; echo $?        # 3 down / 0 up
       meta-app --check page --url URL; echo $?        # 4 down / 0 up
      A missing port must exit with the NAMED code (task 31), never a
      Python traceback.
  D4. Copy URL button (ships with the same error screen per task 26): click
      it, paste into a terminal: must equal the failing URL exactly.
  D5. Screenshot the error screen for the lane report:
       gnome-screenshot -w -f /tmp/t2-dead-port.png
"""


class TestCheckSurface(unittest.TestCase):
    def test_check_modes_exist_with_documented_codes(self):
        # Section B task 30.
        ap = app.build_arg_parser()
        actions = {a.dest: a for a in ap._actions}
        self.assertIn("check", actions)
        self.assertEqual(set(actions["check"].choices),
                         {"binary", "port", "page"})
        self.assertIn("exit codes", ap.epilog)

    def test_exit_codes_are_named(self):
        # Section B task 31: every failure has a named code, docs agree.
        self.assertEqual(
            (app.EXIT_OK, app.EXIT_RUNTIME, app.EXIT_USAGE,
             app.EXIT_PORT_DOWN, app.EXIT_PAGE_DOWN, app.EXIT_NO_BACKEND,
             app.EXIT_ALREADY_RUNNING), (0, 1, 2, 3, 4, 5, 6))
        for code, text in app.EXIT_DESCRIPTIONS.items():
            self.assertTrue(text, code)

    def test_binary_check_reports_missing_backend_here(self):
        # This box has no GTK/WebKit2: the named exit 5, with words.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.run_check("binary", app.build_arg_parser().parse_args(
                ["--check", "binary"]))
        self.assertEqual(rc, app.EXIT_NO_BACKEND)
        self.assertIn("backend missing", err.getvalue())
        self.assertFalse(app.webkit_backend_available())


class TestPortCheck(unittest.TestCase):
    def test_dead_port_is_named_not_traceback(self):
        # Section B task 31: dead localhost port -> exit 3, no traceback.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.main(["--check", "port", "--url", DEAD_URL])
        combined = out.getvalue() + err.getvalue()
        self.assertEqual(rc, app.EXIT_PORT_DOWN)
        self.assertIn("19999", combined)
        self.assertNotIn("Traceback", combined)

    def test_live_port_checks_out(self):
        # Real listener on loopback: the same path must report ok. The
        # listener runs an accept loop: without it, a second SYN against an
        # unaccepted backlog is refused on macOS and the re-check flakes.
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((DEAD_HOST, 0))
        srv.listen(5)
        stop = threading.Event()

        def _accept_loop():
            srv.settimeout(0.2)
            while not stop.is_set():
                try:
                    conn, _addr = srv.accept()
                    conn.close()
                except socket.timeout:
                    pass
                except OSError:
                    break

        thread = threading.Thread(target=_accept_loop, daemon=True)
        thread.start()
        try:
            port = srv.getsockname()[1]
            self.assertTrue(app.check_port_reachable(DEAD_HOST, port))
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = app.main(
                    ["--check", "port",
                     "--url", "http://%s:%d/x" % (DEAD_HOST, port)])
            self.assertEqual(rc, app.EXIT_OK)
        finally:
            stop.set()
            thread.join(timeout=5)
            srv.close()

    def test_garbage_target_is_named_usage(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.main(["--check", "port", "--url", "not a url"])
        self.assertEqual(rc, app.EXIT_USAGE)
        self.assertNotIn("Traceback", out.getvalue() + err.getvalue())


class TestPageCheck(unittest.TestCase):
    def test_dead_page_is_named_not_traceback(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.main(["--check", "page", "--url", DEAD_URL])
        self.assertEqual(rc, app.EXIT_PAGE_DOWN)
        self.assertNotIn("Traceback", out.getvalue() + err.getvalue())

    def test_file_page_is_a_stat_never_a_socket(self):
        # Section B task 44: file:// pages never touch the network.
        with tempfile.NamedTemporaryFile("w", suffix=".html",
                                         delete=False) as tmp:
            tmp.write("<html></html>")
            path = tmp.name
        try:
            ok, reason = app.check_page_reachable("file://" + path)
            self.assertTrue(ok, reason)
            ok, reason = app.check_page_reachable(
                "file:///nonexistent-t2-missing.html")
            self.assertFalse(ok)
            self.assertIn("file not found", reason)
        finally:
            os.unlink(path)

    def test_live_http_page_checks_out(self):
        # Real loopback HTTP 200 through the real check path.
        srv = HTTPServer((DEAD_HOST, 0), _QuietHandler)
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever,
                                  kwargs={"poll_interval": 0.05},
                                  daemon=True)
        thread.start()
        try:
            ok, reason = app.check_page_reachable(
                "http://%s:%d/board.html" % (DEAD_HOST, port))
            self.assertTrue(ok, reason)
        finally:
            srv.shutdown()
            thread.join(timeout=5)


class TestErrorScreen(unittest.TestCase):
    def test_fail_context_names_host_port_url(self):
        # Section B task 24: the named error screen data.
        ctx = app.fail_context("Board", DEAD_URL)
        self.assertEqual(ctx["title"], "Board")
        self.assertEqual(ctx["host"], DEAD_HOST)
        self.assertEqual(ctx["port"], "19999")
        self.assertEqual(ctx["url"], DEAD_URL)

    def test_fail_html_carries_all_four(self):
        html = app.fail_html("Board", DEAD_URL)
        for token in ("Board", DEAD_HOST, "19999", DEAD_URL):
            self.assertIn(token, html)
        self.assertIn("Retry", html)

    def test_retry_rerequests_only_failed_page(self):
        # Section B task 25: the Retry control exists on the dead screen and
        # is wired to re-request exactly the failed URL. The widget click
        # itself needs a display (guest D2); what is honestly assertable
        # headless is that the wiring is present in the shipped AppWindow.
        with open(_APP_PATH, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn('deadbar.add_button("Retry"', src)
        self.assertIn("if response == 1:", src)
        self.assertIn("self.web.load_uri(self.url)", src)

    def test_missing_url_still_exits_named(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = app.main(["--title", "Board"])
        self.assertEqual(rc, app.EXIT_USAGE)
        self.assertNotIn("Traceback", out.getvalue() + err.getvalue())

    def test_guest_steps_documented(self):
        self.assertIn("Retry", GUEST_STEPS)
        self.assertIn("--check", GUEST_STEPS)


if __name__ == "__main__":
    if "--guest" in sys.argv:
        sys.stdout.write(GUEST_STEPS)
    else:
        unittest.main()
