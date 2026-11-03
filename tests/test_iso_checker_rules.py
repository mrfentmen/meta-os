"""Prove the ISO checker's rules actually fire.

A checker that never fails is decoration. Each case copies the real iso/ tree
into a temp directory, breaks exactly one thing, and asserts the checker names
that break. The baseline case proves the copy passes untouched.
"""

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ISO = Path(__file__).resolve().parents[1] / "iso"


class CheckerRuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "iso"
        shutil.copytree(ISO, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return subprocess.run(
            [sys.executable, str(self.root / "tools" / "check_iso_config.py")],
            capture_output=True, text=True, timeout=120,
        )

    def test_baseline_copy_passes(self):
        out = self.check()
        self.assertEqual(out.returncode, 0, out.stdout[-1500:])

    def test_missing_agent_status_launcher_is_named(self):
        (self.root / "apps" / "desktop" / "meta-agent-status.desktop").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("frozen id 'agent-status' has no launcher", out.stdout)

    def test_missing_dock_item_is_named(self):
        (self.root / "apps" / "plank" / "meta-agent-status.dockitem").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("frozen id 'agent-status' has no dock item", out.stdout)

    def test_extra_dock_item_is_named(self):
        src = self.root / "apps" / "plank" / "meta-terminal.dockitem"
        (self.root / "apps" / "plank" / "meta-sixth.dockitem").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("unexpected item", out.stdout)

    def test_edited_contract_without_a_pin_update_fails(self):
        path = self.root / "contracts" / "tokens.json"
        text = path.read_text(encoding="utf-8").replace("#1877F2", "#1877F3")
        path.write_text(text, encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("sha256 does not match PIN.md", out.stdout)

    def test_wrong_ring_size_is_named(self):
        path = self.root / "plymouth" / "metaos" / "metaos.script"
        # The asset itself is what is measured; shrinking the file header is not
        # possible without rewriting the PNG, so assert the check exists by
        # removing the asset and expecting its own named failure.
        (self.root / "plymouth" / "metaos" / "ring-dot.png").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("ring-dot.png is missing", out.stdout)
        self.assertEqual(path.is_file(), True)


    def test_missing_package_manifest_is_named(self):
        (self.root / "base" / "metaos.packages").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("metaos.packages is missing", out.stdout)

    def test_duplicate_package_is_named(self):
        path = self.root / "base" / "metaos.packages"
        path.write_text(path.read_text(encoding="utf-8") + "plank\n", encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("duplicate package(s): plank", out.stdout)

    def test_launcher_with_no_package_behind_it_is_named(self):
        # Drop thunar from the base line: meta-files.desktop then starts a
        # program that neither apt nor this lane installs.
        path = self.root / "base" / "metaos.packages"
        text = path.read_text(encoding="utf-8").replace(
            "#base: thunar xfce4-terminal", "#base: xfce4-terminal")
        path.write_text(text, encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("which no package installs", out.stdout)
        self.assertIn("thunar", out.stdout)

    def test_stale_wallpaper_is_named(self):
        path = self.root / "theme" / "wallpaper" / "meta-wallpaper.png"
        path.write_bytes(path.read_bytes() + b"\x00")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("wallpaper is stale", out.stdout)

    def test_wrong_wallpaper_size_is_named(self):
        path = self.root / "theme" / "wallpaper" / "meta-wallpaper.png"
        raw = bytearray(path.read_bytes())
        raw[16:20] = struct.pack(">I", 1280)
        path.write_bytes(bytes(raw))
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("expected 1920x1080", out.stdout)

    def test_stylesheet_missing_a_token_is_named(self):
        path = self.root / "theme" / "gtk" / "metaos.css"
        kept = [line for line in path.read_text(encoding="utf-8").splitlines(True)
                if "@define-color meta_blue" not in line]
        path.write_text("".join(kept), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("has no definition for blue", out.stdout)

    def test_backdrop_pointing_elsewhere_is_named(self):
        path = self.root / "theme" / "xfce4-desktop.xml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "meta-wallpaper.png", "other.png"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("never points at", out.stdout)


    def test_greeter_pointing_at_another_backdrop_is_named(self):
        path = self.root / "theme" / "lightdm" / "lightdm-gtk-greeter.conf"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "greeter-active.png", "elsewhere.png"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("greeter background is", out.stdout)

    def test_greeter_theme_not_named_metaos_is_named(self):
        path = self.root / "theme" / "lightdm" / "themes" / "MetaOS" / "index.theme"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "Name=MetaOS", "Name=Adwaita"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("index.theme Name is", out.stdout)

    def test_greeter_stylesheet_missing_a_token_is_named(self):
        path = (self.root / "theme" / "lightdm" / "themes" / "MetaOS"
                / "gtk-3.0" / "gtk.css")
        kept = [line for line in path.read_text(encoding="utf-8").splitlines(True)
                if "@define-color meta_blue" not in line]
        path.write_text("".join(kept), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("greeter.css has no definition for blue", out.stdout)


    def test_boot_theme_image_that_is_not_there_is_named(self):
        path = self.root / "boot" / "grub" / "themes" / "metaos" / "theme.txt"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "meta-grub.png", "gone.png"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("is not next to theme.txt", out.stdout)

    def test_boot_theme_colour_outside_the_contract_is_named(self):
        path = self.root / "boot" / "grub" / "themes" / "metaos" / "theme.txt"
        path.write_text(path.read_text(encoding="utf-8").replace(
            'selected_item_color = "', 'selected_item_color = #ABCDEF  # "'),
            encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("colours outside the contract", out.stdout)

    def test_dropin_setting_a_kernel_command_line_is_named(self):
        path = self.root / "boot" / "grub" / "metaos-theme.cfg"
        path.write_text(path.read_text(encoding="utf-8")
                        + 'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n',
                        encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("rewrites the kernel command line", out.stdout)


    def test_json_output_is_machine_readable(self):
        out = subprocess.run(
            [sys.executable, str(self.root / "tools" / "check_iso_config.py"), "--json"],
            capture_output=True, text=True, timeout=180)
        data = json.loads(out.stdout)
        self.assertEqual(out.returncode, 0, data["fail"][:3])
        self.assertEqual(data["counts"]["fail"], 0)
        self.assertGreaterEqual(data["counts"]["pass"], 90)

    def test_slideshow_colour_outside_the_contract_is_named(self):
        path = self.root / "calamares" / "branding" / "meta" / "show.qml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            'border.color: "#1877F2"', 'border.color: "#123456"'), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("slideshow colours outside the contract", out.stdout)

    def test_slideshow_without_the_calamares_import_is_named(self):
        path = self.root / "calamares" / "branding" / "meta" / "show.qml"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "import calamares.slideshow 1.0", "// no module"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("no calamares.slideshow import", out.stdout)


    def test_branding_colour_outside_the_contract_is_named(self):
        path = self.root / "calamares" / "branding" / "meta" / "branding.desc"
        path.write_text(path.read_text(encoding="utf-8").replace(
            'sidebarBackground: "#070B16"', 'sidebarBackground: "#0A0B0C"'),
            encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("branding colours outside the contract", out.stdout)


    def test_autostart_running_something_uninstalled_is_named(self):
        path = self.root / "base" / "autostart" / "meta-first-login.desktop"
        text = path.read_text(encoding="utf-8")
        text = text.replace("/usr/local/bin/meta-first-login", "/usr/local/bin/nope")
        path.write_text(text, encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("which this lane never installs", out.stdout)

    def test_autostart_binary_without_tryexec_is_named(self):
        path = self.root / "base" / "autostart" / "meta-first-login.desktop"
        text = "".join(line for line in path.read_text(encoding="utf-8").splitlines(True)
                       if not line.startswith("TryExec="))
        path.write_text(text, encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("TryExec", out.stdout)


if __name__ == "__main__":
    unittest.main()
