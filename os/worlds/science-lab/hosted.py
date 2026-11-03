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

Agents whose duty needs material this repo does not hold (a physics corpus,
a biology dataset) are NOT listed here. They stay drafts in the registry,
because a duty that has nothing real to read would be a placeholder.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
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


DUTIES = {
    "research-archivist": duty_archivist,
    "research-director": duty_director,
    "scientific-critic": duty_critic,
    "independent-verifier": duty_verifier,
    "scientific-analyst": duty_analyst,
    "literature-researcher": duty_literature,
    "computational-scientist": duty_computational,
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
