"""STR-003 pinning tests: the SAM eval set in intel/evals/sam/."""

import json
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAM_DIR = os.path.join(REPO, "intel", "evals", "sam")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def load_manifest():
    with open(os.path.join(SAM_DIR, "pairs.json")) as fh:
        return json.load(fh)


class SamEvalSetTest(unittest.TestCase):
    def test_manifest_shape(self):
        m = load_manifest()
        self.assertEqual(m["set"], "sam-eval-alerts-panel-v1")
        self.assertEqual(m["panel"], "intel-alerts")
        self.assertEqual(set(m["labels"]), {"build-ok", "build-broken"})
        self.assertEqual(len(m["pairs"]), 2)

    def test_pairs_have_good_and_bad(self):
        m = load_manifest()
        for pair in m["pairs"]:
            self.assertEqual(pair["good"]["label"], "build-ok")
            self.assertEqual(pair["bad"]["label"], "build-broken")
            self.assertNotEqual(pair["good"]["file"], pair["bad"]["file"])
            for half in (pair["good"], pair["bad"]):
                self.assertTrue(half["file"].endswith(".png"))
                self.assertTrue(half["basis"])

    def test_files_exist_and_are_png(self):
        m = load_manifest()
        for pair in m["pairs"]:
            for half in (pair["good"], pair["bad"]):
                path = os.path.join(SAM_DIR, half["file"])
                self.assertTrue(os.path.isfile(path), path)
                with open(path, "rb") as fh:
                    self.assertEqual(fh.read(8), PNG_MAGIC, path)

    def test_bad_alert_ids_match_devpack(self):
        with open(os.path.join(REPO, "intel", "devpack",
                                 "alerts.json")) as fh:
            pack = json.load(fh)

        def ids(node):
            out = []
            if isinstance(node, dict):
                if "id" in node and "kind" in node:
                    out.append(node["id"])
                for v in node.values():
                    out.extend(ids(v))
            elif isinstance(node, list):
                for v in node:
                    out.extend(ids(v))
            return out

        m = load_manifest()
        for pair in m["pairs"]:
            self.assertEqual(sorted(pair["bad"]["alert_ids"]),
                             sorted(ids(pack)))

    def test_firing_copies_match_submission_originals(self):
        import hashlib
        m = load_manifest()
        for pair in m["pairs"]:
            copy = os.path.join(SAM_DIR, pair["bad"]["file"])
            orig = os.path.join(
                REPO, "hackathon", "relay-intelligence",
                "submission-assets", pair["bad"]["file"])
            def digest(path):
                with open(path, "rb") as fh:
                    return hashlib.sha256(fh.read()).hexdigest()
            self.assertEqual(digest(copy), digest(orig), pair["bad"]["file"])

    def test_sam_check_passes(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "intel", "sam_check.py")],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SAM eval set OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
