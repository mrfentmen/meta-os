"""OC2B cycles 6-7: LIVE MCP-GATEWAY discovery discipline. Read-only.

Cycles 006 (Delaney rerun + openalex literature pin) and 007 (biology
GC-content + gbif organism provenance) ran through the live
MCP-GATEWAY backend. Checks: prereg-before-result via ledger order,
falsifiers present, verify outputs match raw outputs, every gateway
call recorded with backend MCP-GATEWAY (no silent failures),
quarantine respected (unconfirmed envelopes until the explicit-id
pin), live-read gotchas handled at call time and documented, ledger /
repository / record levels agree, zero model spend. Writes nothing;
creates no side-effect files and never touches the live gateway.
"""

import hashlib
import json
import os
import re
import unittest

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
CYCLES = os.path.join(REPO, "labs", "cycles")
LEDGER = os.path.join(CYCLES, "ledger.jsonl")
IDS = ["cycle-006", "cycle-007"]
ALL_IDS = ["cycle-001", "cycle-002", "cycle-003", "cycle-004", "cycle-005",
           "cycle-006", "cycle-007"]
EXPECTED_TOOLS = {
    "cycle-006": ("openalex__search_works", "openalex__get_work"),
    "cycle-007": ("gbif__match_species", "gbif__get_species"),
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


class TestOC2BLiveCycles(unittest.TestCase):
    def test_ledger_order_and_prereg_hashes(self):
        """Prereg-before-result: ledger runs 001-007 in order and each
        entry's prereg_sha256 matches its pack's prereg.md bytes."""
        entries = [json.loads(l) for l in open(LEDGER) if l.strip()]
        self.assertEqual([e["cycle_id"] for e in entries], ALL_IDS)
        times = [e["recorded_at"] for e in entries]
        self.assertEqual(times, sorted(times))
        for e in entries:
            if e["cycle_id"] not in IDS:
                continue
            expect = sha(os.path.join(CYCLES, e["cycle_id"], "prereg.md"))
            self.assertEqual(e["prereg_sha256"], expect, e["cycle_id"])

    def test_falsifiers_present(self):
        for cid in IDS:
            text = read(os.path.join(CYCLES, cid, "record.md"))
            m = re.search(r"Falsifier([\s\S]{60,2500})", text)
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

    def test_gateway_backend_recorded_on_call_records(self):
        """Every live call recorded: status ok, backend MCP-GATEWAY,
        zero cost, one attempt per call (exactly 2), no hidden errors."""
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            entries = read_jsonl(os.path.join(pack, "raw",
                                              "gateway-calls.jsonl"))
            self.assertEqual(len(entries), 2, cid)
            for e in entries:
                self.assertEqual(e["status"], "ok", cid)
                self.assertEqual(e["backend"], "MCP-GATEWAY", cid)
                self.assertEqual(e["cost"], 0.0, cid)
                self.assertEqual(e["cycle_id"], cid)
                self.assertIsNotNone(e["result_hash"], cid)

    def test_live_wire_tools_are_the_preregistered_ones(self):
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            pin = load_json(os.path.join(pack, "raw", "gateway",
                                         "pin.json"))
            self.assertEqual(tuple(pin["remote_tools"]),
                             EXPECTED_TOOLS[cid], cid)
            self.assertTrue(pin["pinned"], cid)

    def test_quarantine_respected(self):
        """Gateway payloads stay quarantined (unconfirmed) envelopes;
        only the explicit-id pin promotes them, and only stable
        identifiers enter result.json (no volatile live counts)."""
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            for name in ("search.json", "read.json"):
                env = load_json(os.path.join(pack, "raw", "gateway",
                                             name))
                self.assertEqual(env.get("kind"), "gateway-source", name)
                self.assertEqual(env.get("status"), "unconfirmed", name)
                self.assertIn("not evidence", env.get("note", ""), name)
            pin = load_json(os.path.join(pack, "raw", "gateway",
                                         "pin.json"))
            self.assertIn("explicit", pin.get("rule", ""), cid)
            result_text = read(os.path.join(pack, "raw", "result.json"))
            self.assertNotIn("cited_by_count", result_text, cid)
            self.assertNotIn("confidence", result_text, cid)

    def test_live_read_gotchas_handled_at_call_time(self):
        """Known live-read gotchas mapped/coerced in the lab call layer
        and documented in the cycle record (shared infra untouched)."""
        rec6 = read(os.path.join(CYCLES, "cycle-006", "record.md"))
        self.assertIn("404", rec6)
        self.assertIn("OpenAlex-id locator", rec6)
        run6 = read(os.path.join(CYCLES, "cycle-006", "run.py"))
        self.assertIn("https://openalex.org/W2076498053", run6)
        rec7 = read(os.path.join(CYCLES, "cycle-007", "record.md"))
        self.assertIn("must be a", rec7)
        self.assertIn("string", rec7)
        run7 = read(os.path.join(CYCLES, "cycle-007", "run.py"))
        self.assertIn("str(USAGE_KEY_INT)", run7)
        pin7 = load_json(os.path.join(
            CYCLES, "cycle-007", "raw", "gateway", "pin.json"))
        self.assertTrue(pin7["key_sent_as_string"])
        self.assertEqual(pin7["wire_read_args"], {"key": "5219404"})

    def test_levels_match_across_ledger_repository_record(self):
        entries = {e["cycle_id"]: e
                   for e in read_jsonl(LEDGER) if e["cycle_id"] in IDS}
        cycles = {c["cycle_id"].replace("OC2B-", ""): c
                  for c in read_jsonl(
                      os.path.join(CYCLES, "repository", "cycles.jsonl"))}
        claims = {c["cycle_id"].replace("OC2B-", ""): c
                  for c in read_jsonl(
                      os.path.join(CYCLES, "repository", "claims.jsonl"))}
        for cid in IDS:
            m = re.search(r"Ladder level earned: Level (\d)",
                          read(os.path.join(CYCLES, cid, "record.md")))
            self.assertIsNotNone(m, cid)
            level = int(m.group(1))
            self.assertEqual(entries[cid]["level"], level, cid)
            self.assertEqual(cycles[cid]["level"], level, cid)
            self.assertEqual(claims[cid]["level"], level, cid)
            self.assertEqual(entries[cid]["verdict"], "MATCH", cid)
            self.assertEqual(cycles[cid]["verdict"], "MATCH", cid)
            self.assertEqual(
                cycles[cid]["ledger_entry_hash"],
                entries[cid]["entry_hash"], cid)

    def test_spend_recorded_zero(self):
        for cid in IDS:
            pack = os.path.join(CYCLES, cid)
            text = read(os.path.join(pack, "record.md"))
            self.assertIn("Model spend", text, cid)
            self.assertIn("$0.00", text, cid)
            self.assertFalse(os.path.exists(os.path.join(pack, "model")),
                             cid)

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
                    actual.add(os.path.relpath(os.path.join(root, fn),
                                               pack))
            self.assertEqual(seen, actual, cid)


if __name__ == "__main__":
    unittest.main()
