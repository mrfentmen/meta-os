"""tests/test_os_base.py -- OS-005: the frozen Meta OS base.

OS-005 freezes one base for the whole os/ tree: Debian 12 (bookworm)
amd64, sourced by the debootstrap call pinned in build-all.sh. These
tests pin the freeze, not a build: no image is built here (that is
OS-007's acceptance, not this task's).

- os/BASE.md exists and names the frozen base and its source.
- build-all.sh pins the bookworm suite and the Debian mirror.
- No second base appears in any build file: no other release or
  distro codename in the scripts, preseed answers, package list,
  units, firstboot program, tools, or GRUB config.
- preseed.cfg names no suite and no mirror (installer answers only,
  not a second base).
- os/BASE.md carries no em dash (the check.sh new-doc rule).

No bus post, no live Redis, no network: pure file reads.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")

# Any of these in a build file would be a second base.
FORBIDDEN_CODENAMES = re.compile(
    r"\b(bullseye|trixie|forky|sid|ubuntu|fedora|centos|rhel|archlinux)\b",
    re.IGNORECASE,
)

BUILD_FILES = [
    "build-all.sh",
    "build-image.sh",
    "preseed.cfg",
    "packages.txt",
    "grub-early.cfg",
    "README-FIRSTBOOT.md",
]

BUILD_DIRS = ["services", "bin", "firstboot"]


def _read(relpath):
    with open(os.path.join(OS_DIR, relpath), encoding="utf-8") as handle:
        return handle.read()


def _build_file_list():
    found = list(BUILD_FILES)
    for dirname in BUILD_DIRS:
        dirpath = os.path.join(OS_DIR, dirname)
        for name in sorted(os.listdir(dirpath)):
            path = os.path.join(dirpath, name)
            if os.path.isfile(path):
                found.append(os.path.join(dirname, name))
    return found


class OsBaseFreezeTest(unittest.TestCase):
    def test_base_doc_names_the_frozen_base_and_source(self):
        text = _read("BASE.md")
        self.assertIn("Debian 12", text)
        self.assertIn("bookworm", text)
        self.assertIn("amd64", text)
        self.assertIn("http://deb.debian.org/debian", text)
        self.assertIn("build-all.sh", text)

    def test_build_script_pins_bookworm_suite_and_mirror(self):
        text = _read("build-all.sh")
        self.assertIn("bookworm", text)
        self.assertIn("http://deb.debian.org/debian", text)

    def test_no_second_base_in_build_files(self):
        for relpath in _build_file_list():
            text = _read(relpath)
            match = FORBIDDEN_CODENAMES.search(text)
            self.assertIsNone(match, "%s names a second base: %s" % (
                relpath, match.group(0) if match else ""))

    def test_preseed_names_no_suite_or_mirror(self):
        text = _read("preseed.cfg")
        self.assertNotIn("bookworm", text)
        self.assertNotIn("http://", text)
        self.assertIsNone(FORBIDDEN_CODENAMES.search(text))

    def test_base_doc_carries_no_em_dash(self):
        self.assertNotIn("\u2014", _read("BASE.md"))

    def test_base_doc_states_checksum_limit_honestly(self):
        text = _read("BASE.md")
        self.assertIn("no ISO", text)
        self.assertIn("OS-007", text)
        self.assertIn("metaos-<date>.img.sha256", text)


if __name__ == "__main__":
    unittest.main()
