"""tests/test_relay_intel_config.py — relay_common.intel_config (FND-017).

The MUSE_RELAY_INTEL_* block loads with zero env set, honors each
override, and never carries a secret default: the API key variable is
reported as presence only, never returned.
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, ".")
import relay_common as rc  # noqa: E402

class IntelConfigTest(unittest.TestCase):
    def _config(self, overrides=None):
        """intel_config() with exactly `overrides` set, rest cleared."""
        env = {k: v for k, v in (overrides or {}).items()}
        with mock.patch.dict(os.environ, env, clear=True):
            # clear=True wipes everything; restore nothing — the
            # function under test reads only MUSE_RELAY_INTEL_* vars.
            return rc.intel_config()

    def test_zero_env_gives_safe_defaults(self):
        cfg = self._config()
        self.assertEqual(cfg, {
            "model": "", "endpoint": "", "budget_cap_usd": 0.0,
            "per_call_cap_usd": 0.0, "room": "",
            "api_key_present": False,
        })

    def test_each_override_honored(self):
        cfg = self._config({
            "MUSE_RELAY_INTEL_MODEL": "meta-spark",
            "MUSE_RELAY_INTEL_ENDPOINT": "https://example.invalid/v1",
            "MUSE_RELAY_INTEL_BUDGET_CAP_USD": "75",
            "MUSE_RELAY_INTEL_PER_CALL_USD": "0.5",
            "MUSE_RELAY_INTEL_ROOM": "build-relay-intel",
        })
        self.assertEqual(cfg["model"], "meta-spark")
        self.assertEqual(cfg["endpoint"], "https://example.invalid/v1")
        self.assertEqual(cfg["budget_cap_usd"], 75.0)
        self.assertEqual(cfg["per_call_cap_usd"], 0.5)
        self.assertEqual(cfg["room"], "build-relay-intel")
        self.assertFalse(cfg["api_key_present"])

    def test_unparseable_caps_fall_back_to_default(self):
        cfg = self._config({
            "MUSE_RELAY_INTEL_BUDGET_CAP_USD": "not-a-number",
            "MUSE_RELAY_INTEL_PER_CALL_USD": "",
        })
        self.assertEqual(cfg["budget_cap_usd"], 0.0)
        self.assertEqual(cfg["per_call_cap_usd"], 0.0)

    def test_api_key_reported_as_presence_only(self):
        secret = "sk-test-do-not-log"
        cfg = self._config({"MUSE_RELAY_INTEL_API_KEY": secret})
        self.assertTrue(cfg["api_key_present"])
        self.assertNotIn(secret, repr(cfg.values()))
        self.assertNotIn("api_key", cfg)
