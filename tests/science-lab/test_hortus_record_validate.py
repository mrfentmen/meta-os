"""Tests for the Hortus generation-record validator (CB2-369..370).

Run from the repo root:

    python3 -m unittest discover -s tests/science-lab -p "test_hortus_record_validate.py"
"""

import copy
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "science-lab", "hortus",
    ),
)

from record_validate import validate_generation_record  # noqa: E402

VALID = {
    "kind": "generation-record",
    "generation": 2,
    "parent_ids": ["o1", "o2", "o3"],
    "child_ids": ["o4", "o5"],
}


def fixture():
    return copy.deepcopy(VALID)


class TestValid(unittest.TestCase):
    def test_real_shape_passes(self):
        self.assertEqual(validate_generation_record(fixture()), [])

    def test_child_parents_links_to_known_parents_pass(self):
        record = fixture()
        record["child_parents"] = {"o4": ["o1", "o2"], "o5": ["o2", "o3"]}
        self.assertEqual(validate_generation_record(record), [])


class TestShape(unittest.TestCase):
    def test_not_an_object(self):
        self.assertEqual(
            validate_generation_record("generation"),
            ["record: must be an object"])

    def test_wrong_kind_is_named(self):
        record = fixture()
        record["kind"] = "birth"
        self.assertIn(
            "kind: must be generation-record",
            validate_generation_record(record))

    def test_negative_generation_fails(self):
        record = fixture()
        record["generation"] = -1
        self.assertIn(
            "generation: must be >= 0", validate_generation_record(record))

    def test_boolean_generation_is_not_an_integer(self):
        record = fixture()
        record["generation"] = True
        self.assertIn(
            "generation: must be an integer",
            validate_generation_record(record))

    def test_empty_parent_list_fails(self):
        record = fixture()
        record["parent_ids"] = []
        self.assertIn(
            "parent_ids: must not be empty",
            validate_generation_record(record))

    def test_repeated_child_id_is_reported(self):
        record = fixture()
        record["child_ids"] = ["o4", "o4"]
        self.assertIn(
            "child_ids[1]: duplicate id o4",
            validate_generation_record(record))

    def test_child_in_parent_list_is_refused(self):
        record = fixture()
        record["child_ids"] = ["o1", "o5"]
        errors = validate_generation_record(record)
        self.assertIn(
            "child_ids: an organism cannot be its own parent: o1", errors)

    def test_unexpected_field_is_reported(self):
        record = fixture()
        record["best_score"] = 12.5
        self.assertIn(
            "unexpected field: best_score",
            validate_generation_record(record))


class TestLineage(unittest.TestCase):
    def test_child_referencing_unknown_parent_is_reported(self):
        record = fixture()
        record["child_parents"] = {"o4": ["o1", "o9"]}
        self.assertIn(
            "child_parents.o4[1]: unknown parent o9",
            validate_generation_record(record))

    def test_link_for_unknown_child_is_reported(self):
        record = fixture()
        record["child_parents"] = {"o99": ["o1"]}
        self.assertIn(
            "child_parents.o99: child is not in child_ids",
            validate_generation_record(record))

    def test_empty_link_list_is_reported(self):
        record = fixture()
        record["child_parents"] = {"o4": []}
        self.assertIn(
            "child_parents.o4: must be a non-empty list",
            validate_generation_record(record))

    def test_validator_does_not_mutate_the_record(self):
        record = fixture()
        before = copy.deepcopy(record)
        validate_generation_record(record)
        self.assertEqual(record, before)


if __name__ == "__main__":
    unittest.main()
