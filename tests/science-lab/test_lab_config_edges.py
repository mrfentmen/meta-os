"""Lab config edge tests (CB2-117..119). Temp JSON only."""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import lab_config  # noqa: E402


def write_config(payload):
    path = tempfile.mktemp(suffix=".json", prefix="lab-config-")
    with open(path, "w") as fh:
        json.dump(payload, fh)
    return path


class ConfigEdgeTests(unittest.TestCase):
    def test_missing_name_is_rejected_with_a_named_error(self):
        path = write_config({"agents": {}})
        with self.assertRaisesRegex(ValueError, "name"):
            lab_config.load_config(path)

    def test_unknown_top_level_key_is_ignored(self):
        path = write_config({"name": "lab", "unknownKey": {"x": 1}})
        cfg = lab_config.load_config(path)
        self.assertEqual(cfg["name"], "lab")
        self.assertEqual(cfg["unknownKey"], {"x": 1})

    def test_empty_optional_sections_get_documented_defaults(self):
        path = write_config({"name": "lab", "agents": {}, "cycle": {}})
        cfg = lab_config.load_config(path)
        self.assertEqual(cfg["agents"]["default"],
                         {"maxCalls": 50, "maxSpend": 5.0})
        self.assertEqual(cfg["cycle"]["maxActions"], 200)
        self.assertTrue(cfg["endpoint"].startswith("file://local"))


if __name__ == "__main__":
    unittest.main()
