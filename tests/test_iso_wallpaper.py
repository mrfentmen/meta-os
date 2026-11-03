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


if __name__ == "__main__":
    unittest.main(verbosity=2)
