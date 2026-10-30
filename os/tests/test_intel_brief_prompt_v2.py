"""BRF-019: brief prompt v2 files, tuned from eval failures only.

Morning v2 targets three INT-027 cold-start gaps (ask-nick on the
blocked job, no priority order stated, since-your-last-brief
honesty). On-join v2 targets both BRF-018 cold-read gaps (name
the open job's lane, never drop the crew-building sentence).
The v1 files stay in place for diffing and must not gain the
new rules. No re-score is claimed here: a Spark-composed brief
under v2 cannot be scored until real Spark transport lands.
"""

import os
import unittest


def _prompt(name):
    path = os.path.join(os.path.dirname(__file__), "..",
                        "intel", "prompts", name)
    with open(path) as handle:
        return handle.read()


def _flat(name):
    # Prompt files wrap lines, so phrase checks run on
    # whitespace-normalized text, not raw lines.
    return " ".join(_prompt(name).split())


class BriefPromptV2Test(unittest.TestCase):
    """BRF-019: v2 prompt files exist and carry only the targeted rules."""

    def test_morning_v2_exists_and_names_its_target_failure(self):
        text = _prompt("brief_morning_v2.md")
        self.assertIn("BRF-019", text)
        self.assertIn("INT-027", text)

    def test_morning_v2_carries_the_three_new_rules(self):
        text = _flat("brief_morning_v2.md")
        self.assertIn("owner not reported in this window", text)
        self.assertIn("No priority order is recorded in this window",
                      text)
        self.assertIn("No previous brief is in this window,", text)
        self.assertIn("Since your last brief", text)

    def test_morning_v2_keeps_v1_sections_and_budget(self):
        text = _prompt("brief_morning_v2.md")
        for section in ("Decisions", "In flight", "Owners",
                        "Blocked and why", "Watch items"):
            self.assertIn(section, text)
        self.assertIn("220", text)

    def test_morning_v1_does_not_carry_the_new_rules(self):
        text = _flat("brief_morning.md")
        self.assertNotIn("No priority order is recorded in this window",
                         text)
        self.assertNotIn("No previous brief is in this window,", text)
        self.assertNotIn("owner not reported in this window", text)

    def test_morning_v2_states_the_gaps_it_does_not_fix(self):
        text = _prompt("brief_morning_v2.md")
        self.assertIn("Gap 3", text)
        self.assertIn("Gap 4", text)
        self.assertIn("NOT fixed", text)

    def test_onjoin_v2_exists_and_names_its_target_failure(self):
        text = _prompt("brief_onjoin_v2.md")
        self.assertIn("BRF-019", text)
        self.assertIn("BRF-018", text)

    def test_onjoin_v2_carries_the_two_new_rules(self):
        text = _flat("brief_onjoin_v2.md")
        self.assertIn("belongs to the", text)
        self.assertIn("never dropped under trim", text)
        self.assertIn("Never guess a lane", text)

    def test_onjoin_v2_keeps_v1_sections_and_budget(self):
        text = _prompt("brief_onjoin_v2.md")
        for section in ("What this crew is building",
                        "Your likely lane", "What is blocked",
                        "Who to ask"):
            self.assertIn(section, text)
        self.assertIn("150", text)

    def test_onjoin_v1_does_not_carry_the_new_rules(self):
        text = _flat("brief_onjoin.md")
        self.assertNotIn("never dropped under trim", text)
        self.assertNotIn("never guess a lane", text)

    def test_onjoin_v2_states_the_composer_gap_it_does_not_fix(self):
        text = _prompt("brief_onjoin_v2.md")
        self.assertIn("NOT fix", text)
        self.assertIn("composer", text.lower())

    def test_v2_files_add_no_em_dash_beyond_v1(self):
        # The v1 files already carry em dashes in their headings,
        # so this pins that v2 adds none of its own.
        for v1, v2 in (("brief_morning.md", "brief_morning_v2.md"),
                       ("brief_onjoin.md", "brief_onjoin_v2.md")):
            self.assertEqual(_prompt(v1).count("\u2014"),
                             _prompt(v2).count("\u2014"), v2)

    def test_explainer_names_brief_v2_and_keeps_wiring_gap(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "README.md")
        with open(path) as handle:
            text = handle.read()
        self.assertIn("brief_morning_v2.md", text)
        self.assertIn("brief_onjoin_v2.md", text)
        self.assertIn("not wired", text.lower())


if __name__ == "__main__":
    unittest.main()
