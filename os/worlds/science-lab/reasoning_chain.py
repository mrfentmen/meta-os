"""Scientific Reasoning chain record (Section 3: tasks 27, 28).

Task 27: the reasoning chain record brief -> hypotheses ->
decomposition -> pre-registration -> critique, hash-linked in order
via sha256. Task 28: the gate -- a cycle cannot enter the
Computational Lab without a complete reasoning chain.

Order rule (the load-bearing discipline): the pre-registration is
hashed into the ledger BEFORE any result record exists. A result
that predates the pre-registration breaks the gate loudly, never
silently.

Honesty rules enforced here:

- The paper's own reported fit statistics are NEVER hardcoded here.
  Where a chain needs them it carries TO_BE_READ_AT_RUN (the same
  marker as literature.TO_BE_READ_AT_RUN), resolved only from the
  source at gate run time (SCIENCE_LAB_W2_SLICE1.md section 4).
- A pre-registration threshold MUST be concrete (a number plus a
  sample rule), registered before results exist. It may cite the prep
  run as motivation, never as the paper's figure.
- Reasoning alone earns no evidence level: a complete chain supports
  at most ladder level 1 (existing sources back the assumptions);
  computation and independent re-execution move it further.

Sibling layers (imported, never reimplemented): literature (briefs),
ladder (levels), ledger (append-only log), cycle (phase gates).
reasoning.py (tasks 21-26: hypothesis, decomposition, preregistration
and critic jobs) is owned by a sibling lane: it is imported
defensively -- while it is missing, any use of it raises
NotImplementedError carrying UNIMPLEMENTED.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

# ------------------------------------------------------------------
# Sibling imports. literature / ladder / ledger / cycle are landed
# layers: import them (package form first, direct-script form as
# fallback). reasoning.py (tasks 21-26) belongs to a sibling lane:
# import it defensively; while missing, `reasoning.<job>` raises
# NotImplementedError carrying UNIMPLEMENTED.
# ------------------------------------------------------------------

try:
    from .ledger import append_record as _ledger_append
    from .ledger import read_all as _ledger_read_all
except ImportError:  # direct script use
    try:
        from ledger import append_record as _ledger_append
        from ledger import read_all as _ledger_read_all
    except ImportError:  # ledger sibling missing: filing degrades loudly
        _ledger_append = None
        _ledger_read_all = None

try:
    from . import literature as _literature_mod
except ImportError:
    try:
        import literature as _literature_mod
    except ImportError:
        _literature_mod = None

try:
    from . import ladder as _ladder_mod
except ImportError:
    try:
        import ladder as _ladder_mod
    except ImportError:
        _ladder_mod = None

try:
    from . import cycle as _cycle_mod
except ImportError:
    try:
        import cycle as _cycle_mod
    except ImportError:
        _cycle_mod = None

try:
    from . import reasoning as _reasoning_mod
except ImportError:  # sibling lane file not yet landed / direct use
    try:
        import reasoning as _reasoning_mod
    except ImportError:
        _reasoning_mod = None


#: Marker for work owned by a lane whose file has not landed.
UNIMPLEMENTED = "UNIMPLEMENTED"

#: Marker for values that must be read from the source at run time.
#: Same value as literature.TO_BE_READ_AT_RUN; defined locally so
#: this module keeps working if literature is unavailable.
if _literature_mod is not None:
    TO_BE_READ_AT_RUN = _literature_mod.TO_BE_READ_AT_RUN
else:  # pragma: no cover - literature.py is landed; fallback only
    TO_BE_READ_AT_RUN = "TO_BE_READ_AT_RUN"

#: Ledger entry kinds that count as "a result exists" for the
#: prereg-before-result order check. Matched as substrings of the
#: entry's kind (lowercased), so future computational-lab kinds such
#: as "experiment-result" or "compute-result" are caught without a
#: registry update. Registration / filing kinds ("preregistration-
#: filed", "reasoning-chain-filed", "research-intelligence-*") carry
#: none of these substrings.
_RESULT_KIND_HINTS = ("result", "experiment", "comput")


if _reasoning_mod is None:
    class _ReasoningStub(object):
        """Fallback while sibling-owned reasoning.py has not landed.

        Any attribute access raises NotImplementedError carrying
        UNIMPLEMENTED, never a fabricated job output.
        """

        def __getattr__(self, name):
            raise NotImplementedError(
                "%s: reasoning.%s is unavailable: tasks 21-26 "
                "(hypothesis, decomposition, preregistration, critic "
                "jobs) live in sibling-owned reasoning.py, which has "
                "not landed." % (UNIMPLEMENTED, name)
            )

    reasoning = _ReasoningStub()
else:
    reasoning = _reasoning_mod


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash_obj(obj):
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _level1_status():
    if _ladder_mod is not None:
        try:
            return _ladder_mod.LEVELS[1]["status"]
        except (KeyError, TypeError, IndexError):
            pass
    return "Evidence supported"


def unresolved_markers(obj, _path="$"):
    """Paths in obj whose value is TO_BE_READ_AT_RUN.

    The paper figure marker must NOT block the gate (target numbers
    are pulled at run time), but it must stay visible. Returns a
    list of dotted paths; [] means fully resolved.
    """
    found = []
    if obj == TO_BE_READ_AT_RUN:
        return [_path]
    if isinstance(obj, dict):
        for key in sorted(obj):
            found.extend(unresolved_markers(obj[key], "%s.%s" % (_path, key)))
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            found.extend(unresolved_markers(item, "%s[%d]" % (_path, i)))
    return found


def build_chain(brief, hypotheses, decomposition, prereg_hash, critique):
    """Build the hash-linked reasoning chain (Task 27).

    brief: sourced-brief dict (literature.assemble_brief output).
    hypotheses: list of hypothesis dicts, each with a non-empty id.
    decomposition: dict of smallest checkable computations (or None
      when not yet filed).
    prereg_hash: ledger entry hash of the pre-registration (or None
      when not yet filed). Must be a non-empty string when given.
    critique: scientific-critic record dict (or None when pending).

    Missing stages are recorded as null hashes, never invented: the
    gate (gate_to_computational) refuses an incomplete chain. Links
    cover the stages present, in order
    brief -> hypotheses -> decomposition -> preregistration ->
    critique, each link = sha256(prev_link + stage_hash) starting
    from "GENESIS" (the ledger genesis marker).

    Where the sibling reasoning.py has landed, each hypothesis is
    additionally passed through its validate_hypothesis(); where it
    has not landed, that check is skipped (documented in the
    returned record), never faked.
    """
    if not isinstance(brief, dict) or not brief:
        raise ValueError("build_chain requires a brief dict, got %r" % (brief,))
    if hypotheses is None:
        hypotheses = []
    if not isinstance(hypotheses, (list, tuple)):
        raise TypeError(
            "hypotheses must be a list, got %r" % type(hypotheses).__name__
        )
    if decomposition is not None and not isinstance(decomposition, dict):
        raise TypeError(
            "decomposition must be a dict or None, got %r"
            % type(decomposition).__name__
        )
    if prereg_hash is not None and (
        not isinstance(prereg_hash, str) or not prereg_hash.strip()
    ):
        raise ValueError("prereg_hash must be a non-empty string or None")
    if critique is not None and not isinstance(critique, dict):
        raise TypeError(
            "critique must be a dict or None, got %r" % type(critique).__name__
        )

    hypotheses = list(hypotheses)
    hypotheses_ids = []
    for i, hyp in enumerate(hypotheses):
        if not isinstance(hyp, dict) or not hyp.get("id"):
            raise ValueError(
                "hypothesis at index %d carries no id; a chain cannot "
                "reference an unnamed hypothesis" % (i,)
            )
        hypotheses_ids.append(str(hyp["id"]))

    validated_by = None
    if _reasoning_mod is not None:
        validator = None
        validator_name = None
        for candidate in (
            "validate_hypothesis",
            "assert_valid_hypothesis",
            "validate",
        ):
            maybe = getattr(_reasoning_mod, candidate, None)
            if callable(maybe):
                validator = maybe
                validator_name = "reasoning." + candidate
                break
        if validator is not None:
            for hyp in hypotheses:
                validator(hyp)
            validated_by = validator_name
        else:
            validated_by = (
                "local id check only (sibling reasoning.py exposes no "
                "hypothesis validator entry point; hypothesis content "
                "rules stay sibling-owned)"
            )
    if validated_by is None:
        validated_by = (
            "local id check only (sibling reasoning.py not present; any "
            "reasoning.<job> use raises UNIMPLEMENTED)"
        )

    brief_hash = _hash_obj(brief)
    hypotheses_hash = _hash_obj(hypotheses) if hypotheses else None
    decomposition_hash = _hash_obj(decomposition) if decomposition else None
    critique_id = None
    critique_hash = None
    if critique:
        critique_id = critique.get("id")
        critique_id = str(critique_id) if critique_id else None
        critique_hash = _hash_obj(critique)

    stages = (
        ("brief", brief_hash),
        ("hypotheses", hypotheses_hash),
        ("decomposition", decomposition_hash),
        ("preregistration", prereg_hash.strip() if prereg_hash else None),
        ("critique", critique_hash),
    )
    field_of = {
        "brief": "brief_hash",
        "hypotheses": "hypotheses_hash",
        "decomposition": "decomposition_hash",
        "preregistration": "prereg_hash",
        "critique": "critique_hash",
    }
    links = []
    prev = "GENESIS"
    for stage, stage_hash in stages:
        if stage_hash is None:
            continue
        link = hashlib.sha256((prev + stage_hash).encode("utf-8")).hexdigest()
        links.append(
            {"stage": stage, "hash": stage_hash, "prev": prev, "link": link}
        )
        prev = link

    return {
        "kind": "reasoning-chain",
        "brief_hash": brief_hash,
        "hypotheses_ids": hypotheses_ids,
        "hypotheses_hash": hypotheses_hash,
        "decomposition_hash": decomposition_hash,
        "prereg_hash": prereg_hash.strip() if prereg_hash else None,
        "critique_id": critique_id,
        "critique_hash": critique_hash,
        "hypotheses_validated_by": validated_by,
        "links": links,
        "link_fields": field_of,
        "chain_hash": links[-1]["link"] if links else None,
        "evidence_note": (
            "Reasoning alone earns no evidence level; a complete chain "
            "supports at most ladder level 1 (existing sources back the "
            "assumptions). Computation and independent re-execution move "
            "it further."
        ),
        "recorded_at": _utcnow(),
    }


def verify_chain_links(chain):
    """Verify a chain's hash linkage. Returns True/False, never raises
    for a bad chain (False for a non-dict too)."""
    if not isinstance(chain, dict):
        return False
    links = chain.get("links")
    if not isinstance(links, list) or not links:
        return False
    field_of = chain.get("link_fields") or {}
    prev = "GENESIS"
    for entry in links:
        if not isinstance(entry, dict):
            return False
        stage = entry.get("stage")
        stage_hash = entry.get("hash")
        link = entry.get("link")
        if not stage or not stage_hash or not link:
            return False
        if entry.get("prev") != prev:
            return False
        field = field_of.get(stage)
        if field and chain.get(field) != stage_hash:
            return False
        expect = hashlib.sha256((prev + stage_hash).encode("utf-8")).hexdigest()
        if link != expect:
            return False
        prev = link
    if chain.get("chain_hash") != links[-1]["link"]:
        return False
    return True


def _find_prereg_index(entries, prereg_hash):
    """Ledger line index (0-based) of the pre-registration entry.

    Matches the ledger entry_hash, or any string field carrying the
    hash. Returns None when the hash is filed nowhere in this ledger.
    """
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        if entry.get("entry_hash") == prereg_hash:
            return i
        for value in entry.values():
            if isinstance(value, str) and value == prereg_hash:
                return i
    return None


def _result_indices(entries):
    """0-based indices of entries that count as result records."""
    hits = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        kind = str(entry.get("kind", "")).lower()
        if any(hint in kind for hint in _RESULT_KIND_HINTS):
            hits.append(i)
    return hits


def gate_to_computational(chain, ledger_path=None):
    """Gate a cycle's entry into the Computational Lab (Task 28).

    Requires the complete chain -- brief + hypotheses +
    decomposition + pre-registration BEFORE result + critique --
    with verifying hash links. A missing critique blocks with an
    explicit message, as does a missing pre-registration.

    Pre-registration must precede any result: when ledger_path is
    given, the ledger order is checked (a result filed before the
    pre-registration blocks, as does a prereg_hash filed nowhere in
    that ledger); without a ledger_path, a present prereg_hash is
    required and the order check is reported as not run.

    Returns (ok: bool, msg: str). Never raises for an incomplete or
    tampered chain -- the refusal IS the return value.
    """
    if not isinstance(chain, dict) or chain.get("kind") != "reasoning-chain":
        return (
            False,
            "blocked: not a reasoning-chain record; build one with "
            "build_chain(brief, hypotheses, decomposition, prereg_hash, "
            "critique) before entering the Computational Lab.",
        )
    if not verify_chain_links(chain):
        return (
            False,
            "blocked: reasoning-chain links do not verify (tampered or "
            "misordered stages); rebuild the chain with build_chain() "
            "before entering the Computational Lab.",
        )
    if not chain.get("brief_hash"):
        return (
            False,
            "blocked: missing brief -- no sourced brief hash; file the "
            "brief with literature.assemble_brief() before entering the "
            "Computational Lab.",
        )
    if not chain.get("hypotheses_ids"):
        return (
            False,
            "blocked: missing hypotheses -- no hypothesis ids; the "
            "hypothesis-generator must file ranked hypotheses with "
            "falsifiers (falsifier-less hypotheses are rejected) before "
            "entering the Computational Lab.",
        )
    if not chain.get("decomposition_hash"):
        return (
            False,
            "blocked: missing decomposition -- the scientific-analyst "
            "must decompose a hypothesis into the smallest checkable "
            "computations before entering the Computational Lab.",
        )
    if not chain.get("prereg_hash"):
        return (
            False,
            "blocked: missing pre-registration -- the statistician must "
            "pre-register test, threshold, and sample rule, hashed into "
            "the ledger BEFORE results exist, before entering the "
            "Computational Lab.",
        )
    if not chain.get("critique_hash"):
        return (
            False,
            "blocked: missing critique -- the scientific-critic's attack "
            "on the plan (confounds, leakage, cherry-picking) is a "
            "required record, not advice; file it before entering the "
            "Computational Lab.",
        )

    if ledger_path is None:
        return (
            True,
            "ok: reasoning chain complete (brief %(brief)s -> %(n)d "
            "hypotheses -> decomposition %(decomp)s -> preregistration "
            "%(prereg)s -> critique %(crit)s; %(links)d links verified). "
            "May enter the Computational Lab. Reasoning alone supports "
            "at most ladder level 1 (%(level1)s). Ledger order NOT "
            "checked (no ledger_path given); pre-registration is present "
            "but its precedence over results is unverified."
            % {
                "brief": chain["brief_hash"][:12],
                "n": len(chain["hypotheses_ids"]),
                "decomp": chain["decomposition_hash"][:12],
                "prereg": chain["prereg_hash"][:12],
                "crit": chain["critique_hash"][:12],
                "links": len(chain["links"]),
                "level1": _level1_status(),
            },
        )

    if _ledger_read_all is None:
        return (
            False,
            "blocked: ledger reader unavailable, cannot check that the "
            "pre-registration precedes results in %r; refusing entry "
            "rather than entering on an unchecked order." % (ledger_path,),
        )
    try:
        entries = _ledger_read_all(str(ledger_path))
    except OSError as exc:
        return (
            False,
            "blocked: cannot read ledger %r (%s); the pre-registration "
            "order cannot be checked, so entry is refused."
            % (ledger_path, exc),
        )
    prereg_idx = _find_prereg_index(entries, chain["prereg_hash"])
    if prereg_idx is None:
        return (
            False,
            "blocked: prereg_hash %(prereg)s filed nowhere in ledger "
            "%(path)r; the registration must be hashed into the ledger "
            "BEFORE results exist, before entering the Computational "
            "Lab." % {"prereg": chain["prereg_hash"], "path": ledger_path},
        )
    early = [i for i in _result_indices(entries) if i < prereg_idx]
    if early:
        return (
            False,
            "blocked: pre-registration hash must precede any result "
            "record -- earliest result record at ledger line %d predates "
            "the pre-registration at line %d; registration after the "
            "fact is not pre-registration." % (early[0] + 1, prereg_idx + 1),
        )
    return (
        True,
        "ok: reasoning chain complete (brief %(brief)s -> %(n)d "
        "hypotheses -> decomposition %(decomp)s -> preregistration "
        "%(prereg)s at ledger line %(line)d -> critique %(crit)s; "
        "%(links)d links verified, no result record predates the "
        "pre-registration). May enter the Computational Lab. Reasoning "
        "alone supports at most ladder level 1 (%(level1)s)."
        % {
            "brief": chain["brief_hash"][:12],
            "n": len(chain["hypotheses_ids"]),
            "decomp": chain["decomposition_hash"][:12],
            "prereg": chain["prereg_hash"][:12],
            "line": prereg_idx + 1,
            "crit": chain["critique_hash"][:12],
            "links": len(chain["links"]),
            "level1": _level1_status(),
        },
    )


def cycle_inputs_from_chain(chain):
    """Cycle inputs a complete chain unlocks.

    Keys align with cycle.REQUIRED_INPUTS: a passed gate supplies the
    'hypotheses' input the cheap-computations phase requires, plus the
    chain hash for provenance. Raises ValueError naming the missing
    keys when the chain does not cover them.
    """
    if _cycle_mod is None:  # pragma: no cover - cycle.py is landed
        raise NotImplementedError(
            "%s: cycle module unavailable; cannot map chain to cycle "
            "inputs." % (UNIMPLEMENTED,)
        )
    if not isinstance(chain, dict):
        raise ValueError("cycle_inputs_from_chain requires a chain dict")
    inputs = {}
    if chain.get("hypotheses_ids"):
        inputs["hypotheses"] = list(chain["hypotheses_ids"])
    if chain.get("chain_hash"):
        inputs["reasoning_chain"] = chain["chain_hash"]
    needed = _cycle_mod.REQUIRED_INPUTS.get("cheap-computations", [])
    missing = [k for k in needed if k not in inputs]
    if missing:
        raise ValueError(
            "chain does not unlock cheap-computations; missing inputs %r "
            "(pass the gate first: gate_to_computational)." % (missing,)
        )
    return inputs


def file_chain_record(chain, ledger_path, agent="research-director",
                     cycle_id=None):
    """File a reasoning-chain record to the ledger. Returns the entry.

    One ledger entry per filing; never rewrites history. Requires a
    verifying chain (verify_chain_links) -- a tampered chain is
    refused, not filed.
    """
    if _ledger_append is None:
        raise NotImplementedError(
            "%s: ledger module unavailable; cannot file the chain record."
            % (UNIMPLEMENTED,)
        )
    if not verify_chain_links(chain):
        raise ValueError("refused: chain links do not verify; not filing.")
    record = {
        "kind": "reasoning-chain-filed",
        "agent": agent,
        "chain_hash": chain.get("chain_hash"),
        "brief_hash": chain.get("brief_hash"),
        "hypotheses_ids": list(chain.get("hypotheses_ids") or []),
        "decomposition_hash": chain.get("decomposition_hash"),
        "prereg_hash": chain.get("prereg_hash"),
        "critique_id": chain.get("critique_id"),
        "complete": bool(
            chain.get("brief_hash")
            and chain.get("hypotheses_ids")
            and chain.get("decomposition_hash")
            and chain.get("prereg_hash")
            and chain.get("critique_hash")
        ),
    }
    if cycle_id is not None:
        record["cycle_id"] = cycle_id
    return _ledger_append(str(ledger_path), record)


__all__ = [
    "UNIMPLEMENTED",
    "TO_BE_READ_AT_RUN",
    "reasoning",
    "build_chain",
    "verify_chain_links",
    "gate_to_computational",
    "cycle_inputs_from_chain",
    "file_chain_record",
    "unresolved_markers",
]
