"""Section 8 Tasks 71-80: controlled MCP gateway.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v

Isolation: allowlist/scope/quarantine/budget/offline tests run against
temporary calls.jsonl files so the suite never pollutes the committed
records/gateway/calls.jsonl. One honesty test reads the committed
worked example and re-verifies its hashes.
"""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import gateway  # noqa: E402


def _tmp_calls():
    td = tempfile.mkdtemp()
    return os.path.join(td, "calls.jsonl")


def _read_calls(path):
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


class TestAllowlist(unittest.TestCase):
    def test_allowlist_has_boss_nine(self):
        self.assertEqual(set(gateway.ALLOWLIST), {
            "openalex", "archive-org", "open-library", "gbif",
            "wikidata", "wikisource", "ietf", "federal-register", "osv",
        })

    def test_refusal_recorded(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-REFUSE", calls_path=path)
        with self.assertRaises(gateway.GatewayRefused):
            gw.call_tool("literature-researcher", "evil-tool",
                         {"op": "search", "query": "x"})
        entries = _read_calls(path)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "refused-allowlist")
        self.assertEqual(entry["tool"], "evil-tool")
        self.assertEqual(len(entry["args_hash"]), 64)
        self.assertIsNone(entry["result_hash"])


class TestScopes(unittest.TestCase):
    def test_literature_may_search(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-SCOPE-OK", calls_path=path)
        out = gw.call_tool("literature-researcher", "openalex",
                           {"op": "search", "query": "solubility"})
        self.assertTrue(gateway.is_quarantined(out))

    def test_runner_scope_violation_refused(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-SCOPE-RUN", calls_path=path)
        with self.assertRaises(gateway.GatewayRefused):
            gw.call_tool("computational-scientist", "openalex",
                         {"op": "search", "query": "solubility"})
        entries = _read_calls(path)
        self.assertEqual(entries[-1]["status"], "refused-scope")

    def test_runner_read_also_denied(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-SCOPE-RUN2", calls_path=path)
        with self.assertRaises(gateway.GatewayRefused):
            gw.call_tool("runner", "wikidata",
                         {"op": "read", "locator": "x"})
        self.assertEqual(_read_calls(path)[-1]["status"], "refused-scope")

    def test_unknown_agent_default_deny(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-SCOPE-UNK", calls_path=path)
        with self.assertRaises(gateway.GatewayRefused):
            gw.call_tool("no-such-agent", "openalex",
                         {"op": "search", "query": "x"})


class TestQuarantine(unittest.TestCase):
    def test_results_enter_unconfirmed(self):
        raw = {"backend": "LOCAL-SHELF", "matches": []}
        q = gateway.quarantine(raw, tool="openalex",
                               agent="literature-researcher")
        self.assertEqual(q["status"], "unconfirmed")
        self.assertEqual(q["kind"], "gateway-source")
        self.assertTrue(gateway.is_quarantined(q))

    def test_quarantine_respected_not_confirmed(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-QUAR", calls_path=path)
        out = gw.call_tool("literature-researcher", "openalex",
                           {"op": "search", "query": "solubility"})
        self.assertEqual(out["status"], "unconfirmed")
        self.assertNotEqual(out.get("status"), "confirmed")
        # Pinning is the literature job's business: an unpinned
        # quarantined result must not pass as a pinned claim.
        self.assertNotIn("pinned_sources", out)


class TestBudgetAndOffline(unittest.TestCase):
    def test_budget_stops_with_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "calls.jsonl")
            cfg = {"gateway": {"maxCallsPerCycle": 1}}
            gw = gateway.Gateway("C-CAP", calls_path=path, config=cfg)
            gw.call_tool("literature-researcher", "openalex",
                         {"op": "search", "query": "a"})
            with self.assertRaises(gateway.GatewayBudgetExceeded):
                gw.call_tool("literature-researcher", "openalex",
                             {"op": "search", "query": "b"})
            receipt_p = os.path.join(
                gateway.GATEWAY_RECORDS_DIR, "C-CAP.budget-receipt.json")
            # receipt goes to records/gateway by default; with a temp
            # calls path the receipt still lands in the tree -- check
            # the helper instead, then clean up.
            ok, _ = gateway.check_gateway_budget(
                "C-CAP-X", 999, config=cfg,
                receipt_path=os.path.join(td, "receipt.json"))
            self.assertFalse(ok)
            self.assertTrue(os.path.exists(os.path.join(td, "receipt.json")))
            if os.path.exists(receipt_p):
                os.remove(receipt_p)

    def test_offline_closed_and_recorded(self):
        path = _tmp_calls()
        gw = gateway.Gateway("C-OFF", calls_path=path, offline_mode=True)
        with self.assertRaises(gateway.GatewayClosed):
            gw.call_tool("literature-researcher", "openalex",
                         {"op": "search", "query": "x"})
        entries = _read_calls(path)
        self.assertEqual(entries[-1]["status"], "gateway-closed")
        st = gw.status()
        self.assertTrue(st["offline_mode"])
        self.assertEqual(st["gateway"], "closed")


class TestWorkedExampleHonest(unittest.TestCase):
    def test_example_hashes_verify_no_network(self):
        p = os.path.join(_LAB, "records", "examples",
                         "gateway_example.json")
        d = json.load(open(p))
        self.assertNotEqual(
            d.get("network_touched"), True,
            "example must state no external network was touched")
        for rec in d["call_records"]:
            self.assertEqual(rec["status"], "ok")
            self.assertIn(rec["backend"], ("LOCAL-SHELF", "OFFLINE"))
            self.assertEqual(rec["args_hash"],
                             gateway.canonical_hash(rec["args"]))
            self.assertEqual(rec["result_hash"],
                             gateway.canonical_hash(
                                 rec["quarantined_result"]))
            self.assertEqual(rec["quarantined_result"]["status"],
                             "unconfirmed")


if __name__ == "__main__":
    unittest.main()
