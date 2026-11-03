"""Scientific reasoning jobs (Section 3: tasks 21-26).

Deterministic, stdlib-only reasoning layer over the hypothesis record:

- Task 21 (hypothesis record): new_hypothesis() builds a
  schemas/hypothesis.schema.json record filed at evidence_level 0,
  status unverified. A missing disproof_condition is refused.
- Task 22 (hypothesis-generator job): generate_hypotheses() drafts 3-5
  competing hypotheses from a brief via fixed templates. Every filed
  hypothesis carries a falsifier; candidates without one are rejected
  into a separate logged list. Model synthesis is UNIMPLEMENTED.
- Task 23 (scientific-analyst job): decompose() splits a hypothesis
  into the smallest checkable computations.
- Task 24 (mathematics-researcher job): check_math() runs deterministic
  units/identities/edge checks over a decomposition.
- Task 25 (statistician job): preregister() hashes the analysis plan
  into the ledger BEFORE any result record exists.
- Task 26 (scientific-critic job): critique() attacks the plan and
  always returns a required record (never advice, never empty).

No model calls, no network. Same inputs -> same outputs (except
filed_at/registered_at timestamps and ledger hashes).
"""

import json
import os
import re
from datetime import datetime, timezone

try:
    from .ledger import append_record as _append_ledger_record
    from .ledger import read_all as _read_ledger
except ImportError:  # direct script use / sys.path import (see tests)
    try:
        from ledger import append_record as _append_ledger_record
        from ledger import read_all as _read_ledger
    except ImportError:  # ledger sibling missing: preregister degrades loudly
        _append_ledger_record = None
        _read_ledger = None

#: Marker for work this module will not do on its own. Any model or
#: network call raises NotImplementedError carrying this marker.
UNIMPLEMENTED = "UNIMPLEMENTED"

#: Required issues-list fallback (Task 26): the critique record is
#: never empty; when deterministic checks find nothing, say so.
NO_ISSUES_NOTE = "no issues found under deterministic checks"

#: Agent nicks attested in pack.json for these jobs.
GENERATOR_NICK = "hypothesis-generator"

#: Ledger kinds treated as result records for the preregistration
#: ordering guard (Task 25). A preregistration for a hypothesis must
#: precede any of these for the same hypothesis_id.
RESULT_KINDS = frozenset((
    "result",
    "experiment-result",
    "experiment-record",
    "compute-result",
    "reproduction-result",
))


def _utcnow():
    """Current UTC time as an ISO-8601 string with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_text(name, value):
    """Return stripped value, or raise ValueError naming the field."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("new_hypothesis requires non-empty %r" % (name,))
    return value.strip()


# ------------------------------------------------------------------
# Task 21: hypothesis record.
# ------------------------------------------------------------------

def new_hypothesis(id, question, proposed, measurable, alternative,
                   disproof, sources, filed_by):
    """Build a hypothesis record matching schemas/hypothesis.schema.json.

    Filed at evidence_level 0, status 'unverified', with an ISO-8601
    filed_at timestamp. A missing/empty disproof refuses filing with
    ValueError (a record without disproof_condition is not a
    hypothesis). Pure except for the filed_at timestamp.
    """
    hid = _require_text("id", id)
    rq = _require_text("research_question", question)
    pe = _require_text("proposed_explanation", proposed)
    mp = _require_text("measurable_prediction", measurable)
    ae = _require_text("alternative_explanation", alternative)
    dc = _require_text("disproof_condition", disproof)
    if not isinstance(disproof, str) or not disproof.strip():
        raise ValueError(
            "refused: disproof_condition is required; "
            "a hypothesis without a falsifier cannot be filed")
    fb = _require_text("filed_by", filed_by)
    if sources is None:
        srcs = []
    elif isinstance(sources, (list, tuple)):
        srcs = list(sources)
    else:
        raise TypeError("sources must be a list of source ids, got %r"
                        % type(sources).__name__)
    for sid in srcs:
        if not isinstance(sid, str) or not sid.strip():
            raise ValueError("sources must be non-empty strings, got %r" % (sid,))
    return {
        "id": hid,
        "research_question": rq,
        "proposed_explanation": pe,
        "measurable_prediction": mp,
        "alternative_explanation": ae,
        "disproof_condition": dc,
        "evidence_level": 0,
        "sources": srcs,
        "status": "unverified",
        "filed_at": _utcnow(),
        "filed_by": fb,
    }


# ------------------------------------------------------------------
# Task 22: hypothesis-generator job (deterministic templates).
# ------------------------------------------------------------------

def synthesize_with_model(brief):  # pragma: no cover
    """UNIMPLEMENTED: model-written hypothesis synthesis.

    Hypothesis drafting here is template assembly, never model prose.
    Raises NotImplementedError, never returns a hypothesis.
    """
    raise NotImplementedError(
        "%s: model synthesis is not implemented on this path: "
        "use generate_hypotheses() over the brief deterministically; "
        "any narrative write-up needs an explicit model call, which is "
        "not wired here." % (UNIMPLEMENTED,))


def _brief_question(brief):
    """Extract the research question from a brief dict or string."""
    if isinstance(brief, str):
        return brief.strip()
    if isinstance(brief, dict):
        for key in ("question", "research_question", "title"):
            value = brief.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
    raise TypeError("brief must be a dict or a question string, got %r"
                    % type(brief).__name__)


def _brief_source_ids(brief):
    """Collect source ids cited by a brief, sorted for determinism."""
    ids = set()
    if isinstance(brief, dict):
        for rec in brief.get("sources", []) or []:
            if isinstance(rec, dict) and rec.get("id") is not None:
                ids.add(str(rec["id"]))
        for claim in brief.get("claims", []) or []:
            if isinstance(claim, dict):
                for key in ("pinned_sources", "source_ids", "sources"):
                    for sid in claim.get(key, []) or []:
                        if str(sid).strip():
                            ids.add(str(sid))
    return sorted(ids)


def _brief_claim_texts(brief):
    """Seed claim sentences from a brief (str claims or dict claims)."""
    texts = []
    raws = []
    if isinstance(brief, dict):
        for claim in brief.get("claims", []) or []:
            raws.append(claim)
            if isinstance(claim, str):
                texts.append(claim.strip())
            elif isinstance(claim, dict):
                text = ""
                for key in ("claim", "text", "statement"):
                    value = claim.get(key)
                    if isinstance(value, str) and value.strip():
                        text = value.strip()
                        break
                texts.append(text)
    return texts, raws


# Five fixed competing-hypothesis templates (rank order). Each takes
# (question, seed, sources_note) and returns
# (proposed, measurable, alternative, disproof). Template 5 is the
# null/artefact rival so the set always competes with itself.
_TEMPLATES = (
    ("mechanistic",
     "The observed effect in {q} is driven by a direct mechanistic link: {seed}",
     "Under the stated conditions the target measure shifts by a fixed "
     "direction and amount stated in the plan for {q}",
     "Correlated background conditions, not the proposed mechanism",
     "Independent calculations showing no reproducible directional shift, "
     "or an adequately controlled experiment contradicting the prediction"),
    ("dose-response",
     "The effect in {q} scales monotonically with exposure: {seed}",
     "Increasing exposure increases the measured response monotonically "
     "across at least three pre-stated levels for {q}",
     "Threshold or saturation behaviour with no monotonic trend",
     "A pre-registered monotonicity check showing a flat or non-monotonic "
     "curve within tolerance, or a controlled experiment contradicting it"),
    ("interaction",
     "The effect in {q} depends on an interaction between two factors: {seed}",
     "The response differs between combined and single-factor conditions "
     "by a pre-stated margin for {q}",
     "Additive single-factor effects with no interaction term",
     "A factorial computation showing an interaction term consistent with "
     "zero, or a controlled experiment contradicting the predicted gap"),
    ("measurement-artefact",
     "The apparent effect in {q} is a measurement or selection artefact: {seed}",
     "Re-measurement with a blinded protocol and pre-stated inclusion rules "
     "shrinks the effect to within tolerance for {q}",
     "A real underlying effect robust to blinded re-measurement",
     "Blinded re-measurement reproducing the full original shift, "
     "contradicting the artefact account"),
    ("null",
     "There is no reproducible effect in {q}: {seed}",
     "Repeated computation from archived inputs reproduces the published "
     "baseline within the pre-stated tolerance for {q}",
     "A real effect masked by noise or mis-specified analysis",
     "Independent re-execution showing a reproducible directional shift "
     "beyond tolerance under the pre-registered analysis"),
)


def generate_hypotheses(brief, n=3):
    """Draft n competing hypotheses from a brief (Task 22).

    Deterministic templates only; never calls a model (see
    synthesize_with_model, which is UNIMPLEMENTED). n must be an int
    in 3..5 (pack rule). Returns (hypotheses, rejected): hypotheses
    are new_hypothesis() dicts in rank order (list position is rank);
    rejected are dicts {index, reason, seed} for candidates without a
    falsifier. A candidate whose seed carries an explicitly emptied
    disproof (dict claim with disproof_condition/falsifier set to an
    empty string) is rejected, never filed.
    """
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int in 3..5, got %r" % (n,))
    if n < 3 or n > 5:
        raise ValueError("generate_hypotheses drafts 3-5 hypotheses, got n=%r" % (n,))
    question = _brief_question(brief)
    if not question:
        raise ValueError("generate_hypotheses requires a brief with a question")
    source_ids = _brief_source_ids(brief)
    sources_note = ("pinned sources: %s" % ", ".join(source_ids)) if source_ids \
        else "no pinned sources"
    seeds, raws = _brief_claim_texts(brief)
    hypotheses = []
    rejected = []
    for i in range(n):
        _name, t_proposed, t_meas, t_alt, t_disproof = _TEMPLATES[i]
        seed = seeds[i] if i < len(seeds) else "no seeded claim; generic rival"
        raw = raws[i] if i < len(raws) else None
        forced_empty = False
        if isinstance(raw, dict):
            for key in ("disproof_condition", "falsifier", "disproof"):
                if key in raw and isinstance(raw[key], str) and not raw[key].strip():
                    forced_empty = True
            if raw.get("no_falsifier") is True:
                forced_empty = True
        short_q = question if len(question) <= 160 else question[:157] + "..."
        seed_q = seed if len(seed) <= 160 else seed[:157] + "..."
        fmt = {"q": short_q, "seed": seed_q}
        disproof = "" if forced_empty else t_disproof.format(**fmt)
        hid = "H%03d" % (i + 1)
        try:
            hypotheses.append(new_hypothesis(
                hid,
                question,
                t_proposed.format(**fmt),
                "%s (%s)." % (t_meas.format(**fmt), sources_note),
                t_alt.format(**fmt),
                disproof,
                source_ids,
                GENERATOR_NICK,
            ))
        except ValueError as exc:
            rejected.append({"index": i, "reason": str(exc), "seed": seed})
    return (hypotheses, rejected)


# ------------------------------------------------------------------
# Task 23: scientific-analyst job (decomposition).
# ------------------------------------------------------------------

def decompose(hypothesis):
    """Split a hypothesis into the smallest checkable computations.

    Returns a list of {step, computation, inputs, expected} dicts
    (three fixed steps, deterministic). Raises TypeError for a
    non-dict hypothesis and ValueError when the record lacks the
    fields a decomposition needs.
    """
    if not isinstance(hypothesis, dict):
        raise TypeError("hypothesis must be a dict, got %r"
                        % type(hypothesis).__name__)
    hid = hypothesis.get("id", "?")
    for key in ("research_question", "measurable_prediction",
                "alternative_explanation", "disproof_condition"):
        value = hypothesis.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("decompose requires non-empty %r" % (key,))
    rq = hypothesis["research_question"].strip()
    mp = hypothesis["measurable_prediction"].strip()
    ae = hypothesis["alternative_explanation"].strip()
    dc = hypothesis["disproof_condition"].strip()
    return [
        {
            "step": 1,
            "computation": "Parse measurable prediction of %s into named "
                           "variables with units: %s" % (hid, mp),
            "inputs": ["measurable_prediction text", "research_question: %s" % rq],
            "expected": "Variable list with units stated; empty list means "
                        "the prediction is untestable",
        },
        {
            "step": 2,
            "computation": "Encode the disproof decision rule for %s: %s "
                           "versus alternative %s" % (hid, dc, ae),
            "inputs": ["disproof_condition text", "alternative_explanation text"],
            "expected": "Boolean rule naming the threshold that would "
                        "disprove the hypothesis",
        },
        {
            "step": 3,
            "computation": "Specify the smallest numeric comparison on "
                           "archived inputs that executes the rule for %s" % (hid,),
            "inputs": ["archived inputs", "proposed parameters"],
            "expected": "Numeric output with units plus the match / no-match "
                        "verdict against the pre-stated threshold",
        },
    ]


# ------------------------------------------------------------------
# Task 24: mathematics-researcher job (deterministic math check).
# ------------------------------------------------------------------

_DIVISION_SIGNALS = ("/", "divide", "divided", "ratio", " per ")
_ZERO_GUARDS = ("zero", "guard", "nonzero", "non-zero", "denominator",
                "positive", "strictly", "check")

_UNIT_WORDS = (
    "mg", "mol", "mm", "cm", "celsius", "kelvin", "fahrenheit",
    "second", "minute", "hour", "pascal", "joule", "watt",
)


def _step_text(step):
    """Lowercased searchable text of one decomposition step."""
    parts = [str(step.get("computation", ""))]
    parts.extend(str(v) for v in step.get("inputs", []) or [])
    parts.append(str(step.get("expected", "")))
    return " ".join(parts).lower()


def check_math(decomposition):
    """Check a decomposition deterministically (Task 24).

    Flags empty steps/inputs, possible divide-by-zero (division
    language with no zero-guard stated), possible unit mismatch
    (two distinct unit words with no conversion stated), and log/sqrt
    without a domain guard. Pure. Returns {ok, issues}: ok is True
    iff issues is empty.
    """
    if not isinstance(decomposition, (list, tuple)):
        raise TypeError("decomposition must be a list of steps, got %r"
                        % type(decomposition).__name__)
    if not decomposition:
        return {"ok": False, "issues": ["empty decomposition: no steps to check"]}
    issues = []
    for pos, step in enumerate(decomposition, start=1):
        if not isinstance(step, dict):
            issues.append("step %d is not a record, got %s" % (pos, type(step).__name__))
            continue
        comp = step.get("computation")
        if not isinstance(comp, str) or not comp.strip():
            issues.append("step %d has no computation stated" % (pos,))
        inputs = step.get("inputs")
        if not isinstance(inputs, (list, tuple)) or not inputs \
                or not any(isinstance(v, str) and v.strip() for v in inputs):
            issues.append("step %d has no inputs: smallest check needs named inputs" % (pos,))
        text = _step_text(step) if isinstance(step, dict) else ""
        if any(sig in text for sig in _DIVISION_SIGNALS) \
                and not any(g in text for g in _ZERO_GUARDS):
            issues.append("step %d possible divide-by-zero: division stated "
                          "with no zero-guard" % (pos,))
        found_units = sorted({u for u in _UNIT_WORDS if u in text})
        if len(found_units) >= 2 and "convert" not in text:
            issues.append("step %d possible unit mismatch: units %s with no "
                          "conversion stated" % (pos, found_units))
        if "log" in text and "positive" not in text:
            issues.append("step %d log without positivity guard" % (pos,))
        if "sqrt" in text and not any(g in text for g in
                                      ("non-negative", "nonnegative", "positive", ">= 0")):
            issues.append("step %d sqrt without non-negativity guard" % (pos,))
    return {"ok": not issues, "issues": issues}


# ------------------------------------------------------------------
# Task 25: statistician job (pre-registration before results).
# ------------------------------------------------------------------

def _is_result_kind(kind):
    """True when a ledger entry kind counts as a result record."""
    if not isinstance(kind, str):
        return False
    norm = kind.strip().lower().replace("-", "_")
    return "result" in norm or norm in RESULT_KINDS


def preregister(hypothesis_id, test, threshold, sample_rule, ledger_path):
    """Pre-register the analysis, hashed into the ledger (Task 25).

    Files {kind 'preregistration', hypothesis_id, test, threshold,
    sample_rule, registered_at} via ledger.append_record and returns
    the filed entry; entry['entry_hash'] is the registration hash and
    must precede any result record for the same hypothesis_id. Raises
    ValueError when fields are missing or when the ledger already
    holds a result record for this hypothesis (registration would be
    late). Needs ledger.py; raises if the ledger module is missing.
    """
    hid = hypothesis_id.strip() if isinstance(hypothesis_id, str) else ""
    tst = test.strip() if isinstance(test, str) else ""
    rule = sample_rule.strip() if isinstance(sample_rule, str) else ""
    lpath = ledger_path.strip() if isinstance(ledger_path, str) else ""
    if not hid:
        raise ValueError("preregister requires a non-empty hypothesis_id")
    if not tst:
        raise ValueError("preregister requires a non-empty test")
    if threshold is None or (isinstance(threshold, str) and not threshold.strip()):
        raise ValueError("preregister requires a threshold (set before results)")
    if not rule:
        raise ValueError("preregister requires a non-empty sample_rule")
    if not lpath:
        raise ValueError("preregister requires a ledger_path")
    if _append_ledger_record is None or _read_ledger is None:
        raise RuntimeError("preregister needs ledger.py; ledger module unavailable")
    for entry in _read_ledger(lpath):
        if not isinstance(entry, dict):
            continue
        if _is_result_kind(entry.get("kind")) \
                and entry.get("hypothesis_id") == hid:
            raise ValueError(
                "late registration refused: ledger already holds a result "
                "record for %r; the registration must precede results" % (hid,))
    registration = {
        "kind": "preregistration",
        "hypothesis_id": hid,
        "test": tst,
        "threshold": threshold,
        "sample_rule": rule,
        "registered_at": _utcnow(),
    }
    return _append_ledger_record(lpath, registration)


# ------------------------------------------------------------------
# Task 26: scientific-critic job (required attack record).
# ------------------------------------------------------------------

def critique(plan):
    """Attack the plan; always return the required record (Task 26).

    Deterministic keyword checks over the plan for confounds, leakage
    risks, and cherry-picking risks. Returns {finding_id, issues,
    confounds, leakage_risks, cherry_picking_risks}. The record is
    never empty: when checks find nothing, issues holds exactly
    NO_ISSUES_NOTE ('no issues found under deterministic checks').
    Pure.
    """
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict, got %r" % type(plan).__name__)
    raw_fid = plan.get("finding_id", plan.get("hypothesis_id", plan.get("id")))
    finding_id = str(raw_fid).strip() if raw_fid is not None else ""
    if not finding_id:
        finding_id = "F-UNLINKED"
    text = json.dumps(plan, sort_keys=True, default=str).lower()
    issues = []
    confounds = []
    leakage = []
    cherry = []

    def _flag(bucket, message):
        bucket.append(message)
        issues.append(message)

    if "control" not in text:
        _flag(confounds, "no control condition stated; confounds cannot be ruled out")
    if "random" not in text and "seed" not in text:
        _flag(confounds, "no randomisation or seed stated; order effects uncontrolled")
    if "blind" not in text and "blinded" not in text:
        confounds.append("no blinding stated; observer bias uncontrolled")
        issues.append("no blinding stated; observer bias uncontrolled")
    if "held-out" not in text and "held out" not in text \
            and "test set" not in text and "holdout" not in text \
            and "hold out" not in text:
        _flag(leakage, "no held-out/test split stated; leakage cannot be ruled out")
    if "same data" in text or ("train" in text and "test" in text and "split" not in text):
        _flag(leakage, "train/test overlap signal; leakage risk unaddressed")
    if "preregist" not in text:
        _flag(cherry, "no pre-registration link stated; cherry-picking cannot be ruled out")
    if any(w in text for w in ("average", "mean", "aggregate", "overall")) \
            and "every" not in text and "all " not in text and "per-" not in text \
            and "per " not in text:
        _flag(cherry, "aggregate figure without per-unit filing; misses may be averaged away")
    if not issues:
        issues = [NO_ISSUES_NOTE]
    return {
        "finding_id": finding_id,
        "issues": issues,
        "confounds": confounds,
        "leakage_risks": leakage,
        "cherry_picking_risks": cherry,
    }


# ------------------------------------------------------------------
# Section 6: hypothesis parsing, prediction, evidence, duplicates,
# step-8 marker. Local and deterministic; no model calls.
# ------------------------------------------------------------------

STEP_8 = "step-8-unimplemented"

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "schemas", "hypothesis.schema.json")


def _text_field(record, name):
    value = record.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("hypothesis missing required field %r" % (name,))
    return value.strip()


def extract_variables(text):
    """Extract variables in order: backticked names, then X/Y symbols.

    A variable is an explicitly marked name (`temperature`) or a single
    uppercase symbol (X, Y). Prose words are not guessed as variables.
    """
    if not isinstance(text, str):
        return []
    names = [n.strip() for n in re.findall(r"`([^`]+)`", text)]
    names += re.findall(r"\b([A-Z])\b", text)
    out = []
    for name in names:
        if name and name not in out:
            out.append(name)
    return out


def extract_prediction(text):
    """Return the measurable direction of a prediction, or None."""
    if not isinstance(text, str):
        return {"direction": None, "measurable": False,
                "needs_refinement": True}
    low = text.lower()
    increase = any(w in low for w in
                   ("increase", "increases", "rise", "rises", "higher",
                    "greater", "grow", "grows", "positive"))
    decrease = any(w in low for w in
                   ("decrease", "decreases", "fall", "falls", "lower",
                    "less", "shrink", "shrinks", "negative"))
    if increase and decrease:
        direction = "mixed"
    elif increase:
        direction = "increase"
    elif decrease:
        direction = "decrease"
    else:
        direction = None
    measurable = bool(re.search(r"\d", text)) or direction in (
        "increase", "decrease")
    return {"direction": direction, "measurable": measurable,
            "needs_refinement": direction in (None, "mixed")}


def parse_hypothesis(record):
    """Parse one hypothesis record without inventing missing values.

    `proposed_explanation` is the schema field; `statement` is accepted
    as its alias and both are emitted. A missing statement is a named
    error. Confidence stays None when unset and is refused outside 0..1.
    """
    if not isinstance(record, dict):
        raise ValueError("hypothesis record must be an object")
    statement = record.get("statement") or record.get("proposed_explanation")
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError("hypothesis missing required field 'statement'")
    statement = statement.strip()
    hid = _text_field(record, "id")
    question = _text_field(record, "research_question")
    measurable = _text_field(record, "measurable_prediction")
    alternative = _text_field(record, "alternative_explanation")
    disproof = _text_field(record, "disproof_condition")
    level = record.get("evidence_level", 0)
    if isinstance(level, bool) or not isinstance(level, int) or not 0 <= level <= 6:
        raise ValueError("evidence_level must be an integer 0..6")
    confidence = record.get("confidence")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number or null")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
    parsed = dict(record)
    parsed.update({
        "id": hid, "statement": statement,
        "proposed_explanation": statement,
        "research_question": question,
        "measurable_prediction": measurable,
        "alternative_explanation": alternative,
        "disproof_condition": disproof,
        "evidence_level": level,
        "confidence": float(confidence) if confidence is not None else None,
        "variables": extract_variables(statement + " " + measurable),
        "prediction": extract_prediction(measurable),
    })
    parsed["testable"] = bool(parsed["variables"])
    return parsed


def validate_hypothesis_against_schema(record):
    """Validate a parsed hypothesis against schemas/hypothesis.schema.json."""
    from literature import validate_against_schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    return validate_against_schema(record, schema)


def classify_hypothesis(record, chain_cycle=False):
    """Classify as testable, untestable, needs_refinement, or cyclic."""
    if chain_cycle or (isinstance(record, dict) and record.get("chain_cycle")):
        return "cyclic"
    try:
        parsed = parse_hypothesis(record)
    except (ValueError, TypeError):
        return "untestable"
    if not parsed["variables"]:
        return "untestable"
    if parsed["prediction"]["needs_refinement"]:
        return "needs_refinement"
    return "testable"


def link_evidence(record, source_ids, known_source_ids=None):
    """Attach source ids to a hypothesis, refusing unknown ids."""
    if not isinstance(record, dict):
        raise ValueError("hypothesis record must be an object")
    if isinstance(source_ids, str):
        source_ids = [source_ids]
    if not isinstance(source_ids, (list, tuple)):
        raise TypeError("source_ids must be a list")
    if known_source_ids is not None:
        known = set(str(s) for s in known_source_ids)
        for sid in source_ids:
            if str(sid) not in known:
                raise ValueError("unknown source id %r" % (sid,))
    out = dict(record)
    existing = [str(s) for s in (record.get("sources") or [])]
    for sid in source_ids:
        sid = str(sid)
        if sid and sid not in existing:
            existing.append(sid)
    out["sources"] = existing
    return out


def normalize_statement(text):
    """Lowercase, collapse whitespace, and drop a trailing period."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".")


def find_duplicate_statements(records):
    """Indices of hypotheses whose statement duplicates an earlier one."""
    seen = set()
    duplicates = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        text = record.get("statement") or record.get("proposed_explanation") or ""
        key = normalize_statement(text)
        if key and key in seen:
            duplicates.append(index)
        elif key:
            seen.add(key)
    return duplicates


def step8_block(reason="step 8 is silent in the source text"):
    """The always-blocking step-8 result. Never returns a working step."""
    return {"step": STEP_8, "status": "blocked", "blocked": True,
            "marker": UNIMPLEMENTED, "reason": reason}


def requires_step8(value):
    """True when a phase/step/gate names the unimplemented step 8."""
    if isinstance(value, dict):
        for key in ("step", "phase", "gate", "target"):
            if key in value and requires_step8(value[key]):
                return True
        return False
    if isinstance(value, int) and not isinstance(value, bool):
        return value == 8
    if isinstance(value, str):
        return value.strip().lower() in ("8", STEP_8, "step-8", "step 8")
    return False
