"""Tests for iso/apps/welcome/meta-welcome.py.

The window itself needs a display, which this machine does not have. What can
be tested is everything it reads and every promise it makes: the launcher
list comes from disk, the marker is written once, the headless mode works
without GTK, and the colours come from the contract.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "iso" / "apps" / "welcome" / "meta-welcome.py"
APPS = ROOT / "iso" / "apps" / "desktop"
TOKENS = json.loads((ROOT / "iso" / "contracts" / "tokens.json").read_text())


def run(*args, home=None, extra_env=None):
    env = dict(os.environ)
    if home:
        env["HOME"] = str(home)
        env.pop("XDG_CONFIG_HOME", None)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(APP), "--apps-dir", str(APPS), *args],
        capture_output=True, text=True, env=env,
    )


class Headless(unittest.TestCase):
    def test_lists_the_five_launchers_in_dock_order(self):
        with tempfile.TemporaryDirectory() as home:
            result = run("--json", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            ids = [app["id"] for app in data["apps"]]
            self.assertEqual(ids, [
                "meta-files", "meta-terminal", "meta-settings",
                "meta-browser", "meta-agent-status",
            ])

    def test_every_listed_app_has_a_name(self):
        with tempfile.TemporaryDirectory() as home:
            data = json.loads(run("--json", home=home).stdout)
            for app in data["apps"]:
                self.assertTrue(app["name"])
                self.assertNotEqual(app["name"], app["id"])

    def test_three_pages_and_offline(self):
        with tempfile.TemporaryDirectory() as home:
            data = json.loads(run("--json", home=home).stdout)
            self.assertEqual(data["pages"], ["welcome", "installed", "ready"])
            self.assertTrue(data["offline"])

    def test_empty_apps_dir_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as empty:
            result = subprocess.run(
                [sys.executable, str(APP), "--json", "--apps-dir", empty],
                capture_output=True, text=True,
                env={**os.environ, "HOME": home},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["apps"], [])

    def test_json_does_not_need_gtk(self):
        # If the import were at module level, this would fail on a machine
        # without PyGObject, which is exactly the machine running the tests.
        with tempfile.TemporaryDirectory() as home:
            result = run("--json", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)


class Marker(unittest.TestCase):
    def test_shown_once_then_reset(self):
        with tempfile.TemporaryDirectory() as home:
            self.assertFalse(json.loads(run("--json", home=home).stdout)["shown"])
            self.assertEqual(run("--mark", home=home).returncode, 0)
            self.assertTrue(json.loads(run("--json", home=home).stdout)["shown"])
            self.assertEqual(run("--reset", home=home).returncode, 0)
            self.assertFalse(json.loads(run("--json", home=home).stdout)["shown"])

    def test_marker_lives_under_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as conf:
            env = {"HOME": home, "XDG_CONFIG_HOME": conf}
            result = subprocess.run(
                [sys.executable, str(APP), "--mark"], capture_output=True, text=True,
                env={**os.environ, **env},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(conf) / "metaos" / "welcome.done").is_file())


class Sources(unittest.TestCase):
    def test_gtk_is_imported_lazily(self):
        source = APP.read_text()
        self.assertLess(source.index("def run_gui"), source.index("import gi"))

    def test_nothing_here_reaches_the_network(self):
        source = APP.read_text()
        for word in ("urllib", "requests", "socket", "http://", "https://"):
            self.assertNotIn(word, source)

    def test_stylesheet_uses_only_contract_colours(self):
        allowed = {value.upper() for value in TOKENS.values()}
        css = (ROOT / "iso" / "apps" / "welcome" / "welcome.css").read_text()
        stray = [h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}\b", css)
                 if h.upper() not in allowed]
        self.assertEqual(stray, [])

    def test_palette_matches_the_contract(self):
        palette = json.loads((ROOT / "iso" / "apps" / "welcome" / "palette.json").read_text())
        for name, value in palette.items():
            self.assertEqual(TOKENS[name], value)

    def test_first_login_launches_it_and_can_skip_it(self):
        body = (ROOT / "iso" / "base" / "meta-first-login.sh").read_text()
        self.assertIn("meta-welcome", body)
        self.assertIn("--no-welcome", body)
        self.assertIn("command -v meta-welcome", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
