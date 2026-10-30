"""tests/test_os058_gateway_unit.py -- OS-058: the MCP gateway daemon unit.

OS-058 ships os/services/relay-mcp-gateway.service, the unit that runs
Dale's MCP gateway as a system daemon under relay.target, so every
agent process on the machine reaches the tool estate through the
gateway's one local endpoint. These tests pin the file, not a live
gateway: a boot activation check and a worker plus driver call through
the local endpoint both need the test image, and both are still owed
(see the os/README.md OS-058 section).

- The unit exists and its [Unit] orders after network-online.target
  and belongs to relay.target.
- Its [Unit] carries the OS-012 secrets gate: without
  /etc/metaos/secrets.env systemd skips the unit and the boot
  continues honestly unconfigured.
- Its [Service] runs as relay from the OS-059 bake path
  /opt/relay/mcp-gateway, runs gateway.py with no arguments (the
  program reads backends.json beside itself), restarts on failure,
  and puts no secret on its command line.
- Its [Install] wants relay.target, and relay.target Wants it
  back and all three image routes enable it: the OS-059 bake
  landed, so the deferral these tests pinned before the bake
  is flipped here deliberately, per this file's original note.
- The unit file carries no em dash, and names OS-059 as the owed
  bake in its own header.
- os/README.md carries the OS-058 section naming the owed
  image-run items, and plan/META_OS.md records the unit as
  landed first light.

No gateway process, no live Redis, no network, no systemd: pure
file reads. The gateway program itself is not in this repo (it
lives at ~/workspace/mcp-gateway until the OS-059 bake), so no
test here asserts it exists in-tree.
"""

import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT = os.path.join(ROOT, "os", "services", "relay-mcp-gateway.service")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
README = os.path.join(ROOT, "os", "README.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")
BUILD_IMAGE = os.path.join(ROOT, "os", "build-image.sh")
LIVE_HOOK = os.path.join(
    ROOT, "os", "live-build", "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")


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


def enablement_loop(text):
    for line in text.splitlines():
        if line.strip().startswith("for u in"):
            return line
    return ""


class GatewayUnitTest(unittest.TestCase):
    def test_unit_exists(self):
        self.assertTrue(os.path.exists(UNIT))

    def test_unit_ordering_target_and_secrets_gate(self):
        unit = sections(read(UNIT))["Unit"]
        after = " ".join(unit.get("After", []))
        self.assertIn("network-online.target", after)
        self.assertIn("network-online.target",
                      " ".join(unit.get("Wants", [])))
        self.assertEqual(unit.get("PartOf"), ["relay.target"])
        self.assertEqual(unit.get("ConditionPathExists"),
                         ["/etc/metaos/secrets.env"])

    def test_service_identity_workdir_and_restart(self):
        svc = sections(read(UNIT))["Service"]
        self.assertEqual(svc.get("Type"), ["simple"])
        self.assertEqual(svc.get("User"), ["relay"])
        self.assertEqual(svc.get("Group"), ["relay"])
        self.assertEqual(svc.get("WorkingDirectory"),
                         ["/opt/relay/mcp-gateway"])
        self.assertEqual(svc.get("Restart"), ["on-failure"])
        self.assertEqual(svc.get("RestartSec"), ["5"])
        self.assertEqual(svc.get("EnvironmentFile"),
                         ["/etc/metaos/secrets.env"])

    def test_exec_runs_gateway_with_no_secret_on_command_line(self):
        svc = sections(read(UNIT))["Service"]
        exec_start = " ".join(svc.get("ExecStart", []))
        self.assertEqual(
            exec_start,
            "/usr/bin/python3 /opt/relay/mcp-gateway/gateway.py")
        self.assertNotIn("token", exec_start)
        self.assertNotIn("secret", exec_start)
        self.assertNotIn("key", exec_start)

    def test_install_and_target_wiring_live_after_bake(self):
        install = sections(read(UNIT))["Install"]
        self.assertEqual(install.get("WantedBy"), ["relay.target"])
        self.assertIn("relay-mcp-gateway.service", read(TARGET))

    def test_image_routes_enable_after_bake(self):
        self.assertIn("relay-mcp-gateway.service",
                      enablement_loop(read(BUILD_IMAGE)))
        self.assertIn("relay-mcp-gateway.service",
                      enablement_loop(read(LIVE_HOOK)))

    def test_header_names_bake_and_has_no_em_dash(self):
        text = read(UNIT)
        self.assertIn("OS-059", text)
        self.assertNotIn("waits on the OS-059 bake", text)
        self.assertNotIn("\u2014", text)

    def test_readme_section_and_spec_record(self):
        readme = read(README)
        self.assertIn("OS-058", readme)
        self.assertIn("relay-mcp-gateway.service", readme)
        spec = read(SPEC)
        self.assertIn("OS-058", spec)
        self.assertIn("relay-mcp-gateway.service", spec)


if __name__ == "__main__":
    unittest.main()
