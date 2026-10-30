"""tests/test_os_packer.py -- OS-007: the primary Packer + QEMU pipeline.

OS-007 first light: os/packer/metaos.pkr.hcl plus the one-command
wrapper os/build-packer.sh that resolves the bookworm netinst ISO,
generates a random per-build relay password and a build preseed from
os/preseed.cfg, validates and builds, and renames the raw output to
metaos-<date>.img + .sha256.

These tests pin the pipeline files, not a build: no Packer build has
been run from this template (the sandbox has no packer, no qemu, and
no /dev/kvm), so a build, a boot, and second-run reproducibility are
explicitly UNPROVEN and stay that way until a build host runs the
wrapper end to end. What is pinned here is real: the template shape,
the wrapper guards and transforms, and the honesty limits in the docs.

- Template exists, names a qemu source, bookworm only, raw format,
  vm_name metaos, output under os/work/ (gitignored).
- ISO checksum is the publisher SHA256SUMS file, not a hash invented
  in this repo; the ISO URL itself has no default (the wrapper
  resolves it from the cdimage listing).
- ssh_password is a sensitive variable with no default; no committed
  file carries a literal build password; the wrapper generates one
  with openssl rand and hashes it with openssl passwd.
- The wrapper's preseed transform, run verbatim from the committed
  sed line, changes exactly one line of os/preseed.cfg: the locked
  "*" password line becomes the build hash. The committed preseed
  itself is untouched by the wrapper (it reads it, never writes it).
- Provisioners install the same unit list and stamp format as
  os/build-image.sh, plus the getty autologin drop-ins.
- Wrapper guards: set -euo pipefail, clean-checkout refusal, tool
  checks for packer and qemu-system-x86_64, sha256 step, artifact
  naming metaos-<date>.img.
- os/README.md carries the OS-007 section with the unproven-build
  limit stated, and no em dash (the check.sh new-doc rule).

No bus post, no live Redis, no network: pure file reads plus local
shell syntax and transform checks.
"""

import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
TEMPLATE = os.path.join(OS_DIR, "packer", "metaos.pkr.hcl")
WRAPPER = os.path.join(OS_DIR, "build-packer.sh")

FORBIDDEN_CODENAMES = re.compile(
    r"\b(bullseye|trixie|forky|sid|ubuntu|fedora|centos|rhel|archlinux)\b",
    re.IGNORECASE,
)

# The unit list os/build-image.sh enables (OS-016 target set).
ENABLED_UNITS = [
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "metaos-firstboot.service",
    "relay-watchdog.service",
    "relay-brief.service",
]


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class OsPackerTemplateTest(unittest.TestCase):
    def test_template_exists_and_names_qemu_source(self):
        text = _read(TEMPLATE)
        self.assertIn('source "qemu" "metaos"', text)
        self.assertIn('sources = ["source.qemu.metaos"]', text)

    def test_template_bookworm_only_no_second_base(self):
        text = _read(TEMPLATE)
        self.assertIn("bookworm", text)
        match = FORBIDDEN_CODENAMES.search(text)
        self.assertIsNone(match, "template names a second base: %s" % (
            match.group(0) if match else ""))

    def test_template_raw_output_and_names(self):
        text = _read(TEMPLATE)
        self.assertIn('format            = "raw"', text)
        self.assertIn('vm_name           = "metaos"', text)
        self.assertIn('output_directory  = "work/packer-out"', text)
        self.assertIn('http_directory    = "work/packer-http"', text)

    def test_template_iso_checksum_is_publisher_file_not_invented_hash(self):
        text = _read(TEMPLATE)
        self.assertIn(
            "file:https://cdimage.debian.org/debian-cd/current/"
            "amd64/iso-cd/SHA256SUMS", text)
        self.assertNotIn("iso_checksum      = \"sha256:", text)

    def test_template_iso_url_has_no_default(self):
        text = _read(TEMPLATE)
        block = re.search(
            r'variable "iso_url" \{(.*?)\n\}', text, re.DOTALL)
        self.assertIsNotNone(block)
        self.assertIsNone(re.search(
            r'^\s*default\s*=', block.group(1), re.MULTILINE))

    def test_template_ssh_password_sensitive_and_undefaulted(self):
        text = _read(TEMPLATE)
        block = re.search(
            r'variable "ssh_password" \{(.*?)\n\}', text, re.DOTALL)
        self.assertIsNotNone(block)
        self.assertIn("sensitive   = true", block.group(1))
        self.assertNotIn("default", block.group(1))
        self.assertIn('ssh_username      = "relay"', text)
        self.assertIn("preseed-build.cfg", text)

    def test_template_provisioners_mirror_build_image_glue(self):
        text = _read(TEMPLATE)
        for unit in ENABLED_UNITS:
            self.assertIn(unit, text)
        self.assertIn("/etc/metaos-version", text)
        self.assertIn("(debian 12 bookworm, stock kernel)", text)
        self.assertIn("autologin relay", text)
        for dirname in ("services", "firstboot", "bin"):
            self.assertIn('source      = "%s"' % dirname, text)
            self.assertTrue(
                os.path.isdir(os.path.join(OS_DIR, dirname)),
                "provisioner source dir missing: %s" % dirname)

    def test_no_literal_password_in_template_or_wrapper(self):
        for path in (TEMPLATE, WRAPPER):
            text = _read(path)
            literal = re.search(
                r'ssh_password\s*=\s*"[^"%][^"]{7,}"', text)
            self.assertIsNone(
                literal, "%s assigns ssh_password a literal" % path)
            self.assertNotIn("password123", text)
        wrapper = _read(WRAPPER)
        self.assertIn("printf 'ssh_password = \"%s\"\\n' \"$BUILD_PASS\"",
                      wrapper)


class OsPackerWrapperTest(unittest.TestCase):
    def test_wrapper_syntax_clean(self):
        result = subprocess.run(
            ["bash", "-n", WRAPPER],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrapper_guards(self):
        text = _read(WRAPPER)
        self.assertIn("set -euo pipefail", text)
        self.assertIn("status --porcelain", text)
        self.assertIn("refusing: checkout is dirty", text)
        for tool in ("packer", "qemu-system-x86_64", "openssl", "curl"):
            self.assertIn(tool, text)
        self.assertIn("packer validate", text)
        self.assertIn("packer build", text)
        self.assertIn("sha256sum", text)
        self.assertIn('IMG="metaos-$DATE.img"', text)
        self.assertIn('DATE=$(date +%F)', text)

    def test_wrapper_generates_password_with_openssl_not_a_literal(self):
        text = _read(WRAPPER)
        self.assertIn("openssl rand -base64", text)
        self.assertIn("openssl passwd -6", text)
        self.assertIn('trap cleanup EXIT', text)
        self.assertIn('rm -rf "$HTTP_DIR" "$VAR_FILE"', text)

    def test_wrapper_preseed_transform_changes_exactly_one_line(self):
        wrapper_lines = _read(WRAPPER).splitlines()
        start = next(
            i for i, line in enumerate(wrapper_lines)
            if line.startswith("sed ") and "user-password-crypted" in line)
        snippet = "\n".join(wrapper_lines[start:start + 2])
        with tempfile.TemporaryDirectory() as tmpdir:
            env = dict(os.environ)
            env["HTTP_DIR"] = tmpdir
            env["BUILD_HASH"] = "TESTHASH"
            result = subprocess.run(
                ["bash", "-c", snippet],
                cwd=OS_DIR, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            original = _read(os.path.join(OS_DIR, "preseed.cfg"))
            built = _read(os.path.join(tmpdir, "preseed-build.cfg"))
            orig_lines = original.splitlines()
            built_lines = built.splitlines()
            self.assertEqual(len(orig_lines), len(built_lines))
            diffs = [i for i, (a, b) in enumerate(
                zip(orig_lines, built_lines)) if a != b]
            self.assertEqual(len(diffs), 1)
            i = diffs[0]
            self.assertIn("user-password-crypted password *", orig_lines[i])
            self.assertIn(
                "user-password-crypted password TESTHASH", built_lines[i])

    def test_committed_preseed_still_locked(self):
        text = _read(os.path.join(OS_DIR, "preseed.cfg"))
        self.assertIn("user-password-crypted password *", text)


class OsPackerDocsTest(unittest.TestCase):
    def test_readme_carries_os007_section_with_unproven_limit(self):
        text = _read(os.path.join(OS_DIR, "README.md"))
        self.assertIn("OS-007", text)
        self.assertIn("build-packer.sh", text)
        self.assertIn("packer/metaos.pkr.hcl", text)
        self.assertIn("UNPROVEN", text)
        self.assertNotIn("\u2014", text)
