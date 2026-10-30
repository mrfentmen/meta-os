"""tests/test_os_tree.py -- OS-006: the os/ tree laid down in the repo.

OS-006 lays down the Meta OS tree in this repo by porting the proven
image lane: build scripts, units, firstboot program, tools, GRUB
config, preseed answers, package list, and README. These tests pin
the tree, not a build: no image is built here (that needs root and
debootstrap, and it is OS-007's acceptance, not this task's).

- Every OS-006 tree entry exists.
- Every shell script in the tree passes a syntax check.
- build-image.sh references only paths that exist in os/ (its
  layout-mapping comment may name the old lane paths, but no code
  line may reference them).
- The units build-image.sh enables all exist in services/.
- preseed.cfg carries the OS-009 answers (relay user, UTC, en_US).
- packages.txt carries the proven debootstrap set.
- os/README.md states the honesty limits in plain words: the
  preseed is unproven, the package list is unpinned, and the
  pipeline from this tree is not claimed working yet.
- The new os/ docs carry no em dash (the check.sh new-doc rule).

No bus post, no live Redis, no network: pure file reads plus local
syntax checks.
"""

import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")

TREE_FILES = [
    "build-image.sh",
    "build-all.sh",
    "preseed.cfg",
    "packages.txt",
    "README.md",
    "grub-early.cfg",
    "README-FIRSTBOOT.md",
    "services/relay.target",
    "services/relay-bus.service",
    "services/relay-dashboard.service",
    "services/relay-jobs.service",
    "services/relay-overseer.service",
    "services/relay-overseer.timer",
    "services/relay-ready.service",
    "services/metaos-firstboot.service",
    "firstboot/metaos-firstboot",
    "bin/metaos-boot-checklist",
    "bin/metaos-update",
]

# Units build-image.sh enables into a target (the for-loop list plus
# the relay-overseer.service symlink line).
ENABLED_UNITS = [
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "metaos-firstboot.service",
    "relay-overseer.service",
    "relay-watchdog.service",
    "relay-brief.service",
]

BASH_SCRIPTS = ["build-image.sh", "build-all.sh"]
SH_SCRIPTS = [
    "firstboot/metaos-firstboot",
    "bin/metaos-boot-checklist",
    "bin/metaos-update",
]

PROVEN_PACKAGES = [
    "systemd",
    "systemd-sysv",
    "udev",
    "dbus",
    "linux-image-amd64",
    "initramfs-tools",
    "python3",
    "curl",
    "ca-certificates",
    "iproute2",
    "git",
]


def _read(relpath):
    with open(os.path.join(OS_DIR, relpath), encoding="utf-8") as handle:
        return handle.read()


class OsTreeTest(unittest.TestCase):
    def test_tree_files_exist(self):
        for relpath in TREE_FILES:
            self.assertTrue(
                os.path.isfile(os.path.join(OS_DIR, relpath)), relpath)

    def test_bash_scripts_syntax_clean(self):
        for relpath in BASH_SCRIPTS:
            result = subprocess.run(
                ["bash", "-n", os.path.join(OS_DIR, relpath)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0,
                             "%s: %s" % (relpath, result.stderr))

    def test_sh_scripts_syntax_clean(self):
        for relpath in SH_SCRIPTS:
            result = subprocess.run(
                ["sh", "-n", os.path.join(OS_DIR, relpath)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0,
                             "%s: %s" % (relpath, result.stderr))

    def test_build_image_code_lines_reference_no_lane_src(self):
        for line in _read("build-image.sh").splitlines():
            if line.lstrip().startswith("#"):
                continue
            for lane_path in ("src/units", "src/bin", "src/grub",
                              "src/README"):
                self.assertNotIn(lane_path, line, line)

    def test_build_image_referenced_inputs_exist(self):
        for relpath in ["services", "firstboot", "bin",
                        "grub-early.cfg", "README-FIRSTBOOT.md"]:
            self.assertTrue(os.path.exists(os.path.join(OS_DIR, relpath)),
                            relpath)

    def test_enabled_units_exist_in_services(self):
        for unit in ENABLED_UNITS:
            path = os.path.join(OS_DIR, "services", unit)
            self.assertTrue(os.path.isfile(path), unit)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("[Unit]", text, unit)

    def test_preseed_carries_os009_answers(self):
        text = _read("preseed.cfg")
        self.assertIn("relay", text)
        self.assertIn("en_US.UTF-8", text)
        self.assertIn("Etc/UTC", text)
        self.assertIn("password *", text)

    def test_packages_list_carries_proven_set(self):
        text = _read("packages.txt")
        for package in PROVEN_PACKAGES:
            self.assertIn(package, text, package)

    def test_readme_states_honesty_limits(self):
        text = _read("README.md")
        self.assertIn("Unproven", text)
        self.assertIn("Unpinned", text)
        self.assertIn("not claimed working from this tree", text)

    def test_new_os_docs_carry_no_em_dash(self):
        for relpath in ["README.md", "preseed.cfg", "packages.txt"]:
            self.assertNotIn("\u2014", _read(relpath), relpath)


if __name__ == "__main__":
    unittest.main()
