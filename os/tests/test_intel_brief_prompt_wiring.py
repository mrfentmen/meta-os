"""intel/brief.py: prompt files wired to the Spark composer (Hana lane,
BRF-007 follow-up).

Before this change the brief prompt files in intel/prompts/ were a
spec only: compose_brief built its Spark prompt inline and never
read them. Now load_brief_prompt reads the v1 file for a kind and
both composers send that text as the client's system text when the
caller passes it as system_prompt. Pure-function tests: the clients
here are fakes that record what they were sent, so no Spark call
is made and no real transport is needed. Budget trim and redaction
still apply to the returned text, and a missing prompt file never
fails a brief.
"""

import sys
import tempfile
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


class _RecordingClient:
    def __init__(self, text=""):
        self.text = text
        self.prompt = None
        self.system = "not-called"

    def complete(self, prompt, system=None, lane_feature=None):
        self.prompt = prompt
        self.system = system
        return self.text


class LoadPromptTest(unittest.TestCase):
    def test_each_kind_loads_its_v1_file(self):
        cases = (("morning", "Morning brief prompt"),
                 ("onjoin", "On-join brief prompt"),
                 ("ondemand", "On-demand brief prompt"))
        for kind, heading in cases:
            text = brief.load_brief_prompt(kind)
            self.assertIn(heading, text)
            self.assertEqual(brief.brief_prompt_path(kind).split("/")[-1],
                             brief.BRIEF_PROMPT_FILES[kind])

    def test_unknown_kind_loads_nothing_and_never_raises(self):
        self.assertEqual(brief.load_brief_prompt("nope"), "")
        self.assertIsNone(brief.brief_prompt_path("nope"))

    def test_missing_directory_loads_nothing_and_never_raises(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(
                brief.load_brief_prompt("morning", prompts_dir=empty), "")


class ComposeWiringTest(unittest.TestCase):
    def _snapshot(self):
        return {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}

    def test_prompt_file_text_reaches_client_as_system(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        text = brief.compose_brief(
            self._snapshot(), kind="morning", client=client,
            system_prompt=brief.load_brief_prompt("morning"))
        self.assertIn("Morning brief prompt", client.system)
        self.assertIn("Sections:", client.prompt)
        self.assertIn("ship", text)

    def test_default_call_sends_no_system_text(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        brief.compose_brief(self._snapshot(), kind="morning",
                            client=client)
        self.assertIsNone(client.system)

    def test_empty_system_prompt_sends_no_system_text(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        brief.compose_brief(self._snapshot(), kind="morning",
                            client=client, system_prompt="")
        self.assertIsNone(client.system)

    def test_budget_and_redaction_still_enforced_with_system_prompt(self):
        # Token on a plain line, not a bullet: the BRF-007 trim drops
        # bullet lines first, so a bullet token would be trimmed
        # away by design, not by redaction.
        spark_text = ("Decisions ship api_key=ghp_" + "x" * 25 +
                      "\n" + "word " * 300)
        client = _RecordingClient(text=spark_text)
        text = brief.compose_brief(
            self._snapshot(), kind="morning", client=client,
            system_prompt=brief.load_brief_prompt("morning"))
        self.assertLessEqual(len(text.split()), 220)
        self.assertIn("[redacted]", text)
        self.assertNotIn("ghp_" + "x" * 25, text)

    def test_spark_only_composer_also_carries_system_prompt(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        text = brief.compose_spark_brief(
            self._snapshot(), kind="onjoin", client=client,
            system_prompt=brief.load_brief_prompt("onjoin"))
        self.assertIn("On-join brief prompt", client.system)
        self.assertIn("ship", text)

    def test_spark_only_default_sends_no_system_text(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        brief.compose_spark_brief(self._snapshot(), kind="morning",
                                  client=client)
        self.assertIsNone(client.system)


if __name__ == "__main__":
    unittest.main()
