"""CB2-459 — the 2a gate's fourteen clauses, each mapped to a real test.

The gate script is read as data: its `check("<name>", ...)` calls are the
clauses, and each one is mapped here to a test file in this tree plus a string
that must appear in it. A clause the gate runs but no test covers is a clause
nobody maintains; a mapping that names a missing file is the same gap with a
prettier label.

The gate itself is run by `python3 os-build/officina_2a_gate.py`; this file does
not run it (it shells out to git and the suite), it pins the coverage map.
"""

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GATE = os.path.join(ROOT, "os-build", "officina_2a_gate.py")

# Clause -> (test file in this directory, a string that file must contain).
CLAUSE_MAP = {
    "G1-intake-class": ("test_brief.py", "artefact_class"),
    "G1-intake-target": ("test_brief.py", "stated"),
    "G1-intake-unknowns": ("test_brief.py", "unknowns"),
    "G1-intake-preferences": ("test_brief.py", "preferences"),
    "G2-proven": ("test_brief.py", "proven"),
    "G2-log-sequential": ("test_brief.py", "decision_log"),
    "G2-log-reasons": ("test_brief.py", "reason"),
    "G2-log-intake-honest": ("test_brief.py", "decision_log"),
    "G3-heldout-agrees": ("test_heatsink.py", "GOLDEN_R"),
    "G3-heldout-bar": ("test_design_loop.py", "heldout"),
    "G4-brief-target": ("test_brief.py", "target"),
    "G5-impossible-unproven": ("test_brief.py", "unproven"),
    "G5-export-discipline": ("test_brief.py", "export"),
    "G6-suite": ("test_pack.py", "pack"),
}


def gate_clause_names():
    with open(GATE, encoding="utf-8") as f:
        source = f.read()
    return re.findall(r'check\(\s*"([^"]+)"', source)


class GateMapTest(unittest.TestCase):
    def test_gate_has_fourteen_named_clauses(self):
        names = gate_clause_names()
        self.assertEqual(len(names), 14, "the gate runs 14 clauses, read from its source")
        self.assertEqual(len(set(names)), 14, "no clause name is repeated")

    def test_every_clause_is_in_the_map(self):
        names = gate_clause_names()
        self.assertEqual(
            sorted(CLAUSE_MAP), sorted(names),
            "every gate clause has a mapping, and the map has no invented clause",
        )

    def test_every_mapping_names_a_real_test_file_and_string(self):
        for clause, (filename, needle) in CLAUSE_MAP.items():
            path = os.path.join(HERE, filename)
            self.assertTrue(os.path.exists(path), "%s -> %s exists" % (clause, filename))
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertIn(needle, body, "%s -> %s mentions %r" % (clause, filename, needle))

    def test_the_gate_script_still_exists_and_exits_nonzero_on_failure(self):
        # The map is only worth anything if the script it maps is the one that runs.
        with open(GATE, encoding="utf-8") as f:
            source = f.read()
        self.assertIn("return 0 if not failed else 1", source)
        self.assertIn("GATE:", source)


if __name__ == "__main__":
    unittest.main()
