"""tests/test_os_target_unit.py -- OS-016: the boot target and ready gate.

OS-016 groups the crew units under relay.target and adds the
oneshot relay-ready gate that writes /run/metaos/ready only when
every gateable unit is up. These tests pin the files, not a live
boot: reaching relay.target on a booted image, and the marker
appearing only with all units active (proven by disabling one
unit), are still owed on the test image (see the os/README.md
OS-016 section).

- relay.target wants the full OS-016 set: dashboard, bus, jobs,
  overseer timer, ready, watchdog, brief, watchman (OS-118),
  and firstboot, and keeps the pre-existing multi-user.target
  ordering.
- The ready unit orders after every unit the gate checks
  (dashboard, bus, jobs, overseer timer, watchdog, firstboot)
  and deliberately NOT after relay-brief.service: the brief runs
  After the ready gate by design, so the gate cannot wait on a
  unit that waits on the gate.
- The ready unit is a oneshot with RemainAfterExit that runs
  the real boot checklist, belongs to relay.target, and is
  wanted by it.
- The checklist gate writes the marker only when the gateable
  set passes: dashboard and watchdog always; bus, jobs Result,
  and overseer timer once secrets exist. It never writes the
  marker on a blocked gate, and says so on its BLOCKED line.
- The jobs sweep is gated on its Result, not is-active: jobs
  and overseer are oneshot units with no RemainAfterExit, so
  is-active reads inactive after a clean run. The overseer tick
  itself is not gated: its timer first fires 2 minutes after
  boot, so no tick has run when the gate runs.
- The target set is enabled identically on every image route:
  build-image.sh, the Packer provisioner, and the live-build
  hook all wire watchdog, brief, and watchman into
  relay.target.wants.
- Worker instances are excluded for a stated reason, not by
  omission: no worker instance is auto-enabled (OS-017).

Scope, stated plainly: pure file reads, no bus post, no live
Redis, no network, no systemd. The checklist script itself is
not executed here: it hardcodes /run/metaos/ready, so running
it in the test suite would write system state.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "os", "services", "relay.target")
READY = os.path.join(ROOT, "os", "services", "relay-ready.service")
CHECKLIST = os.path.join(ROOT, "os", "bin", "metaos-boot-checklist")
BUILD_IMAGE = os.path.join(ROOT, "os", "build-image.sh")
PACKER = os.path.join(ROOT, "os", "packer", "metaos.pkr.hcl")
HOOK = os.path.join(
    ROOT, "os", "live-build", "config", "hooks", "live",
    "0900-metaos-services.hook.chroot")
README = os.path.join(ROOT, "os", "README.md")
SPEC = os.path.join(ROOT, "plan", "META_OS.md")

TARGET_SET = [
    "relay-dashboard.service",
    "relay-bus.service",
    "relay-jobs.service",
    "relay-overseer.timer",
    "relay-ready.service",
    "relay-watchdog.service",
    "relay-brief.service",
    "relay-watchman.service",
    "metaos-firstboot.service",
]


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


class TargetGroupingTest(unittest.TestCase):
    def test_target_wants_full_os016_set(self):
        unit = sections(read(TARGET))["Unit"]
        wants = " ".join(unit.get("Wants", []))
        for member in TARGET_SET:
            self.assertIn(member, wants, member)

    def test_target_keeps_preexisting_base_ordering(self):
        unit = sections(read(TARGET))["Unit"]
        wants = " ".join(unit.get("Wants", []))
        after = " ".join(unit.get("After", []))
        self.assertIn("multi-user.target", wants)
        self.assertIn("multi-user.target", after)
        self.assertIn("network-online.target", after)

    def test_target_enabled_identically_on_all_image_routes(self):
        for path in (BUILD_IMAGE, PACKER, HOOK):
            text = read(path)
            for member in ("relay-watchdog.service",
                           "relay-brief.service",
                           "relay-watchman.service"):
                self.assertIn(member, text, "%s missing %s" % (path, member))

    def test_target_names_worker_template_exclusion(self):
        text = read(TARGET)
        self.assertIn("relay-worker@.service", text)
        unit = sections(text)["Unit"]
        wants = " ".join(unit.get("Wants", []))
        self.assertNotIn("relay-worker@.service", wants)


class ReadyUnitTest(unittest.TestCase):
    def test_ready_orders_after_every_checked_unit(self):
        unit = sections(read(READY))["Unit"]
        after = " ".join(unit.get("After", []))
        for dep in ("relay-dashboard.service", "relay-bus.service",
                    "relay-jobs.service", "relay-overseer.timer",
                    "relay-watchdog.service",
                    "metaos-firstboot.service"):
            self.assertIn(dep, after, dep)

    def test_ready_does_not_wait_on_the_brief(self):
        unit = sections(read(READY))["Unit"]
        after = " ".join(unit.get("After", []))
        self.assertNotIn("relay-brief.service", after)

    def test_ready_is_oneshot_checklist_under_relay_target(self):
        parsed = sections(read(READY))
        self.assertEqual(parsed["Service"].get("Type"), ["oneshot"])
        self.assertEqual(parsed["Service"].get("RemainAfterExit"),
                         ["yes"])
        self.assertEqual(parsed["Service"].get("ExecStart"),
                         ["/usr/local/bin/metaos-boot-checklist"])
        self.assertEqual(parsed["Unit"].get("PartOf"), ["relay.target"])
        self.assertEqual(parsed["Install"].get("WantedBy"),
                         ["relay.target"])


class ChecklistGateTest(unittest.TestCase):
    def test_gate_probes_the_gateable_set(self):
        text = read(CHECKLIST)
        for unit in ("relay-dashboard.service",
                     "relay-watchdog.service",
                     "relay-bus.service",
                     "relay-overseer.timer"):
            self.assertIn(unit, text, unit)
        self.assertIn("systemctl show", text)
        self.assertIn("relay-jobs.service", text)

    def test_marker_write_is_guarded_and_block_is_reported(self):
        text = read(CHECKLIST)
        self.assertIn('if [ "$GATE_OK" = "1" ]; then', text)
        self.assertIn("/run/metaos/ready", text)
        guarded = text.split('if [ "$GATE_OK" = "1" ]; then', 1)[1]
        self.assertIn("/run/metaos/ready", guarded)
        self.assertIn("BLOCKED", text)
        self.assertIn("marker not written", text)

    def test_gate_documents_the_oneshot_and_timer_limits(self):
        text = read(CHECKLIST)
        self.assertIn("RemainAfterExit", text)
        self.assertIn("2 minutes after boot", text)

    def test_no_secret_on_any_command_line(self):
        text = read(CHECKLIST)
        self.assertNotIn("MUSE_RELAY_TOKEN=", text)


class DocsTest(unittest.TestCase):
    def test_readme_carries_os016_section_with_exclusions(self):
        text = read(README)
        self.assertIn("Boot target and ready gate (OS-016", text)
        self.assertIn("relay-worker@", text)
        self.assertIn("OS-118", text)

    def test_spec_carries_os016_record(self):
        text = read(SPEC)
        self.assertIn("Boot target and ready gate (OS-016", text)
        self.assertIn("tests/test_os_target_unit.py", text)


if __name__ == "__main__":
    unittest.main()
