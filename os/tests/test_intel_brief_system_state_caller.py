"""intel/brief.py: OS-062 follow-up — with_system_state,
the boot-path caller.

Before this change no caller in the repo filled
`system_state`: a boot brief carried its three drivers
+ tools + apps lines with values only when the snapshot
hand-stated a "system_state" record, and a boot snapshot
that only carried the machine's own stated state carried
the not-reported lines instead. Now the boot path fills
the record first: drivers from the snapshot's own stated
drivers list, gateway health from its own stated
gateway_healthy, and skill apps from its own stated
skill_apps list, with one as_of stamp for the whole
record. A snapshot that hand-states a record keeps it
untouched, and a snapshot that states nothing usable gets
no record added, so older briefs keep their exact shape.
A driver or skill app named twice is one entry, and
malformed names are skipped, never guessed. Gateway
health counts only as a real bool: anything else is
skipped, never guessed.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


SNAPSHOT = {
    "messages": [],
    "drivers": ["muse-code", "relay-driver"],
    "gateway_healthy": True,
    "skill_apps": ["briefing", "dispatch"],
}


class WithSystemStateTest(unittest.TestCase):
    def test_fills_all_three_fields_with_one_stamp(self):
        filled = brief.with_system_state(SNAPSHOT, now=1793093400)
        record = filled["system_state"]
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["drivers"],
                         ["muse-code", "relay-driver"])
        self.assertEqual(record["gateway_healthy"], True)
        self.assertEqual(record["skill_apps"],
                         ["briefing", "dispatch"])

    def test_filled_record_renders_three_lines_in_order(self):
        filled = brief.with_system_state(SNAPSHOT, now=1793093400)
        lines = brief.system_state_lines(filled["system_state"])
        self.assertEqual(lines, [
            "Drivers: muse-code, relay-driver available",
            "Tools: MCP gateway healthy",
            "Skill apps: briefing, dispatch mounted"])

    def test_boot_template_brief_over_filled_snapshot_carries_lines(self):
        filled = brief.with_system_state(SNAPSHOT, now=1793093400)
        text = brief.compose_template_brief(filled, boot=True)
        self.assertIn("Drivers: muse-code, relay-driver available",
                      text)
        self.assertIn("Tools: MCP gateway healthy", text)
        self.assertIn("Skill apps: briefing, dispatch mounted", text)

    def test_boot_brief_via_generate_carries_lines(self):
        filled = brief.with_system_state(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True, boot=True)
        self.assertIn("Drivers: muse-code, relay-driver available",
                      text)
        self.assertIn("Tools: MCP gateway healthy", text)

    def test_non_boot_brief_never_carries_lines_even_when_filled(self):
        filled = brief.with_system_state(SNAPSHOT, now=1793093400)
        text, _record = brief.generate_brief(
            filled, "build", kind="morning", now=1793093400,
            dry_run=True, boot=False)
        self.assertNotIn("Drivers:", text)
        self.assertNotIn("MCP gateway", text)
        self.assertNotIn("Skill apps:", text)

    def test_hand_stated_record_wins_unchanged(self):
        stated = {"drivers": ["muse-code"],
                  "gateway_healthy": False,
                  "skill_apps": []}
        filled = brief.with_system_state(
            {"system_state": stated,
             "drivers": ["some-other-driver"],
             "gateway_healthy": True,
             "skill_apps": ["briefing"]},
            now=1793093400)
        self.assertEqual(filled["system_state"], stated)

    def test_caller_snapshot_is_never_mutated(self):
        original = dict(SNAPSHOT)
        brief.with_system_state(SNAPSHOT, now=1793093400)
        self.assertEqual(SNAPSHOT, original)
        self.assertNotIn("system_state", SNAPSHOT)

    def test_snapshot_with_nothing_usable_gets_no_record(self):
        filled = brief.with_system_state({"messages": []},
                                         now=1793093400)
        self.assertNotIn("system_state", filled)

    def test_name_listed_twice_is_one_entry(self):
        filled = brief.with_system_state(
            {"drivers": ["muse-code", "muse-code"],
             "skill_apps": ["briefing", "briefing", "dispatch"]},
            now=1793093400)
        record = filled["system_state"]
        self.assertEqual(record["drivers"], ["muse-code"])
        self.assertEqual(record["skill_apps"],
                         ["briefing", "dispatch"])

    def test_malformed_names_skipped_never_guessed(self):
        filled = brief.with_system_state(
            {"drivers": ["muse-code", "", 7, None],
             "skill_apps": [True, "dispatch"]},
            now=1793093400)
        record = filled["system_state"]
        self.assertEqual(record["drivers"], ["muse-code"])
        self.assertEqual(record["skill_apps"], ["dispatch"])

    def test_junk_only_lists_build_no_record(self):
        filled = brief.with_system_state(
            {"drivers": ["", 7, None],
             "skill_apps": [True]},
            now=1793093400)
        self.assertNotIn("system_state", filled)

    def test_gateway_down_is_kept_not_omitted(self):
        filled = brief.with_system_state(
            {"gateway_healthy": False},
            now=1793093400)
        self.assertEqual(filled["system_state"]["gateway_healthy"],
                         False)
        lines = brief.system_state_lines(filled["system_state"])
        self.assertIn("Tools: MCP gateway down", lines[1])

    def test_gateway_non_bool_is_skipped_never_guessed(self):
        for bad in ("up", 1, 0, None):
            filled = brief.with_system_state(
                {"gateway_healthy": bad},
                now=1793093400)
            self.assertNotIn("system_state", filled)
        filled = brief.with_system_state(
            {"drivers": ["muse-code"], "gateway_healthy": "up"},
            now=1793093400)
        self.assertNotIn("gateway_healthy",
                         filled["system_state"])

    def test_stated_empty_lists_read_none_not_not_reported(self):
        filled = brief.with_system_state(
            {"drivers": [], "skill_apps": []},
            now=1793093400)
        lines = brief.system_state_lines(filled["system_state"])
        self.assertIn("Drivers: no drivers reported", lines[0])
        self.assertIn("Skill apps: no skill apps mounted", lines[2])
        self.assertIn("Tools: MCP gateway health not reported",
                      lines[1])

    def test_partial_state_builds_partial_record(self):
        filled = brief.with_system_state(
            {"skill_apps": ["dispatch"]},
            now=1793093400)
        record = filled["system_state"]
        self.assertEqual(record["skill_apps"], ["dispatch"])
        self.assertNotIn("drivers", record)
        self.assertNotIn("gateway_healthy", record)
        lines = brief.system_state_lines(record)
        self.assertIn("Drivers: not reported", lines[0])
        self.assertIn("Tools: MCP gateway health not reported",
                      lines[1])

    def test_default_stamp_is_an_int_when_now_is_not_given(self):
        filled = brief.with_system_state(SNAPSHOT)
        self.assertIsInstance(filled["system_state"]["as_of"], int)

    def test_non_dict_snapshot_gets_no_record(self):
        self.assertEqual(brief.with_system_state(None), {})


if __name__ == "__main__":
    unittest.main()
