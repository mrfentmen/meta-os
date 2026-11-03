"""Tests for the wallpaper pack and the size picker in first login.

A scaled ring is a blurry ring, so the desktop ships three files and first
login picks the one that matches the screen. Both halves are testable without
a display: the PNG headers, and the picker with a stub xrandr.
"""

import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WALL_DIR = ROOT / "iso" / "theme" / "wallpaper"
FIRST_LOGIN = ROOT / "iso" / "base" / "meta-first-login.sh"
GEN = ROOT / "iso" / "tools" / "make_wallpaper.py"

SIZES = {
    "meta-wallpaper.png": (1920, 1080),
    "meta-wallpaper-2560x1440.png": (2560, 1440),
    "meta-wallpaper-3840x2160.png": (3840, 2160),
    "meta-wallpaper-1366x768.png": (1366, 768),
}


def png_size(path: Path):
    head = path.read_bytes()[:33]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    width, height, depth, colour = struct.unpack(">IIBB", head[16:26])
    return width, height, depth, colour


def stub(bin_dir: Path, name: str, body: str):
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)


class Pack(unittest.TestCase):
    def test_three_sizes_ship_and_match_their_names(self):
        for name, (want_w, want_h) in SIZES.items():
            with self.subTest(name=name):
                path = WALL_DIR / name
                self.assertTrue(path.is_file(), name)
                width, height, depth, colour = png_size(path)
                self.assertEqual((width, height), (want_w, want_h))
                self.assertEqual((depth, colour), (8, 6), "8-bit RGBA")

    def test_generator_says_all_three_are_current(self):
        result = subprocess.run([sys.executable, str(GEN), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_an_unknown_size_is_refused(self):
        result = subprocess.run([sys.executable, str(GEN), "--size", "800x600"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not one of the shipped sizes", result.stderr)


class Picker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        share = self.root / "share"
        (share / "theme").mkdir(parents=True)
        (share / "dock").mkdir()
        (share / "dock" / "meta-files.dockitem").write_text("[PlankDockItem]\n")
        (share / "theme" / "gtk.css").write_text("@define-color meta_black #070B16;\n")
        for name in SIZES:
            (share / "theme" / name).write_bytes((WALL_DIR / name).read_bytes())
        self.share = share
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_login(self, resolution):
        stub(self.bin, "xrandr",
             'echo "eDP-1 connected primary %s+0+0 (normal left inverted right)"\n' % resolution)
        stub(self.bin, "xfconf-query", "exit 0\n")
        return subprocess.run(
            [str(FIRST_LOGIN), "--dry-run", "--no-welcome"],
            capture_output=True, text=True,
            env={
                "PATH": "%s:/usr/bin:/bin" % self.bin,
                "HOME": str(self.root / "home"),
                "XDG_CONFIG_HOME": str(self.root / "cfg"),
                "METAOS_SHARE": str(self.share),
            },
        )

    def test_matching_screen_gets_its_own_file(self):
        result = self.run_login("2560x1440")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("meta-wallpaper-2560x1440.png", result.stdout)

    def test_1366_screen_gets_the_small_file(self):
        self.assertIn("meta-wallpaper-1366x768.png", self.run_login("1366x768").stdout)

    def test_unknown_screen_falls_back_to_1080p(self):
        output = self.run_login("1024x600").stdout
        self.assertIn("wallpaper meta-wallpaper.png", output)
        self.assertNotIn("1024x600", output)


GREETERS = {
    "greeter-wallpaper.png": (1920, 1080),
    "greeter-wallpaper-2560x1440.png": (2560, 1440),
    "greeter-wallpaper-3840x2160.png": (3840, 2160),
    "greeter-wallpaper-1366x768.png": (1366, 768),
}
SETUP = ROOT / "iso" / "theme" / "lightdm" / "meta-greeter-setup.sh"


class GreeterPack(unittest.TestCase):
    def test_every_greeter_size_ships(self):
        for name, (want_w, want_h) in GREETERS.items():
            with self.subTest(name=name):
                width, height, depth, colour = png_size(WALL_DIR / name)
                self.assertEqual((width, height), (want_w, want_h))
                self.assertEqual((depth, colour), (8, 6))

    def test_active_starts_as_the_default(self):
        self.assertEqual((WALL_DIR / "greeter-active.png").read_bytes(),
                         (WALL_DIR / "greeter-wallpaper.png").read_bytes())

    def test_greeter_config_points_at_the_active_file(self):
        body = (ROOT / "iso" / "theme" / "lightdm" / "lightdm-gtk-greeter.conf").read_text()
        self.assertRegex(body, r"(?m)^background=.*greeter-active\.png$")

    def test_seat_runs_the_picker(self):
        drop = ROOT / "iso" / "theme" / "lightdm" / "lightdm.conf.d" / "90-metaos-greeter.conf"
        self.assertIn("greeter-setup-script=/usr/local/bin/meta-greeter-setup",
                      drop.read_text())

    def test_script_parses(self):
        subprocess.run(["bash", "-n", str(SETUP)], check=True)


class GreeterPicker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.theme = Path(self.tmp.name)
        for name in GREETERS:
            (self.theme / name).write_bytes((WALL_DIR / name).read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def run_setup(self, size=None):
        env = {"PATH": "/usr/bin:/bin", "METAOS_THEME_DIR": str(self.theme)}
        if size:
            env["METAOS_GREETER_SIZE"] = size
        return subprocess.run([str(SETUP)], capture_output=True, text=True, env=env)

    def test_matching_size_is_copied_to_the_active_name(self):
        result = self.run_setup("2560x1440")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.theme / "greeter-active.png").read_bytes(),
                         (self.theme / "greeter-wallpaper-2560x1440.png").read_bytes())
        self.assertIn("2560x1440", result.stdout)

    def test_4k_is_picked_when_the_screen_says_so(self):
        self.assertEqual(self.run_setup("3840x2160").returncode, 0)
        self.assertEqual((self.theme / "greeter-active.png").read_bytes(),
                         (self.theme / "greeter-wallpaper-3840x2160.png").read_bytes())

    def test_unknown_size_falls_back_to_1080p(self):
        self.assertEqual(self.run_setup("1024x600").returncode, 0)
        self.assertEqual((self.theme / "greeter-active.png").read_bytes(),
                         (self.theme / "greeter-wallpaper.png").read_bytes())

    def test_missing_wallpapers_is_a_loud_failure(self):
        empty = self.theme / "empty"
        empty.mkdir()
        env = {"PATH": "/usr/bin:/bin", "METAOS_THEME_DIR": str(empty),
               "METAOS_GREETER_SIZE": "1920x1080"}
        result = subprocess.run([str(SETUP)], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no wallpaper", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
