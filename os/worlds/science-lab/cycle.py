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
