"""Tests for iso/tools/tokens_to_xfce.py and the files it owns.

The shell is the part a user sees after the password: panel, icons, fonts,
terminal colours, lock settings. None of it can be looked at on this machine,
so the tests pin the things that can be read: the panel's plugin wiring, the
palette's provenance, and the generator's own determinism.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ISO_ROOT = Path(__file__).resolve().parents[1]
ISO = ISO_ROOT / "iso"
GENERATOR = ISO / "tools" / "tokens_to_xfce.py"
TOKENS = json.loads((ISO / "contracts" / "tokens.json").read_text(encoding="utf-8"))


def run(*args, cwd=ISO_ROOT):
    return subprocess.run(
        [sys.executable, str(GENERATOR), *args],
        cwd=cwd, capture_output=True, text=True,
    )


class Generator(unittest.TestCase):
    def test_committed_files_match_the_contract(self):
        result = run("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_changed_token_makes_the_output_stale(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "iso" / "contracts").mkdir(parents=True)
            shutil.copy(ISO / "contracts" / "tokens.json", root / "iso" / "contracts")
            self.assertEqual(run("--root", str(root)).returncode, 0)
            panel = root / "iso" / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfce4-panel.xml"
            panel.write_text(panel.read_text().replace("0.0275", "0.5000"))
            result = run("--root", str(root), "--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("xfce4-panel.xml", result.stdout)


class Panel(unittest.TestCase):
    def setUp(self):
        self.path = ISO / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfce4-panel.xml"
        self.tree = ET.parse(self.path)
        self.root = self.tree.getroot()

    def test_every_plugin_id_has_a_plugin(self):
        ids = self.root.find(".//property[@name='plugin-ids']")
        declared = len(ids.findall("value"))
        plugins = self.root.find(".//property[@name='plugins']")
        self.assertEqual(declared, len(plugins.findall("property")))

    def test_launcher_points_at_launchers_that_exist(self):
        items = [v.get("value") for v in self.root.iter("value")
                 if v.get("value", "").endswith(".desktop")]
        self.assertTrue(items)
        for item in items:
            self.assertTrue((ISO / "apps" / "desktop" / item).is_file(), item)

    def test_background_is_the_contract_black(self):
        values = self.root.find(".//property[@name='background-rgba']").findall("value")
        got = [float(v.get("value")) for v in values]
        want = [int(TOKENS["black"][i:i + 2], 16) / 255 for i in (1, 3, 5)]
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=3)
        self.assertEqual(len(got), 4)


class Terminal(unittest.TestCase):
    def test_palette_has_sixteen_entries(self):
        body = (ISO / "apps" / "terminal" / "metaos.theme").read_text()
        palette = re.search(r"^ColorPalette=(.+)$", body, re.M).group(1)
        self.assertEqual(len(palette.split(";")), 16)

    def test_scheme_is_selected_by_default(self):
        rc = (ISO / "apps" / "terminal" / "terminalrc").read_text()
        self.assertIn("ColorScheme=MetaOS", rc)
        self.assertIn("ColorBackground=" + TOKENS["black"], rc)


class Icons(unittest.TestCase):
    def test_theme_inherits_a_real_fallback(self):
        body = (ISO / "theme" / "icons" / "MetaOS" / "index.theme").read_text()
        inherits = re.search(r"^Inherits=(.+)$", body, re.M).group(1).split(",")
        self.assertIn("Adwaita", inherits)

    def test_every_place_icon_parses_and_uses_contract_colours(self):
        allowed = {v.upper() for v in TOKENS.values()}
        icons = sorted((ISO / "theme" / "icons" / "MetaOS" / "places" / "48").glob("*.svg"))
        self.assertEqual(len(icons), 3)
        for icon in icons:
            body = icon.read_text()
            ET.fromstring(body)  # parses or raises
            for hexv in re.findall(r"#[0-9A-Fa-f]{6}\b", body):
                self.assertIn(hexv.upper(), allowed, icon.name)


class Settings(unittest.TestCase):
    def test_icon_theme_named_here_exists_on_disk(self):
        body = (ISO / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xsettings.xml").read_text()
        self.assertIn("Net/IconThemeName", body)
        self.assertTrue((ISO / "theme" / "icons" / "MetaOS" / "index.theme").is_file())

    def test_font_in_settings_is_the_font_fontconfig_prefers(self):
        settings = (ISO / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xsettings.xml").read_text()
        fonts = (ISO / "theme" / "fonts" / "local.conf").read_text()
        ET.fromstring(fonts)
        self.assertIn('value="Inter 10"', settings)
        self.assertIn("<family>Inter</family>", fonts)

    def test_lock_is_on_for_suspend_and_blank(self):
        body = (ISO / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "light-locker.xml").read_text()
        self.assertIn('name="lock-on-suspend" type="bool" value="true"', body)
        self.assertIn('name="lock-after-screensaver" type="bool" value="true"', body)

    def test_power_manager_locks_on_suspend(self):
        body = (ISO / "theme" / "xfce4" / "xfconf" / "xfce-perchannel-xml" / "xfce4-power-manager.xml").read_text()
        self.assertIn("lock-screen-suspend-hibernate", body)
        self.assertIn('value="true"', body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
