"""tests/test_os_livebuild.py -- OS-008: the fallback live-build ISO.

OS-008 first light: os/live-build/ (auto/config, package list,
services hook) plus the one-command wrapper os/build-live.sh
that stages the OS glue from this repo's os/services/,
os/firstboot/, and os/bin/ into config/includes.chroot/,
runs lb clean/config/build, and renames the output to
metaos-<date>.iso + .sha256.

These tests pin the pipeline files, not a build: no live-build
run has happened from this config (the sandbox has no lb
binary, so `lb config` has not run either), so a build, a boot
to the crew session in QEMU, and the OS-010 version pin are
explicitly UNPROVEN and stay that way until a build host runs
the wrapper end to end. What is pinned here is real: the config
shape, the package list coverage, the hook's unit wiring, the
wrapper guards and staging, the single-source-of-truth rule (no
unit copy lives in this tree), and the honesty limits in the
docs.

- auto/config names bookworm amd64 and iso-hybrid only, no
  second base, and states the unproven-build limit.
- The package list covers every uncommented name in
  os/packages.txt plus the five META_OS.md spec extras as real
  Debian package names; versions are not pinned here (OS-010).
- The hook enables exactly the units os/build-image.sh wires
  into relay.target.wants, plus metaos-firstboot into
  multi-user.target.wants, and enables nothing else from
  services/ (OS-016 enables relay-brief and relay-watchdog
  alongside the rest of the target set; only the worker
  template stays unenabled, as a bare unit).
- No .service or .timer copy exists under live-build/: units
  are staged at build time only, from services/.
- Wrapper guards: set -euo pipefail, clean-checkout refusal,
  root requirement, tool checks for lb, mksquashfs, xorriso,
  staging copies from services/firstboot/bin, trap cleanup of
  the staged tree, ISO naming metaos-<date>.iso, sha256 step.
- os/README.md carries the OS-008 section with the unproven
  limit stated, and os/BASE.md carries the fallback
  divergences section; neither new section carries an em dash.

No bus post, no live Redis, no network: pure file reads plus
local shell syntax checks.
"""

import glob
import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
LIVE_DIR = os.path.join(OS_DIR, "live-build")
CONFIG = os.path.join(LIVE_DIR, "auto", "config")
PACKAGE_LIST = os.path.join(
    LIVE_DIR, "config", "package-lists", "metaos.list.chroot")
HOOK = os.path.join(
    LIVE_DIR, "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")
WRAPPER = os.path.join(OS_DIR, "build-live.sh")

# The units os/build-image.sh wires into relay.target.wants
# (its for-loop list plus the relay-overseer.service symlink
# line), with metaos-firstboot wired to multi-user.target.wants.
ENABLED_UNITS = [
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "relay-overseer.service",
    "relay-watchdog.service",
    "relay-brief.service",
]
FIRSTBOOT_UNIT = "metaos-firstboot.service"
# Units that ship in services/ but must stay unenabled here,
# matching build-image.sh: only the worker template, which is
# enabled per nick as an instance (OS-017), never as a bare unit.
NOT_ENABLED_UNITS = [
    "relay-worker@.service",
]
# The META_OS.md spec extras as real Debian package names.
SPEC_EXTRA_PACKAGES = [
    "redis-tools",
    "chromium",
    "fonts-dejavu",
    "openssh-server",
    "qemu-guest-agent",
]
FORBIDDEN_CODENAMES = re.compile(
    r"\b(bullseye|trixie|forky|sid|ubuntu|fedora|centos|rhel|archlinux)\b",
    re.IGNORECASE,
)


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _packages_txt_names():
    names = []
    for line in _read(os.path.join(OS_DIR, "packages.txt")).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def _package_list_names():
    names = []
    for line in _read(PACKAGE_LIST).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def _live_build_files():
    found = []
    for dirpath, _dirnames, filenames in os.walk(LIVE_DIR):
        for name in filenames:
            found.append(os.path.join(dirpath, name))
    return found


class LiveBuildConfigTest(unittest.TestCase):
    def test_config_exists_and_names_bookworm_amd64_iso_hybrid(self):
        text = _read(CONFIG)
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertIn("--distribution bookworm", text)
        self.assertIn("--architectures amd64", text)
        self.assertIn("--binary-images iso-hybrid", text)
        self.assertNotIn("--debian-installer", text,
                         "fallback ISO is a live session, no installer")

    def test_config_states_unproven_limit(self):
        self.assertIn("UNPROVEN", _read(CONFIG))

    def test_no_second_base_in_live_build_files(self):
        for path in _live_build_files():
            self.assertIsNone(
                FORBIDDEN_CODENAMES.search(_read(path)),
                "second base codename in %s" % path)

    def test_config_shell_syntax(self):
        proc = subprocess.run(["sh", "-n", CONFIG],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class PackageListTest(unittest.TestCase):
    def test_covers_packages_txt_names(self):
        listed = _package_list_names()
        for name in _packages_txt_names():
            self.assertIn(name, listed,
                          "packages.txt name %s missing from live list" % name)

    def test_covers_spec_extras_as_real_package_names(self):
        listed = _package_list_names()
        for name in SPEC_EXTRA_PACKAGES:
            self.assertIn(name, listed)

    def test_no_versions_pinned_here(self):
        # OS-010 pins versions against a built image's package
        # list; this list must stay a name list, like packages.txt.
        for name in _package_list_names():
            self.assertNotIn("=", name,
                             "version pin %s belongs to OS-010, not here"
                             % name)


class ServicesHookTest(unittest.TestCase):
    def test_hook_enables_exactly_the_build_image_unit_set(self):
        text = _read(HOOK)
        for unit in ENABLED_UNITS:
            self.assertIn(unit, text)
        self.assertIn(FIRSTBOOT_UNIT, text)
        self.assertIn("relay.target.wants", text)
        self.assertIn("multi-user.target.wants", text)

    def test_hook_enables_nothing_else_from_services(self):
        # Only the code lines count: the header comment names the
        # unenabled units to explain why they are absent.
        code = "\n".join(line for line in _read(HOOK).splitlines()
                         if not line.lstrip().startswith("#"))
        for unit in NOT_ENABLED_UNITS:
            self.assertNotIn(unit, code)

    def test_no_unit_copy_lives_in_live_build_tree(self):
        for path in _live_build_files():
            self.assertFalse(
                path.endswith(".service") or path.endswith(".timer"),
                "unit copy in live-build tree: %s (stage at build time only)"
                % path)

    def test_hook_shell_syntax(self):
        proc = subprocess.run(["sh", "-n", HOOK],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class WrapperTest(unittest.TestCase):
    def test_wrapper_guards(self):
        text = _read(WRAPPER)
        self.assertTrue(text.startswith("#!/bin/bash"))
        self.assertIn("set -euo pipefail", text)
        self.assertIn("git -C", text)
        self.assertIn("status --porcelain", text)
        self.assertIn('id -u', text)
        for tool in ("lb", "mksquashfs", "xorriso", "sha256sum"):
            self.assertIn(tool, text)

    def test_wrapper_stages_from_repo_sources_and_cleans_up(self):
        text = _read(WRAPPER)
        self.assertIn("services/*.service", text)
        self.assertIn("services/*.timer", text)
        self.assertIn("services/relay.target", text)
        self.assertIn("firstboot/metaos-firstboot", text)
        self.assertIn("bin/metaos-boot-checklist", text)
        self.assertIn("bin/metaos-update", text)
        self.assertIn("config/includes.chroot", text)
        self.assertIn('trap cleanup EXIT', text)
        # Every staged source must exist in the repo.
        self.assertTrue(glob.glob(os.path.join(OS_DIR, "services",
                                               "*.service")))
        self.assertTrue(glob.glob(os.path.join(OS_DIR, "services",
                                               "*.timer")))
        self.assertTrue(os.path.exists(
            os.path.join(OS_DIR, "services", "relay.target")))
        self.assertTrue(os.path.exists(
            os.path.join(OS_DIR, "firstboot", "metaos-firstboot")))

    def test_wrapper_build_steps_and_output_naming(self):
        text = _read(WRAPPER)
        self.assertIn("lb clean", text)
        self.assertIn("lb config", text)
        self.assertIn("lb build", text)
        self.assertIn("live-image-amd64.hybrid.iso", text)
        self.assertIn('metaos-$DATE.iso', text)
        self.assertIn("sha256sum", text)

    def test_wrapper_bash_syntax(self):
        proc = subprocess.run(["bash", "-n", WRAPPER],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


class DocsTest(unittest.TestCase):
    def test_readme_carries_os008_section_with_limit(self):
        text = _read(os.path.join(OS_DIR, "README.md"))
        self.assertIn("Fallback pipeline (OS-008", text)
        self.assertIn("UNPROVEN", text)

    def test_base_carries_fallback_divergences(self):
        text = _read(os.path.join(OS_DIR, "BASE.md"))
        self.assertIn("Fallback pipeline divergences (OS-008)", text)
        self.assertIn("live ISO", text)
        self.assertIn("does not install", text)

    def test_new_doc_sections_carry_no_em_dash(self):
        for path in (os.path.join(OS_DIR, "README.md"),
                     os.path.join(OS_DIR, "BASE.md")):
            text = _read(path)
            start = text.find("OS-008")
            section = text[start:]
            self.assertNotIn("\u2014", section,
                             "em dash in OS-008 section of %s" % path)


if __name__ == "__main__":
    unittest.main()
