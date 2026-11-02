"""Science Lab evidence ladder (PACK.md, LABORATORY section 7).

Every claim carries a level 0-6. Levels 4+ require physical
experiments by qualified humans and are unreachable by this
system alone: no automated path in this module grants them.

Source of truth for level names: os/worlds/science-lab/PACK.md
"Evidence ladder" table. Schema caps enforced in
schemas/hypothesis.schema.json (new hypotheses file at 0, only
the verifier may raise, never above 3 automated) and
schemas/experiment.schema.json (record cap 3, unverified and
mismatch cap 2, only reproduced supports 3).
"""

LEVELS = {
    0: {"status": "Idea",
        "meaning": "Interesting research proposal"},
    1: {"status": "Evidence supported",
        "meaning": "Existing sources support some underlying assumptions"},
    2: {"status": "Computationally tested",
        "meaning": "Numerical or simulation results support the hypothesis"},
    3: {"status": "Independently reproduced",
        "meaning": "Separate calculations reproduce the result"},
    4: {"status": "Experimentally validated",
        "meaning": "Appropriate experiments support the prediction"},
    5: {"status": "Independently replicated",
        "meaning": "Another research group reproduces the experimental result"},
    6: {"status": "Established application",
        "meaning": "Evidence supports its practical use, such as a validated treatment"},
}

# Marker for work this system cannot do on its own. Automated
# promotion above level 3 is UNIMPLEMENTED by design.
UNIMPLEMENTED = "UNIMPLEMENTED"

MAX_AUTOMATED_LEVEL = 3
MAX_LEVEL = 6
MIN_LEVEL = 0

VALID_VERIFICATION_STATUSES = ("unverified", "reproduced", "mismatch")

# Promotion rules: the single piece of evidence that moves a claim
# up exactly one rung. Each key is a (current, target) pair.
PROMOTION_RULES = {
    (0, 1): {
        "needs": "pinned original-source claims for the underlying assumptions",
        "evidence_kind": "pinned_source_claims",
        "detail": "Retrieved original sources with locators/content hashes "
                  "(a search result is a lead, never evidence).",
    },
    (1, 2): {
        "needs": "signed computational result supporting the hypothesis",
        "evidence_kind": "computational_result",
        "detail": "Numerical/simulation output filed as a schema-validated "
                  "compute job (labelled is_prediction at filing).",
    },
    (2, 3): {
        "needs": "independent-verifier reproduced record",
        "evidence_kind": "independent_reproduction",
        "detail": "The independent verifier re-executes from archived inputs "
                  "and records verification_status='reproduced'. Only the "
                  "verifier may promote; a mismatch caps the record at 2.",
    },
    (3, 4): {
        "needs": "human physical experiments (qualified humans only)",
        "evidence_kind": "human_physical_experiment",
        "detail": "UNIMPLEMENTED for the automated path: appropriate "
                  "experiments supporting the prediction, run by qualified "
                  "humans. No automated promotion above level 3.",
    },
    (4, 5): {
        "needs": "independent replication by another research group (humans)",
        "evidence_kind": "human_independent_replication",
        "detail": "UNIMPLEMENTED for the automated path.",
    },
    (5, 6): {
        "needs": "evidence of practical use, e.g. a validated treatment (humans)",
        "evidence_kind": "human_established_application",
        "detail": "UNIMPLEMENTED for the automated path.",
    },
}

# Canonical evidence-kind vocabularies (aliases accepted).
_PINNED_SOURCES = {
    "pinned_source_claims", "pinned_source_claim", "pinned_source",
    "pinned_sources", "source_claims", "source_claim", "sources",
    "retrieved_sources", "original_sources", "literature_sources",
    "evidence_supported",
}
_COMPUTATIONAL_RESULTS = {
    "computational_result", "computational_results", "computation",
    "simulation_result", "simulation_results", "simulation",
    "numerical_result", "numerical_results", "numerical",
    "calculation", "calculation_result", "compute_result",
}
_REPRODUCTIONS = {
    "independent_reproduction", "independent_verification",
    "independent_reexecution", "reproduction", "reproduced",
    "verifier_reproduction", "verifier_reproduced",
    "separate_calculations",
}

_HUMAN_HINT_SUBSTRINGS = (
    "human", "experiment", "physical", "wetlab", "wet_lab", "wet-lab",
    "validat", "replicat", "application", "treatment", "clinical",
    "bench", "measur", "fabricat", "metal",
)


def _normalize_evidence_kind(kind):
    """Lowercase/canonicalize an evidence-kind string. Non-strings -> ''."""
    if not isinstance(kind, str):
        return ""
    text = kind.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text


def _normalize_verification_status(status):
    if not isinstance(status, str):
        return status
    return status.strip().lower()


def _is_human_evidence(kind):
    """True when the evidence kind describes human physical-experiment work."""
    norm = _normalize_evidence_kind(kind)
    if not norm:
        return False
    if norm in _PINNED_SOURCES or norm in _COMPUTATIONAL_RESULTS:
        return False
    if norm in _REPRODUCTIONS:
        # A verifier reproduction is automated level-3 evidence, not a
        # human experiment. It never promotes past 3 on its own.
        return False
    if norm in {"human_experiment", "human_physical_experiment",
                "physical_experiment", "experimental_validation",
                "human_independent_replication", "external_replication",
                "independent_replication", "human_established_application",
                "established_application", "practical_use"}:
        return True
    return any(hint in norm for hint in _HUMAN_HINT_SUBSTRINGS)


def _is_valid_level(value):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value in LEVELS
    )


def can_promote(current, target, evidence_kind, verification_status,
                is_human=False):
    """Return True iff the claim may move from current to target.

    Ladder discipline: only single-step upward moves (target ==
    current + 1) ever promote. Levels 4-6 require physical
    experiments by qualified humans: any automated attempt
    (is_human falsy) targeting 4+ returns False. No automated
    path in this module grants 4-6. See promote(), which raises
    NotImplementedError (UNIMPLEMENTED) for the same case, and
    next_required(3), which returns an UNIMPLEMENTED notice.
    """
    if not _is_valid_level(current) or not _is_valid_level(target):
        return False
    if target != current + 1:
        return False
    if target > MAX_AUTOMATED_LEVEL and not is_human:
        # Automated ceiling: UNIMPLEMENTED by design (see promote()).
        return False
    norm_ev = _normalize_evidence_kind(evidence_kind)
    norm_ver = _normalize_verification_status(verification_status)
    if norm_ver not in VALID_VERIFICATION_STATUSES:
        return False
    if (current, target) == (0, 1):
        return (norm_ev in _PINNED_SOURCES
                and norm_ver in ("unverified", "reproduced"))
    if (current, target) == (1, 2):
        return (norm_ev in _COMPUTATIONAL_RESULTS
                and norm_ver in ("unverified", "reproduced"))
    if (current, target) == (2, 3):
        return norm_ev in _REPRODUCTIONS and norm_ver == "reproduced"
    if target > MAX_AUTOMATED_LEVEL:
        # Human-only rungs 4-6: is_human is already truthy here.
        if norm_ver == "mismatch":
            return False
        return _is_human_evidence(evidence_kind)
    return False


def promote(current, target, evidence_kind, verification_status,
            is_human=False):
    """Promote a claim one rung, or raise.

    Returns target when can_promote(...) is True. Raises
    NotImplementedError (UNIMPLEMENTED) for automated attempts above
    level 3, and ValueError for any other non-promotable move.
    """
    if (isinstance(target, int) and not isinstance(target, bool)
            and target > MAX_AUTOMATED_LEVEL and not is_human):
        raise NotImplementedError(
            "%s: automated promotion to level %r is not implemented: "
            "levels 4-6 require physical experiments by qualified humans "
            "and are unreachable by this system alone." % (UNIMPLEMENTED, target)
        )
    if can_promote(current, target, evidence_kind, verification_status,
                   is_human=is_human):
        return target
    raise ValueError(
        "promotion refused: level %r -> %r with evidence_kind=%r, "
        "verification_status=%r, is_human=%r" % (
            current, target, evidence_kind, verification_status, is_human)
    )


def next_required(current):
    """Describe the evidence needed to move up one rung from current."""
    if not _is_valid_level(current):
        raise ValueError("unknown evidence level %r (known: 0-6)" % (current,))
    if current == MAX_LEVEL:
        info = LEVELS[MAX_LEVEL]
        return ("Top of the ladder (level 6, %s): no further promotion." % info["status"])
    rule = PROMOTION_RULES.get((current, current + 1))
    nxt = LEVELS[current + 1]
    if current < MAX_AUTOMATED_LEVEL:
        return ("To reach level %d (%s): %s. %s" % (
            current + 1, nxt["status"], rule["needs"], rule["detail"]))
    # current >= 3: human-gated. Automated path is UNIMPLEMENTED.
    return ("%s: to reach level %d (%s): %s. %s "
            "No automated promotion above level 3." % (
                UNIMPLEMENTED, current + 1, nxt["status"],
                rule["needs"], rule["detail"]))


def _coerce_level(value, name):
    """Accept an int level or a record dict carrying one. Never above 6."""
    if isinstance(value, dict):
        for key in ("evidence_level", "level", "evidenceLevel",
                    "evidence-level"):
            if value.get(key) is not None:
                value = value[key]
                break
        else:
            raise ValueError(
                "%s record carries no level "
                "(looked for evidence_level/level)" % (name,))
    if isinstance(value, bool):
        raise ValueError("%s level must be an int 0-6, got %r" % (name, value))
    try:
        level = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            "%s level must be an int 0-6, got %r" % (name, value))
    if level not in LEVELS:
        raise ValueError(
            "%s level must be an int 0-6, got %r" % (name, value))
    return level


def assert_export_allowed(record_level, display_level):
    """Guard every surface: a claim displays at its record level, never higher.

    Accepts ints or record dicts carrying evidence_level/level (the CLI
    passes a claim dict as record_level). Raises ValueError when
    display_level > record_level. Returns None when allowed.
    """
    record = _coerce_level(record_level, "record")
    display = _coerce_level(display_level, "display")
    if display > record:
        raise ValueError(
            "export blocked: display level %d exceeds recorded level %d; "
            "a claim displays at the level its record holds, never higher." % (
                display, record))
    return None


def cap_for_experiment(verification_status, is_prediction=False):
    """Max evidence level an experiment record may carry.

    Mirrors schemas/experiment.schema.json: the record cap is 3, and
    unverified/mismatch results cap at 2. Only verification_status
    'reproduced' supports 3. is_prediction labels model output at
    filing time; it does not raise the cap. Never returns above 3:
    levels 4-6 require human physical experiments (UNIMPLEMENTED here).
    """
    norm = _normalize_verification_status(verification_status)
    if norm == "unverified":
        return 2
    if norm == "mismatch":
        return 2
    if norm == "reproduced":
        return 3
    raise ValueError(
        "unknown verification_status %r (expected one of %s)" % (
            verification_status, list(VALID_VERIFICATION_STATUSES)))


__all__ = [
    "LEVELS",
    "UNIMPLEMENTED",
    "MAX_AUTOMATED_LEVEL",
    "MAX_LEVEL",
    "MIN_LEVEL",
    "PROMOTION_RULES",
    "VALID_VERIFICATION_STATUSES",
    "can_promote",
    "promote",
    "next_required",
    "assert_export_allowed",
    "cap_for_experiment",
]
