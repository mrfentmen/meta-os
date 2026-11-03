#!/usr/bin/env python3
"""Science Lab — the hosted entry point for the research agents.

Each agent in the registry runs one bounded duty over the records that are
actually on disk here. No model, no network, no invented data: every duty
reads `records/`, says what it found, writes one receipt, and exits.

    python3 os/worlds/science-lab/hosted.py --agent research-archivist
    python3 os/worlds/science-lab/hosted.py --list
    python3 os/worlds/science-lab/hosted.py --agent <name> --check

Exit 0 when the duty ran and the receipt was written. Exit 1 when a record
the duty must read is missing or torn: a broken tree must not look like a
quiet one. Exit 2 on a usage error or an agent with no duty.

The six discipline duties are checks over the cycle and claim records that
do ship: where a discipline has no hypothesis record on disk, the duty
reports zero matches instead of inventing one. A duty that finds nothing
real to read says so; it never files a design, a verdict, or a level.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
RECORDS = BASE / "records"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_root() -> Path:
    env = os.environ.get("METAOS_STATE")
    return Path(env) if env else Path.home() / ".local" / "state" / "metaos"


def _cycles(records: Path) -> list[dict]:
    out = []
    for path in sorted(glob.glob(str(records / "cycles" / "*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        doc["_file"] = os.path.basename(path)
        out.append(doc)
    return out


def _ledger(records: Path) -> list[dict]:
    path = records / "ledger.jsonl"
    if not path.exists():
        raise SystemExit("error: no ledger at " + str(path))
    rows = []
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit("error: ledger line %d does not parse: %s" % (number, exc))
    return rows


def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _threshold(text):
    """Read the one comparison the records state, e.g. 'R2 >= 0.5'."""
    if not isinstance(text, str) or ">=" not in text:
        return None
    try:
        return float(text.split(">=", 1)[1].strip())
    except ValueError:
        return None


# ---------------------------------------------------------------- duties
# Every duty returns (findings, exit_code). A finding says what was read and
# what it means; an empty findings list is a real answer, not a failure.


def duty_archivist(records, _args):
    """The ledger's hash chain: the one claim every other record rests on."""
    sys.path.insert(0, str(BASE))
    import ledger as ledger_mod  # noqa: E402

    path = records / "ledger.jsonl"
    # verify_chain on a missing file reports "ok: 0 entries" -- an empty
    # history and no history must not read the same way.
    if not path.exists():
        return ([{"check": "hash-chain", "ok": False,
                  "detail": "no ledger at " + str(path)}], 1)
    ok, message = ledger_mod.verify_chain(str(path))
    return ([{"check": "hash-chain", "ok": ok, "detail": message}], 0 if ok else 1)


def duty_director(records, _args):
    """Census the cycles and name the ones waiting on a human gate."""
    cycles = _cycles(records)
    findings = []
    for cycle in cycles:
        findings.append({
            "cycle": cycle.get("cycle_id"),
            "phase": cycle.get("phase"),
            "gate": cycle.get("gate_state"),
            "transitions": len(cycle.get("history") or []),
        })
    waiting = [c for c in findings if c["gate"] and c["gate"] != "open"]
    return (findings, 0 if cycles else 1) if cycles else (
        [{"check": "cycles", "ok": False, "detail": "no cycle records found"}], 1)


def duty_critic(records, _args):
    """Claims the lane itself dropped, and cycles with no recorded critique."""
    rows = _ledger(records)
    dropped = [r for r in rows if "dropped" in str(r.get("kind", ""))]
    uncritiqued = []
    for cycle in _cycles(records):
        verdict = (((cycle.get("inputs") or {}).get("critique") or {}).get("verdict"))
        if not verdict:
            uncritiqued.append(cycle.get("cycle_id"))
    findings = [{
        "check": "dropped-claims",
        "count": len(dropped),
        "claims": [str(r.get("claim", ""))[:120] for r in dropped[:5]],
        "uncritiqued_cycles": uncritiqued,
    }]
    return findings, 0


def duty_verifier(records, _args):
    """Compute results with no verification entry on the ledger."""
    rows = _ledger(records)
    verified = {str(r.get("cycle_id")) for r in rows
                if "verification" in str(r.get("kind", ""))}
    computed = []
    for cycle in _cycles(records):
        if ((cycle.get("inputs") or {}).get("compute_results")):
            computed.append(str(cycle.get("cycle_id")))
    unverified = [c for c in computed if c not in verified]
    return ([{
        "check": "reproduction",
        "computed_cycles": computed,
        "verified_cycles": sorted(verified),
        "unverified_cycles": unverified,
    }], 0)


def duty_analyst(records, _args):
    """Re-read the recorded fit statistics and re-apply the recorded threshold."""
    findings = []
    for cycle in _cycles(records):
        results = ((cycle.get("inputs") or {}).get("compute_results")) or {}
        observation = results.get("prep_observation_NOT_paper_report") or {}
        r2 = observation.get("r2")
        threshold = _threshold(results.get("prereg_threshold"))
        if not _numeric(r2):
            continue
        findings.append({
            "cycle": cycle.get("cycle_id"),
            "n": observation.get("n"),
            "r2": r2,
            "rmse": observation.get("rmse"),
            "mae": observation.get("mae"),
            "threshold": threshold,
            "meets_threshold": None if threshold is None else r2 >= threshold,
        })
    return ([{"check": "fit-statistics", "rows": findings}], 0)


def duty_literature(records, _args):
    """The literature shelf: what was read, pinned, dropped, contested."""
    files = sorted(glob.glob(str(records / "literature" / "*.json")))
    findings = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        counts = doc.get("status_counts") or doc
        findings.append({
            "file": os.path.basename(path),
            "question": str(doc.get("question", ""))[:160],
            "claims_pinned": counts.get("claims_pinned"),
            "claims_dropped": counts.get("claims_dropped"),
            "contested": counts.get("contested"),
            "sources_read": counts.get("sources_read"),
        })
    return ([{"check": "literature-shelf", "briefs": findings}], 0)


def duty_computational(records, _args):
    """Every compute result must name its dataset, its method difference and its prereg entry."""
    findings = []
    for cycle in _cycles(records):
        results = ((cycle.get("inputs") or {}).get("compute_results")) or {}
        if not results:
            continue
        missing = [key for key in ("dataset_sha256", "prereg_entry", "method_difference")
                   if not results.get(key)]
        findings.append({"cycle": cycle.get("cycle_id"), "missing": missing})
    return ([{"check": "compute-provenance", "cycles": findings}], 0)


def _cycle_text(cycle):
    """The cycle prose a discipline duty can actually match against."""
    inputs = cycle.get("inputs") or {}
    results = inputs.get("compute_results") or {}
    outputs = cycle.get("outputs") or {}
    return " ".join([
        str(inputs.get("problem_statement", "")),
        str(results.get("method_difference", "")),
        str((inputs.get("hypotheses") or {}).get("note", "")),
        str(outputs.get("hypotheses", "")),
        str(outputs.get("literature", "")),
    ])


def _cycle_hypothesis_ids(cycle):
    hyps = (cycle.get("inputs") or {}).get("hypotheses") or {}
    return list(hyps.get("ids") or [])


def _has_disproof_statement(cycle):
    """True when the cycle prose says its hypotheses carry falsifiers."""
    return "falsif" in _cycle_text(cycle).lower()


def _repository_rows(records, name):
    path = records / "repository" / name
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit("error: %s line %d does not parse: %s"
                                 % (name, number, exc))
    return rows


def _duty_discipline(records, agent, signals, engine_note):
    """One discipline's design audit, over cycle records only.

    A hypothesis counts as matching when the cycle prose names the
    discipline's engine or subject; the duty reports the cycle-level
    falsifier statement and never executes a design, never files one,
    and never promotes anything. Zero matches is a real answer: no
    hypothesis record for that discipline ships on disk.
    """
    cycles = _cycles(records)
    rows = []
    for cycle in cycles:
        text = _cycle_text(cycle).lower()
        matched = [s for s in signals if s in text]
        if not matched:
            continue
        results = (cycle.get("inputs") or {}).get("compute_results") or {}
        for hid in _cycle_hypothesis_ids(cycle):
            rows.append({
                "cycle": cycle.get("cycle_id"),
                "hypothesis": hid,
                "design_signal": matched,
                "has_disproof_statement": _has_disproof_statement(cycle),
                "method_difference": str(results.get("method_difference", ""))[:160],
            })
    return ([{
        "check": "discipline-design-audit",
        "agent": agent,
        "cycles_scanned": len(cycles),
        "matching_hypotheses": len(rows),
        "hypotheses_with_design_signal": rows,
        "engine_note": engine_note,
        "full_record_note": ("No full hypothesis record file ships on disk, "
                             "so per-record design and disproof texts cannot "
                             "be audited here; only the cycle-level falsifier "
                             "statement is reported."),
    }], 0)


def duty_mathematics(records, _args):
    return _duty_discipline(
        records, "mathematics-researcher",
        ("sympy", "scipy", "mathematical"),
        "Light engines SymPy/SciPy named in the agent definition; a design "
        "without a disproof condition is not filed, and no design is "
        "executed here.")


def duty_chemistry(records, _args):
    return _duty_discipline(
        records, "chemistry-researcher",
        ("rdkit", "esol", "solubility", "chemistry"),
        "Light engine RDKit named in the agent definition; a design without "
        "a disproof condition is not filed, and no design is executed here.")


def duty_biology(records, _args):
    return _duty_discipline(
        records, "biology-researcher",
        ("gbif", "uniprot", "rcsb", "biology"),
        "GBIF/UniProt/RCSB depth adapters are stage-2 UNIMPLEMENTED; "
        "designs are limited to currently available sources and say so, "
        "and no design is executed here.")


def duty_physics(records, _args):
    return _duty_discipline(
        records, "physics-researcher",
        ("gnina", "openmm", "psi4", "physics"),
        "Heavy GPU engines GNINA/OpenMM/Psi4 are stage-4 GPU-gated "
        "UNIMPLEMENTED unless del opens the GPU gate; never claimed here, "
        "and no design is executed here.")


def duty_generator(records, _args):
    """Audit the hypothesis ids cycles name. Report only, never a verdict.

    Full hypothesis records (measurable_prediction, alternative_
    explanation, evidence_level, status) do not ship on disk, so
    per-record field checks cannot run; cycle ids are not generator
    filings, so the 3-5-per-problem rule gets no count verdict here.
    """
    cycles = _cycles(records)
    per_cycle = []
    total = 0
    with_statement = 0
    for cycle in cycles:
        ids = _cycle_hypothesis_ids(cycle)
        stated = _has_disproof_statement(cycle)
        total += len(ids)
        if stated:
            with_statement += len(ids)
        per_cycle.append({
            "cycle": cycle.get("cycle_id"),
            "hypothesis_ids": ids,
            "count": len(ids),
            "disproof_statement": stated,
        })
    return ([{
        "check": "hypothesis-filing-audit",
        "cycles": per_cycle,
        "total_ids": total,
        "with_disproof_statement": with_statement,
        "without_disproof_statement": total - with_statement,
    }], 0)


def duty_statistician(records, _args):
    """Re-apply recorded thresholds to recorded figures; outcome is
    match / no-match / indeterminate, no adjectives.

    Same pattern as duty_analyst, extended to the claim verdicts and
    the reproduction records: a threshold met with reproduction still
    pending stays indeterminate, because the cycle itself says so.
    """
    cycles = _cycles(records)
    claims = _repository_rows(records, "claims.jsonl")
    by_cycle = {str(c.get("cycle_id")): c for c in claims if c.get("cycle_id")}
    rows = []
    for cycle in cycles:
        results = (cycle.get("inputs") or {}).get("compute_results") or {}
        verification = (cycle.get("inputs") or {}).get("verification") or {}
        observation = results.get("prep_observation_NOT_paper_report") or {}
        if _numeric(observation.get("r2")):
            figure = {"n": observation.get("n"), "r2": observation.get("r2"),
                      "rmse": observation.get("rmse"), "mae": observation.get("mae")}
            threshold = _threshold(results.get("prereg_threshold"))
            threshold_kind = "R2"
            met = None if threshold is None else observation["r2"] >= threshold
        elif _numeric(results.get("rmse")):
            figure = {"n": results.get("n"), "rmse": results.get("rmse")}
            basis = str((by_cycle.get(str(cycle.get("cycle_id"))) or {}).get("basis", ""))
            found = re.search(r"<=\s*([0-9.]+)", basis)
            threshold = float(found.group(1)) if found else None
            threshold_kind = "RMSE"
            met = None if threshold is None else results["rmse"] <= threshold
        else:
            continue
        recorded = verification.get("outcome") or verification.get("verdict")
        claim_verdict = (by_cycle.get(str(cycle.get("cycle_id"))) or {}).get("verdict")
        if recorded in (None, "indeterminate") or met is None:
            audit = "indeterminate"
        elif claim_verdict == "match" and met:
            audit = "match"
        elif recorded == "reproduced" and met:
            audit = "match"
        else:
            audit = "no-match"
        rows.append({
            "cycle": cycle.get("cycle_id"),
            "figure": figure,
            "threshold": threshold,
            "threshold_kind": threshold_kind,
            "threshold_met": met,
            "recorded_verification": recorded,
            "recorded_claim_verdict": claim_verdict,
            "audit": audit,
        })
    repro = [{"experiment_id": e.get("experiment_id"),
              "cycle": e.get("cycle_id"),
              "verification_status": e.get("verification_status")}
             for e in _repository_rows(records, "experiments.jsonl")
             if e.get("verification_status")]
    return ([{"check": "statistical-audit", "cycles": rows,
              "reproduction_records": repro}], 0)


DUTIES = {
    "research-archivist": duty_archivist,
    "research-director": duty_director,
    "scientific-critic": duty_critic,
    "independent-verifier": duty_verifier,
    "scientific-analyst": duty_analyst,
    "literature-researcher": duty_literature,
    "computational-scientist": duty_computational,
    "mathematics-researcher": duty_mathematics,
    "chemistry-researcher": duty_chemistry,
    "biology-researcher": duty_biology,
    "physics-researcher": duty_physics,
    "hypothesis-generator": duty_generator,
    "statistician": duty_statistician,
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="hosted.py", description=__doc__.splitlines()[0])
    parser.add_argument("--agent", required=True, help="registry agent name")
    parser.add_argument("--records", default=str(RECORDS), help="records directory")
    parser.add_argument("--check", action="store_true", help="prove the duty can read its records")
    args = parser.parse_args(argv)

    if args.agent == "--list" or args.agent == "list":
        for name in DUTIES:
            print(name)
        return 0

    duty = DUTIES.get(args.agent)
    if duty is None:
        print("error: no duty for agent %r; it stays a draft" % args.agent, file=sys.stderr)
        return 2

    records = Path(args.records)
    if not records.is_dir():
        print("error: records dir does not exist: %s" % records, file=sys.stderr)
        return 2

    findings, code = duty(records, args)
    if args.check:
        print("ok: %s can read %s" % (args.agent, records))
        return code

    out_root = _state_root() / "science-lab"
    out_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    receipt = {
        "agent": args.agent,
        "at": _now(),
        "records": str(records),
        "ok": code == 0,
        "findings": findings,
    }
    path = out_root / ("%s-%s.json" % (args.agent, stamp))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, indent=2, sort_keys=True)
    print("science: %s -> %s" % (args.agent, path))
    for finding in findings:
        print("  " + json.dumps(finding, sort_keys=True)[:300])
    return code


if __name__ == "__main__":
    sys.exit(main())
