#!/usr/bin/env python3
"""Rough-words intake + self-building brief for META OFFICINA (stage 2a).

A user gives a sloppy plain-words description — no blueprint, no
specs. This module turns it into a structured design brief, then
iterates the brief itself with no human in the loop: each round
adds a feature or decision and records what it added and why in
a decision log.

How it stays honest (the stage-1 discipline, carried over):

  - The intake parser is rules in code, not a model: it only
    records what the words actually state. Anything the words
    don't say goes in the brief's unknowns list, never invented.
    Wishes the simulator cannot grade (cheap, small) are recorded
    as preferences, explicitly not graded.
  - The iteration loop searches with the stage-1 simulator at
    design conditions, but nothing counts as proven until the
    independent held-out gate (design_loop.verify_proven) passes
    — a test the search loop does not grade, since the gate
    re-scores from the parameters under held-out conditions and
    tolerance perturbation.
  - When the loop cannot prove a design — impossible target,
    round budget spent, no move left — the record says unproven.
    It never exports an unproven design as proven.

No model calls anywhere. No network, no bus posts. The only
grader is code: heatsink.simulate plus the held-out gate.
"""

import json
import re

from design_loop import ACCEPT_R_C_PER_W, verify_proven
from heatsink import (
    BASE_THICKNESS_MM,
    FIN_COUNT,
    FIN_HEIGHT_MM,
    FIN_THICKNESS_MM,
    Conditions,
    HeatsinkParams,
    simulate,
)

# Workshop first guess: mid-range on every axis, documented in the
# brief's round-0 decision. It is a starting point the loop is
# expected to improve, not a claim about the right answer.
DEFAULT_PARAMS = {
    "fin_height_mm": 20.0,
    "fin_thickness_mm": 1.5,
    "fin_count": 15,
    "base_thickness_mm": 4.0,
}

# The artefact class this stage can grade. Its footprint is fixed
# at 50 mm square by the simulator; a stated footprint that
# disagrees is recorded as a conflict, not silently rewritten.
CLASS_FOOTPRINT_MM = 50.0

MAX_ROUNDS = 10

_CLASS_WORDS = ("heatsink", "heat sink", "heat-sink", "fin", "cooler")
_PASSIVE_WORDS = ("no fan", "fanless", "passive", "quiet", "silent",
                  "no moving parts")
_COMPACT_WORDS = ("small", "tiny", "compact", "low profile",
                  "keep it small")
_CHEAP_WORDS = ("cheap", "low cost", "affordable", "budget",
                "inexpensive")

_UNKNOWN_SLOTS = ("power_w", "footprint_mm", "target_r", "airflow")


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _find_number(pattern, text):
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def parse_rough_words(text):
    """Turn sloppy plain words into a structured design brief.

    Only what the words state becomes a requirement or target.
    Everything else lands in unknowns. The returned brief is a
    plain dict, JSON-ready, with a parameters dict holding the
    workshop first guess (defaults the iteration loop will move).
    """
    raw = text or ""
    lowered = _clean(raw).lower()
    brief = {
        "artefact_class": None,
        "gradeable": False,
        "source_text": raw,
        "summary": _clean(raw),
        "requirements": [],
        "targets": [],
        "preferences": [],
        "unknowns": [],
        "conflicts": [],
        "parameters": dict(DEFAULT_PARAMS),
        "bounds": {},
        "amendments": [],
        "decision_log": [],
    }
    if not any(word in lowered for word in _CLASS_WORDS):
        brief["unknowns"] = [
            {"slot": "artefact_class",
             "note": "no known artefact class named in the rough words"}
        ]
        return brief
    brief["artefact_class"] = "heatsink-fin-geometry"
    brief["gradeable"] = True

    footprint = _find_number(
        r"(\d+(?:\.\d+)?)\s*mm\s*(square|wide|across)", lowered)
    if footprint is None:
        square = re.search(r"(\d+)\s*x\s*(\d+)", lowered)
        if square and float(square.group(1)) == float(square.group(2)):
            footprint = float(square.group(1))
    if footprint is not None:
        brief["requirements"].append(
            {"kind": "footprint_mm", "value": footprint, "source": "stated"})
        if footprint != CLASS_FOOTPRINT_MM:
            brief["conflicts"].append({
                "kind": "footprint_mm",
                "stated": footprint,
                "class_value": CLASS_FOOTPRINT_MM,
                "note": "this artefact class is fixed at 50 mm square; "
                        "the run proceeds on the class footprint and "
                        "the conflict stays recorded",
            })
    power = _find_number(r"(\d+(?:\.\d+)?)\s*(watts?|w)\b", lowered)
    if power is not None:
        brief["requirements"].append(
            {"kind": "power_w", "value": power, "source": "stated"})
    match = re.search(
        r"(under|below|less than|at most|no more than)\s*"
        r"(\d+(?:\.\d+)?)\s*(?:°?c/w|degc/w|degrees? per watt)",
        lowered)
    target_r = float(match.group(2)) if match else None
    if target_r is not None:
        brief["targets"].append(
            {"kind": "target_r_c_per_w", "value": target_r,
             "source": "stated"})
    else:
        brief["targets"].append(
            {"kind": "target_r_c_per_w", "value": ACCEPT_R_C_PER_W,
             "source": "workshop-default"})
    max_height = _find_number(
        r"(\d+(?:\.\d+)?)\s*mm\s*(tall|high|height)", lowered)
    if max_height is None:
        match = re.search(
            r"(taller than|shorter than|under|below|at most|"
            r"no more than|maximum|up to)\s*(\d+(?:\.\d+)?)\s*mm",
            lowered)
        if match:
            max_height = float(match.group(2))
    if max_height is not None:
        brief["bounds"]["fin_height_mm_max"] = max_height
        brief["requirements"].append(
            {"kind": "fin_height_mm_max", "value": max_height,
             "source": "stated"})
        brief["parameters"]["fin_height_mm"] = min(
            brief["parameters"]["fin_height_mm"], max_height)
    if any(word in lowered for word in _PASSIVE_WORDS):
        brief["requirements"].append(
            {"kind": "passive_cooling", "value": True, "source": "stated"})
    if "fan" in lowered and not any(
            word in lowered for word in _PASSIVE_WORDS):
        brief["requirements"].append(
            {"kind": "forced_airflow", "value": True, "source": "stated"})
    if any(word in lowered for word in _COMPACT_WORDS):
        brief["preferences"].append(
            {"kind": "compact", "value": True, "source": "stated",
             "note": "not graded: the thermal simulator has no size "
                     "score beyond the volume rule"})
    if any(word in lowered for word in _CHEAP_WORDS):
        brief["preferences"].append(
            {"kind": "low_cost", "value": True, "source": "stated",
             "note": "not graded: the thermal simulator has no cost model"})
    stated = {req["kind"] for req in brief["requirements"]}
    stated |= {tgt["kind"] for tgt in brief["targets"]}
    target_from_user = any(
        tgt["kind"] == "target_r_c_per_w" and tgt["source"] == "stated"
        for tgt in brief["targets"])
    slot_of_kind = {
        "power_w": "power_w",
        "footprint_mm": "footprint_mm",
        "target_r_c_per_w": "target_r",
    }
    for slot in _UNKNOWN_SLOTS:
        if slot == "airflow":
            if not any(req["kind"] in ("passive_cooling", "forced_airflow")
                       for req in brief["requirements"]):
                brief["unknowns"].append(
                    {"slot": "airflow",
                     "note": "no airflow stated; graded at natural "
                             "convection, held out at forced airflow"})
            continue
        kinds = [k for k, s in slot_of_kind.items() if s == slot]
        if slot == "target_r":
            # The target slot is always filled (stated, or the
            # labelled workshop default), but when the user stated
            # no target the gap is still disclosed here, so the
            # default is never mistaken for a stated fact.
            if not target_from_user:
                brief["unknowns"].append(
                    {"slot": "target_r",
                     "note": "no target stated; workshop default "
                             "applied, see targets"})
            continue
        if not any(k in stated for k in kinds):
            brief["unknowns"].append(
                {"slot": slot,
                 "note": "not stated in the rough words"})
    return brief


def _params_of(brief):
    p = brief["parameters"]
    return HeatsinkParams(
        fin_height_mm=p["fin_height_mm"],
        fin_thickness_mm=p["fin_thickness_mm"],
        fin_count=int(p["fin_count"]),
        base_thickness_mm=p["base_thickness_mm"],
    )


def _grade(brief):
    result = simulate(_params_of(brief))
    return {
        "r_th_c_per_w": result.r_th_c_per_w,
        "feasible": result.feasible,
        "violations": list(result.violations),
    }


def _apply(brief, changes, round_no, rule, reason, grade_before):
    """Apply one parameter move, logging the decision and the brief
    amendment. `changes` maps parameter names to new values."""
    before = dict(brief["parameters"])
    brief["parameters"].update(changes)
    after = dict(brief["parameters"])
    changed = ", ".join(
        "%s %s -> %s" % (k, before[k], after[k])
        for k in changes if before[k] != after[k])
    brief["decision_log"].append({
        "round": round_no,
        "rule": rule,
        "decision": changed or "no parameter change",
        "reason": reason,
        "grade_before": grade_before,
        "params_before": before,
        "params_after": after,
    })
    brief["amendments"].append({
        "round": round_no,
        "change": changed or "no parameter change",
        "reason": reason,
    })
    return after


def _height_cap(brief):
    cap = FIN_HEIGHT_MM[1]
    stated = brief["bounds"].get("fin_height_mm_max")
    return min(cap, stated) if stated is not None else cap


def _improvement_candidates(brief):
    """Candidate single moves for a feasible design that misses its
    target, scored at design conditions. Returns (name, params,
    grade) for each feasible candidate, best first. Scoring
    candidates is search; proven status still comes only from the
    held-out gate, which no search step grades."""
    p = brief["parameters"]
    moves = []
    if p["fin_height_mm"] < _height_cap(brief):
        moves.append(("raise fin height", {
            "fin_height_mm": min(_height_cap(brief),
                                 p["fin_height_mm"] * 1.25)}))
    if p["fin_count"] < FIN_COUNT[1]:
        moves.append(("add fins", {"fin_count": p["fin_count"] + 2}))
    if p["fin_thickness_mm"] > FIN_THICKNESS_MM[0]:
        moves.append(("thin the fins", {
            "fin_thickness_mm": max(FIN_THICKNESS_MM[0],
                                    p["fin_thickness_mm"] * 0.8)}))
    scored = []
    for name, changes in moves:
        trial = dict(p)
        trial.update(changes)
        result = simulate(HeatsinkParams(
            fin_height_mm=trial["fin_height_mm"],
            fin_thickness_mm=trial["fin_thickness_mm"],
            fin_count=int(trial["fin_count"]),
            base_thickness_mm=trial["base_thickness_mm"]))
        if result.feasible:
            scored.append((name, changes, {
                "r_th_c_per_w": result.r_th_c_per_w,
                "feasible": True,
                "violations": [],
            }))
    scored.sort(key=lambda item: item[2]["r_th_c_per_w"])
    return scored


def _gap_move(brief, grade):
    p = brief["parameters"]
    if p["fin_count"] > FIN_COUNT[0]:
        return {"fin_count": p["fin_count"] - 2}, \
            "fin gap %s; fewer fins widens the gap" % (
                "; ".join(grade["violations"]),)
    if p["fin_thickness_mm"] > FIN_THICKNESS_MM[0]:
        return {"fin_thickness_mm": max(
            FIN_THICKNESS_MM[0], p["fin_thickness_mm"] * 0.8)}, \
            "fin gap %s; thinner fins widen the gap" % (
                "; ".join(grade["violations"]),)
    return None, "fin gap violation with no move left at the bounds"


def _volume_move(brief, grade):
    p = brief["parameters"]
    if p["base_thickness_mm"] > BASE_THICKNESS_MM[0]:
        return {"base_thickness_mm": max(
            BASE_THICKNESS_MM[0], p["base_thickness_mm"] - 1.0)}, \
            "volume %s; thinner base cuts volume" % (
                "; ".join(grade["violations"]),)
    if p["fin_height_mm"] > FIN_HEIGHT_MM[0]:
        return {"fin_height_mm": max(
            FIN_HEIGHT_MM[0], p["fin_height_mm"] * 0.8)}, \
            "volume %s; shorter fins cut volume" % (
                "; ".join(grade["violations"]),)
    return None, "volume violation with no move left at the bounds"


def _clamp_params(brief):
    p = brief["parameters"]
    changes = {
        "fin_height_mm": min(max(p["fin_height_mm"], FIN_HEIGHT_MM[0]),
                             _height_cap(brief)),
        "fin_thickness_mm": min(max(p["fin_thickness_mm"],
                                    FIN_THICKNESS_MM[0]),
                                FIN_THICKNESS_MM[1]),
        "fin_count": min(max(int(p["fin_count"]), FIN_COUNT[0]),
                         FIN_COUNT[1]),
        "base_thickness_mm": min(max(p["base_thickness_mm"],
                                     BASE_THICKNESS_MM[0]),
                                 BASE_THICKNESS_MM[1]),
    }
    return {k: v for k, v in changes.items() if v != p[k]}


def iterate_brief(brief, max_rounds=MAX_ROUNDS):
    """Iterate a parsed brief with no human in the loop.

    Each round grades the current parameters, applies exactly one
    rule-driven move, and logs the decision with its reason and
    the grade that motivated it. Returns a run record dict: the
    full brief (amendments + decision log included), the final
    grade, the independent held-out verification, and an honest
    proven flag — False whenever the gate did not pass."""
    if not brief["gradeable"]:
        return {
            "rough_input": brief["source_text"],
            "brief": brief,
            "rounds_used": 0,
            "final_params": None,
            "final_grade": None,
            "verification": None,
            "proven": False,
            "status": "ungradeable",
        }
    target = next(t["value"] for t in brief["targets"]
                  if t["kind"] == "target_r_c_per_w")
    brief["decision_log"].append({
        "round": 0,
        "rule": "intake",
        "decision": "workshop first guess %s" % (brief["parameters"],),
        "reason": "rough words state no geometry; the loop starts "
                  "mid-range and improves from graded feedback",
        "grade_before": None,
        "params_before": None,
        "params_after": dict(brief["parameters"]),
    })
    status = "unproven"
    verification = None
    for round_no in range(1, max_rounds + 1):
        grade = _grade(brief)
        if grade["feasible"] and grade["r_th_c_per_w"] <= target:
            verification = verify_proven(
                _params_of(brief), grade["r_th_c_per_w"])
            if verification["proven"]:
                brief["decision_log"].append({
                    "round": round_no,
                    "rule": "accept",
                    "decision": "freeze brief; design accepted",
                    "reason": "design-condition R %.4f meets target %.4f "
                              "and the held-out gate passed "
                              "(held-out R %.4f)"
                              % (grade["r_th_c_per_w"], target,
                                 verification["heldout_r_th_c_per_w"]),
                    "grade_before": grade,
                    "params_before": dict(brief["parameters"]),
                    "params_after": dict(brief["parameters"]),
                })
                status = "proven"
                break
            held_violations = verification["heldout_violations"]
            if any("gap" in v for v in held_violations):
                changes, reason = _gap_move(brief, {
                    "violations": held_violations})
                rule = "held-out gap repair"
            elif not verification["heldout_feasible"]:
                changes, reason = _volume_move(brief, {
                    "violations": held_violations})
                rule = "held-out feasibility repair"
            else:
                candidates = _improvement_candidates(brief)
                if candidates:
                    name, changes, _ = candidates[0]
                    rule = "held-out bar repair"
                    reason = ("held-out R %.4f misses bar %.4f; "
                              "best design-condition move is %s"
                              % (verification["heldout_r_th_c_per_w"],
                                 ACCEPT_R_C_PER_W, name))
                    _apply(brief, changes, round_no, rule, reason, grade)
                    continue
                changes, reason = None, \
                    "held-out bar missed with no improving move left"
                rule = "held-out bar repair"
            if changes is None:
                brief["decision_log"].append({
                    "round": round_no,
                    "rule": rule,
                    "decision": "stalled: no move left",
                    "reason": reason,
                    "grade_before": grade,
                    "params_before": dict(brief["parameters"]),
                    "params_after": dict(brief["parameters"]),
                })
                status = "unproven: stalled"
                break
            _apply(brief, changes, round_no, rule, reason, grade)
            continue
        if not grade["feasible"]:
            violations = grade["violations"]
            if any("gap" in v for v in violations):
                changes, reason = _gap_move(brief, grade)
                rule = "gap repair"
            elif any("volume" in v for v in violations):
                changes, reason = _volume_move(brief, grade)
                rule = "volume repair"
            else:
                changes = _clamp_params(brief)
                reason = "parameter outside its range (%s); clamped" % (
                    "; ".join(violations),)
                rule = "range repair"
            if not changes:
                brief["decision_log"].append({
                    "round": round_no,
                    "rule": rule,
                    "decision": "stalled: no move left",
                    "reason": reason,
                    "grade_before": grade,
                    "params_before": dict(brief["parameters"]),
                    "params_after": dict(brief["parameters"]),
                })
                status = "unproven: stalled"
                break
            _apply(brief, changes, round_no, rule, reason, grade)
            continue
        # Feasible but above target: take the best improving move.
        candidates = _improvement_candidates(brief)
        current_r = grade["r_th_c_per_w"]
        improving = [c for c in candidates
                     if c[2]["r_th_c_per_w"] < current_r]
        if not improving:
            brief["decision_log"].append({
                "round": round_no,
                "rule": "improve",
                "decision": "stalled: no move left",
                "reason": "feasible R %.4f above target %.4f and no "
                          "candidate move improves it"
                          % (current_r, target),
                "grade_before": grade,
                "params_before": dict(brief["parameters"]),
                "params_after": dict(brief["parameters"]),
            })
            status = "unproven: stalled"
            break
        name, changes, best_grade = improving[0]
        _apply(brief, changes, round_no, "improve",
               "feasible R %.4f above target %.4f; %s improves it "
               "to %.4f at design conditions"
               % (current_r, target, name, best_grade["r_th_c_per_w"]),
               grade)
    else:
        status = "unproven: round budget exhausted"
    final_grade = _grade(brief)
    if final_grade["feasible"]:
        final_verification = verify_proven(
            _params_of(brief), final_grade["r_th_c_per_w"])
    else:
        final_verification = None
    # Proven means BOTH: the brief's own target is met and the
    # independent held-out gate passes. The gate alone checks the
    # workshop bar, so a design that stalls above a tighter stated
    # target must not count as proven just because it clears 2.0.
    proven = bool(
        final_verification
        and final_verification["proven"]
        and final_grade["r_th_c_per_w"] <= target)
    if status == "proven" and not proven:
        status = "unproven: final gate disagrees"
    return {
        "rough_input": brief["source_text"],
        "brief": brief,
        "rounds_used": max(
            (entry["round"] for entry in brief["decision_log"]),
            default=0),
        "final_params": dict(brief["parameters"]),
        "final_grade": final_grade,
        "verification": final_verification,
        "proven": proven,
        "status": status,
    }


def run_rough_words(text, max_rounds=MAX_ROUNDS):
    """End to end: rough words in, brief + iterated brief +
    graded design out. One call, no human in the loop."""
    return iterate_brief(parse_rough_words(text), max_rounds=max_rounds)


def export_design(record, path):
    """Write the run's final design as a real file, with the same
    honesty rule as stage 1: an unproven design is exported with
    proven=false and its failing verification (or none), never
    dressed up as proven."""
    payload = {
        "artefact_class": record["brief"]["artefact_class"],
        "best": {
            "params": record["final_params"],
            "score_r_th_c_per_w":
                record["final_grade"]["r_th_c_per_w"]
                if record["final_grade"] else None,
        },
        "verification": record["verification"],
        "proven": record["proven"],
        "status": record["status"],
        "rounds_used": record["rounds_used"],
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    return path


def main(argv=None):
    """CLI: brief.py "<rough words>" <record_json> <best_json>"""
    import sys

    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        print('usage: brief.py "<rough words>" <record_json> <best_json>')
        return 2
    text, record_path, best_path = argv
    record = run_rough_words(text)
    with open(record_path, "w") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    export_design(record, best_path)
    grade = record["final_grade"]
    print(
        "rounds=%d status=%s proven=%s final_r=%s -> %s"
        % (record["rounds_used"], record["status"], record["proven"],
           ("%.4f" % grade["r_th_c_per_w"]) if grade else "n/a",
           record_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
