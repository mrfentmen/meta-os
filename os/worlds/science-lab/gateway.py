"""Controlled MCP gateway (Section 8: tasks 71-77).

The lab's agents may call ONLY the boss-allowlisted MCP servers. Every
call is recorded; refusals are recorded too. Two execution backends
exist: "LOCAL-SHELF" reads LOCAL department shelves as an honest
stand-in and touches no network; "MCP-GATEWAY" (mcp_backends.py) calls
the nine allowlisted servers for real through the boss's own local
MCP gateway. Either way the gateway can be closed entirely
(offline_mode). Results enter records as UNCONFIRMED sources until
the literature job pins them (see quarantine()).

Task map:
  71. ALLOWLIST: the 9 boss-named servers, nothing else.
  72. Call record: agent, tool, args_hash, result_hash, cost,
      timestamp -> records/gateway/calls.jsonl, every call.
  73. Non-allowlisted tool -> GatewayRefused raised AND recorded.
  74. Per-agent scopes enforced (literature may search/read; runners
      may not browse; default-deny for unknown agents).
  75. quarantine(): gateway results are unconfirmed until pinned by
      the literature job's rules (literature.assemble_brief).
  76. Gateway budget: calls per cycle capped via lab_config
      ("gateway" section, else local default); receipt on stop.
  77. Offline mode: Gateway(offline_mode=True) or module
      set_offline(True); call_tool raises GatewayClosed, records the
      refusal, and offline_record() states the cycle ran its
      deterministic parts with the gateway closed.

HONESTY: a gateway result — either backend — is a lead, never
evidence until pinned. Backend is always named in the record
("LOCAL-SHELF" or "MCP-GATEWAY"). The LOCAL-SHELF path opens no
socket; the MCP-GATEWAY path reaches only the boss's local gateway
on 127.0.0.1:8931 (keyless public servers, no credentials).
"""

import hashlib
import json
import os
from datetime import datetime, timezone

try:
    from .lab_config import load_config
except ImportError:  # direct script use / sys.path import (see tests)
    try:
        from lab_config import load_config
    except ImportError:  # config helper missing: local defaults apply
        load_config = None

try:
    from . import mcp_backends
except ImportError:  # direct script use / sys.path import (see tests)
    try:
        import mcp_backends
    except ImportError:  # backend module missing: local-shelf only
        mcp_backends = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHELVES_DIR = os.path.join(BASE_DIR, "shelves")
GATEWAY_RECORDS_DIR = os.path.join(BASE_DIR, "records", "gateway")
DEFAULT_CALLS_PATH = os.path.join(GATEWAY_RECORDS_DIR, "calls.jsonl")

# Task 71: boss allowlist. Exactly these nine MCP server names.
ALLOWLIST = frozenset((
    "openalex",
    "archive-org",
    "open-library",
    "gbif",
    "wikidata",
    "wikisource",
    "ietf",
    "federal-register",
    "osv",
))

#: Operations each allowlisted tool supports on this path.
TOOL_OPS = ("search", "read")

# Task 74: per-agent tool scopes (allowed operations).
# Literature researchers may search and read. Analysts/critics may read
# pinned results but may not initiate searches. Runners (computational
# + department benches) may not browse at all. Unknown agents default
# to no access (default-deny; see _scope_of).
SCOPES = {
    "research-director": frozenset(("search", "read")),
    "literature-researcher": frozenset(("search", "read")),
    "hypothesis-generator": frozenset(("read",)),
    "scientific-analyst": frozenset(("read",)),
    "mathematics-researcher": frozenset(("read",)),
    "statistician": frozenset(("read",)),
    "scientific-critic": frozenset(("read",)),
    "research-archivist": frozenset(("read",)),
    "independent-verifier": frozenset(("read",)),
    "computational-scientist": frozenset(),
    "biology-researcher": frozenset(),
    "chemistry-researcher": frozenset(),
    "physics-researcher": frozenset(),
}

#: Short aliases accepted by normalize_agent() (task spec shorthand
#: like "literature" / "runner" maps to the canonical lab agent id).
_AGENT_ALIASES = {
    "literature": "literature-researcher",
    "director": "research-director",
    "analyst": "scientific-analyst",
    "mathematics": "mathematics-researcher",
    "maths": "mathematics-researcher",
    "hypothesis": "hypothesis-generator",
    "statistician": "statistician",
    "critic": "scientific-critic",
    "verifier": "independent-verifier",
    "archivist": "research-archivist",
    "runner": "computational-scientist",
    "computational": "computational-scientist",
    "computational-scientist": "computational-scientist",
    "biology": "biology-researcher",
    "chemistry": "chemistry-researcher",
    "physics": "physics-researcher",
    "physics-math": "physics-researcher",
}

#: Local-policy default when lab_config.json carries no gateway section.
#: Caps are local policy, not evidence; a stopped run earns no level.
DEFAULT_MAX_CALLS_PER_CYCLE = 50

#: Deterministic cost of one LOCAL-SHELF call (no external spend).
COST_PER_CALL = 0.0

#: Module-level offline flag (see set_offline / is_offline).
_OFFLINE_MODE = False


class GatewayError(Exception):
    """Base class for gateway failures."""


class GatewayRefused(GatewayError):
    """Raised when a call is refused (allowlist or scope). Recorded."""


class GatewayClosed(GatewayError):
    """Raised when the gateway is closed (offline_mode). Recorded."""


class GatewayBudgetExceeded(GatewayError):
    """Raised when the per-cycle call cap is hit. Receipt on stop."""


class GatewayBackendError(GatewayError):
    """Raised when the MCP-GATEWAY backend fails. Recorded."""


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str).encode("utf-8")


def canonical_hash(obj):
    """SHA-256 hex of the canonical JSON of obj (dicts, lists, scalars)."""
    return hashlib.sha256(_canonical(obj)).hexdigest()


def normalize_agent(agent):
    """Map a shorthand or full agent name to the canonical lab agent id."""
    if not isinstance(agent, str) or not agent.strip():
        raise ValueError("call_tool requires a non-empty agent name")
    key = agent.strip().lower().replace("_", "-")
    if key in SCOPES:
        return key
    if key in _AGENT_ALIASES:
        return _AGENT_ALIASES[key]
    return key  # unknown: default-deny scope (empty), still recorded


def _scope_of(agent):
    """Allowed operations for an agent. Unknown agents get none."""
    return SCOPES.get(normalize_agent(agent), frozenset())


def _calls_path(path=None):
    return path or DEFAULT_CALLS_PATH


def _append_call_record(entry, path=None):
    """Append one call/refusal record to calls.jsonl. Returns the entry."""
    target = _calls_path(path)
    parent = os.path.dirname(os.path.abspath(target))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def set_offline(flag=True):
    """Set the module-level offline flag. Returns the new value."""
    global _OFFLINE_MODE
    _OFFLINE_MODE = bool(flag)
    return _OFFLINE_MODE


def is_offline():
    """True when the module-level gateway is closed (offline_mode)."""
    return _OFFLINE_MODE


# ------------------------------------------------------------------
# Task 75: quarantine. Gateway output is UNCONFIRMED until pinned.
# ------------------------------------------------------------------

def quarantine(result, tool=None, agent=None):
    """Mark a gateway result as an unconfirmed source.

    Wraps the raw result dict (or any payload) in an envelope with
    status "unconfirmed". Pinning happens ONLY through the literature
    job's rules (literature.assemble_brief pins claims to source
    records); nothing here confirms a claim. Inputs are not mutated.
    """
    envelope = {
        "kind": "gateway-source",
        "status": "unconfirmed",
        "note": ("UNCONFIRMED gateway result: not evidence until pinned "
                 "by the literature job (assemble_brief)."),
        "result": dict(result) if isinstance(result, dict) else result,
        "recorded_at": _utcnow(),
    }
    if tool is not None:
        envelope["tool"] = tool
    if agent is not None:
        envelope["agent"] = agent
    return envelope


def is_quarantined(record):
    """True iff the record is a quarantined (unconfirmed) gateway source."""
    return (isinstance(record, dict)
            and record.get("kind") == "gateway-source"
            and record.get("status") == "unconfirmed")


# ------------------------------------------------------------------
# Task 76: gateway budget (calls per cycle, receipt on stop).
# ------------------------------------------------------------------

def _gateway_cap(config):
    gw = (config or {}).get("gateway", {})
    cap = gw.get("maxCallsPerCycle", DEFAULT_MAX_CALLS_PER_CYCLE)
    return cap


def check_gateway_budget(cycle_id, calls, config=None, receipt_path=None):
    """Per-cycle gateway call cap (Task 76).

    Caps come from lab_config.json's "gateway" section when present,
    else DEFAULT_MAX_CALLS_PER_CYCLE. Returns (allowed, reason). Over
    cap -> (False, reason) plus a stop receipt written under
    records/gateway/; the caller must stop the run. A stopped run
    earns no level and files no claim.
    """
    if not cycle_id:
        raise ValueError("check_gateway_budget requires a cycle_id")
    if config is None:
        if load_config is not None:
            try:
                config = load_config()
            except (OSError, ValueError):
                config = {}
        else:
            config = {}
    max_calls = _gateway_cap(config)
    if calls > max_calls:
        reason = ("budget-cap-reached: cycle %r gateway cap exceeded: "
                  "calls %s > maxCallsPerCycle %s"
                  % (cycle_id, calls, max_calls))
        receipt = {
            "kind": "budget-receipt",
            "agent": "gateway",
            "cycle_id": cycle_id,
            "calls": calls,
            "max_calls_per_cycle": max_calls,
            "reason": reason,
            "stopped": True,
            "recorded_at": _utcnow(),
        }
        path = receipt_path or os.path.join(
            GATEWAY_RECORDS_DIR, "%s.budget-receipt.json" % cycle_id)
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(receipt, fh, sort_keys=True, indent=2)
            fh.write("\n")
        return (False, reason)
    return (
        True,
        "ok: cycle %r within gateway budget (calls %s/%s)"
        % (cycle_id, calls, max_calls),
    )


# ------------------------------------------------------------------
# Local execution backend: NO network. LOCAL-SHELF stand-in only.
# ------------------------------------------------------------------

def _shelf_sources():
    """Load all department shelf source entries (best effort)."""
    entries = []
    if not os.path.isdir(SHELVES_DIR):
        return entries
    for name in sorted(os.listdir(SHELVES_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(SHELVES_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict) and isinstance(
                payload.get("sources"), list):
            for src in payload["sources"]:
                if isinstance(src, dict):
                    entry = dict(src)
                    entry.setdefault("shelf", "shelves/%s" % name)
                    entries.append(entry)
        elif isinstance(payload, list):
            entries.extend(e for e in payload if isinstance(e, dict))
    return entries


def _execute_local(tool, op, args):
    """Execute a search/read against LOCAL shelves. No network.

    Returns a plain result dict carrying backend "LOCAL-SHELF" and a
    statement that no external network was touched.
    """
    args = dict(args) if isinstance(args, dict) else {"value": args}
    if op == "search":
        query = str(args.get("query", args.get("q", "")))
        q_toks = set(t for t in query.lower().split() if len(t) > 2)
        hits = []
        for src in _shelf_sources():
            hay = " ".join(str(src.get(k, "")) for k in
                           ("citation", "claim", "locator")).lower()
            score = sum(1 for t in q_toks if t in hay)
            if q_toks and score > 0:
                hits.append({"score": score, "source": src})
        hits.sort(key=lambda h: (-h["score"],
                                 str(h["source"].get("citation", ""))))
        return {
            "backend": "LOCAL-SHELF",
            "tool": tool,
            "op": op,
            "query": query,
            "matches": [h["source"] for h in hits[:5]],
            "scores": [h["score"] for h in hits[:5]],
            "network": "no external network touched; local shelves only",
        }
    if op == "read":
        locator = str(args.get("locator", args.get("id", args.get("source_id", ""))))
        for src in _shelf_sources():
            blob = json.dumps(src)
            if locator and locator in blob:
                return {
                    "backend": "LOCAL-SHELF",
                    "tool": tool,
                    "op": op,
                    "locator": locator,
                    "source": src,
                    "network": "no external network touched; local shelves only",
                }
        return {
            "backend": "LOCAL-SHELF",
            "tool": tool,
            "op": op,
            "locator": locator,
            "source": None,
            "note": "no local shelf entry matched this locator",
            "network": "no external network touched; local shelves only",
        }
    raise ValueError("unsupported gateway op %r (want one of %r)"
                     % (op, list(TOOL_OPS)))


def _refusal_entry(agent, tool, args, reason, status, cycle_id):
    return {
        "kind": "gateway-call",
        "status": status,
        "agent": agent,
        "tool": tool,
        "args_hash": canonical_hash(args),
        "result_hash": None,
        "cost": 0.0,
        "reason": reason,
        "cycle_id": cycle_id,
        "timestamp": _utcnow(),
    }


class Gateway(object):
    """A scoped, budgeted, optionally-offline gateway handle.

    cycle_id: labels every record this handle files (budget + calls).
    calls_path: JSONL file for call records (default records/gateway/).
    config: lab config dict (gateway.maxCallsPerCycle); loaded lazily.
    offline_mode: when True the gateway is closed; call_tool raises
        GatewayClosed and records the refusal (Task 77).
    backend: "local-shelf" (default; no network) or "mcp-gateway"
        (live calls through the boss's local MCP gateway, via
        mcp_backends.py). Anything else raises.
    transport: optional callable(wire_tool, wire_args) -> payload for
        the mcp-gateway backend (tests inject fakes; production uses
        mcp_backends.default_transport).
    """

    def __init__(self, cycle_id, calls_path=None, config=None,
                 offline_mode=False, backend="local-shelf",
                 transport=None):
        if not cycle_id:
            raise ValueError("Gateway requires a cycle_id")
        if backend not in ("local-shelf", "mcp-gateway"):
            raise ValueError("unsupported gateway backend %r: want "
                             "'local-shelf' or 'mcp-gateway'"
                             % (backend,))
        if backend == "mcp-gateway" and mcp_backends is None:
            raise ValueError("backend 'mcp-gateway' unavailable: "
                             "mcp_backends.py not importable")
        self.cycle_id = cycle_id
        self.calls_path = _calls_path(calls_path)
        self._config = config
        self.offline_mode = bool(offline_mode)
        self.backend = backend
        self.transport = transport
        self.calls_made = 0

    def _config_now(self):
        if self._config is not None:
            return self._config
        if load_config is not None:
            try:
                return load_config()
            except (OSError, ValueError):
                return {}
        return {}

    def set_offline(self, flag=True):
        """Close (True) or open (False) this handle. Returns the value."""
        self.offline_mode = bool(flag)
        return self.offline_mode

    def status(self):
        """State record: open/closed, cycle, calls made. For cycle logs."""
        if self.offline_mode:
            state = "closed"
            network = "gateway closed; no calls issued"
        elif self.backend == "mcp-gateway":
            state = "open-mcp-gateway"
            network = mcp_backends.NETWORK_STATEMENT
        else:
            state = "open-local-shelf"
            network = "no external network touched on this path"
        return {
            "kind": "gateway-status",
            "cycle_id": self.cycle_id,
            "gateway": state,
            "offline_mode": self.offline_mode,
            "backend": self.backend,
            "calls_made": self.calls_made,
            "network": network,
            "recorded_at": _utcnow(),
        }

    def offline_record(self, path=None):
        """File a record stating the cycle ran with the gateway closed."""
        record = dict(self.status())
        record["note"] = ("Cycle ran its deterministic parts with the "
                          "gateway closed (offline_mode); no tool calls "
                          "were issued or recorded as results.")
        path = path or os.path.join(
            GATEWAY_RECORDS_DIR, "%s.offline.json" % self.cycle_id)
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, sort_keys=True, indent=2)
            fh.write("\n")
        return record

    def _record(self, entry):
        return _append_call_record(entry, self.calls_path)

    def call_tool(self, agent, tool, args):
        """Call an allowlisted tool within the agent's scope.

        Records {agent, tool, args_hash, result_hash, cost, timestamp}
        to calls.jsonl on EVERY path (success + refusal). Returns the
        quarantined (unconfirmed) result on success. Raises:
          GatewayClosed on offline_mode (Task 77),
          GatewayRefused on non-allowlisted tool (Task 73) or scope
            violation (Task 74),
          GatewayBudgetExceeded when the cycle cap is hit (Task 76).
        """
        canon_agent = normalize_agent(agent)
        args = dict(args) if isinstance(args, dict) else {"value": args}
        op = str(args.get("op", "search")).strip().lower() or "search"

        if self.offline_mode or _OFFLINE_MODE:
            reason = ("gateway closed: offline_mode; cycle %r runs "
                      "deterministic parts only, no tool calls"
                      % (self.cycle_id,))
            self._record(_refusal_entry(canon_agent, tool, args, reason,
                                        "gateway-closed", self.cycle_id))
            raise GatewayClosed(reason)

        if tool not in ALLOWLIST:
            reason = ("refused: tool %r not in gateway allowlist (%d "
                      "allowed servers)" % (tool, len(ALLOWLIST)))
            self._record(_refusal_entry(canon_agent, tool, args, reason,
                                        "refused-allowlist", self.cycle_id))
            raise GatewayRefused(reason)

        if op not in TOOL_OPS:
            reason = ("refused: op %r unsupported (want one of %r)"
                      % (op, list(TOOL_OPS)))
            self._record(_refusal_entry(canon_agent, tool, args, reason,
                                        "refused-op", self.cycle_id))
            raise GatewayRefused(reason)

        if op not in _scope_of(canon_agent):
            reason = ("scope violation: agent %r may not perform op %r "
                      "(scope: %s)"
                      % (canon_agent, op,
                         sorted(_scope_of(canon_agent)) or ["none"]))
            self._record(_refusal_entry(canon_agent, tool, args, reason,
                                        "refused-scope", self.cycle_id))
            raise GatewayRefused(reason)

        allowed, budget_reason = check_gateway_budget(
            self.cycle_id, self.calls_made + 1, config=self._config_now())
        if not allowed:
            self._record(_refusal_entry(canon_agent, tool, args,
                                        budget_reason, "budget-stopped",
                                        self.cycle_id))
            raise GatewayBudgetExceeded(budget_reason)

        if self.backend == "mcp-gateway":
            try:
                raw = mcp_backends.execute_mcp(
                    tool, op, args, transport=self.transport)
            except mcp_backends.McpBackendError as exc:
                reason = "backend-error: %s" % (exc,)
                self._record(_refusal_entry(
                    canon_agent, tool, args, reason, "backend-error",
                    self.cycle_id))
                raise GatewayBackendError(reason)
            backend_name = mcp_backends.BACKEND_NAME
        else:
            raw = _execute_local(tool, op, args)
            backend_name = "LOCAL-SHELF"
        quarantined = quarantine(raw, tool=tool, agent=canon_agent)
        entry = {
            "kind": "gateway-call",
            "status": "ok",
            "agent": canon_agent,
            "tool": tool,
            "op": op,
            "args_hash": canonical_hash(args),
            "result_hash": canonical_hash(quarantined),
            "cost": COST_PER_CALL,
            "cycle_id": self.cycle_id,
            "backend": backend_name,
            "timestamp": _utcnow(),
        }
        self._record(entry)
        self.calls_made += 1
        return quarantined


def call_tool(agent, tool, args, cycle_id="GATEWAY-DEFAULT",
              calls_path=None, config=None, offline_mode=None,
              backend="local-shelf", transport=None):
    """Module-level call_tool(agent, tool, args) per the task spec.

    Convenience wrapper over Gateway with one call per handle (plus
    budget counted against the existing calls.jsonl for the cycle).
    Optional kwargs: cycle_id, calls_path (tests), config,
    offline_mode (True closes the gateway for this call), backend
    ("local-shelf" default, or "mcp-gateway" for live calls),
    transport (fake transport for tests on the mcp-gateway backend).
    """
    gw = Gateway(cycle_id,
                 calls_path=calls_path,
                 config=config,
                 offline_mode=_OFFLINE_MODE if offline_mode is None
                 else offline_mode,
                 backend=backend,
                 transport=transport)
    if cycle_id != "GATEWAY-DEFAULT":
        gw.calls_made = _cycle_call_count(cycle_id, gw.calls_path)
    return gw.call_tool(agent, tool, args)


def _cycle_call_count(cycle_id, calls_path):
    """Count prior ok calls for a cycle in a calls.jsonl file."""
    target = _calls_path(calls_path)
    if not os.path.exists(target):
        return 0
    count = 0
    with open(target, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if (entry.get("cycle_id") == cycle_id
                    and entry.get("status") == "ok"):
                count += 1
    return count
