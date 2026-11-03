"""Missing cases for the Python dashboard pack (B222).

`test_intel_devpack.py` covers the checked-in pack equality, the fresh and
stale brief ages, the plan preview shape, the alert feed, and the crew
board sources. This file covers the refusal and boundary cases it does
not:

- `brief_entry` keeping extra record fields and allowing a negative age;
- bool/float timestamps refused, not coerced;
- an empty plan preview (zero jobs, zero budget);
- a malformed job raising `KeyError` (the real shape) rather than a clean
  `ValueError`;
- alert ties broken by id, and a missing `created_at` sorting as zero;
- a non-list alert input failing inside `sorted`;
- `crew_board` copying its three sources rather than aliasing them;
- `load_pack` missing directory failing as `FileNotFoundError`.

No network, no Redis: pure functions.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import devpack  # noqa: E402

NOW = 1000000


class BriefEntryMissingTest(unittest.TestCase):
    def test_extra_record_fields_are_preserved(self):
        record = {"generated_at": NOW - 10, "sections": {"x": ["y"]},
                  "model": "template", "extra": 7}
        entry = devpack.brief_entry(record, NOW)
        self.assertEqual(entry["extra"], 7)
        self.assertEqual(entry["model"], "template")
        self.assertEqual(entry["sections"], {"x": ["y"]})
        self.assertEqual(entry["age_seconds"], 10)

    def test_negative_age_is_returned_not_clamped(self):
        entry = devpack.brief_entry({"generated_at": NOW + 500}, NOW)
        self.assertEqual(entry["age_seconds"], -500)

    def test_bool_and_float_timestamps_are_refused(self):
        for value in (True, False):
            with self.assertRaises(ValueError):
                devpack.brief_entry({"generated_at": value}, NOW)
        with self.assertRaises(ValueError):
            devpack.brief_entry({"generated_at": NOW + 0.5}, NOW)
        with self.assertRaises(ValueError):
            devpack.brief_entry({"generated_at": NOW}, True)


class PlanPreviewMissingTest(unittest.TestCase):
    def test_empty_plan_previews_to_zero_budgets(self):
        preview = devpack.plan_preview({"summary": "empty", "jobs": []}, [])
        self.assertEqual(preview["jobs"], [])
        self.assertEqual(preview["posting_order"], [])
        self.assertEqual(preview["budgets"],
                         {"jobs": 0, "max_attempts_total": 0})

    def test_missing_job_field_raises_key_error(self):
        plan = {"summary": "s", "jobs": [{"title": "t"}]}
        with self.assertRaises(KeyError):
            devpack.plan_preview(plan, [None])

    def test_duplicate_order_entry_is_refused(self):
        plan = {"summary": "s", "jobs": [
            {"key": "a", "title": "t", "files": [], "deps": [],
             "max_attempts": 1, "accept": []}]}
        with self.assertRaises(ValueError):
            devpack.plan_preview(plan, ["a", "a"])

    def test_output_arrays_do_not_alias_the_input(self):
        job = {"key": "a", "title": "t", "files": ["f"], "deps": [],
               "max_attempts": 1, "accept": ["file-exists f"]}
        preview = devpack.plan_preview(
            {"summary": "s", "jobs": [job]}, ["a"])
        job["files"].append("mutated")
        self.assertEqual(preview["jobs"][0]["files"], ["f"])


class AlertsFeedMissingTest(unittest.TestCase):
    def test_ties_break_on_id_descending(self):
        records = [
            {"id": "a", "created_at": 10},
            {"id": "c", "created_at": 10},
            {"id": "b", "created_at": 10},
        ]
        self.assertEqual([r["id"] for r in devpack.alerts_feed(records)],
                         ["c", "b", "a"])

    def test_missing_created_at_sorts_as_zero(self):
        records = [{"id": "new", "created_at": 5}, {"id": "old"}]
        self.assertEqual([r["id"] for r in devpack.alerts_feed(records)],
                         ["new", "old"])

    def test_non_list_mapping_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            devpack.alerts_feed({"a": 1})

    def test_empty_mapping_is_an_empty_feed(self):
        self.assertEqual(devpack.alerts_feed({}), [])


class CrewBoardMissingTest(unittest.TestCase):
    def test_sources_are_copied_not_aliased(self):
        caps = {"hana": {"brief": True}}
        jobs = [{"id": "1", "status": "open"}]
        board = devpack.crew_board(("hana",), caps, jobs)
        caps["hana"]["brief"] = False
        jobs[0]["status"] = "done"
        self.assertTrue(board["caps"]["hana"]["brief"])
        self.assertEqual(board["jobs"][0]["status"], "open")
        self.assertEqual(board["presence"], ["hana"])


class LoadPackMissingTest(unittest.TestCase):
    def test_missing_directory_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            devpack.load_pack("/definitely/not/a/pack")


if __name__ == "__main__":
    unittest.main()
