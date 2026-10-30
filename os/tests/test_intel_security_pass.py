"""INT-011: tests for the security pass scanner.

All planted values are built by concatenation, so no
complete credential-shaped literal sits in this file:
the full value exists only at runtime, inside a temp
dir the scanner reads. That keeps the repo-wide scan
clean while still proving the scanner flags real
shapes, never prints values, and excuses only the
documented fixture rules.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import security_pass  # noqa: E402


def _planted_token():
    return "ghp_" + "K7m9Q2xR4vT8yN5bD3fH6jK1mP"


def _planted_key_header():
    return "-----BEGIN " + "RSA PRIVATE " + "KEY-----"


def _planted_api_key():
    return "sk-" + "Z8w3E5rT7yU2iO9pA4sD6fG1hJ"


def _write(tmpdir, name, text):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


class SecurityPassTest(unittest.TestCase):
    def test_flags_planted_provider_token_and_key_header(self):
        token = _planted_token()
        header = _planted_key_header()
        with tempfile.TemporaryDirectory() as tmpdir:
            _write(tmpdir, "leak.py",
                    "key = " + repr(token) + "\n")
            _write(tmpdir, "key.pem.txt", header + "\n")
            findings, _fixtures, _count = \
                security_pass.scan_root(tmpdir)
            kinds = {kind for _rel, _line, kind in findings}
            self.assertIn("github-token", kinds)
            self.assertIn("private-key", kinds)

    def test_flags_secret_filenames_even_when_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write(tmpdir, "prod.env", "")
            _write(tmpdir, "id.keyring", "")
            findings, _fixtures, _count = \
                security_pass.scan_root(tmpdir)
            names = {rel for rel, _line, _kind in findings}
            self.assertIn("prod.env", names)
            self.assertIn("id.keyring", names)
            self.assertTrue(all(line == 0 for _rel, line, _k
                                in findings))

    def test_report_never_prints_planted_values(self):
        token = _planted_token()
        api_key = _planted_api_key()
        with tempfile.TemporaryDirectory() as tmpdir:
            _write(tmpdir, "leak.py",
                    "api_key = " + repr(api_key) + "\n"
                    "key = " + repr(token) + "\n")
            out = io.StringIO()
            with redirect_stdout(out):
                code = security_pass.main(["security_pass", tmpdir])
            self.assertEqual(code, 1)
            self.assertNotIn(token, out.getvalue())
            self.assertNotIn(api_key, out.getvalue())

    def test_fixture_rules_excuse_only_documented_fakes(self):
        repeated = "ghp_" + "q" * 36
        labeled = "api_key = " + repr("drill-value-9x4k2")
        sequential = "Bearer " + "abcdefghij123456"
        with tempfile.TemporaryDirectory() as tmpdir:
            _write(tmpdir, "fakes.py",
                    "a = " + repr(repeated) + "\n"
                    + labeled + "\n"
                    "b = " + repr(sequential) + "\n")
            findings, fixtures, _count = \
                security_pass.scan_root(tmpdir)
            self.assertEqual(findings, [])
            self.assertEqual(len(fixtures), 3)

    def test_clean_dir_passes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write(tmpdir, "plain.py", "x = 1\n")
            out = io.StringIO()
            with redirect_stdout(out):
                code = security_pass.main(["security_pass", tmpdir])
            self.assertEqual(code, 0)
            self.assertIn("0 findings", out.getvalue())

    def test_gitignore_covers_keyring_and_env_files(self):
        with open(os.path.join(ROOT, ".gitignore"),
                  encoding="utf-8") as handle:
            ignored = handle.read()
        for entry in ("*.env", ".env*", "*.keyring",
                      "job-secret", "admin_secret",
                      "*.pem", "*.key"):
            self.assertIn(entry, ignored)

    def test_drill_carries_no_committed_keyring_literal(self):
        from intel import spoof_dispatch_drill as drill
        self.assertFalse(hasattr(drill, "KEYRING_LINE"))
        self.assertTrue(callable(drill._fresh_keyring_line))
        first = drill._fresh_keyring_line()
        second = drill._fresh_keyring_line()
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith("crew-2026-09:"))
        path = os.path.join(ROOT, "intel",
                            "spoof_dispatch_drill.py")
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("crew-secret", source)
