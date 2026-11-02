"""Research Intelligence literature layer (Section 2: tasks 11, 13, 14, 16, 17, 18).

- Task 11 (literature job): literature_search() produces a sourced
  brief (title, sources with locators/hashes) deterministically from
  LOCAL source files. No network; model calls are UNIMPLEMENTED.
- Task 13 (brief assembler): assemble_brief() pins each claim to a
  source record; unpinned claims are dropped and the drop is logged.
- Task 14 (prior-result finder): find_prior_result() locates the
  published computational result the first reproduction test will
  target and records why it qualifies.
- Task 17 (literature budget guard): check_source_budget() enforces
  per-cycle source and call caps, with a receipt on stop.
- Task 18 (status record): status_record() builds the per-cycle
  Research Intelligence status record, stored under records/.

Source of truth for the first reproduction target: os-build/
SCIENCE_LAB_W2_SLICE1.md section 4 (Delaney 2004 ESOL gate) and the
archived inputs in gate/delaney/ (see gate/delaney/SOURCES.md).

HONESTY: target fit numbers are pulled at run time from the paper,
never hardcoded here (slice section 4). Anything this module could
not verify is left as TO_BE_READ_AT_RUN, never invented. A claim
displays at the level its record holds, never higher (all work
here supports at most ladder level 1).
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone

try:
    from .lab_config import load_config
except ImportError:  # direct script use
    from lab_config import load_config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHELVES_DIR = os.path.join(BASE_DIR, "shelves")
GATE_DELANEY_DIR = os.path.join(BASE_DIR, "gate", "delaney")
ARCHIVED_DATASET = os.path.join(GATE_DELANEY_DIR, "delaney-processed.csv")
DATASET_SOURCES = os.path.join(GATE_DELANEY_DIR, "SOURCES.md")
DEFAULT_TARGET_PATH = os.path.join(BASE_DIR, "reproduction_target.json")
LITERATURE_RECORDS_DIR = os.path.join(BASE_DIR, "records", "literature")
LEDGER_PATH = os.path.join(BASE_DIR, "records", "ledger.jsonl")

#: Marker for values that must be read from the source at run time.
TO_BE_READ_AT_RUN = "TO_BE_READ_AT_RUN"

#: The one DOI this module asserts. Verified in-repo: it is the
#: citation recorded in gate/delaney/SOURCES.md. No other DOI is
#: asserted anywhere in this module or the seed shelves.
DELANEY_CITATION = (
    "Delaney, J. S. (2004). ESOL: Estimating Aqueous Solubility "
    "Directly from Molecular Structure. "
    "J. Chem. Inf. Comput. Sci. 44(3), 1000-1005. "
    "doi:10.1021/ci034243x."
)

#: Local-policy defaults when lab_config.json carries no literature
#: section. Caps are local policy, not evidence; a stopped run earns
#: no level and files no claim.
DEFAULT_MAX_SOURCES_PER_CYCLE = 50
DEFAULT_MAX_CALLS_PER_CYCLE = 50


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_dataset_hash():
    """Read the archived-dataset SHA-256 stated in SOURCES.md.

    Returns (hash, raw_line). Raises if the file or hash is missing,
    so a changed archive can never silently pass.
    """
    with open(DATASET_SOURCES, "r", encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(r"\bSHA-256\b.*?`([0-9a-f]{64})`", text, re.DOTALL)
    if not match:
        raise ValueError(
            "no SHA-256 stated in %s; archive provenance unreadable" % DATASET_SOURCES
        )
    return match.group(1), match.group(0).strip().splitlines()[-1].strip()


def find_prior_result(shelves_dir=SHELVES_DIR):
    """Locate the published computational result for the first reproduction test.

    Picks the Delaney (2004) ESOL entry from the chemistry shelf and
    verifies the archived inputs on disk (CSV present, SHA-256 matches
    gate/delaney/SOURCES.md). Returns the target record dict; file it
    with file_target_record(). Target fit numbers are NOT read here:
    per SCIENCE_LAB_W2_SLICE1.md section 4 they are pulled at run time
    from the paper, so the record carries TO_BE_READ_AT_RUN.
    """
    shelf_path = os.path.join(shelves_dir, "chemistry.json")
    shelf = _read_json(shelf_path)
    candidates = shelf.get("sources", [])
    pick = None
    for entry in candidates:
        if "Delaney" in entry.get("citation", ""):
            pick = entry
            break
    if pick is None:
        raise ValueError(
            "no Delaney ESOL entry in %s; first reproduction target unknown" % shelf_path
        )
    if not os.path.exists(ARCHIVED_DATASET):
        raise ValueError(
            "archived inputs missing: %s not found; target not reproducible "
            "from this checkout" % ARCHIVED_DATASET
        )
    expected_hash, _ = _expected_dataset_hash()
    actual_hash = _sha256_file(ARCHIVED_DATASET)
    if actual_hash != expected_hash:
        raise ValueError(
            "archive hash mismatch for %s: expected %s, got %s; "
            "inputs changed, target record refused" % (ARCHIVED_DATASET, expected_hash, actual_hash)
        )
    with open(ARCHIVED_DATASET, "r", encoding="utf-8") as fh:
        rows = sum(1 for _ in fh) - 1  # minus header
    return {
        "kind": "reproduction-target",
        "target_id": "delaney-2004-esol",
        "question": "Can the published Delaney (2004) ESOL aqueous-solubility "
                    "model be reproduced from the archived compound set?",
        "paper": {
            "citation": DELANEY_CITATION,
            "shelf_locator": "shelves/chemistry.json",
            "method_locator": "Delaney (2004) paper text + "
                              "os/worlds/science-lab/gate/GATE_PREP.md "
                              "(prep-run reading of the published equation; "
                              "coefficients re-extracted at gate run time)",
        },
        "dataset": {
            "file": "gate/delaney/delaney-processed.csv",
            "source_record": "gate/delaney/SOURCES.md",
            "rows": rows,
            "sha256": actual_hash,
            "hash_verified_at": _utcnow(),
        },
        "qualifies": {
            "inputs_available": "Archived compound set present in this checkout "
                "(%d data rows) with SHA-256 matching SOURCES.md, verified "
                "above; public retrieval URL recorded in SOURCES.md." % rows,
            "result_checkable": "The paper publishes the model and its own "
                "reported fit statistics; the gate re-scores predicted "
                "against measured across the full archived set and files "
                "every compound where the model misses badly, then hands "
                "the archived inputs to the independent verifier for "
                "re-execution within a pre-stated tolerance "
                "(SLICE1 section 4; gate/GATE_PREP.md).",
            "method_no_paywall": "Running the reproduction needs no paywalled "
                "access: the published equation, open RDKit descriptors, "
                "and the public compound set (DeepChem mirror, URL in "
                "SOURCES.md). The ACS paper text itself is paywalled; the "
                "run-time extraction step reads it, but no licence blocks "
                "the computation.",
        },
        "target_numbers": {
            "reported_fit_statistics": TO_BE_READ_AT_RUN,
            "note": "Per SCIENCE_LAB_W2_SLICE1.md section 4, target numbers "
                    "are pulled at run time from the source, never hardcoded. "
                    "The paper text was not opened by this function.",
        },
        "gate_status": "NOT attempted. Prep run only (gate/GATE_PREP.md, "
                       "gate/prep_results.json). No evidence level earned; "
                       "a verified gate earns exactly ladder level 3 for the "
                       "reproduction itself, and no discovery claim.",
        "recorded_at": _utcnow(),
        "recorded_by": "find_prior_result() in os/worlds/science-lab/literature.py",
    }


def file_target_record(record=None, path=DEFAULT_TARGET_PATH):
    """File the reproduction-target record as JSON. Returns the path."""
    if record is None:
        record = find_prior_result()
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, sort_keys=True, indent=2)
        fh.write("\n")
    return path


def _literature_caps(config):
    """Read per-cycle literature caps from config; local-policy defaults."""
    lit = (config or {}).get("literature", {})
    return (
        lit.get("maxSourcesPerCycle", DEFAULT_MAX_SOURCES_PER_CYCLE),
        lit.get("maxCallsPerCycle", DEFAULT_MAX_CALLS_PER_CYCLE),
    )


def check_source_budget(cycle_id, sources_read, calls, config=None, receipt_path=None):
    """Per-cycle source and call caps for the literature job (Task 17).

    Extends lab_config usage: caps come from lab_config.json's
    "literature" section when present, else local-policy defaults.
    Returns (allowed: bool, reason: str). Over cap -> (False, reason)
    plus a stop receipt written under records/literature/; the caller
    must stop the run. A stopped run earns no level and files no claim.
    """
    if not cycle_id:
        raise ValueError("check_source_budget requires a cycle_id")
    if config is None:
        try:
            config = load_config()
        except (OSError, ValueError):
            config = {}
    max_sources, max_calls = _literature_caps(config)
    breaches = []
    if sources_read > max_sources:
        breaches.append(
            "sources_read %s > maxSourcesPerCycle %s" % (sources_read, max_sources)
        )
    if calls > max_calls:
        breaches.append("calls %s > maxCallsPerCycle %s" % (calls, max_calls))
    if not breaches:
        return (
            True,
            "ok: cycle %r within literature budget "
            "(sources %s/%s, calls %s/%s)"
            % (cycle_id, sources_read, max_sources, calls, max_calls),
        )
    reason = "budget-cap-reached: cycle %r literature cap exceeded: %s" % (
        cycle_id,
        "; ".join(breaches),
    )
    receipt = {
        "kind": "budget-receipt",
        "agent": "literature-researcher",
        "cycle_id": cycle_id,
        "sources_read": sources_read,
        "calls": calls,
        "max_sources_per_cycle": max_sources,
        "max_calls_per_cycle": max_calls,
        "reason": reason,
        "stopped": True,
        "recorded_at": _utcnow(),
    }
    path = receipt_path or os.path.join(
        LITERATURE_RECORDS_DIR, "%s.budget-receipt.json" % cycle_id
    )
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, sort_keys=True, indent=2)
        fh.write("\n")
    return (False, reason)


def status_record(cycle_id, sources_read, claims_pinned, claims_dropped, contested):
    """Per-cycle Research Intelligence status record (Task 18).

    sources_read: list of source locators consulted this cycle.
    claims_pinned: claims each pinned to a source record.
    claims_dropped: unpinned claims, dropped with the reason logged.
    contested: claims two sources disagree on (never silently resolved).
    Returns the record dict; file it with file_status_record().
    Assigns no evidence level; counts are derived, never hand-written.
    """
    for name, value in (
        ("sources_read", sources_read),
        ("claims_pinned", claims_pinned),
        ("claims_dropped", claims_dropped),
        ("contested", contested),
    ):
        if not isinstance(value, list):
            raise TypeError("%s must be a list, got %r" % (name, type(value).__name__))
    return {
        "kind": "research-intelligence-status",
        "cycle_id": cycle_id,
        "sources_read": list(sources_read),
        "claims_pinned": list(claims_pinned),
        "claims_dropped": list(claims_dropped),
        "contested": list(contested),
        "counts": {
            "sources_read": len(sources_read),
            "claims_pinned": len(claims_pinned),
            "claims_dropped": len(claims_dropped),
            "contested": len(contested),
        },
        "recorded_at": _utcnow(),
    }


def file_status_record(record, path=None):
    """Store a status record under records/. Returns the path."""
    if not isinstance(record, dict) or not record.get("cycle_id"):
        raise ValueError("file_status_record requires a status record with a cycle_id")
    if path is None:
        path = os.path.join(
            LITERATURE_RECORDS_DIR, "%s.json" % record["cycle_id"]
        )
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, sort_keys=True, indent=2)
        fh.write("\n")
    return path


# ------------------------------------------------------------------
# Tasks 11, 13, 16: literature job, brief assembler, contradiction
# check (appended; tasks 14/17/18 above untouched).
#
# literature_search() and assemble_brief() are pure functions of
# their inputs (local source files + question + claims). No network,
# no model calls on this path.
#
# UNIMPLEMENTED (explicit, never silent):
#   - search_remote(): network literature search. Use
#     literature_search() over a local sources file instead.
#   - synthesize_with_model(): narrative synthesis requires model
#     judgement. Briefs here are assembled, not written.
#
# Honesty rules enforced here:
#   - Unpinned claims are dropped from the brief and each drop is
#     logged (brief['dropped'] always; ledger entry when ledger_path
#     is given).
#   - Contradicting sources never cancel out: mark_contested() flags
#     the claim 'contested' with both sides named. Contested claims
#     are kept and flagged, never silently resolved or dropped.
#
# Source shape (schemas/source.schema.json, required keys):
#   id, citation, retrieved_at, access_note, supports_claim, locator,
#   content_hash. Optional: stance ('supports' default | 'disputes').
#
# Claim shape for assemble_brief()/mark_contested():
#   str, or dict with 'claim' (aliases 'text', 'statement') and
#   optional 'source_id' / 'source_ids' / 'sources' (explicit
#   citations by source id), plus optional 'attestations'
#   [{'source_id', 'stance'}].
# ------------------------------------------------------------------

try:
    from .ledger import append_record as _append_ledger_record
except ImportError:  # direct script use / sys.path import (see tests)
    try:
        from ledger import append_record as _append_ledger_record
    except ImportError:  # ledger sibling missing: ledger logging degrades
        _append_ledger_record = None

#: Marker for work this section will not do on its own. Any model or
#: network call raises NotImplementedError carrying this marker.
UNIMPLEMENTED = "UNIMPLEMENTED"

SOURCE_SCHEMA_FILENAME = os.path.join(
    BASE_DIR, "schemas", "source.schema.json")

REQUIRED_SOURCE_FIELDS = (
    "id", "citation", "retrieved_at", "access_note",
    "supports_claim", "locator", "content_hash",
)

VALID_STANCES = ("supports", "disputes")

_CLAIM_TEXT_KEYS = ("claim", "text", "statement")

_CITATION_KEYS = ("source_id", "source_ids", "sources", "sourceIds")

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# Tokens too common to carry topical signal. Fixed list -> deterministic.
_STOPWORDS = frozenset((
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to",
    "is", "are", "was", "were", "be", "by", "with", "what", "which",
    "how", "why", "does", "do", "did", "can", "could", "would",
    "should", "it", "its", "this", "that", "these", "those", "as",
    "at", "from", "into", "about",
))


def _normalize_text(text):
    """Lowercase, drop non-alphanumerics, collapse whitespace."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _tokens(text):
    """Topical tokens of a string (stopwords removed)."""
    return set(t for t in _TOKEN_RE.findall(text.lower())
              if t not in _STOPWORDS)


def _claim_text(claim):
    """Extract the claim sentence from a str or dict claim."""
    if isinstance(claim, str):
        return claim
    if isinstance(claim, dict):
        for key in _CLAIM_TEXT_KEYS:
            value = claim.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return ""


def _cited_ids(claim):
    """Explicit source ids cited by a claim dict. [] for str claims."""
    if not isinstance(claim, dict):
        return []
    ids = []
    for key in _CITATION_KEYS:
        value = claim.get(key)
        if isinstance(value, str) and value.strip():
            ids.append(value.strip())
        elif isinstance(value, (list, tuple)):
            ids.extend(str(v).strip() for v in value
                       if str(v).strip())
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def validate_source(record):
    """Check a source record against the required shape.

    Returns a list of error strings; [] means valid. Never raises for
    a bad record (use assert_valid_source to raise). Non-dicts yield
    a single error.
    """
    errors = []
    if not isinstance(record, dict):
        return ["source record must be an object, got %r" % type(record).__name__]
    for field in REQUIRED_SOURCE_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append("missing or empty required field %r" % (field,))
    if isinstance(record.get("content_hash"), str) and record["content_hash"].strip():
        if not _HASH_RE.match(record["content_hash"].strip()):
            errors.append("content_hash must be a SHA-256 hex digest (64 hex chars)")
    if isinstance(record.get("retrieved_at"), str) and record["retrieved_at"].strip():
        raw = record["retrieved_at"].strip()
        try:
            from datetime import datetime as _dt
            _dt.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            errors.append("retrieved_at must be ISO-8601 (YYYY-MM-DD or timestamp), got %r" % (raw,))
    stance = record.get("stance", "supports")
    if stance not in VALID_STANCES:
        errors.append("stance must be one of %r, got %r" % (list(VALID_STANCES), stance))
    return errors


def assert_valid_source(record):
    """Raise ValueError listing problems, or return the record."""
    errors = validate_source(record)
    if errors:
        raise ValueError("invalid source record %r: %s"
                         % (record.get("id") if isinstance(record, dict) else record,
                            "; ".join(errors)))
    return record


def _records_from_payload(payload, origin):
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict) and isinstance(payload.get("sources"), list):
        return list(payload["sources"])
    if isinstance(payload, dict):
        return [payload]
    raise ValueError("sources_db entry %r holds neither a record, a list, "
                     "nor {'sources': [...]}" % (origin,))


def _load_sources(sources_db):
    """Load source records from a list, a JSON file, or a directory.

    - list: used as-is (each entry validated by the caller).
    - path to a .json file: object list, or {'sources': [...]}.
    - path to a directory: every '*.json' file, each a record or a
      list / {'sources': [...]}; read in sorted filename order.
    Returns (records, load_notes). load_notes names files skipped as
    invalid JSON (never silent). Raises ValueError/FileNotFoundError
    with an explicit message when the db itself is unusable.
    """
    if isinstance(sources_db, (list, tuple)):
        return (list(sources_db), [])
    if not isinstance(sources_db, (str, bytes, os.PathLike)):
        raise TypeError("sources_db must be a list, a JSON file path, "
                        "or a directory path, got %r"
                        % type(sources_db).__name__)
    path = os.fspath(sources_db)
    if not os.path.exists(path):
        raise FileNotFoundError("sources_db not found: %r" % (path,))
    records = []
    notes = []
    if os.path.isdir(path):
        names = sorted(n for n in os.listdir(path) if n.endswith(".json"))
        if not names:
            raise ValueError("sources_db directory holds no *.json files: %r" % (path,))
        for name in names:
            full = os.path.join(path, name)
            try:
                payload = json.load(open(full, "r", encoding="utf-8"))
            except (OSError, ValueError) as exc:
                notes.append({"file": name, "skipped": "unreadable JSON: %s" % (exc,)})
                continue
            records.extend(_records_from_payload(payload, name))
        return (records, notes)
    try:
        payload = json.load(open(path, "r", encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("sources_db file unreadable: %r (%s)" % (path, exc))
    return (_records_from_payload(payload, os.path.basename(path)), [])


def literature_search(question, sources_db):
    """Produce a sourced brief for a question from LOCAL sources only.

    question: non-empty research question string.
    sources_db: list of source records, path to a JSON file, or path
      to a directory of JSON files (see _load_sources). No network is
      touched; a network search is UNIMPLEMENTED (see search_remote).

    Returns a brief dict:
      {'title', 'question', 'sources': [matched valid records],
       'scores': {source_id: overlap}, 'invalid_sources': [...]}
    Records that fail validation are NOT sources; they are reported
    under 'invalid_sources' (a search result without locator+hash is
    a lead, never evidence). Zero topical overlap yields an honest
    empty 'sources' list, never an invented one. Deterministic:
    same inputs -> same brief (sources sorted by score desc, id asc).
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("literature_search requires a non-empty question string")
    question = question.strip()
    records, load_notes = _load_sources(sources_db)
    q_toks = _tokens(question)
    matched = []
    invalid = []
    for rec in records:
        errors = validate_source(rec)
        if errors:
            rid = rec.get("id") if isinstance(rec, dict) else None
            invalid.append({"id": rid, "errors": errors,
                            "reason": "not a retrieved original source; "
                                      "a result without locator+hash is a lead, never evidence"})
            continue
        haystack = " ".join(str(rec.get(k, "")) for k in
                            ("citation", "supports_claim", "locator", "id", "title"))
        score = len(q_toks & _tokens(haystack))
        if score > 0:
            matched.append((score, rec))
    matched.sort(key=lambda pair: (-pair[0], str(pair[1].get("id", ""))))
    sources = [rec for _, rec in matched]
    scores = {str(rec.get("id")): score for score, rec in matched}
    title = "Literature brief — %s" % (question if len(question) <= 140 else question[:137] + "...")
    brief = {
        "title": title,
        "question": question,
        "sources": sources,
        "scores": scores,
        "invalid_sources": invalid,
    }
    if load_notes:
        brief["load_notes"] = load_notes
    return brief


def search_remote(question, adapter="openalex"):  # pragma: no cover
    """UNIMPLEMENTED: network literature search.

    Literature adapters beyond local files are not wired here; use
    literature_search() over a local sources file. Raises
    NotImplementedError, never returns a fabricated result.
    """
    raise NotImplementedError(
        "%s: network literature search via adapter %r is not implemented: "
        "no verified live-search path exists in this module. Use "
        "literature_search(question, sources_db) over local source files." % (
            UNIMPLEMENTED, adapter))


def synthesize_with_model(brief):  # pragma: no cover
    """UNIMPLEMENTED: model-written narrative synthesis of a brief.

    Narrative synthesis requires model judgement; this deterministic
    module assembles briefs instead of writing them. Raises
    NotImplementedError, never returns prose.
    """
    raise NotImplementedError(
        "%s: model synthesis is not implemented on this path: "
        "assemble_brief() pins claims to source records deterministically; "
        "any narrative write-up needs an explicit model call, which is "
        "not wired here." % (UNIMPLEMENTED,))


def assemble_brief(question, claims, sources, ledger_path=None):
    """Assemble a brief: claims each pinned to a source record.

    claims: list of str or dict claims (see section docstring).
    sources: list of valid source records (validated first; invalid
      entries raise ValueError -- a brief never rests on a bad record).
    ledger_path: optional JSONL ledger file. Every dropped (unpinned)
      claim is filed there as a 'brief-claim-dropped' entry via
      ledger.append_record. The drop is ALWAYS in brief['dropped'];
      the ledger write is the durable log.

    A claim is pinned iff at least one source shares its normalized
    text (source.supports_claim) or is explicitly cited by id and
    present. Otherwise it is dropped with a reason naming what failed.
    Explicit citations of unknown ids are kept as 'warnings' on the
    pinned claim, never silently ignored.

    Returns {'title', 'question', 'claims': [pinned...],
             'dropped': [{'claim','reason'}], 'sources': [used...]}.
    Pinned entries: {'claim', 'pinned_sources': [ids], 'status':
    'pinned', 'warnings': [...]} (warnings omitted when empty).
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("assemble_brief requires a non-empty question string")
    question = question.strip()
    if not isinstance(claims, (list, tuple)):
        raise TypeError("claims must be a list, got %r" % type(claims).__name__)
    if not isinstance(sources, (list, tuple)):
        raise TypeError("sources must be a list, got %r" % type(sources).__name__)
    for rec in sources:
        assert_valid_source(rec)
    by_id = {str(rec["id"]): rec for rec in sources}
    text_index = {}
    for rec in sources:
        text_index.setdefault(_normalize_text(rec["supports_claim"]), []).append(str(rec["id"]))

    pinned = []
    dropped = []
    used_ids = set()
    ledger_errors = []
    for claim in claims:
        text = _claim_text(claim)
        norm = _normalize_text(text)
        if not norm:
            if isinstance(claim, str):
                raw = claim
            elif isinstance(claim, dict):
                raw = dict(claim)
            else:
                raw = repr(claim)
            dropped.append({"claim": raw,
                            "reason": "empty claim text; nothing to pin"})
            continue
        cited = [c for c in _cited_ids(claim) if c]
        known_cited = [c for c in cited if c in by_id]
        text_matched = list(text_index.get(norm, []))
        pinned_ids = []
        for sid in known_cited + text_matched:
            if sid not in pinned_ids:
                pinned_ids.append(sid)
        if not pinned_ids:
            if cited:
                reason = ("unpinned: cited source(s) %r not in the source set, "
                          "and no source states this claim" % (cited,))
            else:
                reason = ("unpinned: no source states this claim "
                          "(no supports_claim match, no citation)")
            dropped.append({"claim": text, "reason": reason})
            continue
        entry = {"claim": text, "pinned_sources": pinned_ids, "status": "pinned"}
        if isinstance(claim, dict):
            for key, value in claim.items():
                if key not in ("claim", "text", "statement", "source_id",
                               "source_ids", "sources", "sourceIds",
                               "pinned_sources", "status"):
                    entry[key] = value
        unknown = [c for c in cited if c not in by_id]
        if unknown:
            entry["warnings"] = ["cited source(s) not in source set: %s" % (", ".join(unknown))]
        pinned.append(entry)
        used_ids.update(pinned_ids)

    if ledger_path is not None and dropped:
        if _append_ledger_record is None:
            ledger_errors.append("ledger module unavailable; drops kept in brief['dropped'] only")
        else:
            for item in dropped:
                try:
                    _append_ledger_record(str(ledger_path), {
                        "kind": "brief-claim-dropped",
                        "question": question,
                        "claim": item["claim"] if isinstance(item["claim"], str) else repr(item["claim"]),
                        "reason": item["reason"],
                    })
                except Exception as exc:  # logged on the brief, never silent
                    ledger_errors.append("ledger write failed for claim %r: %s"
                                        % (item.get("claim"), exc))
                    break

    title = "Sourced brief — %s" % (question if len(question) <= 140 else question[:137] + "...")
    brief = {
        "title": title,
        "question": question,
        "claims": pinned,
        "dropped": dropped,
        "sources": [by_id[sid] for sid in sorted(used_ids)],
    }
    if ledger_errors:
        brief["ledger_errors"] = ledger_errors
    return brief


def _stance_of(source_id, by_id):
    rec = by_id.get(str(source_id))
    if rec is None:
        return "unknown"
    stance = rec.get("stance", "supports")
    return stance if stance in VALID_STANCES else "unknown"


def mark_contested(claims, sources=None):
    """Flag claims where sources disagree. Never silently resolved.

    claims: list of str or dict claims. Dicts may carry
      'pinned_sources' ([ids], as filed by assemble_brief) and/or
      'attestations' ([{'source_id', 'stance'}]).
    sources: optional list of source records used to look up each
      cited source's stance. Unknown ids (or no sources given) yield
      stance 'unknown' and are named, never guessed.

    Grouping: attestations are merged by normalized claim text, so two
    entries stating the same claim with opposing stances still collide.
    A claim with both 'supports' and 'disputes' stances is returned as
    a copy with status 'contested', naming both sides in
    'contested_by' plus an adjudication note. Claims without conflict
    keep (or gain) status 'pinned'. Contested claims are KEPT in the
    output -- flagging never drops a claim. Inputs are not mutated.
    """
    if not isinstance(claims, (list, tuple)):
        raise TypeError("claims must be a list, got %r" % type(claims).__name__)
    sources = list(sources) if sources is not None else []
    by_id = {}
    for rec in sources:
        if isinstance(rec, dict) and rec.get("id") is not None:
            by_id[str(rec["id"])] = rec

    normalized = []
    for claim in claims:
        text = _claim_text(claim)
        stances = {}
        ordered = []
        if isinstance(claim, dict):
            for sid in claim.get("pinned_sources", []) or []:
                sid = str(sid)
                if sid not in stances:
                    stances[sid] = _stance_of(sid, by_id)
                    ordered.append(sid)
            attest = claim.get("attestations", []) or []
            if isinstance(attest, (list, tuple)):
                for item in attest:
                    if not isinstance(item, dict):
                        continue
                    sid = item.get("source_id", item.get("id"))
                    if sid is None:
                        continue
                    sid = str(sid)
                    stance = item.get("stance", _stance_of(sid, by_id))
                    if stance not in VALID_STANCES and stance != "unknown":
                        stance = "unknown"
                    if sid not in stances:
                        stances[sid] = stance
                        ordered.append(sid)
                    elif stances[sid] == "unknown" and stance in VALID_STANCES:
                        stances[sid] = stance
        normalized.append((claim, text, ordered, stances))

    by_text = {}
    for _, text, ordered, stances in normalized:
        key = _normalize_text(text)
        bucket = by_text.setdefault(key, {})
        for sid in ordered:
            bucket.setdefault(sid, stances[sid])

    out = []
    for claim, text, ordered, stances in normalized:
        merged = by_text[_normalize_text(text)]
        supports = sorted(s for s, st in merged.items() if st == "supports")
        disputes = sorted(s for s, st in merged.items() if st == "disputes")
        unknown = sorted(s for s, st in merged.items() if st not in VALID_STANCES)
        if isinstance(claim, dict):
            entry = dict(claim)
            entry.setdefault("claim", text)
        else:
            entry = {"claim": text}
        if supports and disputes:
            entry["status"] = "contested"
            entry["contested_by"] = {"supports": supports, "disputes": disputes}
            if unknown:
                entry["contested_by"]["unknown_stance"] = unknown
            entry["note"] = ("CONTESTED: sources disagree on this claim; "
                             "held for human adjudication, never silently resolved.")
        else:
            entry.setdefault("status", "pinned")
            if unknown and isinstance(claim, dict):
                entry.setdefault("warnings", []).append(
                    "stance unknown for source(s): %s" % (", ".join(unknown)))
        out.append(entry)
    return out


# ------------------------------------------------------------------
# Source parsing, dedupe, shelves, citations, and schema conformance
# (Section 5, CB2-101..125). Everything here is local and deterministic.
# ------------------------------------------------------------------

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
YEAR_RE = re.compile(r"^\d{4}$")
ARCHIVE_URL_RE = re.compile(
    r"^https?://(?:www\.)?archive\.org/", re.IGNORECASE)

SHELF_NAMES = ("biology", "chemistry", "materials", "physics_math")
UNFILED_SHELF = "unfiled"


class LiteratureSourceError(ValueError):
    """A source record cannot be parsed as a real source."""


def normalize_doi(value):
    """Return a lowercase bare DOI, or None. Never guesses one."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().rstrip(".,;")
    match = DOI_RE.search(text)
    return match.group(0).lower() if match else None


def normalize_authors(value):
    """A single author string or a list both become a clean list.

    Whitespace-only entries are dropped. Order is preserved and no
    author is invented.
    """
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        parts = text.split(";") if ";" in text else [text]
    elif isinstance(value, (list, tuple)):
        parts = value
    else:
        raise LiteratureSourceError(
            "authors must be a string or a list, got %r"
            % type(value).__name__)
    authors = []
    for part in parts:
        if not isinstance(part, str):
            continue
        name = part.strip()
        if name and name not in authors:
            authors.append(name)
    return authors


def parse_year(value):
    """A four-digit year as int; a range is refused, never split."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise LiteratureSourceError("year must be a four-digit year, got a bool")
    if isinstance(value, int):
        if 1000 <= value <= 9999:
            return value
        raise LiteratureSourceError(
            "year must be a four-digit year, got %r" % (value,))
    if isinstance(value, str):
        text = value.strip()
        if YEAR_RE.match(text):
            return int(text)
        raise LiteratureSourceError(
            "year must be a four-digit year; ranges are not split: %r"
            % (value,))
    raise LiteratureSourceError(
        "year must be a four-digit year, got %r" % type(value).__name__)


def _source_doi(record):
    for field in ("doi", "identifier", "locator", "citation"):
        doi = normalize_doi(record.get(field))
        if doi:
            return doi
    return None


def parse_source(record, require_title=True):
    """Parse and normalise one source record.

    The schema's required fields are checked. `title` is required by
    this parser (the schema keeps it optional for display), because
    a source with no title cannot be cited or deduped by title.
    Missing abstracts stay None; an archive URL identifier stays an
    archive URL and is never relabelled as a DOI.
    """
    if not isinstance(record, dict):
        raise LiteratureSourceError(
            "source record must be an object, got %r"
            % type(record).__name__)
    title = record.get("title")
    if require_title and (not isinstance(title, str) or not title.strip()):
        raise LiteratureSourceError(
            "source record missing required field 'title'")
    errors = validate_source(record)
    if errors:
        raise LiteratureSourceError(
            "invalid source record: %s" % "; ".join(errors))

    parsed = dict(record)
    parsed["title"] = title.strip() if isinstance(title, str) else None
    parsed["authors"] = normalize_authors(record.get("authors"))
    abstract = record.get("abstract")
    parsed["abstract"] = (abstract if isinstance(abstract, str)
                          and abstract.strip() else None)
    parsed["year"] = parse_year(record.get("year"))

    doi = _source_doi(record)
    identifier = record.get("identifier")
    if not isinstance(identifier, str) or not identifier.strip():
        identifier = ("doi:%s" % doi) if doi else None
    if doi:
        identifier_type = "doi"
    elif isinstance(identifier, str) and ARCHIVE_URL_RE.match(identifier):
        identifier_type = "archive-url"
    elif isinstance(identifier, str) and identifier.startswith(("http://",
                                                               "https://")):
        identifier_type = "url"
    else:
        identifier_type = "none"
    parsed["doi"] = doi
    parsed["identifier"] = identifier
    parsed["identifier_type"] = identifier_type
    parsed["origin"] = record.get("origin") or record.get("server")
    return parsed


def _dedupe_key(record):
    doi = _source_doi(record)
    if doi:
        return ("doi", doi)
    title = record.get("title") or record.get("citation") or ""
    return ("title", _normalize_text(str(title)))


def dedupe_sources(records):
    """Keep the first source per DOI (case-insensitive) or title."""
    if not isinstance(records, (list, tuple)):
        raise TypeError("records must be a list, got %r"
                        % type(records).__name__)
    seen = set()
    kept = []
    for record in records:
        if not isinstance(record, dict):
            continue
        key = _dedupe_key(record)
        if key in seen:
            continue
        seen.add(key)
        kept.append(record)
    return kept


def assign_shelf(source):
    """The shelf a source belongs on; untagged sources are unfiled."""
    if not isinstance(source, dict):
        return UNFILED_SHELF
    raw = source.get("shelf") or source.get("tags") or \
        source.get("tag") or source.get("department")
    if isinstance(raw, str):
        tags = [raw]
    elif isinstance(raw, (list, tuple)):
        tags = [t for t in raw if isinstance(t, str)]
    else:
        tags = []
    for tag in tags:
        name = tag.strip().lower().replace("-", "_").replace(" ", "_")
        if name.startswith("shelves/"):
            name = name[len("shelves/"):]
        if name.endswith(".json"):
            name = name[:-5]
        if name in SHELF_NAMES:
            return name
    return UNFILED_SHELF


class ShelfIndex(object):
    """In-memory shelf index: file sources, then list in filing order."""

    def __init__(self):
        self._shelves = {}

    def file(self, source):
        parsed = parse_source(source)
        shelf = assign_shelf(parsed)
        self._shelves.setdefault(shelf, []).append(parsed)
        return shelf

    def list(self, shelf=None):
        if shelf is None:
            return {name: list(items)
                    for name, items in self._shelves.items()}
        return list(self._shelves.get(shelf, []))


def format_citation(source):
    """A deterministic citation string from parsed source fields."""
    if not isinstance(source, dict):
        raise LiteratureSourceError("citation source must be an object")
    authors = normalize_authors(source.get("authors"))
    author_text = ", ".join(authors) if authors else "Unknown author"
    year = parse_year(source.get("year"))
    year_text = str(year) if year is not None else "n.d."
    title = str(source.get("title") or "").strip()
    parts = ["%s (%s)." % (author_text, year_text)]
    if title:
        parts.append(title + ".")
    venue = str(source.get("venue") or "").strip()
    if venue:
        parts.append(venue + ".")
    doi = _source_doi(source)
    if doi:
        parts.append("doi:%s." % doi)
    else:
        identifier = source.get("identifier") or source.get("locator")
        if isinstance(identifier, str) and identifier.startswith(
                ("http://", "https://")):
            parts.append(identifier + ".")
    return " ".join(parts)


def parse_source_corpus(records):
    """Parse a mixed corpus and count parsed, rejected, duplicate rows."""
    if not isinstance(records, (list, tuple)):
        raise TypeError("records must be a list, got %r"
                        % type(records).__name__)
    parsed = []
    rejected = []
    duplicates = 0
    seen = set()
    for index, record in enumerate(records):
        try:
            item = parse_source(record)
        except (LiteratureSourceError, TypeError) as exc:
            rejected.append({"index": index, "error": str(exc)})
            continue
        key = _dedupe_key(item)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        parsed.append(item)
    return {
        "parsed": parsed,
        "rejected": rejected,
        "duplicates": duplicates,
        "counts": {
            "received": len(records),
            "parsed": len(parsed),
            "rejected": len(rejected),
            "duplicates": duplicates,
        },
    }


def validate_against_schema(record, schema):
    """Validate the subset of JSON Schema this repo's schemas use.

    Supports object/array/string/integer/number/boolean/null, required,
    properties, minLength, pattern, and enum. Unknown schema keywords are
    ignored (the schemas are plain). Returns a list of named errors.
    """
    errors = []
    if not isinstance(schema, dict):
        return ["schema must be an object"]
    expected = schema.get("type")
    types = {
        "object": dict, "array": (list, tuple), "string": str,
        "integer": int, "number": (int, float), "boolean": bool,
    }
    if expected in types:
        value_ok = isinstance(record, types[expected])
        if expected in ("integer", "number") and isinstance(record, bool):
            value_ok = False
        if not value_ok:
            return ["value is not of schema type %r" % expected]
    if not isinstance(record, dict):
        return errors
    for field in schema.get("required") or []:
        if record.get(field) is None:
            errors.append("missing required field %r" % (field,))
    for field, rule in (schema.get("properties") or {}).items():
        if not isinstance(rule, dict) or field not in record:
            continue
        value = record.get(field)
        if value is None:
            continue
        rule_type = rule.get("type")
        if rule_type in types and not isinstance(value, types[rule_type]):
            errors.append("field %r must be %r" % (field, rule_type))
            continue
        if isinstance(value, str):
            minimum = rule.get("minLength")
            if isinstance(minimum, int) and len(value) < minimum:
                errors.append("field %r is shorter than minLength %d"
                              % (field, minimum))
            pattern = rule.get("pattern")
            if isinstance(pattern, str) and not re.fullmatch(pattern, value):
                errors.append("field %r does not match %r" % (field, pattern))
        enum = rule.get("enum")
        if isinstance(enum, list) and value not in enum:
            errors.append("field %r must be one of %r" % (field, enum))
    return errors


def validate_source_against_schema(record, schema_path=SOURCE_SCHEMA_FILENAME):
    """Load schemas/source.schema.json and validate one parsed source."""
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    return validate_against_schema(record, schema)
