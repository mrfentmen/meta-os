"""tests/test_os_boot_harness.py -- OS-019: the QEMU boot test harness.

OS-019 first light: os/test-boot.sh boots a built image headless
in QEMU, waits for the relay-ready marker via the guest agent,
reads the image version stamp, and screenshots the dashboard.

These tests pin the harness, not a boot: no QEMU run has happened
from this script (the sandbox has no qemu-system-x86_64 binary,
and no test image has been booted by it yet), so the launch
flags, the guest-agent handshake, and the monitor screendump are
pinned as written text plus real negative runs, and the QEMU run
itself stays explicitly UNPROVEN until a build host runs the
script end to end. What is pinned here is real:

- The script is bash-clean (bash -n) and its two embedded
  Python clients compile (heredoc extraction plus compile()).
- Argument handling: no IMAGE is a usage error; a missing image,
  a bad timeout/memory/cpus value, and a non-PPM screenshot path
  all fail naming the problem; nothing boots on a bad call.
- A missing qemu-system-x86_64 binary fails naming the binary
  (run with a PATH that holds no qemu, so the guard is exercised,
  not asserted from text).
- The launch line carries the OS-019 contract: snapshot overlay
  by default, no network device, the guest-agent virtserialport
  name, the monitor socket, the serial log, and the
  /run/metaos/ready marker plus /etc/metaos-version reads.
- os/README.md carries the OS-019 section with the unproven
  limit stated, and no em dash appears in any new content here.

No bus post, no live Redis, no network: pure file reads plus
local negative runs of the script itself.
"""

import os
import re
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
SCRIPT = os.path.join(OS_DIR, "test-boot.sh")
README = os.path.join(OS_DIR, "README.md")

# The guest-agent device name the harness must attach, and the
# marker/version paths it must read through that channel.
QGA_DEVICE = "org.qemu.guest_agent.0"
READY_MARKER = "/run/metaos/ready"
VERSION_FILE = "/etc/metaos-version"


def run_script(args, env=None):
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", SCRIPT] + args,
        capture_output=True, text=True, env=run_env, timeout=60)


def heredoc_bodies(text):
    """Yield (name, body) for every <<'NAME' ... NAME heredoc."""
    bodies = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.search(r"<<'([A-Za-z0-9_]+)'\s*$", lines[i])
        if m:
            name = m.group(1)
            i += 1
            body = []
            while i < len(lines) and lines[i] != name:
                body.append(lines[i])
                i += 1
            bodies.append((name, "\n".join(body)))
        i += 1
    return bodies


class BootHarnessTest(unittest.TestCase):
    def test_script_exists_and_bash_clean(self):
        self.assertTrue(os.path.isfile(SCRIPT), "os/test-boot.sh missing")
        proc = subprocess.run(["bash", "-n", SCRIPT],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         "bash -n failed: %s" % proc.stderr)

    def test_embedded_python_compiles(self):
        with open(SCRIPT) as f:
            text = f.read()
        bodies = heredoc_bodies(text)
        names = [n for n, _ in bodies]
        self.assertIn("QGA_WAIT_PY", names)
        self.assertIn("QGA_VERSION_PY", names)
        self.assertIn("MON_PY", names)
        for name, body in bodies:
            self.assertTrue(body.strip(), "empty heredoc %s" % name)
            compile(body, "<%s>" % name, "exec")

    def test_no_image_is_usage_error(self):
        proc = run_script([])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("usage", proc.stderr.lower())

    def test_missing_image_fails_naming_path(self):
        proc = run_script(["/tmp/does-not-exist-metaos.img"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("/tmp/does-not-exist-metaos.img",
                      proc.stdout + proc.stderr)

    def test_bad_numbers_fail(self):
        with tempfile.NamedTemporaryFile(suffix=".img") as img:
            for flag, value in [("--timeout", "abc"),
                                ("--timeout", "0"),
                                ("--memory", "-1"),
                                ("--cpus", "x")]:
                proc = run_script([img.name, flag, value])
                self.assertNotEqual(proc.returncode, 0,
                                    "%s %s should fail" % (flag, value))

    def test_non_ppm_screenshot_fails(self):
        with tempfile.NamedTemporaryFile(suffix=".img") as img:
            proc = run_script([img.name, "--screenshot",
                               "/tmp/shot.png"])
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn(".ppm", proc.stdout + proc.stderr)

    def test_missing_qemu_fails_naming_binary(self):
        # A PATH with no qemu at all: the guard must fire before
        # any launch is attempted. The script is invoked by absolute
        # bash path, so the empty PATH cannot break the invocation.
        with tempfile.TemporaryDirectory() as empty:
            with tempfile.NamedTemporaryFile(suffix=".img") as img:
                proc = subprocess.run(
                    ["/bin/bash", SCRIPT, img.name],
                    capture_output=True, text=True,
                    env={"PATH": empty}, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("qemu-system-x86_64", proc.stdout + proc.stderr)

    def test_launch_contract_in_script(self):
        with open(SCRIPT) as f:
            text = f.read()
        self.assertIn("snapshot=on", text)
        self.assertIn(QGA_DEVICE, text)
        self.assertIn(READY_MARKER, text)
        self.assertIn(VERSION_FILE, text)
        self.assertIn("screendump", text)
        self.assertIn("monitor", text)
        self.assertIn("serial", text)
        # Isolated guest: no network device flag in code lines
        # (comments describing the absence do not count).
        code = "\n".join(
            line for line in text.splitlines()
            if not line.strip().startswith("#"))
        self.assertNotIn("-netdev", code)
        self.assertNotIn("-nic ", code)
        # Cleanup is trapped, not best-effort.
        self.assertIn("trap cleanup EXIT", text)
        # Guest agent reads are the readiness signal, never a
        # message counter or a fixed sleep.
        self.assertIn("guest-exec", text)

    def test_readme_section_states_unproven_limit(self):
        with open(README) as f:
            text = f.read()
        self.assertIn("OS-019", text)
        self.assertIn("test-boot.sh", text)
        self.assertIn("UNPROVEN", text)
        self.assertIn("screendump", text)

    def test_no_em_dash_in_new_content(self):
        with open(SCRIPT) as f:
            self.assertNotIn("\u2014", f.read())
        with open(os.path.abspath(__file__)) as f:
            self.assertNotIn("\u2014", f.read())


if __name__ == "__main__":
    unittest.main()
