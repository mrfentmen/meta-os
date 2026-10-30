"""tests/test_os_worker_units.py -- OS-017: the worker fleet template.

OS-017 ships os/services/relay-worker@.service, one template unit
instantiated per crew nick, with a per-instance env file and the
OS-035 worker slice. These tests pin the file, not a live fleet:
a live two-instance run needs the test image, and two acceptance
blockers are still owed (see the unit header): no stock handler
program ships for the mos.py worker loop, and the DM secret has
no environment path in mos.py, so the template passes no --dm.

- The template exists and its [Unit] orders after
  relay-jobs.service and belongs to relay.target.
- Its [Service] runs as relay, joins relay-workers.slice,
  restarts on failure, and works from /opt/relay.
- The instance name is the nick: MUSE_RELAY_NICK=%i.
- Env files: the image-wide secrets file is required, and the
  per-instance file is optional (leading dash).
- ExecStart runs the real mos.py worker entry and carries no
  --dm flag: no secret ever lands on the unit command line.
- The build scripts stage every services/*.service (which
  carries the template into both image routes) but never name
  relay-worker@ for auto-enable: instances stay off until the
  handler program and the DM env path land.
- os/README.md carries the OS-017 section naming both owed items,
  and plan/META_OS.md records the template as landed.

No bus post, no live Redis, no network, no systemd: pure file
reads.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.path.join(ROOT, "os", "services", "relay-worker@.service")
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


class WorkerTemplateTest(unittest.TestCase):
    def test_template_exists(self):
        self.assertTrue(os.path.exists(UNIT))

    def test_unit_ordering_and_target(self):
        unit = sections(read(UNIT))["Unit"]
        after = " ".join(unit.get("After", []))
        self.assertIn("relay-jobs.service", after)
        self.assertEqual(unit.get("PartOf"), ["relay.target"])

    def test_service_identity_slice_restart(self):
        svc = sections(read(UNIT))["Service"]
        self.assertEqual(svc.get("User"), ["relay"])
        self.assertEqual(svc.get("Group"), ["relay"])
        self.assertEqual(svc.get("WorkingDirectory"), ["/opt/relay"])
        self.assertEqual(svc.get("Slice"), ["relay-workers.slice"])
        self.assertEqual(svc.get("Restart"), ["on-failure"])

    def test_instance_name_is_the_nick(self):
        svc = sections(read(UNIT))["Service"]
        env = svc.get("Environment", [])
        self.assertIn("MUSE_RELAY_NICK=%i", env)

    def test_env_files_required_and_optional(self):
        svc = sections(read(UNIT))["Service"]
        files = svc.get("EnvironmentFile", [])
        self.assertIn("/etc/metaos/secrets.env", files)
        self.assertIn("-/etc/metaos/worker-%i.env", files)

    def test_exec_runs_mos_worker_without_dm_secret(self):
        svc = sections(read(UNIT))["Service"]
        starts = svc.get("ExecStart", [])
        self.assertEqual(len(starts), 1)
        self.assertIn("/opt/relay/mos.py worker", starts[0])
        self.assertNotIn("--dm", starts[0])

    def test_build_scripts_carry_template_but_never_auto_enable(self):
        build = read(BUILD_IMAGE)
        self.assertIn("services/*.service", build)
        self.assertNotIn("relay-worker@", build)
        live = read(BUILD_LIVE)
        self.assertIn("services/*.service", live)
        self.assertNotIn("relay-worker@", live)

    def test_readme_section_names_both_owed_items(self):
        readme = read(README)
        self.assertIn("OS-017", readme)
        self.assertIn("relay-worker@.service", readme)
        self.assertIn("handler", readme)
        self.assertIn("DM secret", readme)

    def test_spec_records_template_as_landed(self):
        spec = read(SPEC)
        self.assertIn("relay-worker@.service", spec)
        self.assertIn("OS-017", spec)
        self.assertIn("worker fleet template", spec)

    def test_no_em_dash_in_new_files(self):
        for path in (UNIT, __file__):
            self.assertNotIn("\u2014", read(path))


if __name__ == "__main__":
    unittest.main()
