"""tests/test_os021_update.py -- OS-021: the metaos-update path, first light.

OS-021 ships the update path as os/bin/metaos-update: verify a git
bundle, apply it to the crew tree, keep the previous tree for
rollback, restart relay.target. The script landed in the tree under
OS-006 with no behavioral tests; this file pins its behavior against
fixture trees in a temp dir, through the script's METAOS_RELAY_ROOT
test hook (never set on the image, where the target stays
/opt/relay). The tests prove:

- Apply moves the tree to the bundle's main commit and keeps the
  previous tree intact beside it.
- Rollback swaps the live tree with the kept previous tree, so a
  second rollback swaps back; rollback with no previous tree refuses.
- A missing bundle file is a usage error (exit 2); a corrupt bundle
  and a non-git target refuse (exit 1) with the target untouched.
- With no arguments and no hook set, the script exits 2 before it
  touches any target, so the default /opt/relay path is never
  exercised by these tests.

No root, no network, no live systemd: systemctl failures are
absorbed by the script's own `|| true`, and every run carries a
timeout so a stuck helper cannot hang the suite.
"""

import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "os", "bin", "metaos-update")
README = os.path.join(ROOT, "os", "README.md")


def _git(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "user.email=test@metaos.local",
         "-c", "user.name=Meta OS test", "-C", cwd] + list(args),
        capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError(
            "git %s in %s failed: %s" % (" ".join(args), cwd, result.stderr))
    return result.stdout.strip()


def _make_repo(path, content):
    os.makedirs(path, exist_ok=True)
    _git(path, "init", "-q", "-b", "main")
    with open(os.path.join(path, "app.txt"), "w", encoding="utf-8") as handle:
        handle.write(content)
    _git(path, "add", "app.txt")
    _git(path, "commit", "-q", "-m", "fixture")
    return _git(path, "rev-parse", "HEAD")


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class Os021UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.live = os.path.join(self.tmp.name, "relay")
        self.v1 = _make_repo(self.live, "v1\n")
        self.src = os.path.join(self.tmp.name, "src")
        self.v2 = _make_repo(self.src, "v2\n")
        self.bundle = os.path.join(self.tmp.name, "update.bundle")
        _git(self.src, "bundle", "create", self.bundle, "main")
        self.env = dict(os.environ)
        self.env["METAOS_RELAY_ROOT"] = self.live

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args, env=None):
        return subprocess.run(
            ["sh", SCRIPT] + list(args),
            capture_output=True, text=True, timeout=60,
            env=self.env if env is None else env)

    def _live_content(self):
        return _read(os.path.join(self.live, "app.txt"))

    def _live_head(self):
        return _git(self.live, "rev-parse", "HEAD")

    def test_apply_moves_tree_and_keeps_previous(self):
        result = self._run(self.bundle)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applied", result.stdout)
        self.assertEqual(self._live_content(), "v2\n")
        self.assertEqual(self._live_head(), self.v2)
        prev = self.live + ".prev"
        self.assertTrue(os.path.isdir(prev))
        self.assertEqual(_read(os.path.join(prev, "app.txt")), "v1\n")
        self.assertEqual(_git(prev, "rev-parse", "HEAD"), self.v1)

    def test_rollback_swaps_and_second_rollback_swaps_back(self):
        self.assertEqual(self._run(self.bundle).returncode, 0)
        rolled = self._run("--rollback")
        self.assertEqual(rolled.returncode, 0, rolled.stderr)
        self.assertIn("rolled back", rolled.stdout)
        self.assertEqual(self._live_content(), "v1\n")
        self.assertEqual(self._live_head(), self.v1)
        self.assertEqual(
            _read(os.path.join(self.live + ".prev", "app.txt")), "v2\n")
        self.assertEqual(self._run("--rollback").returncode, 0)
        self.assertEqual(self._live_content(), "v2\n")
        self.assertEqual(self._live_head(), self.v2)

    def test_rollback_without_previous_refuses(self):
        result = self._run("--rollback")
        self.assertEqual(result.returncode, 1)
        self.assertIn("no previous tree", result.stderr)
        self.assertEqual(self._live_content(), "v1\n")

    def test_missing_bundle_is_usage_error(self):
        result = self._run(os.path.join(self.tmp.name, "nope.bundle"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)
        self.assertEqual(self._live_content(), "v1\n")
        self.assertFalse(os.path.exists(self.live + ".prev"))

    def test_corrupt_bundle_refuses_and_leaves_target(self):
        bad = os.path.join(self.tmp.name, "bad.bundle")
        with open(bad, "w", encoding="utf-8") as handle:
            handle.write("this is not a git bundle\n")
        result = self._run(bad)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._live_content(), "v1\n")
        self.assertEqual(self._live_head(), self.v1)
        self.assertFalse(os.path.exists(self.live + ".prev"))

    def test_non_git_target_refuses(self):
        plain = os.path.join(self.tmp.name, "plain")
        os.makedirs(plain)
        env = dict(self.env)
        env["METAOS_RELAY_ROOT"] = plain
        result = self._run(self.bundle, env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a git checkout", result.stderr)

    def test_no_args_without_hook_exits_before_touching_target(self):
        env = dict(os.environ)
        env.pop("METAOS_RELAY_ROOT", None)
        result = self._run(env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage", result.stderr)
        self.assertEqual(self._live_content(), "v1\n")

    def test_script_defaults_to_opt_relay_and_names_hook(self):
        text = _read(SCRIPT)
        self.assertIn("TARGET=${METAOS_RELAY_ROOT:-/opt/relay}", text)
        self.assertIn("METAOS_RELAY_ROOT", text)

    def test_readme_documents_rollback(self):
        text = _read(README)
        self.assertIn("metaos-update --rollback", text)
        self.assertIn("second", text)
        self.assertIn("swaps back", text)


if __name__ == "__main__":
    unittest.main()
