"""tests/test_os_jobs_unit.py -- OS-014: the relay jobs unit.

OS-014 ships os/services/relay-jobs.service, the unit that runs
the jobs.py queue service pass at boot: a lease sweep that
requeues claimed jobs whose claim holder is gone, so a job
posted before shutdown is claimable again after boot. These
tests pin the file, not a live boot: the announced-and-
claimable-after-boot run on the test image is still owed (see
the os/README.md OS-014 section).

- The unit exists and its [Unit] orders after
  network-online.target and relay-bus.service, so the queue
  pass never runs before the bus side it reads.
- Its [Unit] belongs to relay.target and carries the OS-012
  secrets gate: without /etc/metaos/secrets.env systemd skips
  the unit and the boot continues honestly unconfigured.
- Its [Service] is a oneshot as the relay user from
  /opt/relay, running the real jobs.py sweep with no secret on
  its command line (the token travels via the secrets env file
  only, as a file path, never as a value).
- Its [Install] wants relay.target, and relay.target wants it
  back, so the unit is part of the boot target.
- build-image.sh enables it (relay.target.wants symlink) and
  build-live.sh stages services/*.service, so both image routes
  carry it.
- jobs.py really is the process the unit names: it defines the
  sweep subcommand, and cmd_sweep requeues claimed jobs whose
  mutex holder is gone.
- os/README.md carries the OS-014 section naming the owed
  image-run items, and plan/META_OS.md records the unit as
  landed first light.

Scope, stated plainly: the unit as landed is a boot-time sweep
oneshot, not a continuous queue-service loop. jobs.py defines no
loop or serve subcommand, so the continuous-loop half of the
OS-014 wording is owed, not pinned here. No bus post, no live
Redis, no network, no systemd: pure file reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.path.join(ROOT, "os", "services", "relay-jobs.service")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
JOBS = os.path.join(ROOT, "jobs.py")
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


class JobsUnitTest(unittest.TestCase):
    def test_unit_exists(self):
        self.assertTrue(os.path.exists(UNIT))

    def test_unit_ordering_target_and_secrets_gate(self):
        unit = sections(read(UNIT))["Unit"]
        after = " ".join(unit.get("After", []))
        self.assertIn("network-online.target", after)
        self.assertIn("relay-bus.service", after)
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

    def test_exec_runs_jobs_sweep_with_no_secret_on_command_line(self):
        svc = sections(read(UNIT))["Service"]
        exec_start = " ".join(svc.get("ExecStart", []))
        self.assertEqual(
            exec_start,
            "/usr/bin/python3 /opt/relay/jobs.py sweep")
        self.assertNotIn("token", exec_start)
        self.assertNotIn("secret", exec_start)
        env = " ".join(svc.get("Environment", []))
        self.assertIn("MUSE_RELAY_TOKEN_FILE=/etc/metaos/token", env)

    def test_install_and_target_want_each_other(self):
        install = sections(read(UNIT))["Install"]
        self.assertEqual(install.get("WantedBy"), ["relay.target"])
        target = read(TARGET)
        self.assertIn("relay-jobs.service", target)

    def test_image_route_enables_and_live_route_stages(self):
        build_image = read(BUILD_IMAGE)
        self.assertIn("relay-jobs.service", build_image)
        self.assertIn("relay.target.wants", build_image)
        build_live = read(BUILD_LIVE)
        self.assertIn("services/*.service", build_live)

    def test_jobspy_is_the_named_process(self):
        jobs = read(JOBS)
        self.assertIn('"sweep"', jobs)
        self.assertIn("set_defaults(fn=cmd_sweep)", jobs)
        self.assertIn("def cmd_sweep", jobs)
        self.assertIn("_requeue_fields", jobs)
        self.assertIn("REQUEUED", jobs)

    def test_readme_section_and_spec_record(self):
        readme = read(README)
        self.assertIn("OS-014", readme)
        self.assertIn("relay-jobs.service", readme)
        spec = read(SPEC)
        self.assertIn("OS-014", spec)
        self.assertIn("relay-jobs.service", spec)


if __name__ == "__main__":
    unittest.main()
