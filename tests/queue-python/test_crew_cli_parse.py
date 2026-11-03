"""Crew CLI parser tests (CB2-025). Imports the parser only; no run."""
import io
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402


class CrewCliParseTests(unittest.TestCase):
    def test_dry_run_is_accepted(self):
        args = crew.build_arg_parser().parse_args(["--dry-run"])
        self.assertIs(args.dry_run, True)

    def test_default_is_not_dry_run(self):
        args = crew.build_arg_parser().parse_args([])
        self.assertIs(args.dry_run, False)

    def test_unknown_flag_exits_with_a_usage_error(self):
        with unittest.mock.patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                crew.build_arg_parser().parse_args(["--not-a-flag"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
