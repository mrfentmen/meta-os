"""Live MCP backends for the controlled gateway (Section 8 follow-on).

Until now the gateway's only execution backend was LOCAL-SHELF: calls
were answered from the lab's own department shelves and no network was
touched. This module adds the second backend, "MCP-GATEWAY": the nine
allowlisted servers are called for real through the boss's own local
MCP gateway (Streamable HTTP on 127.0.0.1:8931, driven here through
its `mcp_call.py` client). Every server on the allowlist is keyless
and public; the lab spends nothing and holds no credentials.

The gateway module (gateway.py) keeps every rule it already had —
allowlist, per-agent scopes, budget, offline mode, quarantine — and
records the backend name on every call. This module only translates
and transports:

  lab call:  call_tool(agent, "openalex", {"op": "search",
                                           "query": "CRISPR"})
  wire call: openalex__search_works {"query": "CRISPR", "limit": 5}

Translation table (SERVER_SPECS) is grounded in the gateway's own
tool list (backends.json prefixes + each server's documented tools):

  lab server       prefix        search tool        read tool
  openalex         openalex      search_works       get_work
  archive-org      archiveorg    search_items       get_item
  open-library     openlibrary   search_books       get_work
  gbif             gbif          match_species      get_species
  wikidata         wikidata      search_entities    get_entity
  wikisource       wikisource    search_texts       read_text
  ietf             ietf          search_documents   get_document
  federal-register fedreg        search_documents   get_document
  osv              osv           check_package      get_vulnerability

Lab-side argument conventions mirror the LOCAL-SHELF backend: search
takes "query" (or "q"); read takes "locator" (or "id" / "source_id").
Per-server argument names differ (federal-register wants "term",
gbif wants "name", wikisource read wants "title", ...); the spec's
"map" renames lab keys to wire keys. Any extra wire arguments a tool
accepts (osv "ecosystem", gbif occurrence filters, date ranges) go in
the lab args under "remote" and are merged verbatim after mapping.

HONESTY: a transport failure raises McpTransportError with the real
error text; nothing here fabricates a result. A successful result
carries the server's payload untruncated under "result" (search) or
"source" (read); "matches" is only a convenience view extracted when
the payload shape is unambiguous. Results stay quarantined by the
gateway exactly like LOCAL-SHELF results: a lead, never evidence.
"""

import json
import os
import subprocess

#: Backend name recorded on every call this module executes.
BACKEND_NAME = "MCP-GATEWAY"

#: The boss's local MCP gateway (same box; keyless public servers).
GATEWAY_DIR = os.environ.get(
    "SCIENCE_LAB_MCP_GATEWAY_DIR",
    os.path.expanduser("~/workspace/mcp-gateway"))
GATEWAY_CALL = os.path.join(GATEWAY_DIR, "mcp_call.py")
GATEWAY_PYTHON = os.environ.get(
    "SCIENCE_LAB_MCP_CALL_PYTHON",
    os.path.join(GATEWAY_DIR, ".venv", "bin", "python"))
GATEWAY_URL = "http://127.0.0.1:8931/mcp"

#: Default per-call timeout (seconds) for one gateway round trip.
DEFAULT_TIMEOUT = 60

#: Statement recorded on every result this backend produces.
NETWORK_STATEMENT = ("boss's local MCP gateway %s; keyless public "
                     "servers; no credentials held by the lab"
                     % GATEWAY_URL)


class McpBackendError(Exception):
    """Base class for MCP backend failures. Always recorded upstream."""


class McpTransportError(McpBackendError):
    """The gateway call itself failed (down, timeout, bad exit)."""


class McpArgError(McpBackendError):
    """The lab args cannot fill the wire tool's required arguments."""


# ------------------------------------------------------------------
# Translation table. "map" renames lab arg keys to wire arg keys;
# "required" lists wire keys that must be present after mapping and
# the "remote" merge, else McpArgError names what is missing.
# ------------------------------------------------------------------

SERVER_SPECS = {
    "openalex": {
        "prefix": "openalex",
        "search": {"tool": "search_works",
                   "map": {"query": "query", "limit": "limit"},
                   "required": ("query",)},
        "read": {"tool": "get_work",
                 "map": {"locator": "id"},
                 "required": ("id",)},
    },
    "archive-org": {
        "prefix": "archiveorg",
        "search": {"tool": "search_items",
                   "map": {"query": "query", "limit": "limit"},
                   "required": ("query",)},
        "read": {"tool": "get_item",
                 "map": {"locator": "identifier"},
                 "required": ("identifier",)},
    },
    "open-library": {
        "prefix": "openlibrary",
        "search": {"tool": "search_books",
                   "map": {"query": "query", "limit": "limit"},
                   "required": ("query",)},
        "read": {"tool": "get_work",
                 "map": {"locator": "key"},
                 "required": ("key",)},
    },
    "gbif": {
        "prefix": "gbif",
        # Name matching is GBIF's search-shaped operation; occurrence
        # search needs a taxon key, which a read/match produces first.
        "search": {"tool": "match_species",
                   "map": {"query": "name"},
                   "required": ("name",)},
        "read": {"tool": "get_species",
                 "map": {"locator": "key"},
                 "required": ("key",)},
    },
    "wikidata": {
        "prefix": "wikidata",
        "search": {"tool": "search_entities",
                   "map": {"query": "query"},
                   "required": ("query",)},
        "read": {"tool": "get_entity",
                 "map": {"locator": "id"},
                 "required": ("id",)},
    },
    "wikisource": {
        "prefix": "wikisource",
        "search": {"tool": "search_texts",
                   "map": {"query": "query"},
                   "required": ("query",)},
        "read": {"tool": "read_text",
                 "map": {"locator": "title"},
                 "required": ("title",)},
    },
    "ietf": {
        "prefix": "ietf",
        "search": {"tool": "search_documents",
                   "map": {"query": "query", "limit": "limit"},
                   "required": ("query",)},
        "read": {"tool": "get_document",
                 "map": {"locator": "name"},
                 "required": ("name",)},
    },
    "federal-register": {
        "prefix": "fedreg",
        "search": {"tool": "search_documents",
                   "map": {"query": "term", "limit": "perPage"},
                   "required": ("term",)},
        "read": {"tool": "get_document",
                 "map": {"locator": "documentNumber"},
                 "required": ("documentNumber",)},
    },
    "osv": {
        # OSV has no free-text search: its search-shaped operation is
        # a package check, which needs name + ecosystem. Callers pass
        # them as lab args ("query" = package name) plus
        # {"remote": {"ecosystem": "PyPI"}} (or lab arg "ecosystem").
        "prefix": "osv",
        "search": {"tool": "check_package",
                   "map": {"query": "name", "ecosystem": "ecosystem",
                           "version": "version"},
                   "required": ("name", "ecosystem")},
        "read": {"tool": "get_vulnerability",
                 "map": {"locator": "id"},
                 "required": ("id",)},
    },
}


def spec_for(server):
    """Translation spec for one allowlisted server. Raises KeyError."""
    return SERVER_SPECS[server]


def wire_tool_name(server, op):
    """Full gateway tool name, e.g. ("openalex", "search") ->
    "openalex__search_works"."""
    spec = SERVER_SPECS[server]
    return "%s__%s" % (spec["prefix"], spec[op]["tool"])


def build_wire_args(server, op, args):
    """Translate lab args to wire args for (server, op).

    Search reads the query from "query" (or "q"); read reads the
    locator from "locator" (or "id" / "source_id") — the same
    conventions as the LOCAL-SHELF backend. The spec's map renames
    keys; args["remote"] (a dict) is merged last, verbatim. Missing
    required wire keys raise McpArgError naming them.
    """
    spec = SERVER_SPECS[server]
    op_spec = spec[op]
    args = dict(args) if isinstance(args, dict) else {"value": args}
    if op == "search" and "query" not in args and "q" in args:
        args["query"] = args["q"]
    if op == "read" and "locator" not in args:
        for alt in ("id", "source_id"):
            if alt in args:
                args["locator"] = args[alt]
                break
    wire = {}
    for lab_key, wire_key in op_spec["map"].items():
        if lab_key in args and args[lab_key] is not None:
            wire[wire_key] = args[lab_key]
    remote = args.get("remote")
    if isinstance(remote, dict):
        wire.update(remote)
    missing = [k for k in op_spec["required"] if k not in wire]
    if missing:
        raise McpArgError(
            "%s %s via %s requires wire argument(s) %s; lab args gave "
            "keys %s (pass extras under 'remote')"
            % (server, op, op_spec["tool"], missing, sorted(args)))
    return wire


# ------------------------------------------------------------------
# Transport. A transport is callable(wire_tool, wire_args) -> payload.
# Tests inject fakes; production uses the mcp_call.py subprocess.
# ------------------------------------------------------------------

def default_transport(wire_tool, wire_args, timeout=DEFAULT_TIMEOUT):
    """Call the boss's MCP gateway via its mcp_call.py client.

    Returns the tool payload as a dict (non-dict payloads are wrapped
    under "result"; unparseable output is kept verbatim under
    "raw_text" — never silently reshaped). Raises McpTransportError
    on a missing client, timeout, or nonzero exit, carrying the real
    stderr text.
    """
    if not os.path.exists(GATEWAY_CALL):
        raise McpTransportError(
            "MCP gateway client not found at %s (gateway dir %s)"
            % (GATEWAY_CALL, GATEWAY_DIR))
    cmd = [GATEWAY_PYTHON, GATEWAY_CALL, "call", wire_tool,
           json.dumps(wire_args)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        raise McpTransportError(
            "MCP gateway call %s timed out after %ss"
            % (wire_tool, timeout))
    except OSError as exc:
        raise McpTransportError(
            "MCP gateway call %s could not start: %s" % (wire_tool, exc))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise McpTransportError(
            "MCP gateway call %s failed (exit %d): %s"
            % (wire_tool, proc.returncode, detail[:500]))
    out = (proc.stdout or "").strip()
    try:
        payload = json.loads(out)
    except ValueError:
        return {"raw_text": out}
    if isinstance(payload, dict):
        return payload
    return {"result": payload}


# ------------------------------------------------------------------
# Execution: same result shape family as gateway._execute_local.
# ------------------------------------------------------------------

#: Payload keys that unambiguously hold a search result list.
_MATCH_KEYS = ("results", "items", "works", "matches", "documents",
               "entities", "occurrences")


def _matches_of(payload):
    """Convenience view: the result list when the shape is clear."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        inner = payload.get("result")
        if isinstance(inner, list):
            return inner
        for key in _MATCH_KEYS:
            if isinstance(payload.get(key), list):
                return payload[key]
    return []


def payload_form(payload):
    """How the server answered: "text" or "json".

    Several of the boss's MCP servers answer in formatted plain text
    (e.g. openalex returns a human-readable hit list), others in JSON.
    Text is kept verbatim under "raw_text" by the transport; it is
    labelled, never parsed into invented structure.
    """
    if isinstance(payload, dict) and set(payload) == {"raw_text"}:
        return "text"
    return "json"


def execute_mcp(tool, op, args, transport=None):
    """Execute one search/read against a live allowlisted server.

    Returns a result dict in the LOCAL-SHELF shape family, carrying
    backend "MCP-GATEWAY", the wire tool name, and the server's full
    payload (under "result" for search, "source" for read). Raises
    McpArgError / McpTransportError on failure — never fabricates.
    """
    if tool not in SERVER_SPECS:
        raise McpTransportError(
            "no MCP backend spec for server %r (specs cover exactly "
            "the gateway allowlist)" % (tool,))
    if op not in ("search", "read"):
        raise McpArgError("unsupported gateway op %r" % (op,))
    wire_args = build_wire_args(tool, op, args)
    wire_tool = wire_tool_name(tool, op)
    call = transport or default_transport
    payload = call(wire_tool, wire_args)
    if not isinstance(payload, dict):
        payload = {"result": payload}
    if op == "search":
        query = wire_args.get("term", wire_args.get(
            "name", wire_args.get("query", "")))
        return {
            "backend": BACKEND_NAME,
            "tool": tool,
            "op": op,
            "query": query,
            "remote_tool": wire_tool,
            "remote_args": wire_args,
            "payload_form": payload_form(payload),
            "matches": _matches_of(payload),
            "result": payload,
            "network": NETWORK_STATEMENT,
        }
    locator = args.get("locator", args.get("id", args.get("source_id", "")))
    return {
        "backend": BACKEND_NAME,
        "tool": tool,
        "op": op,
        "locator": locator,
        "remote_tool": wire_tool,
        "remote_args": wire_args,
        "payload_form": payload_form(payload),
        "source": payload,
        "network": NETWORK_STATEMENT,
    }
