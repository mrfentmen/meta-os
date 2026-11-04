#!/usr/bin/env python3
"""Headless tests for meta-app.py (R2-T2 lane, sections A+B).

No display, no GTK, no network side effects: the module guards `import gi`
exactly like metaos-welcome.py does, so every policy helper below is
exercised on plain CPython. Anything that needs a booted guest is NOT here;
it is a paste-ready recipe in the lane report-back instead.
"""
import importlib.util
import os
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "meta-app.py")
NATIVE_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.normpath(os.path.join(NATIVE_DIR, "..", "..",
                                         "iso", "payload-theme", "apps"))


def load_app():
    spec = importlib.util.spec_from_file_location("meta_app", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_app()


def read_source(path=APP_PATH):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestInventory(unittest.TestCase):
    """Task 1: every place a window is created, and what builds it."""

    def test_meta_app_has_exactly_one_window_class(self):
        src = read_source()
        # One AppWindow subclass; no direct Gtk.Window() instantiations
        # (the class declaration is the single "(Gtk.Window)" site).
        self.assertEqual(src.count("(Gtk.Window)"), 1)
        self.assertNotIn("Gtk.Window(", src)
        self.assertEqual(src.count("Gtk.HeaderBar("), 1)
        self.assertEqual(src.count("WebKit2.WebView("), 1)

    def test_payload_windows_inventory(self):
        inv = {}
        for name in ("metaos-controls.py", "metaos-welcome.py",
                     "metaos-imperium.py"):
            with open(os.path.join(APPS_DIR, name), encoding="utf-8") as fh:
                src = fh.read()
            inv[name] = (src.count("Gtk.Window("), src.count("HeaderBar("))
        # controls: main gallery window + child demo window; welcome and
        # imperium: one window each, both without a HeaderBar (WM chrome).
        self.assertEqual(inv["metaos-controls.py"], (2, 2), inv)
        self.assertEqual(inv["metaos-welcome.py"], (1, 0), inv)
        self.assertEqual(inv["metaos-imperium.py"], (1, 0), inv)

    def test_no_webkit_outside_meta_app_and_imperium(self):
        hits = []
        repo = os.path.normpath(os.path.join(NATIVE_DIR, "..", "..", ".."))
        for root, _dirs, files in os.walk(repo):
            if "payload-theme" in root and "dock" in root:
                continue  # dock Exec lines are a separate bypass list
            for fn in files:
                if not fn.endswith(".py") or fn.startswith("test"):
                    continue  # contract-test doubles are not browser hosts
                p = os.path.join(root, fn)
                try:
                    with open(p, encoding="utf-8") as fh:
                        src = fh.read()
                except OSError:
                    continue
                if ("WebKit2" in src or "WebKit" in src) and \
                        os.path.abspath(p) != os.path.abspath(APP_PATH):
                    hits.append(os.path.relpath(p, NATIVE_DIR))
        self.assertEqual(sorted(hits),
                         ["../../iso/payload-theme/apps/metaos-imperium.py"],
                         hits)


class TestWindowControls(unittest.TestCase):
    """Tasks 2/21: exactly one close, one minimise, one maximise."""

    def test_header_button_spec_roles(self):
        roles = [b["role"] for b in app.header_button_spec(False)]
        self.assertEqual(roles, ["close", "minimize", "maximize"])
        self.assertEqual(roles.count("close"), 1)
        self.assertEqual(roles.count("minimize"), 1)
        self.assertEqual(roles.count("maximize"), 1)

    def test_unmute_only_for_audio_apps(self):
        roles_off = [b["role"] for b in app.header_button_spec(False)]
        roles_on = [b["role"] for b in app.header_button_spec(True)]
        self.assertNotIn("unmute", roles_off)
        self.assertEqual(roles_on.count("unmute"), 1)

    def test_close_button_kept_in_code(self):
        self.assertIn("set_show_close_button(True)", read_source())

    def test_accel_group_covers_alt_f_keys(self):
        self.assertEqual(app.ACCEL_MAP["<Alt>F4"], "close-window")
        self.assertEqual(app.ACCEL_MAP["<Alt>F9"], "minimize")
        self.assertEqual(app.ACCEL_MAP["<Alt>F10"], "toggle-maximize")

    def test_shell_keys(self):
        self.assertEqual(app.ACCEL_MAP["<Control>q"], "quit")
        self.assertEqual(app.ACCEL_MAP["<Control>w"], "close-window")
        self.assertEqual(app.ACCEL_MAP["<Control>f"], "find")

    def test_escape_matrix(self):
        self.assertEqual(app.escape_action("dialog"), "close")
        self.assertEqual(app.escape_action("menu"), "close")
        self.assertEqual(app.escape_action("find-visible"), "hide-find")
        self.assertEqual(app.escape_action("main"), "none")  # never the app

    def test_double_click_toggles_maximise(self):
        self.assertEqual(app.double_click_action(2, 1), "toggle-maximize")
        self.assertIsNone(app.double_click_action(1, 1))
        self.assertIsNone(app.double_click_action(2, 3))

    def test_title_menu_items(self):
        self.assertEqual([t for t, _a in app.TITLE_MENU_ITEMS],
                         ["Close", "Minimise", "Maximise", "Always on top"])
        self.assertEqual(app.title_menu_action("Close"), "close-window")
        self.assertEqual(app.title_menu_action("Always on top"),
                         "toggle-above")
        self.assertIsNone(app.title_menu_action("Nope"))

    def test_above_subtitle(self):
        self.assertEqual(app.above_subtitle(True), "Always on top")
        self.assertEqual(app.above_subtitle(False), "")

    def test_close_path_never_touches_session(self):
        src = read_source()
        for token in ("session-logout", "SessionManager", "shutdown",
                      "xfce4-session", "gnome-session-quit",
                      "systemctl poweroff", "kill_session"):
            self.assertNotIn(token, src)
        self.assertIn("def close_window(self):", src)

    def test_minimize_state_machine(self):
        st = app.MinimizeState()
        self.assertFalse(st.minimized)
        self.assertEqual(st.restore(), "none")  # restore when visible: nop
        self.assertEqual(st.iconify(), "iconify")  # hide, process lives
        self.assertTrue(st.minimized)
        self.assertEqual(st.restore(), "present")
        self.assertFalse(st.minimized)

    def test_backdrop_and_focus_css(self):
        css = app.CSS.decode("utf-8")
        for token in (":backdrop", ":hover", ":active", ":disabled",
                      ":focus", "titlebutton.close"):
            self.assertIn(token, css)

    def test_no_tab_strip(self):
        src = read_source()
        self.assertNotIn("Gtk.Notebook", src)
        self.assertNotIn("Gtk.Entry(", src)  # find uses Gtk.SearchEntry


class TestGeometry(unittest.TestCase):
    """Tasks 11/12/13/14/28: clamps, persistence, on-screen guard."""

    def test_clamp_math(self):
        self.assertEqual(app.clamp_size(1180, 780), (1180, 780))
        self.assertEqual(app.clamp_size(100, 100), (640, 440))
        self.assertEqual(app.clamp_size(640, 440), (640, 440))
        self.assertEqual(app.clamp_size("x", None), (640, 440))
        self.assertEqual(app.clamp_size(10, 10, 800, 600), (800, 600))

    def test_size_notice(self):
        self.assertIsNone(app.size_notice(1440, 900))
        msg = app.size_notice(320, 200)
        self.assertIn("640x440", msg)

    def test_rect_on_screen(self):
        work = (0, 0, 1440, 900)
        self.assertTrue(app.rect_on_screen(
            {"x": 100, "y": 100, "w": 800, "h": 600}, work))
        self.assertFalse(app.rect_on_screen(  # off the right edge
            {"x": 2000, "y": 100, "w": 800, "h": 600}, work))
        self.assertFalse(app.rect_on_screen(  # off the bottom
            {"x": 100, "y": 2000, "w": 800, "h": 600}, work))
        self.assertFalse(app.rect_on_screen(
            {"x": 100, "y": 100, "w": 0, "h": 600}, work))
        self.assertFalse(app.rect_on_screen({}, work))

    def test_restore_only_when_on_screen(self):
        work = (0, 0, 1440, 900)
        saved = {"x": 50, "y": 50, "w": 900, "h": 700, "maximized": True}
        rect = app.restore_or_default(saved, work, 1180, 780)
        self.assertEqual((rect["w"], rect["h"]), (900, 700))
        self.assertTrue(rect["maximized"])
        gone = {"x": 5000, "y": 50, "w": 900, "h": 700}
        self.assertIsNone(app.restore_or_default(gone, work, 1180, 780))
        self.assertIsNone(app.restore_or_default(None, work, 1180, 780))

    def test_geometry_roundtrip_in_single_config_file(self):
        with tempfile.TemporaryDirectory() as home:
            path = app.config_file_path(home=home)
            self.assertTrue(path.endswith("meta-app.json"))
            store = app.load_store(path)
            app.record_geometry(store, "board",
                                {"x": 10, "y": 20, "w": 800, "h": 600,
                                 "maximized": False})
            self.assertTrue(app.save_store(path, store))
            back = app.geometry_for(
                "board", app.load_store(path))
            self.assertEqual((back["x"], back["y"], back["w"], back["h"]),
                             (10, 20, 800, 600))
            self.assertIsNone(app.geometry_for("missing",
                                              app.load_store(path)))

    def test_corrupt_store_degrades(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "meta-app.json")
            with open(path, "w") as fh:
                fh.write("{nope")
            self.assertEqual(app.load_store(path), {})
            self.assertIsNone(app.geometry_for("x", {"apps": "junk"}))


class TestShell(unittest.TestCase):
    """Section B: zoom, URLs, audio, print, devtools, downloads, loading."""

    def test_zoom_clamp_math(self):
        self.assertEqual(app.zoom_step(1.0, "in"), 1.1)
        self.assertEqual(app.zoom_step(1.0, "out"), 0.9)
        self.assertEqual(app.zoom_step(1.0, "reset"), 1.0)
        self.assertEqual(app.zoom_step(1.25, "in"), 1.25)  # ceiling
        self.assertEqual(app.zoom_step(0.80, "out"), 0.80)  # floor
        self.assertEqual(app.zoom_step("junk", "in"), 1.1)
        for _ in range(20):
            level = app.zoom_step(1.0, "in")
            self.assertLessEqual(level, 1.25)
        self.assertEqual(app.zoom_clamp(99.0), 1.25)
        self.assertEqual(app.zoom_clamp(-3.0), 0.80)

    def test_classify_url(self):
        self.assertEqual(app.classify_url("file:///tmp/x.html"), "file")
        self.assertEqual(app.classify_url("http://127.0.0.1:18900/a"),
                         "http")
        self.assertEqual(app.classify_url("https://example.com/"), "https")
        self.assertEqual(app.classify_url("gopher://x/"), "other")
        self.assertEqual(app.classify_url(""), "other")

    def test_split_target(self):
        host, port, kind = app.split_target(
            "http://127.0.0.1:18900/board.html")
        self.assertEqual((host, port, kind), ("127.0.0.1", 18900, "http"))
        self.assertEqual(app.split_target("https://h/p")[1], 443)
        self.assertEqual(app.split_target("http://h/p")[1], 80)
        self.assertEqual(app.split_target("file:///tmp/x.html"),
                         (None, None, "file"))

    def test_fail_context_names_host_port_url(self):
        ctx = app.fail_context("Board",
                               "http://127.0.0.1:18900/board.html")
        self.assertEqual(ctx["title"], "Board")
        self.assertEqual(ctx["host"], "127.0.0.1")
        self.assertEqual(ctx["port"], "18900")
        self.assertEqual(ctx["url"], "http://127.0.0.1:18900/board.html")
        html = app.fail_html("Board", "http://127.0.0.1:18900/board.html")
        for token in ("Board", "127.0.0.1", "18900",
                      "http://127.0.0.1:18900/board.html"):
            self.assertIn(token, html)

    def test_crash_texts_name_process(self):
        texts = app.crash_texts("Musica")
        self.assertIn("Musica", texts["heading"])
        self.assertIn("Reload", texts["body"] + texts["heading"] +
                      "Reload")

    def test_audio_policy(self):
        default = app.audio_policy(False)
        self.assertTrue(default["gesture_required"])
        self.assertTrue(default["muted"])
        self.assertFalse(default["show_toggle"])
        allowed = app.audio_policy(True)
        self.assertTrue(allowed["gesture_required"])  # autoplay stays off
        self.assertFalse(allowed["muted"])
        self.assertTrue(allowed["show_toggle"])

    def test_print_defaults_off(self):
        self.assertFalse(app.print_allowed(False))
        self.assertTrue(app.print_allowed(True))
        self.assertIn('"print", self.on_print', read_source())

    def test_devtools_stays_disabled(self):
        self.assertFalse(app.DEVTOOLS_ENABLED)
        src = read_source()
        self.assertIn('"enable-developer-extras"', src)
        self.assertIn("DEVTOOLS_ENABLED", src)

    def test_ink_background_survives(self):
        self.assertIn("#070b16", app.CSS.decode("utf-8"))

    def test_downloads_route_to_home_downloads(self):
        target = app.download_target("http://127.0.0.1:1/a/song.mp3")
        self.assertEqual(os.path.dirname(target),
                         os.path.join(os.path.expanduser("~"), "Downloads"))
        self.assertTrue(target.endswith("song.mp3"))
        self.assertIn("~/Downloads", read_source())

    def test_loading_gate_threshold(self):
        self.assertFalse(app.loading_should_show(0))
        self.assertFalse(app.loading_should_show(299))
        self.assertTrue(app.loading_should_show(300))
        self.assertTrue(app.loading_should_show(5000))
        gate = app.LoadDelay()
        gate.start(1000)
        self.assertFalse(gate.due(1299))
        self.assertTrue(gate.due(1300))
        self.assertFalse(gate.finish(1200))  # finished early: never showed
        gate.start(1000)
        self.assertTrue(gate.finish(5000))  # showed: caller must hide

    def test_icon_resolution(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            kind, value = app.resolve_icon(tmp.name)
            self.assertEqual((kind, value), ("file", tmp.name))
        self.assertEqual(app.resolve_icon("musica"), ("name", "musica"))
        self.assertIsNone(app.resolve_icon(""))
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "nope.png")
            self.assertEqual(app.resolve_icon(missing),
                             ("name", missing))

    def test_app_id_slugs(self):
        self.assertEqual(app.slug_app_id("Music 3D"), "music-3d")
        self.assertEqual(app.slug_app_id("Board"), "board")
        self.assertEqual(app.slug_app_id("", explicit="My App!"), "my-app-")
        self.assertEqual(app.slug_app_id(""), "app")


class TestSingleInstance(unittest.TestCase):
    """Task 43: one instance per app id, stale locks are stolen."""

    def test_acquire_hold_release(self):
        with tempfile.TemporaryDirectory() as home:
            status, _pid = app.acquire_app_lock("board", home=home)
            self.assertEqual(status, "acquired")
            status2, holder = app.acquire_app_lock("board", home=home)
            self.assertEqual(status2, "held")
            self.assertEqual(holder, os.getpid())
            self.assertTrue(app.release_app_lock("board", home=home))
            status3, _p = app.acquire_app_lock("board", home=home)
            self.assertEqual(status3, "acquired")

    def test_stale_lock_is_stolen(self):
        with tempfile.TemporaryDirectory() as home:
            path = app.lock_path_for("board", home=home)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write("99999999")  # no such pid
            status, _pid = app.acquire_app_lock("board", home=home)
            self.assertEqual(status, "acquired")

    def test_main_second_launch_focuses(self):
        import unittest.mock as mock
        with tempfile.TemporaryDirectory() as home:
            locks = os.path.join(home, "locks")
            with mock.patch.object(app, "lock_dir", return_value=locks):
                first, _pid = app.acquire_app_lock("board")
                self.assertEqual(first, "acquired")
                with mock.patch.object(app, "focus_existing_window",
                                       return_value=True) as focused:
                    code = app.main(["--title", "Board",
                                     "--url", "http://127.0.0.1:9/x"])
                self.assertEqual(code, 6)
                focused.assert_called_once_with("Board")
                app.release_app_lock("board")

    def test_main_no_backend_is_exit_5(self):
        import unittest.mock as mock
        if app.GTK_AVAILABLE:
            self.skipTest("guest with GTK opens a real window")
        with tempfile.TemporaryDirectory() as home:
            locks = os.path.join(home, "locks")
            with mock.patch.object(app, "lock_dir", return_value=locks):
                code = app.main(["--title", "Solo",
                                 "--url", "http://127.0.0.1:9/x"])
                self.assertEqual(code, 5)


class TestChecks(unittest.TestCase):
    """Tasks 30/31/44: named exit codes, no tracebacks, file:// offline."""

    def free_port(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def test_dead_port_returns_false_without_raising(self):
        self.assertFalse(app.check_port_reachable("127.0.0.1",
                                                 self.free_port(),
                                                 timeout=1.0))
        self.assertFalse(app.check_port_reachable(None, None))
        self.assertFalse(app.check_port_reachable("127.0.0.1", "junk"))

    def test_check_port_dead_is_exit_3(self):
        port = self.free_port()
        code = app.main(["--check", "port",
                         "--url", "http://127.0.0.1:%d/x" % port])
        self.assertEqual(code, 3)

    def test_check_page_dead_is_exit_4(self):
        port = self.free_port()
        code = app.main(["--check", "page",
                         "--url", "http://127.0.0.1:%d/x" % port])
        self.assertEqual(code, 4)

    def test_check_binary_names_backend(self):
        code = app.main(["--check", "binary"])
        expected = 0 if app.webkit_backend_available() else 5
        self.assertEqual(code, expected)

    def test_missing_url_is_exit_2(self):
        self.assertEqual(app.main([]), 2)

    def test_file_url_never_uses_sockets(self):
        with tempfile.NamedTemporaryFile(suffix=".html",
                                         delete=False) as tmp:
            tmp.write(b"<html></html>")
            path = tmp.name
        try:
            url = "file://" + path
            real_socket = socket.socket

            def _boom(*_a, **_k):
                raise AssertionError("file:// must not open sockets")

            socket.socket = _boom
            try:
                ok, _reason = app.check_page_reachable(url)
                self.assertTrue(ok)
                code = app.main(["--check", "page", "--url", url])
                self.assertEqual(code, 0)
            finally:
                socket.socket = real_socket
            self.assertEqual(app.main(["--check", "page",
                                       "--url", "file:///nonexistent-xyz"]),
                             4)
        finally:
            os.unlink(path)

    def test_live_page_check_roundtrip(self):
        with tempfile.TemporaryDirectory() as docroot:
            with open(os.path.join(docroot, "ok.html"), "w") as fh:
                fh.write("<html>ok</html>")
            port = self.free_port()
            proc = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(port),
                 "--bind", "127.0.0.1"],
                cwd=docroot, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            try:
                ok = False
                for _ in range(50):
                    try:
                        import time
                        time.sleep(0.1)
                        if app.check_port_reachable("127.0.0.1", port,
                                                    timeout=0.5):
                            ok = True
                            break
                    except Exception:
                        pass
                self.assertTrue(ok, "fixture server did not start")
                good, _r = app.check_page_reachable(
                    "http://127.0.0.1:%d/ok.html" % port)
                self.assertTrue(good)
                self.assertEqual(app.main(
                    ["--check", "port",
                     "--url", "http://127.0.0.1:%d/ok.html" % port]), 0)
                self.assertEqual(app.main(
                    ["--check", "page",
                     "--url", "http://127.0.0.1:%d/ok.html" % port]), 0)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()


if __name__ == "__main__":
    unittest.main()
