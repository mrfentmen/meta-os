"""Unit tests for jobs.py --req (DSP-012).

Posting with --req stores the required capability names on the
job hash, normalized to the form mos/capabilities.find_for
matches: lowercase, deduped, comma-joined. The stored value is
visible in list --json and in show, so a dashboard or watchdog
reader can see what skill a posted job asks for. A post with no
--req carries an empty req: jobs._hset skips empty values, so
the field is absent on the hash and reads back as "".
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import RelayTestCase
import jobs


class ReqPostTest(RelayTestCase):
    def test_post_stores_normalized_req(self):
        rc, out, err = self.run_cli(
            jobs.main, ["post", "--title", "Fix login",
                        "--spec", "make it work",
                        "--req", "Python, GIT,python"])
        self.assertEqual(rc, 0)
        h, _spec = jobs.job_get("1")
        self.assertEqual(h["req"], "python,git")

    def test_post_without_req_stores_empty(self):
        rc, out, err = self.run_cli(
            jobs.main, ["post", "--title", "T", "--spec", "s"])
        self.assertEqual(rc, 0)
        h, _spec = jobs.job_get("1")
        self.assertEqual(h.get("req", ""), "")

    def test_list_json_and_show_carry_req(self):
        self.run_cli(jobs.main, ["post", "--title", "T", "--spec", "s",
                                 "--req", "python"])
        rc, out, err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(rc, 0)
        docs = json.loads(out)
        self.assertEqual(docs[0]["req"], "python")
        rc, out, err = self.run_cli(jobs.main, ["show", "1"])
        self.assertEqual(rc, 0)
        self.assertIn("req: python", out)


if __name__ == "__main__":
    unittest.main()
