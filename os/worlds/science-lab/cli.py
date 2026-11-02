#!/usr/bin/env python3
"""Science Lab CLI skeleton (Task 9).

Real commands over real records. stdlib only.

Usage (direct path; the directory name contains a dash so
``python -m os.worlds.science-lab.cli`` is not a valid module
reference -- run the file directly)::

    python3 os/worlds/science-lab/cli.py --help
    python3 os/worlds/science-lab/cli.py cycle start --id C001 --question "..."
    python3 os/worlds/science-lab/cli.py cycle status --id C001
    python3 os/worlds/science-lab/cli.py cycle advance --id C001 --to 2 --reason "..."
    python3 os/worlds/science-lab/cli.py experiment list [--cycle C001]
    python3 os/worlds/science-lab/cli.py experiment show --id EXP_ID
    python3 os/worlds/science-lab/cli.py ladder show --level 2
    python3 os/worlds/science-lab/cli.py ladder show --claim '{"evidence_level": 2}' [--display-level 3]

Sibling dependency modules (ladder.py, ledger.py, cycle.py,
lab_config.py) may not exist yet. Every use of them is wrapped
in try/except with a clear stderr message and a stdlib fallback,
so the CLI works against stubbed or missing siblings.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CYCLES_DIR = BASE_DIR / "records" / "cycles"
LEDGER_PATH = BASE_DIR / "records" / "ledger.jsonl"

# Fallback evidence ladder, sourced from PACK.md "The evidence
# ladder" table (LABORATORY section 7). Used only when ladder.py
# is missing or does not expose LEVELS.
_FALLBACK_LEVELS = {
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_sibling_module(name: str):
    """Load BASE_DIR/<name>.py via file location. Returns None if missing.

    Never raises for a missing/unusable sibling: the caller falls
    back to stdlib behaviour and reports the gap.
    """
    path = BASE_DIR / f"{name}.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            f"science_lab_{name}", str(path)
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod
    except Exception as exc:  # stubbed/broken sibling: fall back
        print(
            f"warning: sibling {name}.py exists but failed to load "
            f"({exc}); using stdlib fallback.",
            file=sys.stderr,
        )
        return None


def _ladder_levels() -> dict:
    """Return {level: {status, meaning}} from ladder.py LEVELS if present."""
    mod = _load_sibling_module("ladder")
    if mod is not None and hasattr(mod, "LEVELS"):
        try:
            raw = mod.LEVELS
            out = {}
            if isinstance(raw, dict):
                for k, v in raw.items():
                    level = int(k)
                    if isinstance(v, dict):
                        out[level] = {
                            "status": str(v.get("status", v.get("name", "?"))),
                            "meaning": str(v.get("meaning", v.get("description", ""))),
                        }
                    else:
                        out[level] = {"status": str(v), "meaning": ""}
                if out:
                    return out
            elif isinstance(raw, (list, tuple)):
                for i, v in enumerate(raw):
                    if isinstance(v, dict):
                        out[i] = {
                            "status": str(v.get("status", v.get("name", "?"))),
                            "meaning": str(v.get("meaning", v.get("description", ""))),
                        }
                    else:
                        out[i] = {"status": str(v), "meaning": ""}
                if out:
                    return out
        except Exception as exc:
            print(
                f"warning: ladder.py LEVELS unreadable ({exc}); "
                "using PACK.md fallback table.",
                file=sys.stderr,
            )
    return dict(_FALLBACK_LEVELS)


def _read_ledger_entries() -> list:
    """Read ledger.jsonl via ledger.py read_all(path) if available, else stdlib."""
    mod = _load_sibling_module("ledger")
    if mod is not None and hasattr(mod, "read_all"):
        try:
            entries = mod.read_all(str(LEDGER_PATH))
            if isinstance(entries, list):
                return entries
        except Exception as exc:
            print(
                f"warning: ledger.py read_all() failed ({exc}); "
                "reading ledger.jsonl directly.",
                file=sys.stderr,
            )
    if not LEDGER_PATH.exists():
        return []
    entries = []
    with LEDGER_PATH.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(
                    f"warning: {LEDGER_PATH} line {lineno} is not valid "
                    f"JSON, skipping ({exc}).",
                    file=sys.stderr,
                )
    return entries


def _append_ledger(entry: dict) -> dict:
    """File one ledger entry, via ledger.py append_record (hash chain) if available."""
    mod = _load_sibling_module("ledger")
    if mod is not None and hasattr(mod, "append_record"):
        try:
            filed = mod.append_record(str(LEDGER_PATH), entry)
            if isinstance(filed, dict):
                return filed
        except Exception as exc:
            print(
                f"warning: ledger.py append_record() failed ({exc}); "
                "appending raw JSONL.",
                file=sys.stderr,
            )
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def _cycle_path(cycle_id: str) -> Path:
    return CYCLES_DIR / f"{cycle_id}.json"


def _read_cycle(cycle_id: str) -> dict:
    path = _cycle_path(cycle_id)
    if not path.exists():
        print(f"error: no such cycle '{cycle_id}' ({path}).", file=sys.stderr)
        raise SystemExit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"error: cycle file {path} is corrupt: {exc}", file=sys.stderr)
        raise SystemExit(1)


# Phase names 1-7, sourced from cycle.py PHASES when present.
_FALLBACK_PHASES = [
    "problem",
    "literature",
    "hypotheses",
    "cheap-computations",
    "critic",
    "verification",
    "sealing",
]


def _phase_names() -> list:
    mod = _load_sibling_module("cycle")
    if mod is not None and hasattr(mod, "PHASES"):
        try:
            phases = list(mod.PHASES)
            if phases and all(isinstance(x, str) for x in phases):
                return phases
        except Exception:
            pass
    return list(_FALLBACK_PHASES)


def _resolve_phase(raw: str) -> str:
    """Accept '2' or 'literature'; map 1-7 onto the sourced phase names."""
    text = str(raw).strip()
    try:
        n = int(text)
    except ValueError:
        return text
    phases = _phase_names()
    if 1 <= n <= len(phases):
        return phases[n - 1]
    return text  # unknown: let cycle.py reject it explicitly


# ------------------------------------------------------------------
# cycle commands
# ------------------------------------------------------------------

def cmd_cycle_start(args: argparse.Namespace) -> int:
    path = _cycle_path(args.id)
    if path.exists():
        print(f"error: cycle '{args.id}' already exists ({path}).",
              file=sys.stderr)
        return 1
    now = _now_iso()
    mod = _load_sibling_module("cycle")
    new_cycle = getattr(mod, "new_cycle", None) if mod else None
    if callable(new_cycle):
        try:
            record = new_cycle(args.id, args.question)
        except Exception as exc:
            print(f"error: cycle.py new_cycle() refused: {exc}",
                  file=sys.stderr)
            return 1
        if not isinstance(record, dict):
            print("error: cycle.py new_cycle() did not return a record.",
                  file=sys.stderr)
            return 1
        # Annotation keys outside the schema (schema stays source of truth).
        record.setdefault("question", args.question)
        record.setdefault("created_at", now)
        record["updated_at"] = now
    else:
        if not (BASE_DIR / "cycle.py").exists():
            print("note: cycle.py not present; writing a minimal cycle "
                  "record (phase 1/problem).", file=sys.stderr)
        record = {
            "cycle_id": args.id,
            "id": args.id,
            "question": args.question,
            "phase": "problem",
            "gate_state": "open",
            "inputs": {"problem_statement": args.question},
            "outputs": {},
            "created_at": now,
            "updated_at": now,
            "history": [],
        }
    _write_cycle(record)
    _append_ledger({
        "ts": now,
        "kind": "cycle.start",
        "type": "cycle.start",
        "cycle_id": args.id,
        "phase": record.get("phase"),
        "question": args.question,
    })
    print(str(path))
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def _count(mapping_or_list) -> int:
    if isinstance(mapping_or_list, dict):
        return len(mapping_or_list)
    if isinstance(mapping_or_list, list):
        return len(mapping_or_list)
    return 0


def cmd_cycle_status(args: argparse.Namespace) -> int:
    record = _read_cycle(args.id)
    cid = record.get("cycle_id", record.get("id", args.id))
    phase = record.get("phase", "?")
    gate = record.get("gate_state", record.get("gate", "?"))
    inputs = record.get("inputs", [])
    outputs = record.get("outputs", [])
    question = record.get("question")
    if question is None and isinstance(inputs, dict):
        question = inputs.get("problem_statement")
    print(f"cycle: {cid}")
    print(f"phase: {phase}")
    print(f"gate_state: {gate}")
    print(f"inputs: {_count(inputs)}")
    print(f"outputs: {_count(outputs)}")
    if question is not None:
        print(f"question: {question}")
    if record.get("updated_at") is not None:
        print(f"updated_at: {record['updated_at']}")
    if record.get("parked_gate") is not None:
        print(f"parked_gate: {record['parked_gate']}")
    return 0


def _try_cycle_py_transition(record: dict, target: str, reason: str):
    """Try cycle.py transition(record, target, reason, ledger_path).

    Returns (status, payload) where status is 'ok' (payload = updated
    record), 'blocked' (payload = refusal message; caller must NOT fall
    back to a manual update), or 'missing' (no usable helper; caller
    may apply the manual JSON fallback).
    """
    mod = _load_sibling_module("cycle")
    if mod is None:
        return ("missing", None)
    for attr in ("transition", "advance", "transition_phase", "advance_phase"):
        fn = getattr(mod, attr, None)
        if callable(fn):
            try:
                updated = fn(record, target, reason, str(LEDGER_PATH))
            except TypeError as exc:
                # Signature drift: do not guess twice; report and stop.
                return ("blocked",
                        f"cycle.py {attr}() signature mismatch ({exc}); "
                        "refusing manual bypass.")
            except ValueError as exc:
                # A gate refusal is a verdict, not a missing helper.
                return ("blocked", str(exc))
            except Exception as exc:
                print(
                    f"warning: cycle.py {attr}() failed ({exc}); "
                    "falling back to manual JSON update.",
                    file=sys.stderr,
                )
                return ("missing", None)
            if isinstance(updated, dict):
                return ("ok", updated)
            return ("ok", record)  # helper mutated in place
    return ("missing", None)


def _write_cycle(record: dict) -> None:
    CYCLES_DIR.mkdir(parents=True, exist_ok=True)
    cid = record.get("cycle_id", record.get("id"))
    if not cid:
        print("error: cycle record has no cycle_id/id; refusing to write.",
              file=sys.stderr)
        raise SystemExit(1)
    path = _cycle_path(str(cid))
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")


def cmd_cycle_advance(args: argparse.Namespace) -> int:
    record = _read_cycle(args.id)
    old_phase = record.get("phase")
    target = _resolve_phase(args.to)
    reason = args.reason or ""
    status, payload = _try_cycle_py_transition(record, target, reason)
    if status == "blocked":
        print(f"blocked: {payload}", file=sys.stderr)
        return 1
    if status == "ok":
        _write_cycle(payload)
        print(f"cycle {args.id}: {old_phase} -> {payload.get('phase')}")
        print("ledger: transition filed by cycle.py "
              f"(entry counted in {LEDGER_PATH}).")
        return 0
    # No usable cycle.py: manual JSON update with our own ledger entry.
    if not (BASE_DIR / "cycle.py").exists():
        print("note: cycle.py not present; applying manual JSON update.",
              file=sys.stderr)
    now = _now_iso()
    record["phase"] = target
    record["updated_at"] = now
    history = record.setdefault("history", [])
    if isinstance(history, list):
        history.append({"ts": now, "event": "cycle.transition",
                        "from": old_phase, "to": target,
                        "reason": reason})
    _write_cycle(record)
    _append_ledger({
        "ts": now,
        "kind": "cycle.transition",
        "type": "cycle.transition",
        "cycle_id": args.id,
        "from": old_phase,
        "to": target,
        "reason": reason,
    })
    print(f"cycle {args.id}: {old_phase} -> {target}")
    return 0


# ------------------------------------------------------------------
# experiment commands (read the real ledger)
# ------------------------------------------------------------------

def _entry_cycle_id(entry: dict):
    for key in ("cycle_id", "cycle", "cycleId"):
        if entry.get(key) is not None:
            return entry[key]
    return None


def _entry_id(entry: dict):
    for key in ("id", "experiment_id", "exp_id"):
        if entry.get(key) is not None:
            return str(entry[key])
    eh = entry.get("entry_hash")
    if eh:
        return str(eh)
    return "?"


def cmd_experiment_list(args: argparse.Namespace) -> int:
    entries = _read_ledger_entries()
    if args.cycle is not None:
        entries = [e for e in entries
                   if str(_entry_cycle_id(e)) == str(args.cycle)]
    if not entries:
        if not LEDGER_PATH.exists():
            print(f"no ledger yet ({LEDGER_PATH} does not exist).")
        elif args.cycle is not None:
            print(f"no ledger entries for cycle '{args.cycle}'.")
        else:
            print("no ledger entries.")
        return 0
    for e in entries:
        if not isinstance(e, dict):
            print(f"?  ?  cycle=?  {e}")
            continue
        eid = _entry_id(e)
        etype = e.get("kind", e.get("type", "?"))
        cid = _entry_cycle_id(e)
        short = eid[:12] if len(eid) > 12 else eid
        print(f"{short}  {etype}  cycle={cid}")
    return 0


def cmd_experiment_show(args: argparse.Namespace) -> int:
    entries = _read_ledger_entries()
    want = str(args.id)
    for e in entries:
        if not isinstance(e, dict):
            continue
        candidates = [str(e.get(k)) for k in
                      ("id", "experiment_id", "exp_id", "entry_hash")
                      if e.get(k) is not None]
        if want in candidates or any(c.startswith(want) for c in candidates):
            print(json.dumps(e, indent=2, sort_keys=True))
            return 0
    if not LEDGER_PATH.exists():
        print(f"error: no ledger yet ({LEDGER_PATH} does not exist).",
              file=sys.stderr)
    else:
        print(f"error: no experiment '{args.id}' in {LEDGER_PATH}.",
              file=sys.stderr)
    return 1


# ------------------------------------------------------------------
# ladder commands
# ------------------------------------------------------------------

def _parse_claim(claim_src: str) -> dict:
    maybe_path = Path(claim_src)
    text = claim_src
    if maybe_path.exists() and maybe_path.is_file():
        try:
            text = maybe_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read claim file {maybe_path}: {exc}",
                  file=sys.stderr)
            raise SystemExit(1)
    try:
        claim = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"error: --claim is not valid JSON ({exc}).", file=sys.stderr)
        raise SystemExit(1)
    if not isinstance(claim, dict):
        print("error: --claim JSON must be an object.", file=sys.stderr)
        raise SystemExit(1)
    return claim


def _claim_level(claim: dict) -> int:
    for key in ("evidence_level", "level", "evidenceLevel"):
        if claim.get(key) is not None:
            try:
                return int(claim[key])
            except (TypeError, ValueError):
                pass
    print("error: claim JSON carries no level "
          "(looked for evidence_level/level).", file=sys.stderr)
    raise SystemExit(1)


def cmd_ladder_show(args: argparse.Namespace) -> int:
    if args.claim is not None:
        claim = _parse_claim(args.claim)
        level = _claim_level(claim)
    elif args.level is not None:
        claim = {"evidence_level": args.level}
        level = int(args.level)
    else:
        print("error: ladder show needs --claim CLAIM_JSON or --level N.",
              file=sys.stderr)
        return 1
    levels = _ladder_levels()
    if level not in levels:
        print(f"error: unknown evidence level {level} (known: "
              f"{sorted(levels)}).", file=sys.stderr)
        return 1
    info = levels[level]
    print(f"level: {level}")
    print(f"status: {info.get('status', '?')}")
    print(f"meaning: {info.get('meaning', '')}")
    if level >= 4:
        print("note: levels 4-6 require physical experiments by "
              "qualified humans; unreachable by this system alone.")
    if args.display_level is None:
        return 0
    try:
        want = int(args.display_level)
    except (TypeError, ValueError):
        print("error: --display-level must be an integer 0-6.",
              file=sys.stderr)
        return 1
    # Export guard: ladder.py assert_export_allowed if available.
    mod = _load_sibling_module("ladder")
    guard = getattr(mod, "assert_export_allowed", None) if mod else None
    if callable(guard):
        try:
            guard(claim, want)
            print(f"export guard: ALLOWED (display {want} "
                  f"<= recorded {level}; ladder.py).")
            return 0
        except Exception as exc:
            print(f"export guard: BLOCKED (display {want} > recorded "
                  f"{level}; ladder.py: {exc}).")
            return 1
    if not (BASE_DIR / "ladder.py").exists():
        print("note: ladder.py not present; applying built-in guard "
              "(display <= recorded).", file=sys.stderr)
    if want <= level:
        print(f"export guard: ALLOWED (display {want} <= recorded {level}).")
        return 0
    print(f"export guard: BLOCKED (display {want} > recorded {level}: "
          "a claim displays at the level its record holds, never higher).")
    return 1


# ------------------------------------------------------------------
# argparse wiring
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="Science Lab CLI skeleton: cycles, experiments, ladder "
                    "(real commands over records/ files).",
    )
    sub = p.add_subparsers(dest="group", required=True)

    p_cycle = sub.add_parser("cycle", help="discovery cycle records")
    csub = p_cycle.add_subparsers(dest="cmd", required=True)

    p_start = csub.add_parser("start", help="create a cycle record")
    p_start.add_argument("--id", required=True, help="cycle id (e.g. C001)")
    p_start.add_argument("--question", required=True,
                         help="research question for the cycle")
    p_start.set_defaults(func=cmd_cycle_start)

    p_status = csub.add_parser("status", help="print cycle phase/gate state")
    p_status.add_argument("--id", required=True, help="cycle id")
    p_status.set_defaults(func=cmd_cycle_status)

    p_adv = csub.add_parser("advance",
                            help="transition a cycle to another phase")
    p_adv.add_argument("--id", required=True, help="cycle id")
    p_adv.add_argument("--to", required=True,
                       help="target phase: 1-7 (mapped to the sourced names) "
                            "or a phase name")
    p_adv.add_argument("--reason", required=True,
                       help="reason recorded in history + ledger")
    p_adv.set_defaults(func=cmd_cycle_advance)

    p_exp = sub.add_parser("experiment", help="experiment ledger records")
    esub = p_exp.add_subparsers(dest="cmd", required=True)

    p_list = esub.add_parser("list", help="list ledger entries")
    p_list.add_argument("--cycle", required=False, default=None,
                        help="filter to one cycle id")
    p_list.set_defaults(func=cmd_experiment_list)

    p_show = esub.add_parser("show", help="print one ledger record")
    p_show.add_argument("--id", required=True, help="experiment/record id")
    p_show.set_defaults(func=cmd_experiment_show)

    p_lad = sub.add_parser("ladder", help="evidence ladder levels")
    lsub = p_lad.add_subparsers(dest="cmd", required=True)

    p_lshow = lsub.add_parser("show", help="show a claim's level")
    p_lshow.add_argument("--claim", required=False, default=None,
                         help="claim JSON object (or path to a JSON file)")
    p_lshow.add_argument("--level", required=False, default=None, type=int,
                         help="evidence level 0-6")
    p_lshow.add_argument("--display-level", required=False, default=None,
                         type=int,
                         help="run the export guard for this display level")
    p_lshow.set_defaults(func=cmd_ladder_show)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
