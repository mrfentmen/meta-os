"""tests/test_os_stackbake.py -- OS-011: the stack baked at a pinned commit.

OS-011 first light: os/build-image.sh refuses a dirty checkout,
captures the checkout HEAD as PINNED_COMMIT, and stamps it into
the image in two places: /opt/relay/.metaos-source-commit (the sha
alone) and the second line of /etc/metaos-version
("source-commit <sha>"). The payload copy still excludes .git,
and the empty local commit in /opt/relay/.git exists only so
metaos-update sees a git tree; it carries no source history and
is not the pinned record.

These tests pin the bake script, not a build: no build has run
from this change (the sandbox has no debootstrap rootfs to
assemble), so a stamped image, a stamp-to-checkout match on a
built image, and a boot of that image are explicitly UNPROVEN
and stay that way until a build host runs build-image.sh end to
end. What is pinned here is real: the dirty guard, the
rev-parse capture, both stamp writes driven by the same
variable, the .git exclusion, and the honesty limits in the docs.

Venv and requirements: the stack is standard library only (every
payload import resolves to the standard library or to another
first party module in this repo) and no requirements file exists
here, so there is no pip install step to pin. If a requirements
file lands, the bake must gain a venv plus install step; until
then that step is owed, not claimed, and no test here pretends
otherwise.

No bus post, no live Redis, no network: pure file reads plus
local shell syntax checks.
"""

import os
import re
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
SCRIPT = os.path.join(OS_DIR, "build-image.sh")
README = os.path.join(OS_DIR, "README.md")

SHA40 = re.compile(r"\b[0-9a-f]{40}\b")


def read_script():
    with open(SCRIPT) as f:
        return f.read()


class BakeScriptTest(unittest.TestCase):
    def test_script_bash_syntax(self):
        proc = subprocess.run(
            ["bash", "-n", SCRIPT], capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_refuses_dirty_checkout(self):
        script = read_script()
        self.assertIn('git -C "$PAYLOAD_SRC" status --porcelain', script)
        self.assertIn("refusing: checkout is dirty", script)

    def test_pinned_commit_captured_from_checkout_head(self):
        script = read_script()
        self.assertIn('PINNED_COMMIT="$(git -C "$PAYLOAD_SRC" rev-parse HEAD)"', script)
        self.assertIn('refusing: no pinned commit resolved', script)

    def test_dirty_guard_runs_before_any_image_write(self):
        script = read_script()
        guard = script.index("refusing: checkout is dirty")
        first_write = script.index('> "$ROOTFS/etc/hostname"')
        self.assertLess(guard, first_write)

    def test_source_commit_stamp_file_written_from_variable(self):
        script = read_script()
        self.assertIn('echo "$PINNED_COMMIT" > "$ROOTFS/opt/relay/.metaos-source-commit"', script)

    def test_version_stamp_carries_source_commit_line(self):
        script = read_script()
        self.assertIn('echo "source-commit $PINNED_COMMIT" >> "$ROOTFS/etc/metaos-version"', script)

    def test_no_hardcoded_commit_sha_in_script(self):
        script = read_script()
        hits = [line for line in script.splitlines() if SHA40.search(line)]
        self.assertEqual(hits, [])

    def test_payload_still_excludes_git(self):
        script = read_script()
        self.assertIn("--exclude='.git'", script)
        self.assertIn('rm -rf "$ROOTFS/opt/relay/.git"', script)

    def test_stamp_written_after_git_removal(self):
        script = read_script()
        removal = script.index('rm -rf "$ROOTFS/opt/relay/.git"')
        stamp = script.index(
            'echo "$PINNED_COMMIT" > "$ROOTFS/opt/relay/.metaos-source-commit"'
        )
        self.assertLess(removal, stamp)


class BakeDocsTest(unittest.TestCase):
    def test_readme_has_os011_section_with_limits(self):
        with open(README) as f:
            text = f.read()
        self.assertIn("OS-011", text)
        self.assertIn(".metaos-source-commit", text)
        self.assertIn("source-commit <sha>", text)
        self.assertIn("UNPROVEN", text)
        self.assertIn("Packer route", text)

    def test_readme_states_no_venv_step_and_why(self):
        with open(README) as f:
            text = f.read()
        self.assertIn("no venv step", text)
        self.assertIn("standard library", text)

    def test_readme_has_no_em_dash(self):
        with open(README) as f:
            text = f.read()
        self.assertNotIn("\u2014", text)


class StackDepsTest(unittest.TestCase):
    def test_no_requirements_file_exists(self):
        for name in ("requirements.txt", "requirements-dev.txt"):
            self.assertFalse(
                os.path.exists(os.path.join(ROOT, name)),
                "%s exists but the bake has no install step for it" % name,
            )


if __name__ == "__main__":
    unittest.main()
