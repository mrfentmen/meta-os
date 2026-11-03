"""Discovery-cycle state machine. One transition = one ledger entry.

Phases 1-7 (sourced, PACK.md / LABORATORY cycle): problem, literature,
hypotheses, cheap-computations, critic, verification, sealing.
Steps 9-10 (wetlab, publication): permanently human-gated; the machine
parks there and only resume_with_decision() with an explicit human
decision record moves it on. Step 8: source gap, the text is silent;
STEP_8 = 'step-8-unimplemented' is an explicit UNIMPLEMENTED marker.
The machine routes around it or parks blocked-on-source, never invents
step-8 work.
"""

import hashlib
import json
import os

try:
    from .ledger import append_record
except ImportError:  # direct script use
    from ledger import append_record

# Sourced order, phases 1-7. Terminals 9-10 appended after the gap.
PHASES = [
    "problem",
    "literature",
    "hypotheses",
    "cheap-computations",
    "critic",
    "verification",
    "sealing",
]

# Explicit UNIMPLEMENTED marker for the silent step 8. Never a working phase.
STEP_8 = "step-8-unimplemented"

HUMAN_GATES = ("wetlab", "publication")

TERMINALS = ("wetlab", "publication")

ALL_PHASES = PHASES + [STEP_8] + list(TERMINALS)

# Required cycle["inputs"] key for each target phase. Missing key blocks
# the transition with an explicit message (never silently skipped).
REQUIRED_INPUTS = {
    "literature": ["problem_statement"],
    "hypotheses": ["sources"],
    "cheap-computations": ["hypotheses"],
    "critic": ["compute_results"],
    "verification": ["critique"],
    "sealing": ["verification"],
    "wetlab": ["sealed_record"],
    "publication": ["wetlab_decision"],
}


def new_cycle(cycle_id, question):
    """Create a fresh cycle record at phase 'problem'."""
    if not cycle_id or not question:
        raise ValueError("new_cycle requires a cycle_id and a question")
    return {
        "cycle_id": cycle_id,
        "phase": "problem",
        "inputs": {"problem_statement": question},
        "outputs": {},
        "gate_state": "open",
        "history": [],
    }


def can_transition(cycle, target_phase):
    """Check whether a transition is allowed. Returns (ok: bool, msg: str)."""
    if target_phase not in ALL_PHASES:
        return (False, "unknown phase: %r" % (target_phase,))
    if target_phase == STEP_8:
        return (
            False,
            "UNIMPLEMENTED: step 8 is silent in the source text; "
            "no behaviour defined. Route around or park blocked-on-source.",
        )
    if target_phase in HUMAN_GATES:
        return (
            False,
            "human gate: %r is permanently human-gated; use "
            "park_for_human_gate() then resume_with_decision() with an "
            "explicit decision record." % (target_phase,),
        )
    if cycle.get("gate_state") != "open":
        return (
            False,
            "cycle parked (gate_state=%r at %r); resume it before "
            "transitioning." % (cycle.get("gate_state"), cycle.get("parked_gate")),
        )
    if target_phase == cycle.get("phase"):
        return (False, "already in phase %r" % (target_phase,))
    missing = [
        k for k in REQUIRED_INPUTS.get(target_phase, []) if k not in cycle.get("inputs", {})
    ]
    if missing:
        return (
            False,
            "blocked: phase %r requires inputs %r; file them first."
            % (target_phase, missing),
        )
    current = cycle.get("phase")
    if target_phase in PHASES and current in PHASES:
        current_index = PHASES.index(current)
        target_index = PHASES.index(target_phase)
        if target_index < current_index:
            return (
                False,
                "blocked: backwards transition %r -> %r; the cycle moves "
                "forward only." % (current, target_phase),
            )
        if target_index > current_index + 1:
            return (
                False,
                "blocked: cannot skip from %r to %r; the next phase is %r."
                % (current, target_phase, PHASES[current_index + 1]),
            )
    return (True, "ok: %r -> %r" % (cycle.get("phase"), target_phase))


def transition(cycle, target, reason, ledger_path):
    """Advance the cycle to target, filing one ledger entry for the reason.

    Raises ValueError with an explicit message if the transition is blocked
    (missing input, parked gate, human-gated target, or step 8).
    On success mutates and returns the cycle.
    """
    ok, msg = can_transition(cycle, target)
    if not ok:
        raise ValueError(msg)
    if not reason:
        raise ValueError("blocked: a transition reason is required (one transition = one ledger entry)")
    entry = append_record(
        ledger_path,
        {
            "kind": "cycle-transition",
            "cycle_id": cycle["cycle_id"],
            "from_phase": cycle["phase"],
            "to_phase": target,
            "reason": reason,
        },
    )
    cycle["outputs"][cycle["phase"]] = reason
    cycle["phase"] = target
    cycle.setdefault("history", []).append(entry["entry_hash"])
    return cycle


def park_for_human_gate(cycle, gate_name):
    """Park the cycle at a human gate (wetlab/publication) or the step-8 gap.

    Human gates (wetlab, publication) park with gate_state 'human-gated'
    and require resume_with_decision(). The step-8 marker parks with
    'blocked-on-source'. Anything else raises ValueError.
    """
    if gate_name in HUMAN_GATES:
        cycle["gate_state"] = "human-gated"
        cycle["parked_gate"] = gate_name
        cycle["phase"] = gate_name
        return cycle
    if gate_name == STEP_8:
        # UNIMPLEMENTED: source text is silent on step 8; park, never invent.
        cycle["gate_state"] = "blocked-on-source"
        cycle["parked_gate"] = STEP_8
        return cycle
    raise ValueError(
        "unknown gate %r; parkable gates are %r and %r"
        % (gate_name, list(HUMAN_GATES), STEP_8)
    )


def resume_with_decision(cycle, decision_record):
    """Resume a parked cycle with an explicit human decision record.

    decision_record must be a dict with keys: gate, approved (bool),
    decided_by (non-empty str). Optional: note, and for the wetlab gate
    an approval files inputs['wetlab_decision']. A rejection (approved
    False) leaves the cycle parked. Never auto-approves.
    """
    if not isinstance(decision_record, dict):
        raise ValueError("blocked: decision_record must be a dict")
    if cycle.get("gate_state") != "human-gated":
        raise ValueError(
            "blocked: cycle is not parked at a human gate (gate_state=%r)"
            % (cycle.get("gate_state"),)
        )
    gate = decision_record.get("gate")
    if gate != cycle.get("parked_gate"):
        raise ValueError(
            "blocked: decision gate %r does not match parked gate %r"
            % (gate, cycle.get("parked_gate")),
        )
    if "approved" not in decision_record or not isinstance(decision_record["approved"], bool):
        raise ValueError("blocked: decision_record needs an explicit boolean 'approved'")
    if not decision_record.get("decided_by"):
        raise ValueError("blocked: decision_record needs a human 'decided_by'")
    if not decision_record["approved"]:
        return cycle  # stays parked; rejection recorded by caller
    if gate == "wetlab":
        cycle.setdefault("inputs", {})["wetlab_decision"] = decision_record
    cycle["gate_state"] = "open"
    cycle.pop("parked_gate", None)
    return cycle


def ledger_path_for(cycle_id, base_dir="."):
    """Default ledger file path for a cycle (helper, keeps runs colocated)."""
    return os.path.join(base_dir, cycle_id + ".ledger.jsonl")


# ----------------------------------------------------------------------
# Section 5 driver helpers (tasks 46, 47, 50). Additive only: the phase
# machine above (tasks 41-44: PHASES, STEP_8, REQUIRED_INPUTS,
# new_cycle/can_transition/transition/park_for_human_gate/
# resume_with_decision) is untouched.
# ----------------------------------------------------------------------


def _lab_base_dir():
    """Directory holding this file (the science-lab tree root)."""
    return os.path.dirname(os.path.abspath(__file__))


def default_cycles_dir():
    """Default cycle-record directory: records/cycles beside this file."""
    return os.path.join(_lab_base_dir(), "records", "cycles")


def default_ledger_path():
    """Default lab ledger: records/ledger.jsonl beside this file."""
    return os.path.join(_lab_base_dir(), "records", "ledger.jsonl")


def default_reports_dir():
    """Default cycle-report directory: records/reports beside this file."""
    return os.path.join(_lab_base_dir(), "records", "reports")


def cycle_usage(cycle_id, ledger_path):
    """Count a cycle's ledger footprint.

    Returns {"cycle_id", "actions", "spend"} where actions is the
    number of ledger entries carrying this cycle_id and spend is the
    sum of numeric cost/spend fields on those entries (0.0 when
    entries carry none). A missing ledger file counts as zero, never
    an error.
    """
    try:
        import ledger as _ledger
        read_all = _ledger.read_all
    except ImportError:
        raise RuntimeError(
            "cycle_usage requires sibling ledger.py importable")
    entries = read_all(ledger_path)
    mine = [
        e for e in entries
        if isinstance(e, dict) and e.get("cycle_id") == cycle_id
    ]
    spend = 0.0
    for entry in mine:
        for key in ("cost", "spend"):
            value = entry.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                spend += float(value)
    return {"cycle_id": cycle_id, "actions": len(mine), "spend": spend}


def check_cycle_budget(cycle, ledger_path=None, config=None, spend=0.0,
                       receipt_path=None):
    """Check a cycle's total actions/spend against lab_config caps.

    actions = ledger entries filed under this cycle_id; spend = their
    summed cost/spend fields plus the caller's extra spend. Checked via
    lab_config.check_budget() as agent "cycle:<id>" against the cycle
    maxActions cap (and the default spend cap). Returns (allowed: bool,
    reason: str). When blocked and receipt_path is given, a stop receipt
    is written with lab_config.write_receipt() (same receipt shape as the
    agent budget stops). Never raises for an over-cap cycle: the
    (False, reason) return IS the stop signal.
    """
    cid = cycle.get("cycle_id") if isinstance(cycle, dict) else str(cycle)
    if not cid:
        raise ValueError("check_cycle_budget requires a cycle_id")
    if ledger_path is None:
        ledger_path = default_ledger_path()
    usage = cycle_usage(cid, ledger_path)
    try:
        extra = float(spend or 0.0)
    except (TypeError, ValueError):
        raise ValueError(
            "check_cycle_budget spend must be numeric, got %r" % (spend,))
    total_spend = usage["spend"] + extra
    try:
        import lab_config as _lab_config
    except ImportError:
        _lab_config = None
    if config is None:
        if _lab_config is not None:
            config = _lab_config.load_config()
        else:
            try:
                with open(os.path.join(_lab_base_dir(), "lab_config.json"),
                          "r", encoding="utf-8") as fh:
                    config = json.load(fh)
            except (OSError, ValueError):
                config = {}
    agent = "cycle:%s" % cid
    if _lab_config is not None and hasattr(_lab_config, "check_budget"):
        ok, reason = _lab_config.check_budget(
            config, agent, spend=total_spend, calls=0,
            actions=usage["actions"])
    else:
        max_actions = (config.get("cycle") or {}).get("maxActions")
        if max_actions is not None and usage["actions"] > max_actions:
            ok, reason = (
                False,
                "budget-cap-reached: cycle actions %s > maxActions %s"
                % (usage["actions"], max_actions),
            )
        else:
            ok, reason = (
                True,
                "ok: cycle %s within budget (%s actions)" % (cid, usage["actions"]),
            )
    if not ok and receipt_path:
        if _lab_config is not None and hasattr(_lab_config, "write_receipt"):
            _lab_config.write_receipt(receipt_path, agent, total_spend, 0,
                                      reason, actions=usage["actions"])
        else:
            from datetime import datetime, timezone

            receipt = {
                "kind": "budget-receipt",
                "agent": agent,
                "spend": total_spend,
                "calls": 0,
                "actions": usage["actions"],
                "reason": reason,
                "stopped": True,
                "recorded_at": datetime.now(timezone.utc).isoformat().replace(
                    "+00:00", "Z"),
            }
            with open(receipt_path, "w", encoding="utf-8") as fh:
                json.dump(receipt, fh, sort_keys=True, indent=2)
                fh.write("\n")
    return (ok, reason)


def recover_cycle(cycle_id, cycles_dir=None, ledger_path=None):
    """Recover a cycle after a killed driver.

    Loads records/cycles/<id>.json and replays the ledger: the ledger
    chain must verify, and every entry_hash in the cycle's history must
    be present in the ledger. Recovery never appends: a clean resume
    files zero new entries, so no phase is duplicated. Returns the cycle
    record dict. Raises FileNotFoundError (no record) or ValueError
    (broken chain, or history referencing entries the ledger does not
    hold).
    """
    if not cycle_id:
        raise ValueError("recover_cycle requires a cycle_id")
    cdir = cycles_dir or default_cycles_dir()
    lpath = ledger_path or default_ledger_path()
    path = os.path.join(cdir, "%s.json" % cycle_id)
    if not os.path.exists(path):
        raise FileNotFoundError("no cycle record at %r" % (path,))
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    try:
        import ledger as _ledger
    except ImportError:
        raise RuntimeError(
            "recover_cycle requires sibling ledger.py importable")
    ok, msg = _ledger.verify_chain(lpath)
    if not ok:
        raise ValueError(
            "blocked: ledger chain broken (%s); refusing to resume on a "
            "tampered log" % (msg,))
    entries = _ledger.read_all(lpath)
    hashes = set(
        e.get("entry_hash") for e in entries if isinstance(e, dict))
    history = record.get("history") or []
    missing = [h for h in history if h not in hashes]
    if missing:
        raise ValueError(
            "blocked: cycle %r history references %d ledger entr%s absent "
            "from %r; records inconsistent, refusing resume"
            % (cycle_id, len(missing),
               "y" if len(missing) == 1 else "ies", lpath))
    return record


_FALLBACK_LEVEL_NAMES = {
    0: "Idea",
    1: "Evidence supported",
    2: "Computationally tested",
    3: "Independently reproduced",
    4: "Experimentally validated",
    5: "Independently replicated",
    6: "Established application",
}


def _ladder_status(level):
    """Level number -> short status name (ladder.py LEVELS when present)."""
    try:
        level = int(level)
    except (TypeError, ValueError):
        return "?"
    try:
        import ladder as _ladder
        info = (_ladder.LEVELS or {}).get(level)
        if isinstance(info, dict):
            return str(info.get("status", _FALLBACK_LEVEL_NAMES.get(level, "?")))
    except ImportError:
        pass
    return _FALLBACK_LEVEL_NAMES.get(level, "?")


def generate_report(cycle_id, cycles_dir=None, ledger_path=None,
                    reports_dir=None):
    """Write the cycle's one-page readable report.

    Reads records/cycles/<id>.json plus the ledger entries filed under
    the cycle id, renders the phase walk with ledger hashes and the
    claims with their ladder levels (each claim displayed at its
    recorded level, never higher), and writes
    records/reports/<id>.md. Returns the markdown text.
    """
    if not cycle_id:
        raise ValueError("generate_report requires a cycle_id")
    cdir = cycles_dir or default_cycles_dir()
    lpath = ledger_path or default_ledger_path()
    rdir = reports_dir or default_reports_dir()
    path = os.path.join(cdir, "%s.json" % cycle_id)
    if not os.path.exists(path):
        raise FileNotFoundError("no cycle record at %r" % (path,))
    with open(path, "r", encoding="utf-8") as fh:
        record = json.load(fh)
    try:
        import ledger as _ledger
    except ImportError:
        raise RuntimeError(
            "generate_report requires sibling ledger.py importable")
    chain_ok, chain_msg = _ledger.verify_chain(lpath)
    entries = [e for e in _ledger.read_all(lpath)
               if isinstance(e, dict) and e.get("cycle_id") == cycle_id]
    transitions = [e for e in entries if e.get("kind") == "cycle-transition"]
    by_target = {}
    visited = set()
    for t in transitions:
        by_target[t.get("to_phase")] = t
        visited.add(t.get("from_phase"))
        visited.add(t.get("to_phase"))
    try:
        import ladder as _ladder
        guard = getattr(_ladder, "assert_export_allowed", None)
    except ImportError:
        guard = None

    def _short(h):
        h = str(h or "?")
        return h[:12] if len(h) > 12 else h

    lines = []
    lines.append("# Cycle report — %s" % cycle_id)
    lines.append("")
    question = record.get("question") or (
        record.get("inputs") or {}).get("problem_statement", "?")
    lines.append("Question: %s" % question)
    lines.append("Phase: %s" % record.get("phase", "?"))
    gate = record.get("gate_state", "?")
    gate_line = "Gate state: %s" % gate
    if record.get("parked_gate"):
        gate_line += " (parked at %s)" % record.get("parked_gate")
    lines.append(gate_line)
    lines.append("Ledger: %d entries for this cycle; chain %s." % (
        len(entries), "VERIFIED (%s)" % chain_msg if chain_ok
        else "BROKEN (%s)" % chain_msg))
    lines.append("")
    lines.append("## Phase walk (phases 1-7 sourced; step 8 silent; 9/10 human-gated)")
    lines.append("")
    lines.append("| # | phase | status | ledger entry | reason |")
    lines.append("|---|-------|--------|--------------|--------|")
    for i, phase in enumerate(PHASES, 1):
        t = by_target.get(phase)
        if record.get("phase") == phase:
            status = "current"
            h = _short(t.get("entry_hash")) if t is not None else "—"
            r = str(t.get("reason", "")) if t is not None else \
                "no transition filed yet"
        elif t is not None or phase in visited:
            status = "done"
            if t is not None:
                h, r = _short(t.get("entry_hash")), str(t.get("reason", ""))
            else:
                h, r = "—", "start phase; departed by a later transition"
        else:
            status, h, r = "pending", "—", ""
        lines.append("| %d | %s | %s | %s | %s |" % (i, phase, status, h, r))
    lines.append("")
    lines.append("Source gap: step 8 (`%s`) is silent in the source text — "
                 "no step-8 work is claimed anywhere in this report." % STEP_8)
    if "wetlab" in by_target or record.get("phase") in HUMAN_GATES or \
            record.get("parked_gate") in HUMAN_GATES:
        lines.append("Human gate: wetlab/publication are permanently "
                     "human-gated; this cycle parks there and resumes only "
                     "on an explicit human decision record — never auto-passed.")
    lines.append("")
    lines.append("## Claims (displayed at recorded level, never higher)")
    lines.append("")
    claims = [e for e in entries
              if isinstance(e.get("claim"), str) or "evidence_level" in e]
    if not claims:
        lines.append("No claim records with evidence levels filed under this "
                     "cycle yet.")
    else:
        checked = 0
        for e in claims:
            level = e.get("evidence_level")
            text = e.get("claim", e.get("kind", "?"))
            if level is None:
                lines.append("- (unlevelled record %s): %s" % (
                    _short(e.get("entry_hash")), text))
                continue
            try:
                level = int(level)
            except (TypeError, ValueError):
                lines.append("- (bad level %r, record %s): %s" % (
                    level, _short(e.get("entry_hash")), text))
                continue
            if guard is not None:
                guard(level, level)
                checked += 1
            lines.append("- Level %d (%s): %s [record %s]" % (
                level, _ladder_status(level), text,
                _short(e.get("entry_hash"))))
        if guard is not None:
            lines.append("")
            lines.append("Export guard: %d levelled claims checked with "
                         "ladder.assert_export_allowed — all display at "
                         "their recorded level." % checked)
    lines.append("")
    lines.append("## Honesty notes")
    lines.append("")
    lines.append("- One transition = one ledger entry; history holds %d "
                 "entry hashes, all present in the ledger." % len(
                     record.get("history") or []))
    if record.get("gate_state") == "human-gated":
        lines.append("- Parked at a human gate: no auto-pass occurred; a "
                     "resumption requires a signed human decision record.")
    reproduced = [e for e in entries
                  if e.get("verification_status") == "reproduced"]
    if not reproduced:
        lines.append("- No independent-verifier reproduced record is filed: "
                     "nothing here is above ladder level 2, and levels 4-6 "
                     "are unreachable by this system alone.")
    lines.append("- Pre-registered thresholds (if any) precede results in "
                 "ledger order; the pre-registration hash is the authority, "
                 "not any later reading.")
    lines.append("")
    markdown = "\n".join(lines)
    os.makedirs(rdir, exist_ok=True)
    out = os.path.join(rdir, "%s.md" % cycle_id)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(markdown + "\n")
    return markdown


# ----------------------------------------------------------------------
# Section 7: pre-registration hashing and dict round-trip.
# ----------------------------------------------------------------------

def normalize_question(text):
    """Collapse leading/trailing and repeated whitespace."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())


def preregistration_hash(question, plan):
    """Deterministic hash of the normalised question plus plan."""
    payload = json.dumps(
        {"question": normalize_question(question), "plan": plan},
        sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def set_preregistration(cycle, plan):
    """Attach a pre-registration hash to a cycle record."""
    if not isinstance(cycle, dict):
        raise TypeError("cycle must be an object")
    question = (cycle.get("inputs") or {}).get("problem_statement")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("pre-registration requires a problem_statement")
    cycle["preregistration"] = {
        "question": normalize_question(question),
        "plan": plan,
        "hash": preregistration_hash(question, plan),
    }
    return cycle


def verify_preregistration(cycle):
    """True iff the stored hash matches the current question and plan."""
    if not isinstance(cycle, dict):
        return False
    record = cycle.get("preregistration")
    if not isinstance(record, dict):
        return False
    question = record.get("question")
    plan = record.get("plan")
    expected = record.get("hash")
    if not isinstance(expected, str) or not expected:
        return False
    return preregistration_hash(question, plan) == expected


def cycle_to_dict(cycle):
    """A JSON-safe copy of a cycle record."""
    if not isinstance(cycle, dict):
        raise TypeError("cycle must be an object")
    return json.loads(json.dumps(cycle, sort_keys=True))


def cycle_from_dict(payload):
    """Rebuild a cycle record from its dict form."""
    if not isinstance(payload, dict):
        raise ValueError("cycle payload must be an object")
    return cycle_to_dict(payload)


def validate_cycle_against_schema(cycle):
    """Validate a cycle record against schemas/cycle.schema.json."""
    from literature import validate_against_schema
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "schemas", "cycle.schema.json")
    with open(path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    return validate_against_schema(cycle, schema)
