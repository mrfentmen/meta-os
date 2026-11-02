"""Breeding variants as experiment variants (Section 7, tasks 62-67).

A Variant is a plan delta with its own seed and its own falsifier.
Variants are proposed via reasoning.generate_hypotheses (each variant
carries the disproof_condition of its hypothesis; a variant without a
falsifier is rejected, never run), executed through the Computational
Lab path (compute.run_experiment / the department runners -- same
records, same budgets, no side door), and selected AFTER results only
against a pre-registered rule. Losing variants are preserved in the
Knowledge Repository as negative results at their true level.

Hortus (hortus/engine.py) is audited in hortus_audit.md, not
reimplemented here. hortus/ is READ-ONLY: this module imports it when
importable and records what it found, but Hortus's genetic algorithm
searches heatsink genomes under hortus/model.py -- it does not mutate
experiment plans, so variant deltas come from
reasoning.generate_hypotheses. Where Hortus is not importable from the
caller's path, an UNIMPLEMENTED marker is carried instead of inventing
a Hortus call. Stdlib only.

Task map:
  62 new_variant(): plan delta + seed + falsifier; empty falsifier
     refused with ValueError.
  63 propose_variants(): hypotheses from a plan via
     reasoning.generate_hypotheses plus a Hortus availability note.
  64 run_variant(): through compute (run_experiment or the matching
     department runner); same record schema, same sandbox rule.
  65 select_survivor(): AFTER results only, against a filed
     pre-registration (kind 'preregistration' + entry_hash);
     unregistered rules refused with ValueError.
  66 build_lineage()/verify_lineage(): parent -> variants -> survivor,
     sha256 hash-linked.
  67 preserve_dead_ends(): losing variants filed in the repository as
     negative results at level <= 2 (unverified cap).
"""

import hashlib
import json
from datetime import datetime, timezone

try:
    from . import compute as _compute_mod
    from . import reasoning as _reasoning_mod
    from . import ledger as _ledger_mod
    from . import repository as _repository_mod
except ImportError:  # tests put science-lab dir on sys.path directly
    try:
        import compute as _compute_mod
    except ImportError:
        _compute_mod = None
    try:
        import reasoning as _reasoning_mod
    except ImportError:
        _reasoning_mod = None
    try:
        import ledger as _ledger_mod
    except ImportError:
        _ledger_mod = None
    try:
        import repository as _repository_mod
    except ImportError:
        _repository_mod = None

#: Marker for Hortus work this module will not invent. Hortus's GA
#: searches heatsink genomes, not experiment plans; where Hortus is
#: not importable, this marker is carried instead of a fake call.
UNIMPLEMENTED = "UNIMPLEMENTED"

HORTUS_ENGINE_NAME = "hortus"
HORTUS_EVIDENCE_CAP = 2


def _utcnow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hortus_status():
    """Report whether hortus.engine imports from here, honestly.

    Returns a dict: available True/False plus engine name/version
    when importable, else the UNIMPLEMENTED marker and the reason.
    Never raises for a missing Hortus: unavailability is a finding.
    """
    for attempt in ("package-relative", "top-level"):
        try:
            if attempt == "package-relative":
                from .hortus import engine as _eng  # noqa
            else:
                from hortus import engine as _eng  # noqa
        except ImportError:
            continue
        return {
            "available": True,
            "import_path": attempt,
            "engine": getattr(_eng, "ENGINE_NAME", HORTUS_ENGINE_NAME),
            "version": getattr(_eng, "ENGINE_VERSION", "unknown"),
            "model": getattr(_eng, "MODEL_ID", "unknown"),
            "evidence_level_cap": getattr(_eng, "EVIDENCE_LEVEL_CAP",
                                         HORTUS_EVIDENCE_CAP),
            "note": ("hortus.engine imports; its GA (run_evolution) "
                     "searches heatsink genomes under hortus/model.py, "
                     "not experiment plans, so variant deltas here come "
                     "from reasoning.generate_hypotheses; Hortus is "
                     "recorded as provenance, not used as a plan mutator."),
        }
    return {
        "available": False,
        "marker": UNIMPLEMENTED,
        "note": ("%s: hortus.engine not importable from this path; "
                 "variants proposed by reasoning.generate_hypotheses "
                 "alone; no Hortus call invented." % (UNIMPLEMENTED,)),
    }


# ------------------------------------------------------------------
# Task 62: variant record
# ------------------------------------------------------------------

def new_variant(variant_id, parent_plan, delta, seed, falsifier,
                hypothesis_id=None):
    """Build a variant: plan delta + own seed + own falsifier.

    variant_id/parent_plan/delta/seed are required; falsifier must be
    a non-empty string or the variant is refused with ValueError (a
    variant without a falsifier cannot be proposed, run, or
    selected). The runnable plan is the parent plan with the delta
    applied, the seed set, and the hypothesis link attached. Pure.
    """
    if not isinstance(variant_id, str) or not variant_id.strip():
        raise ValueError("new_variant requires a non-empty variant_id")
    if not isinstance(parent_plan, dict):
        raise TypeError("parent_plan must be a dict, got %r"
                        % type(parent_plan).__name__)
    if not isinstance(delta, dict):
        raise TypeError("delta must be a dict, got %r"
                        % type(delta).__name__)
    if seed is None or isinstance(seed, bool):
        raise ValueError("new_variant requires a seed (int)")
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        raise ValueError("new_variant requires an int seed, got %r"
                         % (seed,))
    if not isinstance(falsifier, str) or not falsifier.strip():
        raise ValueError(
            "refused: variant %r carries no falsifier; a variant without "
            "a falsifier cannot be filed, run, or selected"
            % (variant_id,))
    plan = dict(parent_plan)
    plan.update(delta)
    plan["seed"] = seed
    plan["random_seed"] = seed
    parent_id = str(parent_plan.get("id", parent_plan.get("plan_id",
                                                           "P-UNLINKED")))
    plan["id"] = "%s-%s" % (parent_id, variant_id.strip())
    if hypothesis_id is not None:
        plan["hypothesis_id"] = str(hypothesis_id)
    return {
        "variant_id": variant_id.strip(),
        "parent_plan_id": parent_id,
        "delta": dict(delta),
        "seed": seed,
        "falsifier": falsifier.strip(),
        "hypothesis_id": str(hypothesis_id) if hypothesis_id is not None
        else str(parent_plan.get("hypothesis_id", "H-UNLINKED")),
        "plan": plan,
        "proposed_at": _utcnow(),
    }


# ------------------------------------------------------------------
# Task 63: variant generator job
# ------------------------------------------------------------------

def _plan_brief(plan):
    """Render a plan as the brief generate_hypotheses needs."""
    question = ""
    for key in ("research_question", "question", "title"):
        value = plan.get(key)
        if isinstance(value, str) and value.strip():
            question = value.strip()
            break
    if not question:
        raise ValueError("propose_variants requires a plan with a "
                         "research question (research_question/question)")
    claims = plan.get("claims")
    if not isinstance(claims, list):
        claims = []
    sources = plan.get("sources")
    if not isinstance(sources, list):
        sources = []
    return {"question": question, "claims": claims, "sources": sources}


def propose_variants(plan, n=3, base_seed=None):
    """Propose n variants of a plan (Task 63).

    Hypotheses come from reasoning.generate_hypotheses over the plan;
    each hypothesis becomes one variant carrying that hypothesis's
    disproof_condition as its falsifier. Candidates the generator
    rejects (no falsifier) are returned in 'rejected', never filed
    as variants. The 'hortus' entry records Hortus availability (see
    hortus_status): Hortus's GA is provenance here, not a plan
    mutator, and when Hortus is not importable an UNIMPLEMENTED
    marker is carried instead of inventing a call.

    Returns {"variants": [...], "rejected": [...], "hortus": {...}}.
    """
    if _reasoning_mod is None:
        raise RuntimeError(
            "propose_variants needs reasoning.py; module unavailable")
    if not isinstance(plan, dict):
        raise TypeError("plan must be a dict, got %r"
                        % type(plan).__name__)
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an int in 3..5, got %r" % (n,))
    if n < 3 or n > 5:
        raise ValueError("propose_variants drafts 3-5 variants, got n=%r"
                         % (n,))
    brief = _plan_brief(plan)
    hypotheses, rejected = _reasoning_mod.generate_hypotheses(brief, n)
    hstat = hortus_status()
    if base_seed is None:
        base_seed = plan.get("seed", plan.get("random_seed", 0))
    try:
        base_seed = int(base_seed)
    except (TypeError, ValueError):
        base_seed = 0
    variants = []
    for i, hyp in enumerate(hypotheses):
        seed = base_seed + i
        delta = {
            "hypothesis_id": hyp["id"],
            "hypothesis_version": "v%d" % (i + 1),
            "variant_index": i,
            "proposed_explanation": hyp["proposed_explanation"],
        }
        variants.append(new_variant(
            "V%03d" % (i + 1), plan, delta, seed,
            hyp["disproof_condition"], hypothesis_id=hyp["id"]))
        variants[-1]["hortus"] = hstat
    return {"variants": variants, "rejected": list(rejected),
            "hortus": hstat}


# ------------------------------------------------------------------
# Task 64: variant runner (same Computational Lab path, no side door)
# ------------------------------------------------------------------

def _dispatch_record(plan, timeout, ledger_path):
    """Run one runnable plan through compute; return the record."""
    if _compute_mod is None:
        raise RuntimeError(
            "run_variant needs compute.py; module unavailable")
    if plan.get("command"):
        return _compute_mod.run_experiment(plan, timeout=timeout,
                                           ledger_path=ledger_path)
    if "sequence" in plan:
        rec = _compute_mod.run_bio(plan)
    elif "formula" in plan or "dataset" in plan:
        rec = _compute_mod.run_chem(plan)
    elif "v0" in plan and "angle_deg" in plan:
        rec = _compute_mod.run_physics(plan)
    elif "fractions" in plan and "densities" in plan:
        rec = _compute_mod.run_materials(plan)
    else:
        raise ValueError(
            "run_variant refused: plan carries no runnable command "
            "('command') or department inputs (bio sequence / chem "
            "formula+dataset / physics v0+angle_deg / materials "
            "fractions+densities); refusing instead of inventing a run")
    if ledger_path is not None:
        _compute_mod.file_experiment_record(
            rec, ledger_path,
            agent=plan.get("agent", "computational-scientist"))
    return rec


def run_variant(variant, ledger_path=None, timeout=30, config=None,
                agent="computational-scientist"):
    """Execute one variant through the Computational Lab path.

    Dispatches to compute.run_experiment (command plans) or the
    matching department runner (bio/chem/physics/materials) -- the
    same record schema, the same sandbox rule, the same ledger
    filing as any lab computation. No side door: there is no other
    execution path in this module. Optional config enforces the
    compute budget first (cap reached -> PermissionError, no run).
    Returns {"variant_id", "record"}.
    """
    if not isinstance(variant, dict) or not isinstance(
            variant.get("plan"), dict):
        raise TypeError("variant must be a new_variant() dict with a "
                        "'plan'")
    if not variant.get("falsifier"):
        raise ValueError(
            "run_variant refused: variant %r carries no falsifier"
            % (variant.get("variant_id"),))
    if config is not None:
        if _compute_mod is None:
            raise RuntimeError("budget check needs compute.py")
        allowed, reason = _compute_mod.check_compute_budget(
            config, agent, 0, 0, 0.0)
        if not allowed:
            raise PermissionError("budget-cap-reached: %s" % (reason,))
    record = _dispatch_record(variant["plan"], timeout, ledger_path)
    return {"variant_id": variant["variant_id"], "record": record}


# ------------------------------------------------------------------
# Task 65: selection AFTER results, against the registered rule only
# ------------------------------------------------------------------

_REGISTERED_KIND = "preregistration"

_DIRECTIONS = (">=", "<=", ">", "<", "==")


def _parse_rule(registered_rule):
    """Normalise a registered rule to (kind, target, direction/tol).

    Accepts threshold rules (numeric 'threshold' + 'direction', or a
    {'value', 'direction'} threshold mapping filed at registration)
    and expected-value rules ('expected_value' + 'tolerance').
    Raises ValueError when the rule carries no numeric criterion.
    """
    if not isinstance(registered_rule, dict):
        raise TypeError("registered rule must be a dict, got %r"
                        % type(registered_rule).__name__)
    direction = registered_rule.get("direction")
    threshold = registered_rule.get("threshold")
    if isinstance(threshold, dict):
        direction = threshold.get("direction", direction)
        threshold = threshold.get("value", threshold.get("threshold"))
    if threshold is not None and not isinstance(threshold, bool):
        try:
            target = float(threshold)
        except (TypeError, ValueError):
            target = None
        else:
            direction = str(direction or ">=").strip()
            if direction not in _DIRECTIONS:
                raise ValueError(
                    "selection refused: rule direction %r not one of %s"
                    % (direction, list(_DIRECTIONS)))
            return ("threshold", target, direction)
    for key in ("expected_value", "expected", "prediction"):
        if registered_rule.get(key) is not None:
            try:
                target = float(registered_rule[key])
            except (TypeError, ValueError):
                continue
            try:
                tol = float(registered_rule.get("tolerance",
                                                registered_rule.get("tol",
                                                                    0.0)))
            except (TypeError, ValueError):
                tol = 0.0
            return ("expected", target, abs(tol))
    raise ValueError(
        "selection refused: registered rule carries no numeric "
        "criterion (needs 'threshold' + 'direction' or "
        "'expected_value' + 'tolerance')")


def _observed_number(record):
    """Numeric observation from a variant's experiment record."""
    for key in ("value", "observed", "observed_value", "result"):
        val = record.get(key)
        if isinstance(val, bool):
            continue
        if isinstance(val, (int, float)):
            return float(val)
    params = record.get("parameters")
    if isinstance(params, dict):
        for key in ("result", "range_m", "density", "gc_fraction",
                    "exact_mass_da", "value"):
            val = params.get(key)
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                return float(val)
    return None


def select_survivor(results, registered_rule, ledger_path=None):
    """Select the surviving variant AFTER results exist (Task 65).

    results: non-empty list of run_variant() outputs, each carrying
    a completed experiment 'record' (crashed records with
    output_hash None are ranked as failed, never selected).
    registered_rule: the filed pre-registration entry (kind
    'preregistration' with an entry_hash proving it was filed in
    the ledger BEFORE results). An ad-hoc rule without that proof
    is refused with ValueError -- selection against an
    unregistered rule never happens.

    Threshold rule: every variant whose observed value meets the
    threshold in the stated direction passes; the survivor is the
    pass with the extreme value in the winning direction (max for
    >=/>, min for <=/<, exact for ==). Expected-value rule: passes
    within tolerance win; the survivor minimises |observed-target|.
    No passes -> survivor None (honest: every variant is a
    dead end). Filed to ledger_path when given. Returns the
    selection record.
    """
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("select_survivor requires a non-empty results list")
    if not isinstance(registered_rule, dict):
        raise TypeError("registered rule must be a dict")
    if registered_rule.get("kind") != _REGISTERED_KIND:
        raise ValueError(
            "selection refused: rule is not a filed pre-registration "
            "(kind %r, need %r); selection against an unregistered "
            "rule never happens"
            % (registered_rule.get("kind"), _REGISTERED_KIND))
    if not registered_rule.get("entry_hash"):
        raise ValueError(
            "selection refused: rule carries no entry_hash proof of "
            "ledger filing; selection against an unregistered rule "
            "never happens")
    if ledger_path is not None and _ledger_mod is not None:
        hashes = {e.get("entry_hash") for e in _ledger_mod.read_all(
            ledger_path) if isinstance(e, dict)}
        if registered_rule["entry_hash"] not in hashes:
            raise ValueError(
                "selection refused: rule entry_hash %r not found in "
                "ledger %r; the rule was not registered there"
                % (registered_rule["entry_hash"][:12], ledger_path))
    kind, target, tol_or_dir = _parse_rule(registered_rule)
    for pos, item in enumerate(results):
        if not isinstance(item, dict) or not isinstance(
                item.get("record"), dict):
            raise ValueError(
                "selection refused: result %d is not a completed "
                "run_variant() output; selection happens AFTER results "
                "only" % (pos,))
        if "output_hash" not in item["record"]:
            raise ValueError(
                "selection refused: variant %r has no completed "
                "experiment record yet"
                % (item.get("variant_id"),))
    candidates = []
    for item in results:
        record = item["record"]
        observed = _observed_number(record)
        crashed = record.get("output_hash") is None
        if crashed or observed is None:
            verdict = "no-match"
            detail = ("crashed run (output_hash null)" if crashed
                      else "no numeric observation in record")
        elif kind == "threshold":
            ops = {">=": observed >= target, "<=": observed <= target,
                   ">": observed > target, "<": observed < target,
                   "==": observed == target}
            verdict = "match" if ops[tol_or_dir] else "no-match"
            detail = ("observed=%r threshold=%r direction=%r"
                      % (observed, target, tol_or_dir))
        else:
            verdict = ("match" if abs(observed - target) <= tol_or_dir
                       else "no-match")
            detail = ("observed=%r expected=%r tolerance=%r"
                      % (observed, target, tol_or_dir))
        candidates.append({
            "variant_id": item.get("variant_id"),
            "experiment_id": record.get("id"),
            "observed": observed,
            "crashed": crashed,
            "verdict": verdict,
            "detail": detail,
        })
    passes = [c for c in candidates if c["verdict"] == "match"]
    survivor = None
    if passes:
        if kind == "threshold":
            if tol_or_dir in (">=", ">"):
                survivor = max(passes, key=lambda c: c["observed"])
            elif tol_or_dir in ("<=", "<"):
                survivor = min(passes, key=lambda c: c["observed"])
            else:
                survivor = passes[0]
        else:
            survivor = min(passes,
                           key=lambda c: abs(c["observed"] - target))
    selection = {
        "kind": "breeding-selection",
        "rule_kind": registered_rule.get("kind"),
        "rule_entry_hash": registered_rule.get("entry_hash"),
        "rule_test": registered_rule.get("test"),
        "rule_hypothesis_id": registered_rule.get("hypothesis_id"),
        "criterion": ("threshold=%r direction=%r" % (target, tol_or_dir)
                      if kind == "threshold"
                      else "expected=%r tolerance=%r" % (target,
                                                        tol_or_dir)),
        "candidates": candidates,
        "survivor_id": (survivor["variant_id"] if survivor is not None
                        else None),
        "survivor_measured": (survivor["observed"] if survivor is not None
                              else None),
        "recorded_at": _utcnow(),
    }
    if ledger_path is not None:
        if _ledger_mod is None:
            raise RuntimeError(
                "selection filing needs ledger.py; module unavailable")
        selection = _ledger_mod.append_record(ledger_path, selection)
    return selection


# ------------------------------------------------------------------
# Task 66: lineage record, hash-linked
# ------------------------------------------------------------------

def build_lineage(parent_plan, variants, selection, ledger_path=None):
    """File parent plan -> variants -> survivor, hash-linked.

    parent_hash = sha256(canonical parent plan); each variant links
    parent_hash + variant_id + seed + falsifier; the lineage head
    links every variant hash plus the survivor id. Returns the
    lineage record (filed to ledger_path when given).
    """
    if not isinstance(parent_plan, dict):
        raise TypeError("parent_plan must be a dict")
    if not variants:
        raise ValueError("build_lineage requires at least one variant")
    if not isinstance(selection, dict):
        raise TypeError("selection must be a selection record dict")
    parent_hash = hashlib.sha256(_canonical(parent_plan)).hexdigest()
    links = []
    for variant in variants:
        if not isinstance(variant, dict) or not variant.get("variant_id"):
            raise ValueError("lineage refused: malformed variant entry")
        vhash = _sha256_text("|".join((
            parent_hash, str(variant["variant_id"]),
            str(variant.get("seed")), str(variant.get("falsifier")))))
        links.append({
            "variant_id": variant["variant_id"],
            "seed": variant.get("seed"),
            "variant_hash": vhash,
            "parent_hash": parent_hash,
        })
    head = _sha256_text("|".join(
        [parent_hash]
        + [link["variant_hash"] for link in links]
        + [str(selection.get("survivor_id"))]))
    lineage = {
        "kind": "breeding-lineage",
        "parent_plan_id": str(parent_plan.get(
            "id", parent_plan.get("plan_id", "P-UNLINKED"))),
        "parent_hash": parent_hash,
        "variants": links,
        "survivor_id": selection.get("survivor_id"),
        "selection_criterion": selection.get("criterion"),
        "rule_entry_hash": selection.get("rule_entry_hash"),
        "lineage_hash": head,
        "recorded_at": _utcnow(),
    }
    if ledger_path is not None:
        if _ledger_mod is None:
            raise RuntimeError(
                "lineage filing needs ledger.py; module unavailable")
        lineage = _ledger_mod.append_record(ledger_path, lineage)
        if lineage.get("lineage_hash") != head:
            raise AssertionError(
                "ledger filing must not rewrite the lineage hash")
    return lineage


def verify_lineage(lineage, parent_plan=None, variants=None):
    """Verify a lineage record's hash links. Returns (ok, msg).

    With parent_plan + variants supplied, every link is recomputed;
    otherwise the record's internal consistency (head over its own
    links) is checked. Never raises for a bad chain: a break is a
    (False, reason) finding.
    """
    if not isinstance(lineage, dict):
        return (False, "not a lineage record dict")
    links = lineage.get("variants")
    if not isinstance(links, list) or not links:
        return (False, "lineage carries no variant links")
    if parent_plan is not None:
        try:
            parent_hash = hashlib.sha256(
                _canonical(parent_plan)).hexdigest()
        except Exception as exc:
            return (False, "parent plan not hashable: %s" % (exc,))
        if lineage.get("parent_hash") != parent_hash:
            return (False, "parent_hash mismatch: lineage does not "
                    "descend from this parent plan")
        by_id = {}
        if variants is not None:
            for variant in variants:
                if isinstance(variant, dict) and variant.get("variant_id"):
                    by_id[variant["variant_id"]] = variant
        for link in links:
            # Recompute strictly when the variant dicts are supplied
            # (falsifier text lives in the variant, not the link, so a
            # bare link can only be shape-checked, not re-derived).
            if variants is not None:
                variant = by_id.get(link.get("variant_id"))
                if variant is None:
                    return (False, "variant %r in lineage but not "
                            "supplied" % (link.get("variant_id"),))
                strict = _sha256_text("|".join((
                    parent_hash, str(variant["variant_id"]),
                    str(variant.get("seed")),
                    str(variant.get("falsifier")))))
                if link.get("variant_hash") != strict:
                    return (False, "variant_hash mismatch for %r"
                            % (link.get("variant_id"),))
                if link.get("parent_hash") != parent_hash:
                    return (False, "link parent_hash mismatch for %r"
                            % (link.get("variant_id"),))
            else:
                if not link.get("variant_hash") or \
                        link.get("parent_hash") != lineage.get(
                            "parent_hash"):
                    return (False, "link shape broken for %r"
                            % (link.get("variant_id"),))
    head = _sha256_text("|".join(
        [str(lineage.get("parent_hash"))]
        + [str(link.get("variant_hash")) for link in links]
        + [str(lineage.get("survivor_id"))]))
    if lineage.get("lineage_hash") != head:
        return (False, "lineage_hash mismatch: head does not cover "
                "parent + variants + survivor")
    return (True, "ok: %d variant links verify, survivor %r"
            % (len(links), lineage.get("survivor_id")))


# ------------------------------------------------------------------
# Task 67: dead-end preservation (negative results at true level)
# ------------------------------------------------------------------

def preserve_dead_ends(results, survivor_id, base=None):
    """File every losing variant as a negative result (Task 67).

    Each non-survivor with a completed record is filed in the
    repository: an experiment pointer at its true (capped) level --
    unverified runs cap at 2 -- and a negative-result claim at the
    same level stating it did not meet the pre-registered rule. The
    survivor is filed as an experiment pointer only (surviving
    selection is not a discovery claim). Returns the filed entries.
    """
    if _repository_mod is None:
        raise RuntimeError(
            "preserve_dead_ends needs repository.py; module unavailable")
    filed = []
    for item in results or []:
        if not isinstance(item, dict) or not isinstance(
                item.get("record"), dict):
            continue
        record = item["record"]
        vid = item.get("variant_id")
        try:
            level = int(record.get("evidence_level", 2))
        except (TypeError, ValueError):
            level = 2
        level = max(0, min(level, HORTUS_EVIDENCE_CAP))
        filed.append(_repository_mod.file_experiment({
            "experiment_id": str(record.get("id", vid)),
            "variant_id": vid,
            "level": level,
            "department": record.get("parameters", {}).get(
                "_dept", "computation"),
            "agent": "breeding-round",
            "selection": ("survivor" if vid == survivor_id
                          else "dead-end"),
            "output_hash": record.get("output_hash"),
        }, base=base))
        if vid != survivor_id:
            filed.append(_repository_mod.file_claim({
                "claim_id": "NEG-%s" % (vid,),
                "statement": ("Breeding variant %s did not meet the "
                              "pre-registered selection rule; kept as a "
                              "negative result, not re-run blindly."
                              % (vid,)),
                "level": level,
                "experiment_ids": [str(record.get("id", vid))],
            }, base=base))
    return filed


__all__ = [
    "UNIMPLEMENTED",
    "hortus_status",
    "new_variant",
    "propose_variants",
    "run_variant",
    "select_survivor",
    "build_lineage",
    "verify_lineage",
    "preserve_dead_ends",
]
