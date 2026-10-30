"""intel/brief.py: prompt-file version selection + stored-brief
passthrough (Hana lane, BRF-007 follow-up).

Before this change the loader read v1 only, and generate_brief
took a client but no prompt: a caller that wanted prompt-file
wiring through the stored-brief path had to call compose_brief
directly and give up storage and the BRF-028 guard. Now
load_brief_prompt takes a version ("v1" default, "v2"), and
generate_brief passes system_prompt through to compose_brief.
Pure-function tests: the clients here are fakes that record
what they were sent, so no Spark call is made and no real
transport is needed. A missing v2 file never fails a brief,
and a v2 request never silently falls back to v1 text.
"""

import sys
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


class LoadVersionTest(unittest.TestCase):
    def test_v1_default_unchanged(self):
        text = brief.load_brief_prompt("morning")
        self.assertIn("Morning brief prompt", text)
        self.assertIn("v1 (BRF-001)", text)
        self.assertEqual(
            brief.brief_prompt_path("morning").split("/")[-1],
            "brief_morning.md")

    def test_v2_morning_loads_v2_file(self):
        text = brief.load_brief_prompt("morning", version="v2")
        self.assertIn("Morning brief prompt", text)
        self.assertIn("v2 (BRF-019)", text)
        self.assertEqual(
            brief.brief_prompt_path("morning",
                                    version="v2").split("/")[-1],
            "brief_morning_v2.md")

    def test_v2_onjoin_loads_v2_file(self):
        text = brief.load_brief_prompt("onjoin", version="v2")
        self.assertIn("On-join brief prompt", text)
        self.assertIn("v2 (BRF-019)", text)
        self.assertEqual(
            brief.brief_prompt_path("onjoin",
                                    version="v2").split("/")[-1],
            "brief_onjoin_v2.md")

    def test_v2_ondemand_loads_nothing_no_v1_fallback(self):
        # Ondemand has no v2 file: the caller gets "", not a
        # silent v1 text under a v2 label.
        self.assertEqual(
            brief.load_brief_prompt("ondemand", version="v2"), "")
        self.assertIsNone(
            brief.brief_prompt_path("ondemand", version="v2"))

    def test_unknown_version_and_kind_load_nothing(self):
        self.assertEqual(
            brief.load_brief_prompt("morning", version="v3"), "")
        self.assertIsNone(
            brief.brief_prompt_path("morning", version="v3"))
        self.assertEqual(
            brief.load_brief_prompt("nope", version="v2"), "")
        self.assertIsNone(
            brief.brief_prompt_path("nope", version="v2"))


class GeneratePromptTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, "tests")
        from fake_redis import FakeUpstash
        import relay_common as rc
        self.fake = FakeUpstash()
        self._old_get = rc.api_get
        self._old_post = rc.api_post
        rc.api_get = self.fake.api_get
        rc.api_post = self.fake.api_post

    def tearDown(self):
        import relay_common as rc
        rc.api_get = self._old_get
        rc.api_post = self._old_post

    def _snapshot(self):
        return {"messages": [{"nick": "pax",
                               "text": "DECISION: ship the panel"}],
                "jobs": []}

    def test_v2_prompt_reaches_client_through_generate_brief(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        system = brief.load_brief_prompt("morning", version="v2")
        text, record = brief.generate_brief(
            self._snapshot(), "prompt-v2-room", kind="morning",
            now=1793000000, client=client, system_prompt=system)
        self.assertIn("Morning brief prompt", client.system)
        self.assertIn("v2 (BRF-019)", client.system)
        self.assertIn("ship", text)
        self.assertEqual(record["model"], "spark")

    def test_v1_prompt_reaches_client_through_generate_brief(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        text, _record = brief.generate_brief(
            self._snapshot(), "prompt-v1-room", kind="morning",
            now=1793010000, client=client,
            system_prompt=brief.load_brief_prompt("morning"))
        self.assertIn("v1 (BRF-001)", client.system)
        self.assertIn("ship", text)

    def test_generate_default_still_sends_no_system_text(self):
        client = _RecordingClient(text="Decisions\n- ship\n")
        text, _record = brief.generate_brief(
            self._snapshot(), "prompt-default-room", kind="morning",
            now=1793020000, client=client)
        self.assertIsNone(client.system)
        self.assertIn("ship", text)


if __name__ == "__main__":
    unittest.main()
