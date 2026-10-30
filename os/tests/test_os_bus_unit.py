"""tests/test_os_bus_unit.py -- OS-013: the relay bus unit.

OS-013 ships os/services/relay-bus.service, the unit that keeps the
local bus side current on a Meta OS machine: the watch.py listener
with its presence beat, as the relay user, under relay.target.
These tests pin the file, not a live bus process: a kill-restart
run and a clean start-order check need the test image, and both
are still owed (see the os/README.md OS-013 section).

- The unit exists and its [Unit] orders after
  network-online.target and belongs to relay.target.
- Its [Unit] carries the OS-012 secrets gate: without
  /etc/metaos/secrets.env systemd skips the unit and the boot
  continues honestly unconfigured.
- Its [Service] runs as relay from /opt/relay, runs the real
  watch.py entry with --interval 10, restarts on failure, and
  puts no secret on its command line (no --dm flag; the token
  travels via the secrets env file only).
- Its [Install] wants relay.target, and relay.target wants it
  back, so the unit is part of the boot target.
- build-image.sh enables it (relay.target.wants symlink) and
  build-live.sh stages services/*.service, so both image routes
  carry it; the live-build enable step is not pinned here
  because no live-build enable hook exists in this tree yet.
- watch.py really is the process the unit names: it defines
  --interval and beats presence on its loop.
- os/README.md carries the OS-013 section naming the owed
  image-run items, and plan/META_OS.md records the unit as
  landed first light.

No bus post, no live Redis, no network, no systemd: pure file
reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.path.join(ROOT, "os", "services", "relay-bus.service")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
WATCH = os.path.join(ROOT, "watch.py")
README = os.path.join(ROOT, "os", "README.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
BUILD_IMAGE = os.path.join(ROOT, "os", "build-image.sh")
BUILD_LIVE = os.path.join(ROOT, "os", "build-live.sh")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def sections(text):
    out = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            out.setdefault(section, {})
            continue
        if section is not None and "=" in line:
            key, val = line.split("=", 1)
            out[section].setdefault(key.strip(), []).append(val.strip())
    return out


class BusUnitTest(unittest.TestCase):
    def test_unit_exists(self):
        self.assertTrue(os.path.exists(UNIT))

    def test_unit_ordering_target_and_secrets_gate(self):
        unit = sections(read(UNIT))["Unit"]
        after = " ".join(unit.get("After", []))
        self.assertIn("network-online.target", after)
        self.assertEqual(unit.get("PartOf"), ["relay.target"])
        self.assertEqual(unit.get("ConditionPathExists"),
                         ["/etc/metaos/secrets.env"])

    def test_service_identity_workdir_and_restart(self):
        svc = sections(read(UNIT))["Service"]
        self.assertEqual(svc.get("Type"), ["simple"])
        self.assertEqual(svc.get("User"), ["relay"])
        self.assertEqual(svc.get("Group"), ["relay"])
        self.assertEqual(svc.get("WorkingDirectory"), ["/opt/relay"])
        self.assertEqual(svc.get("Restart"), ["on-failure"])
        self.assertEqual(svc.get("RestartSec"), ["5"])
        self.assertEqual(svc.get("EnvironmentFile"),
                         ["/etc/metaos/secrets.env"])

    def test_exec_runs_watchpy_with_no_secret_on_command_line(self):
        svc = sections(read(UNIT))["Service"]
        exec_start = " ".join(svc.get("ExecStart", []))
        self.assertEqual(
            exec_start,
            "/usr/bin/python3 /opt/relay/watch.py --interval 10")
        self.assertNotIn("--dm", exec_start)
        self.assertNotIn("token", exec_start)

    def test_install_and_target_want_each_other(self):
        install = sections(read(UNIT))["Install"]
        self.assertEqual(install.get("WantedBy"), ["relay.target"])
        target = read(TARGET)
        self.assertIn("relay-bus.service", target)

    def test_image_route_enables_and_live_route_stages(self):
        build_image = read(BUILD_IMAGE)
        self.assertIn("relay-bus.service", build_image)
        self.assertIn("relay.target.wants", build_image)
        build_live = read(BUILD_LIVE)
        self.assertIn("services/*.service", build_live)

    def test_watchpy_is_the_named_process(self):
        watch = read(WATCH)
        self.assertIn('"--interval"', watch)
        self.assertIn("presence_beat", watch)

    def test_readme_section_and_spec_record(self):
        readme = read(README)
        self.assertIn("OS-013", readme)
        self.assertIn("relay-bus.service", readme)
        spec = read(SPEC)
        self.assertIn("OS-013", spec)
        self.assertIn("relay-bus.service", spec)


if __name__ == "__main__":
    unittest.main()
