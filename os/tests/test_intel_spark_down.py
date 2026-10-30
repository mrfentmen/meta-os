"""INT-008: Spark endpoint down for all features, drill pinned.

The drill script itself (intel/spark_down_drill.py) is the
acceptance artifact; these tests pin it in the suite so a
later change that breaks a fallback breaks the suite too.
The down endpoint is a closed localhost port through the
shipped HTTP transport, never a stubbed failure: the
precondition test proves the real client raises SparkError
against it. No network beyond that closed port, no live
Redis, no bus posts, no Spark spend.
"""

import copy
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

import relay_common as rc  # noqa: E402
from fake_redis import FakeUpstash  # noqa: E402
from intel import brief as brief_mod  # noqa: E402
from intel import spark_down_drill as drill  # noqa: E402
from intel.spark_client import SparkClient, SparkError  # noqa: E402


class SparkDownDrillTest(unittest.TestCase):

    def test_drill_passes_all_stages(self):
        result = drill.run_drill(write_log=False)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["stages"]), 6)
        for name, passed, detail in result["stages"]:
            self.assertTrue(passed, f"stage {name} failed: {detail}")

    def test_dead_endpoint_raises_spark_error_through_real_client(self):
        client = SparkClient(
            transport="http", endpoint=drill.DOWN_ENDPOINT,
            api_key="drill-not-a-secret", ledger=False)
        with self.assertRaises(SparkError) as caught:
            client.complete("hello", lane_feature="drill-probe")
        self.assertIn("unreachable", str(caught.exception))
        self.assertEqual(client.spent_usd, 0.0)

    def test_brief_record_model_is_template_on_failed_client(self):
        client = SparkClient(
            transport="http", endpoint=drill.DOWN_ENDPOINT,
            api_key="drill-not-a-secret", ledger=False)
        fake = FakeUpstash()
        patches = [
            mock.patch.object(rc, "api_get", fake.api_get),
            mock.patch.object(rc, "api_post", fake.api_post),
        ]
        for patch in patches:
            patch.start()
        try:
            text, record = brief_mod.generate_brief(
                copy.deepcopy(drill.SNAPSHOT), "drill-room",
                kind="morning", now=drill.NOW, dry_run=True,
                client=client)
        finally:
            for patch in patches:
                patch.stop()
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertEqual(record["model"], "template")


if __name__ == "__main__":
    unittest.main()
