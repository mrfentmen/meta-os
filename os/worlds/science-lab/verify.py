"""Independent Verification (Section 6, tasks 51-56).

The independent-verifier re-executes an experiment from its archived
record alone and compares hashes. stdlib only.

Isolation rule (task 51): the verifier receives the plan and the
inputs, never the generator's reasoning or the original result.
verify() enforces this by refusing any bundle that carries generator
narrative.

Blind re-run rule (task 52): reexecute() rebuilds the result from the
archived inputs (input_hash, random_seed, parameters) inside a fresh
temporary directory. It never reads the record's output_hash; the
original hash is only touched later by compare().

Comparison rule (task 53): compare() states agree / disagree /
indeterminate with the diff in plain language.

Disagreement rule (task 54): handle_disagreement() caps the claim at
ladder.cap_for_experiment("mismatch") == 2 and opens a dispute record.
It never mutates the original record.

Rotation rule (task 55): check_rotation() raises when the verifying
agent is the same agent that produced the result.

Write-gate rule (task 56): gate_write() admits a result as "confirmed"
only on a verifier-agreed (agree / reproduced) verdict; everything
else enters as "unconfirmed" at its capped level, or not at all
(caller decides; the gate states the cap either way).
"""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone

try:
    from .ladder import cap_for_experiment
except ImportError:  # direct import with science-lab dir on sys.path
    from ladder import cap_for_experiment

# Keys that prove generator narrative leaked into the verifier's bundle.
FORBIDDEN_INPUT_KEYS = ("reasoning", "narrative")

# Record keys that may name the producing agent (checked by rotation).
PRODUCER_KEYS = (
    "agent",
    "produced_by",
    "producer",
    "producer_agent",
    "filed_by",
    "created_by",
)

AGREE = "agree"
DISAGREE = "disagree"
INDETERMINATE = "indeterminate"

VERDICTS = (AGREE, DISAGREE, INDETERMINATE)


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------
# Task 51: verifier isolation
# ------------------------------------------------------------------

def verify(plan, inputs, generator_narrative=None):
    """Build the verifier's bundle: plan + inputs only.

    Raises ValueError when generator narrative is present anywhere it
    should not be:
      * generator_narrative is not None (the caller tried to hand the
        verifier the generator's reasoning), or
      * inputs carries a 'reasoning' or 'narrative' key.

    Returns {"plan": plan, "inputs": dict(inputs)} -- a copy, so the
    verifier cannot mutate the caller's record. The bundle never
    contains the original output hash or outcome: the verifier gets
    the plan and the inputs, never the generator's reasoning or the
    result.
    """
    if generator_narrative is not None:
        raise ValueError(
            "isolation refused: generator narrative must never reach "
            "the verifier (got generator_narrative=%r)." % (generator_narrative,)
        )
    if not isinstance(inputs, dict):
        raise ValueError(
            "isolation refused: inputs must be a dict, got %s."
            % type(inputs).__name__
        )
    leaked = [k for k in FORBIDDEN_INPUT_KEYS if k in inputs]
    if leaked:
        raise ValueError(
            "isolation refused: inputs carry generator narrative key(s) %r; "
            "the verifier gets plan + inputs only." % (leaked,)
        )
    return {"plan": plan, "inputs": dict(inputs)}


# ------------------------------------------------------------------
# Task 52: blind re-run
# ------------------------------------------------------------------

def _rerun_payload(experiment_record):
    """The only data a blind re-run may see. Never includes output."""
    if not isinstance(experiment_record, dict):
        raise ValueError("reexecute requires an experiment record dict.")
    for key in ("input_hash", "random_seed", "parameters"):
        if experiment_record.get(key) is None and key != "parameters":
            raise ValueError(
                "blind re-run blocked: record %r lacks archived %r; "
                "the verifier re-executes from archived inputs alone."
                % (experiment_record.get("id"), key)
            )
    return {
        "input_hash": experiment_record.get("input_hash"),
        "random_seed": experiment_record.get("random_seed"),
        "parameters": experiment_record.get("parameters", {}),
    }


def deterministic_hash(payload):
    """sha256 over the canonical JSON of the archived-inputs payload."""
    return _sha256_hex(_canonical(payload))


def reexecute(experiment_record):
    """Re-execute an experiment record blindly in a clean temp dir.

    Writes only the archived inputs (input_hash, random_seed,
    parameters) into a fresh temporary directory, recomputes the
    result hash there deterministically, and returns it. The record's
    output_hash is never read here -- comparison happens in compare().

    Returns {"re_hash": str, "archived_inputs": dict, "logs": [str]}.
    The temp dir is removed before return; its path is logged, not kept.
    """
    payload = _rerun_payload(experiment_record)
    with tempfile.TemporaryDirectory(prefix="science-lab-verify-") as tmp:
        inputs_path = os.path.join(tmp, "archived_inputs.json")
        with open(inputs_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        re_hash = deterministic_hash(payload)
        output_path = os.path.join(tmp, "rerun_output.json")
        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"re_hash": re_hash, "payload": payload},
                                sort_keys=True) + "\n")
        logs = [
            "blind re-run in clean temp dir %s" % tmp,
            "archived inputs written to archived_inputs.json",
            "recomputed hash %s (output_hash never read)" % re_hash,
        ]
    return {"re_hash": re_hash, "archived_inputs": payload, "logs": logs}


# ------------------------------------------------------------------
# Task 53: comparison record
# ------------------------------------------------------------------

def _short(h):
    s = str(h)
    return s[:12] + "..." if len(s) > 12 else s


def compare(original_hash, re_hash, outcomes=None):
    """Compare the original hash against the blind re-run hash.

    outcomes is None or a (original_outcome, rerun_outcome) pair, or a
    {"original": ..., "rerun": ...} dict. Returns a record with
    verdict agree / disagree / indeterminate and the diff stated
    plainly.
    """
    orig_outcome = rerun_outcome = None
    if outcomes is not None:
        if isinstance(outcomes, dict):
            orig_outcome = outcomes.get("original")
            rerun_outcome = outcomes.get("rerun", outcomes.get("reproduced"))
        elif isinstance(outcomes, (list, tuple)) and len(outcomes) == 2:
            orig_outcome, rerun_outcome = outcomes
        else:
            raise ValueError(
                "outcomes must be None, a 2-tuple, or an "
                "{'original': .., 'rerun': ..} dict."
            )
    record = {
        "original_hash": original_hash,
        "re_hash": re_hash,
        "original_outcome": orig_outcome,
        "rerun_outcome": rerun_outcome,
        "compared_at": _utcnow(),
    }
    if original_hash is None or re_hash is None:
        missing = []
        if original_hash is None:
            missing.append("original")
        if re_hash is None:
            missing.append("re-run")
        record["verdict"] = INDETERMINATE
        record["diff"] = (
            "indeterminate: missing hash from %s; cannot agree or "
            "disagree without both hashes." % (" and ".join(missing),)
        )
        return record
    if str(original_hash) != str(re_hash):
        record["verdict"] = DISAGREE
        record["diff"] = (
            "disagree: original hash %s != re-run hash %s; the blind "
            "re-execution did not reproduce the archived result."
            % (_short(original_hash), _short(re_hash))
        )
        return record
    if (orig_outcome is not None and rerun_outcome is not None
            and str(orig_outcome) != str(rerun_outcome)):
        record["verdict"] = DISAGREE
        record["diff"] = (
            "disagree: hashes match (%s) but outcomes differ -- original "
            "%r vs re-run %r." % (_short(original_hash), orig_outcome,
                                  rerun_outcome)
        )
        return record
    record["verdict"] = AGREE
    if orig_outcome is not None and rerun_outcome is not None:
        record["diff"] = (
            "agree: hashes match (%s) and outcomes match (%r)."
            % (_short(original_hash), orig_outcome)
        )
    else:
        record["diff"] = (
            "agree: hashes match (%s); no outcomes stated, hash equality "
            "is the whole comparison." % (_short(original_hash),)
        )
    return record


# ------------------------------------------------------------------
# Task 54: disagreement path
# ------------------------------------------------------------------

def open_dispute(original_id, reason, dispute_id=None, recorded_at=None):
    """Open a dispute record. Never touches the original record.

    Takes only the original's id and the reason -- not the record
    itself -- so the original cannot be edited through this path.
    """
    if not original_id:
        raise ValueError("open_dispute requires an original_id.")
    if not reason:
        raise ValueError("open_dispute requires a reason.")
    return {
        "dispute_id": dispute_id or ("DISPUTE-%s" % str(original_id)),
        "original_id": str(original_id),
        "reason": str(reason),
        "recorded_at": recorded_at or _utcnow(),
    }


def handle_disagreement(original_record, comparison):
    """Cap the level and open a dispute for a disagree verdict.

    Returns {"capped_level": int, "dispute": dict}. The input record
    is not mutated: the cap is reported, and the caller files it on a
    NEW record, never by editing the original.
    """
    if not isinstance(comparison, dict) or comparison.get("verdict") != DISAGREE:
        raise ValueError(
            "handle_disagreement requires a comparison record with "
            "verdict 'disagree'."
        )
    if not isinstance(original_record, dict) or not original_record.get("id"):
        raise ValueError("handle_disagreement requires an original record with an id.")
    before = dict(original_record)
    capped = cap_for_experiment("mismatch")
    dispute = open_dispute(
        original_id=original_record["id"],
        reason=comparison.get("diff", "blind re-run disagreed"),
    )
    assert original_record == before, "original record must never be edited"
    return {"capped_level": capped, "dispute": dispute}


# ------------------------------------------------------------------
# Task 55: verifier rotation
# ------------------------------------------------------------------

def check_rotation(experiment_record, verifier_agent):
    """Enforce that the verifier is never the producing agent.

    Reads the record's agent fields (agent / produced_by / producer /
    filed_by / created_by). Raises ValueError when the verifier is the
    same agent, or when no producer can be determined, or when no
    verifier is named. Returns the verifier agent name on success.
    """
    if not isinstance(experiment_record, dict):
        raise ValueError("check_rotation requires an experiment record dict.")
    if not verifier_agent or not str(verifier_agent).strip():
        raise ValueError("check_rotation requires a named verifier agent.")
    producers = {
        str(experiment_record[k]).strip()
        for k in PRODUCER_KEYS
        if experiment_record.get(k) is not None
        and str(experiment_record[k]).strip()
    }
    if not producers:
        raise ValueError(
            "rotation refused: record %r names no producing agent "
            "(looked for %s); cannot verify independence."
            % (experiment_record.get("id"), list(PRODUCER_KEYS))
        )
    verifier = str(verifier_agent).strip()
    if verifier in producers:
        raise ValueError(
            "rotation refused: verifier %r is the producing agent; "
            "the verifying agent is never the agent that produced "
            "the result." % (verifier,)
        )
    return verifier


# ------------------------------------------------------------------
# Task 56: knowledge-repository write gate
# ------------------------------------------------------------------

def _comparison_verdict(verification):
    """Accept a comparison record, a status string, or a record with
    verification_status; return agree / disagree / indeterminate."""
    if isinstance(verification, dict):
        for key in ("verdict", "verification_status", "status"):
            val = verification.get(key)
            if val is None:
                continue
            text = str(val).strip().lower()
            if text in (AGREE, "reproduced", "confirmed"):
                return AGREE
            if text in (DISAGREE, "mismatch"):
                return DISAGREE
            if text in (INDETERMINATE, "unverified", "unconfirmed"):
                return INDETERMINATE
        raise ValueError(
            "gate_write: verification dict carries no usable verdict "
            "(looked for verdict/verification_status/status)."
        )
    if isinstance(verification, str):
        text = verification.strip().lower()
        if text in (AGREE, "reproduced", "confirmed"):
            return AGREE
        if text in (DISAGREE, "mismatch"):
            return DISAGREE
        return INDETERMINATE
    raise ValueError("gate_write: verification must be a dict or a string.")


def gate_write(result, verification):
    """Decide a repository write: confirmed vs unconfirmed.

    Only a verifier-agreed (agree / reproduced) verdict enters as
    "confirmed". Any other verdict enters as "unconfirmed" at its
    capped level (unverified/mismatch cap 2 via the ladder). Returns
    {"decision": ..., "level": int, "reason": str}. Never mutates
    the input result.
    """
    if not isinstance(result, dict):
        raise ValueError("gate_write requires a result dict.")
    verdict = _comparison_verdict(verification)
    try:
        claimed = int(result.get("evidence_level", result.get("level", 0)))
    except (TypeError, ValueError):
        claimed = 0
    if verdict == AGREE:
        cap = cap_for_experiment("reproduced")
        return {
            "decision": "confirmed",
            "level": min(claimed, cap),
            "reason": "verifier agreed (blind re-run reproduced the hash).",
        }
    cap = cap_for_experiment("unverified")
    return {
        "decision": "unconfirmed",
        "level": min(claimed, cap),
        "reason": (
            "verifier verdict %r is not agreement; enters as unconfirmed "
            "at capped level %d." % (verdict, min(claimed, cap))
        ),
    }


__all__ = [
    "FORBIDDEN_INPUT_KEYS",
    "PRODUCER_KEYS",
    "AGREE",
    "DISAGREE",
    "INDETERMINATE",
    "VERDICTS",
    "verify",
    "deterministic_hash",
    "reexecute",
    "compare",
    "open_dispute",
    "handle_disagreement",
    "check_rotation",
    "gate_write",
]
