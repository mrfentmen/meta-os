"""OC2B cycles 1-7 pack discipline (Sections 8-11, OC2B-176-275). Read-only.

Checks: prereg-before-result via ledger order, falsifiers present,
verify outputs match raw outputs, ladder honesty (no level above
earned), pack hashes cover their packs, ledger chain verifies.
Writes nothing; creates no side-effect files.
"""

import hashlib
import json
import os
import re
import unittest

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CYCLES = os.path.join(REPO, "labs", "cycles")
LEDGER = os.path.join(CYCLES, "ledger.jsonl")
IDS = ["cycle-001", "cycle-002", "cycle-003", "cycle-004", "cycle-005",
       "cycle-006", "cycle-007"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class TestOC2BCycles(unittest.TestCase):
    def test_ledger_order_and_prereg_hashes(self):
        """Prereg-before-result: ledger entries ordered 001-005 and each
        entry's prereg_sha256 matches its pack's prereg.md bytes."""
        entries = [json.loads(l) for l in open(LEDGER) if l.strip()]
        self.assertEqual([e["cycle_id"] for e in entries], IDS)
        times = [e["recorded_at"] for e in entries]
        self.assertEqual(times, sorted(times))
        for e in entries:
            expect = sha(os.path.join(CYCLES, e["cycle_id"], "prereg.md"))
            self.assertEqual(e["prereg_sha256"], expect, e["cycle_id"])

    def test_ledger_chain(self):
        import sys
        sys.path.insert(0, os.path.join(REPO, "os", "worlds", "science-lab"))
        import ledger
        ok, msg = ledger.verify_chain(LEDGER)
        self.assertTrue(ok, msg)
        self.assertEqual(len(ledger.read_all(LEDGER)), 7)

    def test_falsifiers_present(self):
        for cid in IDS:
            text = read(os.path.join(CYCLES, cid, "record.md"))
            m = re.search(r"Falsifier([\s\S]{60,2000})",
                          text)
            self.assertIsNotNone(m, cid)
            self.assertIn("kill", m.group(1), cid)

    def test_verify_matches_raw(self):
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            raw = sha(os.path.join(pack, "raw", "result.json"))
            rerun = sha(os.path.join(pack, "verify", "rerun_result.json"))
            self.assertEqual(raw, rerun, cid)
            for name, val in (("raw/result.sha256", raw),
                              ("verify/rerun_result.sha256", rerun)):
                recorded = read(os.path.join(pack, name)).split()[0]
                self.assertEqual(recorded, val, "%s %s" % (cid, name))

    def test_ladder_honesty(self):
        earned = {}
        for cid in IDS:
            m = re.search(r"Ladder level earned: Level (\d)",
                          read(os.path.join(CYCLES, cid, "record.md")))
            self.assertIsNotNone(m, cid)
            earned[cid] = int(m.group(1))
        self.assertTrue(all(v <= 3 for v in earned.values()))
        self.assertEqual(earned["cycle-005"], 2)
        high = re.compile(r"[Ll]evel [4-6]|\"level\": [4-6]")
        for root, dirs, files in os.walk(CYCLES):
            if "repository" in root.split(os.sep):
                for fn in files:
                    text = read(os.path.join(root, fn))
                    for line in text.splitlines():
                        if high.search(line):
                            self.fail("level above earned in %s: %s"
                                      % (fn, line[:100]))
                continue
            for fn in files:
                if fn.endswith((".json", ".md")):
                    text = read(os.path.join(root, fn))
                    for line in text.splitlines():
                        if high.search(line):
                            self.fail("level above earned in %s: %s"
                                      % (os.path.join(root, fn)[:80],
                                         line[:100]))
        claims = [json.loads(l) for l in
                  open(os.path.join(CYCLES, "repository", "claims.jsonl"))]
        for c in claims:
            cid = c["cycle_id"].replace("OC2B-", "")
            self.assertEqual(c["level"], earned[cid], cid)

    def test_pack_hashes_cover_packs(self):
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            lines = [l.strip() for l in
                     open(os.path.join(pack, "pack.sha256")) if l.strip()]
            seen = set()
            for line in lines:
                h, rel = line.split("  ")
                seen.add(rel)
                self.assertEqual(sha(os.path.join(pack, rel)), h,
                                 "%s %s" % (cid, rel))
            actual = set()
            for root, dirs, files in os.walk(pack):
                for fn in sorted(files):
                    if fn == "pack.sha256":
                        continue
                    actual.add(os.path.relpath(os.path.join(root, fn), pack))
            self.assertEqual(seen, actual, cid)

    def test_spend_recorded(self):
        for cid in IDS:
            text = read(os.path.join(CYCLES, cid, "record.md"))
            self.assertIn("Model spend", text, cid)
        spend = json.load(open(os.path.join(
            CYCLES, "cycle-003", "model", "spend.json")))
        self.assertIn("total_est_cost_usd", spend)
        self.assertIn("0.005358",
                      read(os.path.join(CYCLES, "cycle-003", "record.md")))


if __name__ == "__main__":
    unittest.main()
