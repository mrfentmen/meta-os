"""OS-010 first light: the package manifest name set is frozen.

os/packages.txt is the single frozen name set for every image
route, and the live-build package list must match it entry for
entry. Versions are deliberately NOT pinned here: the pin step
diffs this list against a built image's dpkg -l output, and that
diff is owed to a build host run (see os/README.md, OS-010
section). A version written here without that diff would be a
guess, not a pin.

No bus post, no live Redis, no network: pure file reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
MANIFEST = os.path.join(OS_DIR, "packages.txt")
PACKAGE_LIST = os.path.join(
    OS_DIR, "live-build", "config", "package-lists",
    "metaos.list.chroot",
)
README = os.path.join(OS_DIR, "README.md")

# The frozen set, in file order: 11 proven debootstrap packages,
# then the spec set (python3-venv for the spec's python3 + venv,
# plus the five spec extras as real Debian names).
EXPECTED_PACKAGES = [
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
    "python3-venv",
    "redis-tools",
    "chromium",
    "fonts-dejavu",
    "openssh-server",
    "qemu-guest-agent",
]

SPEC_PACKAGES = [
    "python3-venv",
    "redis-tools",
    "chromium",
    "fonts-dejavu",
    "openssh-server",
    "qemu-guest-agent",
]


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _names(path):
    names = []
    for line in _read(path).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


class ManifestTest(unittest.TestCase):
    def test_packages_txt_is_exactly_the_frozen_set(self):
        self.assertEqual(_names(MANIFEST), EXPECTED_PACKAGES)

    def test_no_duplicates_and_no_version_pins(self):
        names = _names(MANIFEST)
        self.assertEqual(len(names), len(set(names)),
                         "duplicate package entry in packages.txt")
        for name in names:
            self.assertNotIn("=", name,
                             "version pin %s is a guess until the "
                             "dpkg -l diff lands" % name)

    def test_spec_set_present(self):
        names = _names(MANIFEST)
        for name in SPEC_PACKAGES:
            self.assertIn(name, names, name)

    def test_header_states_unpinned_and_owed_diff(self):
        text = _read(MANIFEST)
        self.assertIn("NOT PINNED", text)
        self.assertIn("dpkg -l", text)
        # Header phrases wrap across comment lines, so flatten first.
        flat = " ".join(line.lstrip("# ").strip()
                        for line in text.splitlines())
        self.assertIn("owed to a build host run", flat)

    def test_openssh_disabled_by_default_noted(self):
        self.assertIn("disabled by default", _read(MANIFEST))

    def test_live_build_list_matches_packages_txt(self):
        # Both directions: no route silently installs a different set.
        self.assertEqual(set(_names(PACKAGE_LIST)),
                         set(_names(MANIFEST)))

    def test_readme_carries_os010_section_with_limit(self):
        text = _read(README)
        self.assertIn("## Package manifest (OS-010, first light)", text)
        self.assertIn("dpkg -l", text)
        self.assertIn("UNPROVEN", text)

    def test_no_em_dash_in_manifest_files(self):
        for path in (MANIFEST, PACKAGE_LIST):
            self.assertNotIn("\u2014", _read(path), path)


if __name__ == "__main__":
    unittest.main()
