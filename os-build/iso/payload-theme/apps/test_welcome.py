#!/usr/bin/env python3
"""Unit tests for metaos-welcome.py. Headless: no display needed.

GTK import is guarded inside the app module (GTK_AVAILABLE=False when
gi is absent), so this file runs under plain `python3 -m unittest`.
GDK_BACKEND=test is set as a belt-and-braces measure for environments
where gi exists but no X server does.
"""
import configparser
import importlib.util
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("GDK_BACKEND", "test")

APPS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(APPS_DIR, "metaos-welcome.py")
DESKTOP_PATH = os.path.join(APPS_DIR, "metaos-welcome.desktop")


def load_app_module():
    spec = importlib.util.spec_from_file_location("metaos_welcome", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


welcome = load_app_module()


class FakeAppInfo(object):
    launched = []

    def __init__(self, ok=True):
        self._ok = ok

    def launch(self, files, ctx):
        if not self._ok:
            raise RuntimeError("launch failed")
        FakeAppInfo.launched.append(True)
        return True


class FakeDesktopAppInfo(object):
    available = {}

    @staticmethod
    def new(app_id):
        if app_id in FakeDesktopAppInfo.available:
            return FakeAppInfo(ok=FakeDesktopAppInfo.available[app_id])
        return None


class FakeGio(object):
    DesktopAppInfo = FakeDesktopAppInfo


class TestImport(unittest.TestCase):
    def test_module_loads_and_exports(self):
        for symbol in ("get_system_info", "get_os_name", "get_hostname",
                       "get_memory_text", "find_metafetch_script",
                       "get_metafetch_text", "launch_entry",
                       "on_launch_clicked", "on_dismiss_clicked",
                       "on_brand_draw", "brand_css", "build_window",
                       "should_show", "mark_shown", "main",
                       "QUICK_LAUNCH", "GTK_AVAILABLE"):
            self.assertTrue(hasattr(welcome, symbol), symbol)

    def test_brand_tokens_match_contract(self):
        self.assertEqual(welcome.BRAND_BLUE, "#1877F2")
        self.assertEqual(welcome.BRAND_WHITE, "#EDF5FF")
        self.assertEqual(welcome.BRAND_BLACK, "#070B16")

    def test_css_carries_brand_colors(self):
        css = welcome.brand_css()
        for token in ("#1877F2", "#EDF5FF", "#070B16"):
            self.assertIn(token, css)


class TestQuickLaunchTable(unittest.TestCase):
    def test_frozen_four_entries(self):
        labels = [entry["label"] for entry in welcome.QUICK_LAUNCH]
        self.assertEqual(labels, ["Files", "Terminal", "Settings", "Browser"])

    def test_each_entry_has_candidate_ids(self):
        for entry in welcome.QUICK_LAUNCH:
            self.assertTrue(entry["ids"], entry["label"])
            for app_id in entry["ids"]:
                self.assertTrue(app_id.endswith(".desktop"), app_id)


class TestSystemInfo(unittest.TestCase):
    def test_info_keys_nonempty(self):
        info = welcome.get_system_info()
        for key in ("hostname", "os", "memory"):
            self.assertIn(key, info)
            self.assertTrue(isinstance(info[key], str) and info[key], key)

    def test_os_release_pretty_name(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write('NAME="MetaOS"\nPRETTY_NAME="MetaOS 1.0"\n')
            path = tmp.name
        try:
            self.assertEqual(welcome.get_os_name(path), "MetaOS 1.0")
        finally:
            os.unlink(path)

    def test_os_release_fallback_name_version(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write('NAME="MetaOS"\nVERSION_ID="1.0"\n')
            path = tmp.name
        try:
            self.assertEqual(welcome.get_os_name(path), "MetaOS 1.0")
        finally:
            os.unlink(path)

    def test_os_release_missing_file(self):
        self.assertTrue(welcome.get_os_name("/nonexistent-os-release-xyz"))

    def test_memory_parses_gigabytes(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("MemTotal:        4024548 kB\n")
            path = tmp.name
        try:
            self.assertEqual(welcome.get_memory_text(path), "3.8 GB")
        finally:
            os.unlink(path)

    def test_memory_parses_megabytes(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("MemTotal:         500000 kB\n")
            path = tmp.name
        try:
            self.assertEqual(welcome.get_memory_text(path), "488 MB")
        finally:
            os.unlink(path)

    def test_memory_missing_file_degrades(self):
        self.assertEqual(
            welcome.get_memory_text("/nonexistent-meminfo-xyz"), "unavailable")


class TestFirstRunFlag(unittest.TestCase):
    def test_shows_once(self):
        with tempfile.TemporaryDirectory() as home:
            flag = welcome.get_flag_path(home=home)
            self.assertTrue(welcome.should_show(flag))
            self.assertTrue(welcome.mark_shown(flag))
            self.assertTrue(os.path.isfile(flag))
            self.assertFalse(welcome.should_show(flag))

    def test_mark_shown_never_raises(self):
        self.assertFalse(welcome.mark_shown("/proc/nope/flag"))


class TestMetafetch(unittest.TestCase):
    def test_no_node_hides_section(self):
        with mock.patch.object(welcome.shutil, "which", return_value=None):
            self.assertIsNone(welcome.get_metafetch_text())

    def test_no_script_hides_section(self):
        with mock.patch.object(welcome.shutil, "which",
                               return_value="/usr/bin/node"):
            with mock.patch.object(welcome, "find_metafetch_script",
                                   return_value=None):
                self.assertIsNone(welcome.get_metafetch_text())

    def test_runner_failure_hides_section(self):
        with mock.patch.object(welcome.shutil, "which",
                               return_value="/usr/bin/node"):
            with mock.patch.object(welcome, "find_metafetch_script",
                                   return_value="/tmp/x.mjs"):
                with mock.patch.object(welcome.subprocess, "run",
                                       side_effect=OSError("nope")):
                    self.assertIsNone(welcome.get_metafetch_text())

    def test_runner_output_returned(self):
        proc = mock.Mock()
        proc.returncode = 0
        proc.stdout = "  MetaOS 1.0\n"
        with mock.patch.object(welcome.shutil, "which",
                               return_value="/usr/bin/node"):
            with mock.patch.object(welcome, "find_metafetch_script",
                                   return_value="/tmp/x.mjs"):
                with mock.patch.object(welcome.subprocess, "run",
                                       return_value=proc):
                    self.assertEqual(welcome.get_metafetch_text(),
                                     "MetaOS 1.0")

    def test_find_script_env_override(self):
        with tempfile.NamedTemporaryFile("w", suffix=".mjs",
                                         delete=False) as tmp:
            path = tmp.name
        try:
            with mock.patch.dict(os.environ, {"METAFETCH_PATH": path}):
                self.assertEqual(welcome.find_metafetch_script(), path)
        finally:
            os.unlink(path)


class TestLaunch(unittest.TestCase):
    def setUp(self):
        FakeAppInfo.launched = []
        FakeDesktopAppInfo.available = {}

    def test_no_gio_degrades_false(self):
        self.assertFalse(welcome.launch_entry(["thunar.desktop"],
                                              gio_module=None)
                         if welcome.Gio is None
                         else welcome.launch_entry(["thunar.desktop"],
                                                   gio_module=object()))

    def test_all_missing_returns_false(self):
        self.assertFalse(welcome.launch_entry(["nope.desktop"],
                                              gio_module=FakeGio))

    def test_first_hit_launches(self):
        FakeDesktopAppInfo.available = {"thunar.desktop": True}
        self.assertTrue(welcome.launch_entry(
            ["missing.desktop", "thunar.desktop"], gio_module=FakeGio))
        self.assertEqual(len(FakeAppInfo.launched), 1)

    def test_failing_entry_falls_through(self):
        FakeDesktopAppInfo.available = {"bad.desktop": False,
                                       "good.desktop": True}
        self.assertTrue(welcome.launch_entry(
            ["bad.desktop", "good.desktop"], gio_module=FakeGio))

    def test_button_callback_delegates(self):
        with mock.patch.object(welcome, "launch_entry",
                               return_value=True) as launcher:
            self.assertTrue(welcome.on_launch_clicked(None, ["a.desktop"]))
            launcher.assert_called_once_with(["a.desktop"])

    def test_dismiss_marks_shown_and_closes(self):
        window = mock.Mock()
        with mock.patch.object(welcome, "mark_shown",
                               return_value=True) as marked:
            welcome.on_dismiss_clicked(None, window)
            marked.assert_called_once_with()
            window.destroy.assert_called_once_with()


class TestDesktopFile(unittest.TestCase):
    def _read(self):
        parser = configparser.ConfigParser(interpolation=None,
                                           strict=True)
        parser.optionxform = str  # keep key case
        with open(DESKTOP_PATH, encoding="utf-8") as handle:
            parser.read_file(handle)
        return parser

    def test_required_keys(self):
        parser = self._read()
        self.assertIn("Desktop Entry", parser.sections())
        section = parser["Desktop Entry"]
        for key in ("Type", "Name", "Exec", "TryExec", "Icon",
                    "OnlyShowIn", "X-GNOME-Autostart-enabled"):
            self.assertIn(key, section, key)
        self.assertEqual(section["Type"], "Application")

    def test_tryexec_points_at_own_binary(self):
        parser = self._read()
        section = parser["Desktop Entry"]
        exe = section["Exec"].split()[0]
        tried = section["TryExec"].split()[0]
        self.assertEqual(
            os.path.basename(exe), welcome.APP_FILENAME)
        self.assertEqual(exe, tried)

    def test_exec_exists_relative_to_install_prefix(self):
        parser = self._read()
        exe = parser["Desktop Entry"]["Exec"].split()[0]
        self.assertTrue(exe.startswith(welcome.INSTALL_PREFIX + "/"),
                        exe)
        repo_equivalent = os.path.join(
            APPS_DIR, os.path.basename(exe))
        self.assertTrue(os.path.isfile(repo_equivalent),
                        repo_equivalent)

    def test_autostart_first_run_flags(self):
        parser = self._read()
        section = parser["Desktop Entry"]
        self.assertIn("XFCE", section["OnlyShowIn"])
        self.assertEqual(section["X-GNOME-Autostart-enabled"].lower(),
                         "true")

    def test_main_skips_when_already_shown(self):
        with tempfile.TemporaryDirectory() as home:
            flag = welcome.get_flag_path(home=home)
            welcome.mark_shown(flag)
            with mock.patch.object(welcome, "get_flag_path",
                                   return_value=flag):
                self.assertEqual(welcome.main([]), 0)


if __name__ == "__main__":
    unittest.main()
