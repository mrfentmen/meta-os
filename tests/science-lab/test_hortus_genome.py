"""CB2-201/202/222: Hortus genome parsing and round-trip."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import model  # noqa: E402


FIXTURE = {
    "n_fins": 10,
    "fin_height_mm": 25.0,
    "fin_thickness_mm": 1.5,
    "base_thickness_mm": 3.0,
}


class TestGenome(unittest.TestCase):
    def test_valid_genome_parses_to_documented_fields(self):
        genome = model.parse_genome(FIXTURE)
        self.assertEqual(genome, (10.0, 25.0, 1.5, 3.0))
        self.assertEqual(model.genome_to_dict(genome), FIXTURE)

    def test_unknown_gene_key_rejected(self):
        bad = dict(FIXTURE, spines=4)
        with self.assertRaisesRegex(ValueError, "unknown gene"):
            model.parse_genome(bad)

    def test_missing_gene_rejected(self):
        bad = dict(FIXTURE)
        bad.pop("fin_height_mm")
        with self.assertRaisesRegex(ValueError, "missing gene"):
            model.parse_genome(bad)

    def test_serialisation_round_trip(self):
        genome = model.parse_genome(FIXTURE)
        serialised = model.genome_to_dict(genome)
        self.assertEqual(model.parse_genome(serialised), genome)


if __name__ == "__main__":
    unittest.main()
