"""Tests for os-build/tools/cross_lane_claims.py.

The tool's value is its narrowness: it must flag a real stale count and stay
quiet about the things that only look like counts. Each test pins one of those
rules on a throwaway tree, so a rule cannot quietly loosen later.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "os-build" / "tools"))

import cross_lane_claims as scan  # noqa: E402


def make_tree(tmp: Path, *, crates=3, kernel_files=2, kernel_lines=10):
    for i in range(crates):
        (tmp / "crates" / f"c{i}" / "src").mkdir(parents=True, exist_ok=True)
    for i in range(kernel_files):
        (tmp / "kernel" / "src").mkdir(parents=True, exist_ok=True)
        (tmp / "kernel" / "src" / f"f{i}.rs").write_text(
            "\n".join(f"// line {n}" for n in range(kernel_lines)) + "\n",
            encoding="utf-8",
        )
    (tmp / "os-build").mkdir(parents=True, exist_ok=True)


def write_status(tmp: Path, body: str, name="X_STATUS.md"):
    path = tmp / "os-build" / name
    path.write_text(body, encoding="utf-8")
    return path


class ClaimScan(unittest.TestCase):
    def test_matching_count_is_not_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "The layer has 19 crates.\n")
            rows, meta = scan.scan(tmp)
            self.assertEqual([r["verdict"] for r in rows], ["MATCH"])
            self.assertEqual(meta["counts"]["CONTRADICTED"], 0)

    def test_stale_count_is_a_finding(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "The layer has 18 crates.\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows[0]["verdict"], "CONTRADICTED")
            self.assertEqual(rows[0]["said"], 18)
            self.assertEqual(rows[0]["actual"], 19)

    def test_table_row_number_is_not_a_count(self):
        # `| 1 crates/os-boot |` is an index. Counting it flagged 18 false rows
        # on the real tree, which is exactly how a scan gets ignored.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "| 1 crates/os-boot | B001-B012 | 8 |\n| 2 crates/os-jobs | B025 | 8 |\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_audit_row_is_not_a_claim(self):
        # A row that says STALE is the correction, not the claim.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "| Rust OS layer: 18 crates | measured 19 | STALE |\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_prose_lines_are_not_kernel_claims(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, kernel_files=13, kernel_lines=100)
            write_status(tmp, "- lane-3 version was 276 lines with worked examples.\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_kernel_line_count_is_measured_from_the_files(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, kernel_files=2, kernel_lines=10)  # 20 lines
            write_status(tmp, "| Kernel source | 13 files, 5833 lines |\n")
            rows, _ = scan.scan(tmp)
            by_label = {r["label"]: r for r in rows}
            # says 13 files, tree has 2: a finding, and it must say so.
            self.assertEqual(by_label["kernel files"]["verdict"], "CONTRADICTED")
            self.assertEqual(by_label["kernel files"]["actual"], 2)
            self.assertEqual(by_label["kernel lines"]["said"], 5833)
            self.assertEqual(by_label["kernel lines"]["actual"], 20)

    def test_serial_capture_is_not_a_kernel_source_claim(self):
        # "serial 1086 lines panic 0" is a boot log. For a while this scan
        # reported it as a stale kernel line count.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, kernel_files=13, kernel_lines=460)
            write_status(
                tmp,
                "Kernel gate GREEN, serial 1086 lines panic 0, all assertions SAME.\n",
            )
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_line_count_without_file_count_is_not_judged(self):
        # A bare "5,833 lines" cannot be told apart from a log capture.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, kernel_files=13, kernel_lines=460)
            write_status(tmp, "Kernel source measured at 5,833 lines.\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_missing_base_is_skipped_not_guessed(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "os-build").mkdir()
            write_status(tmp, "The kernel has 5,833 lines across 13 files.\n")
            rows, _ = scan.scan(tmp)
            self.assertEqual(rows, [])

    def test_main_exits_one_on_a_contradiction(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "The layer has 18 crates.\n")
            self.assertEqual(scan.main(["--root", d, "--check"]), 1)

    def test_main_exits_zero_when_clean(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "The layer has 19 crates.\n")
            self.assertEqual(scan.main(["--root", d, "--check"]), 0)

    def test_write_creates_the_report(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            make_tree(tmp, crates=19)
            write_status(tmp, "The layer has 19 crates.\n")
            scan.main(["--root", d, "--write"])
            report = (tmp / scan.REPORT_PATH).read_text(encoding="utf-8")
            self.assertIn("# Cross-lane claim scan", report)
            self.assertIn("| **MATCH** | 1 |", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
