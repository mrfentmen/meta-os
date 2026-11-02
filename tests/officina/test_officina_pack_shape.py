"""CB2-475 — the Officina pack.json parses and its parts exist."""

import json
import os
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACK = os.path.join(ROOT, "os", "worlds", "officina", "pack.json")


class PackShape(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PACK, "r", encoding="utf-8") as fh:
            cls.pack = json.load(fh)

    def test_pack_identity_and_agents(self):
        self.assertEqual(self.pack["pack"], "officina")
        self.assertTrue(self.pack["agents"])
        for agent in self.pack["agents"]:
            self.assertTrue(agent["nick"])
            self.assertTrue(agent["role"])

    def test_every_declared_runtime_part_exists(self):
        parts = self.pack["runtime"]["parts"]
        self.assertTrue(parts)
        for part in parts:
            path = os.path.join(ROOT, part["path"])
            self.assertTrue(os.path.isfile(path), part["path"])
            self.assertIn("what", part)

    def test_status_is_a_documented_value(self):
        self.assertIn(self.pack["status"], ("partial", "complete", "seed"))


if __name__ == "__main__":
    unittest.main()
