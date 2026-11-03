"""MCP-GATEWAY backend for the controlled gateway (Section 8 follow-on).

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v

All tests run against a FAKE transport (no network, no MCP gateway
process) and temporary calls.jsonl files, so the suite never touches
the committed records and never needs the live gateway. The live
smoke is a separate, explicitly-labelled step (see
records/gateway/mcp_smoke record), not a unit test.
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
import mcp_backends  # noqa: E402


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


class FakeTransport(object):
    """Records wire calls; returns a canned payload per call."""

    def __init__(self, payload=None, fail_with=None):
        self.calls = []
        self.payload = payload if payload is not None else {
            "results": [{"title": "fake hit"}],
            "echo": True,
        }
        self.fail_with = fail_with

    def __call__(self, wire_tool, wire_args):
        self.calls.append((wire_tool, dict(wire_args)))
        if self.fail_with is not None:
            raise self.fail_with
        return dict(self.payload)


def _gw(transport, calls_path, **kw):
    kw.setdefault("backend", "mcp-gateway")
    kw.setdefault("transport", transport)
    return gateway.Gateway("CYCLE-MCP-TEST", calls_path=calls_path, **kw)


class SpecTableTests(unittest.TestCase):

    def test_specs_cover_exactly_the_allowlist(self):
        self.assertEqual(set(mcp_backends.SERVER_SPECS),
                         set(gateway.ALLOWLIST))

    def test_wire_tool_names(self):
        self.assertEqual(mcp_backends.wire_tool_name("openalex", "search"),
                         "openalex__search_works")
        self.assertEqual(mcp_backends.wire_tool_name("federal-register",
                                                     "read"),
                         "fedreg__get_document")
        self.assertEqual(mcp_backends.wire_tool_name("archive-org", "read"),
                         "archiveorg__get_item")
        self.assertEqual(mcp_backends.wire_tool_name("open-library",
                                                     "search"),
                         "openlibrary__search_books")


class ArgTranslationTests(unittest.TestCase):

    def setUp(self):
        self.calls_path = _tmp_calls()
        self.transport = FakeTransport()
        self.gw = _gw(self.transport, self.calls_path)

    def test_search_translation_per_server(self):
        cases = [
            ("openalex", {"query": "crispr", "limit": 3},
             "openalex__search_works", {"query": "crispr", "limit": 3}),
            ("archive-org", {"query": "apollo"},
             "archiveorg__search_items", {"query": "apollo"}),
            ("open-library", {"query": "dune"},
             "openlibrary__search_books", {"query": "dune"}),
            ("gbif", {"query": "Panthera leo"},
             "gbif__match_species", {"name": "Panthera leo"}),
            ("wikidata", {"query": "Douglas Adams"},
             "wikidata__search_entities", {"query": "Douglas Adams"}),
            ("wikisource", {"query": "Gettysburg"},
             "wikisource__search_texts", {"query": "Gettysburg"}),
            ("ietf", {"query": "httpbis"},
             "ietf__search_documents", {"query": "httpbis"}),
            ("federal-register", {"query": "emissions", "limit": 5},
             "fedreg__search_documents", {"term": "emissions",
                                          "perPage": 5}),
            ("osv", {"query": "requests",
                     "remote": {"ecosystem": "PyPI"}},
             "osv__check_package", {"name": "requests",
                                    "ecosystem": "PyPI"}),
        ]
        for server, lab_args, wire_tool, wire_args in cases:
            args = dict(lab_args)
            args["op"] = "search"
            self.gw.call_tool("literature-researcher", server, args)
            got_tool, got_args = self.transport.calls[-1]
            self.assertEqual(got_tool, wire_tool, server)
            self.assertEqual(got_args, wire_args, server)
        self.assertEqual(len(self.transport.calls), len(cases))

    def test_read_translation_per_server(self):
        cases = [
            ("openalex", "W2741809807", "openalex__get_work",
             {"id": "W2741809807"}),
            ("archive-org", "apollo11", "archiveorg__get_item",
             {"identifier": "apollo11"}),
            ("open-library", "OL66554W", "openlibrary__get_work",
             {"key": "OL66554W"}),
            ("gbif", "2435099", "gbif__get_species", {"key": "2435099"}),
            ("wikidata", "Q42", "wikidata__get_entity", {"id": "Q42"}),
            ("wikisource", "Gettysburg Address", "wikisource__read_text",
             {"title": "Gettysburg Address"}),
            ("ietf", "rfc9110", "ietf__get_document",
             {"name": "rfc9110"}),
            ("federal-register", "2026-00001", "fedreg__get_document",
             {"documentNumber": "2026-00001"}),
            ("osv", "CVE-2021-44228", "osv__get_vulnerability",
             {"id": "CVE-2021-44228"}),
        ]
        for server, locator, wire_tool, wire_args in cases:
            self.gw.call_tool("research-director", server,
                              {"op": "read", "locator": locator})
            got_tool, got_args = self.transport.calls[-1]
            self.assertEqual(got_tool, wire_tool, server)
            self.assertEqual(got_args, wire_args, server)

    def test_search_accepts_q_alias_and_read_accepts_id_alias(self):
        self.gw.call_tool("literature", "openalex",
                          {"op": "search", "q": "alias query"})
        self.assertEqual(self.transport.calls[-1][1],
                         {"query": "alias query"})
        self.gw.call_tool("director", "wikidata",
                          {"op": "read", "id": "Q1"})
        self.assertEqual(self.transport.calls[-1][1], {"id": "Q1"})

    def test_osv_search_without_ecosystem_is_an_arg_error(self):
        with self.assertRaises(gateway.GatewayBackendError) as ctx:
            self.gw.call_tool("literature-researcher", "osv",
                              {"op": "search", "query": "requests"})
        self.assertIn("ecosystem", str(ctx.exception))
        self.assertEqual(self.transport.calls, [])
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "backend-error")
        self.assertIsNone(entries[-1]["result_hash"])


class GatewayRuleTests(unittest.TestCase):
    """The pre-existing gateway rules bind the live backend too."""

    def setUp(self):
        self.calls_path = _tmp_calls()
        self.transport = FakeTransport()
        self.gw = _gw(self.transport, self.calls_path)

    def test_allowlist_refusal_never_reaches_transport(self):
        with self.assertRaises(gateway.GatewayRefused):
            self.gw.call_tool("literature-researcher", "not-a-server",
                              {"op": "search", "query": "x"})
        self.assertEqual(self.transport.calls, [])
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "refused-allowlist")

    def test_scope_refusal_never_reaches_transport(self):
        with self.assertRaises(gateway.GatewayRefused):
            self.gw.call_tool("computational-scientist", "openalex",
                              {"op": "search", "query": "x"})
        self.assertEqual(self.transport.calls, [])
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "refused-scope")

    def test_offline_never_reaches_transport(self):
        gw = _gw(self.transport, self.calls_path, offline_mode=True)
        with self.assertRaises(gateway.GatewayClosed):
            gw.call_tool("literature-researcher", "openalex",
                         {"op": "search", "query": "x"})
        self.assertEqual(self.transport.calls, [])
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "gateway-closed")

    def test_budget_stops_before_transport(self):
        gw = _gw(self.transport, self.calls_path,
                 config={"gateway": {"maxCallsPerCycle": 0}})
        with self.assertRaises(gateway.GatewayBudgetExceeded):
            gw.call_tool("literature-researcher", "openalex",
                         {"op": "search", "query": "x"})
        self.assertEqual(self.transport.calls, [])
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "budget-stopped")

    def test_success_is_quarantined_and_recorded_with_backend(self):
        out = self.gw.call_tool("literature-researcher", "openalex",
                                {"op": "search", "query": "crispr"})
        self.assertTrue(gateway.is_quarantined(out))
        self.assertEqual(out["result"]["backend"], "MCP-GATEWAY")
        self.assertEqual(out["result"]["remote_tool"],
                         "openalex__search_works")
        self.assertEqual(out["result"]["matches"],
                         [{"title": "fake hit"}])
        entries = _read_calls(self.calls_path)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "ok")
        self.assertEqual(entry["backend"], "MCP-GATEWAY")
        self.assertEqual(entry["result_hash"],
                         gateway.canonical_hash(out))
        self.assertEqual(entry["cost"], 0.0)

    def test_transport_failure_is_recorded_and_raises(self):
        transport = FakeTransport(
            fail_with=mcp_backends.McpTransportError("gateway down: boom"))
        gw = _gw(transport, self.calls_path)
        with self.assertRaises(gateway.GatewayBackendError) as ctx:
            gw.call_tool("literature-researcher", "openalex",
                         {"op": "search", "query": "x"})
        self.assertIn("gateway down: boom", str(ctx.exception))
        entries = _read_calls(self.calls_path)
        self.assertEqual(entries[-1]["status"], "backend-error")
        self.assertIn("gateway down: boom", entries[-1]["reason"])
        self.assertIsNone(entries[-1]["result_hash"])

    def test_text_payload_is_labelled_not_parsed(self):
        # Several real servers answer in formatted plain text. The
        # backend labels the form and keeps the text verbatim; it
        # never invents structured matches from prose.
        transport = FakeTransport(
            payload={"raw_text": "OpenAlex found 2 work(s):\n1. X\n"})
        gw = _gw(transport, self.calls_path)
        out = gw.call_tool("literature-researcher", "openalex",
                           {"op": "search", "query": "x"})
        result = out["result"]
        self.assertEqual(result["payload_form"], "text")
        self.assertEqual(result["matches"], [])
        self.assertIn("OpenAlex found 2 work(s)",
                      result["result"]["raw_text"])

    def test_json_payload_form_is_labelled(self):
        out = self.gw.call_tool("literature-researcher", "ietf",
                                {"op": "search", "query": "quic"})
        self.assertEqual(out["result"]["payload_form"], "json")

    def test_status_names_the_mcp_backend(self):
        status = self.gw.status()
        self.assertEqual(status["gateway"], "open-mcp-gateway")
        self.assertEqual(status["backend"], "mcp-gateway")
        self.assertIn("127.0.0.1:8931", status["network"])

    def test_module_level_call_tool_with_backend(self):
        out = gateway.call_tool(
            "literature-researcher", "ietf",
            {"op": "search", "query": "quic"},
            cycle_id="CYCLE-MCP-MODULE", calls_path=self.calls_path,
            backend="mcp-gateway", transport=self.transport)
        self.assertTrue(gateway.is_quarantined(out))
        self.assertEqual(self.transport.calls[-1][0],
                         "ietf__search_documents")


class DefaultBackendRegressionTests(unittest.TestCase):

    def test_default_backend_is_still_local_shelf(self):
        calls_path = _tmp_calls()
        gw = gateway.Gateway("CYCLE-REGRESSION", calls_path=calls_path)
        out = gw.call_tool("literature-researcher", "openalex",
                           {"op": "search", "query": "anything"})
        self.assertEqual(out["result"]["backend"], "LOCAL-SHELF")
        entries = _read_calls(calls_path)
        self.assertEqual(entries[0]["backend"], "LOCAL-SHELF")
        self.assertEqual(gw.status()["gateway"], "open-local-shelf")

    def test_unknown_backend_still_raises(self):
        with self.assertRaises(ValueError):
            gateway.Gateway("CYCLE-X", backend="carrier-pigeon")


if __name__ == "__main__":
    unittest.main()
