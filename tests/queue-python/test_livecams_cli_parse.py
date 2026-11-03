"""Live camera CLI tests (CB2-083). Parser only; no fetch."""
import io
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import livecams  # noqa: E402


class LiveCamCliTests(unittest.TestCase):
    def test_list_area_and_division_parse(self):
        args = livecams.build_arg_parser().parse_args(
            ["--list", "--area", "Brooklyn", "--division", "ignis"])
        self.assertTrue(args.list)
        self.assertEqual(args.area, "Brooklyn")
        self.assertEqual(args.division, "ignis")

    def test_unknown_flag_exits_with_usage_error(self):
        with unittest.mock.patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                livecams.build_arg_parser().parse_args(["--nope"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
