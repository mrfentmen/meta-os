"""tests/test_os_overseer_unit.py -- OS-015: the relay overseer unit.

OS-015 ships os/services/relay-overseer.service, the unit that runs
the overseer tick as a service: one overseer pass (lease sweep,
stale-capability prune, done-job verification) per firing, driven
on a timer so the pass repeats without a loop process. These
tests pin the file, not a live boot: the tick-on-a-booted-image
run is still owed (see the os/README.md OS-015 section).

- The unit exists and its [Unit] orders after
  network-online.target, relay-bus.service, and
  relay-jobs.service, and wants all three, so the tick never
  runs before the bus side and the queue pass it reads. This
  is the OS-015 wording: the unit as it landed with the OS-006
  tree wanted only network-online.target and ordered after
  relay-jobs.service alone, so this batch brings the [Unit]
  section up to the plan before pinning it.
- Its [Unit] belongs to relay.target and carries the OS-012
  secrets gate: without /etc/metaos/secrets.env systemd skips
  the unit and the boot continues honestly unconfigured.
- Its [Service] is a oneshot as the relay user from
  /opt/relay, running the real overseer tick with no secret on
  its command line (the token travels via the secrets env file
  only, as a file path, never as a value).
- Its [Install] wants relay.target, relay.target wants the
  timer back, and build-image.sh enables the service itself
  via a relay.target.wants symlink, so the unit is part of
  the boot target on both image routes (build-live.sh stages
  services/*.service).
- The timer is the loop: relay-overseer.timer fires the
  service 2 minutes after boot and every 5 minutes after, and
  is itself wanted by relay.target.
- mos.py really is the process the unit names: it is a shim
  onto mos/cli.py, whose tick subcommand runs
  mos/overseer.py tick(), the pass the unit describes.
- os/README.md carries the OS-015 section naming the owed
  image-run items, and plan/META_OS.md records the unit as
  landed first light.

Scope, stated plainly: the service is one tick pass per timer
firing, not a long-running loop process; the timer is what
repeats it. No bus post, no live Redis, no network, no
systemd: pure file reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.path.join(ROOT, "os", "services", "relay-overseer.service")
TIMER = os.path.join(ROOT, "os", "services", "relay-overseer.timer")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
MOS_SHIM = os.path.join(ROOT, "mos.py")
MOS_CLI = os.path.join(ROOT, "mos", "cli.py")
OVERSEER = os.path.join(ROOT, "mos", "overseer.py")
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


class OverseerUnitTest(unittest.TestCase):
    def test_unit_exists(self):
        self.assertTrue(os.path.exists(UNIT))

    def test_unit_ordering_wants_and_secrets_gate(self):
        unit = sections(read(UNIT))["Unit"]
        after = " ".join(unit.get("After", []))
        wants = " ".join(unit.get("Wants", []))
        for dep in ("network-online.target", "relay-bus.service",
                    "relay-jobs.service"):
            self.assertIn(dep, after)
            self.assertIn(dep, wants)
        self.assertEqual(unit.get("PartOf"), ["relay.target"])
        self.assertEqual(unit.get("ConditionPathExists"),
                         ["/etc/metaos/secrets.env"])

    def test_service_identity_workdir_and_oneshot(self):
        svc = sections(read(UNIT))["Service"]
        self.assertEqual(svc.get("Type"), ["oneshot"])
        self.assertEqual(svc.get("User"), ["relay"])
        self.assertEqual(svc.get("Group"), ["relay"])
        self.assertEqual(svc.get("WorkingDirectory"), ["/opt/relay"])
        self.assertEqual(svc.get("EnvironmentFile"),
                         ["/etc/metaos/secrets.env"])

    def test_exec_runs_mos_tick_with_no_secret_on_command_line(self):
        svc = sections(read(UNIT))["Service"]
        exec_start = " ".join(svc.get("ExecStart", []))
        self.assertEqual(
            exec_start,
            "/usr/bin/python3 /opt/relay/mos.py tick")
        self.assertNotIn("token", exec_start)
        self.assertNotIn("secret", exec_start)
        env = " ".join(svc.get("Environment", []))
        self.assertIn("MUSE_RELAY_TOKEN_FILE=/etc/metaos/token", env)

    def test_install_target_and_image_routes(self):
        install = sections(read(UNIT))["Install"]
        self.assertEqual(install.get("WantedBy"), ["relay.target"])
        target = read(TARGET)
        self.assertIn("relay-overseer.timer", target)
        build_image = read(BUILD_IMAGE)
        self.assertIn("relay-overseer.service", build_image)
        self.assertIn("relay.target.wants", build_image)
        build_live = read(BUILD_LIVE)
        self.assertIn("services/*.service", build_live)

    def test_timer_is_the_loop(self):
        timer = sections(read(TIMER))
        self.assertEqual(timer["Timer"].get("Unit"),
                         ["relay-overseer.service"])
        self.assertEqual(timer["Timer"].get("OnBootSec"), ["2min"])
        self.assertEqual(timer["Timer"].get("OnUnitActiveSec"), ["5min"])
        self.assertEqual(timer["Install"].get("WantedBy"),
                         ["relay.target"])

    def test_mospy_is_the_named_process(self):
        shim = read(MOS_SHIM)
        self.assertIn("from mos.cli import main", shim)
        cli = read(MOS_CLI)
        self.assertIn('"tick"', cli)
        self.assertIn("overseer.tick", cli)
        self.assertIn("set_defaults(fn=cmd_tick)", cli)
        overseer = read(OVERSEER)
        self.assertIn("def tick", overseer)
        self.assertIn("jobs.main([\"sweep\"])", overseer)
        self.assertIn("prune_stale", overseer)

    def test_readme_section_and_spec_record(self):
        readme = read(README)
        self.assertIn("OS-015", readme)
        self.assertIn("relay-overseer.service", readme)
        spec = read(SPEC)
        self.assertIn("OS-015", spec)
        self.assertIn("relay-overseer.service", spec)


if __name__ == "__main__":
    unittest.main()
