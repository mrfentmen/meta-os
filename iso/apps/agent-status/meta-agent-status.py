#!/usr/bin/env python3
"""meta-agent-status — report what the local agent layer is doing.

Reads files. Writes nothing. Starts nothing. Every number printed here is
read from a file on disk, and a file that is absent is reported absent.

    meta-agent-status [--root DIR] [--json] [--stale-after SECONDS] [--strict]

The root is the relay's own state directory — the same one the watchman unit
is started with: `$METAOS_AGENT_STATE`, else `$XDG_STATE_HOME/oc2-agent`,
else `~/.local/state/oc2-agent`. It is per-user state, not the read-only
payload under /usr/share/metaos/agent, which holds the code and the registry
template.

Freshness is the heartbeat file's modification time, not a field inside it.

Exit codes
    0  every required row was read
    1  a required row is missing or unreadable (or stale, with --strict)
    2  bad usage
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_STALE = 10.0
REQUIRED = "required"
OPTIONAL = "optional"


def default_root():
    if os.environ.get("METAOS_AGENT_STATE"):
        return os.environ["METAOS_AGENT_STATE"]
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return str(Path(base) / "oc2-agent")


def probe_table():
    """Every row this tool knows how to read. Paths are relative to the root."""
    return [
        {"key": "registry", "label": "agent registry",
         "path": "registry.json", "kind": "registry", "need": REQUIRED},
        {"key": "heartbeat", "label": "watchman heartbeat",
         "path": "watchman.heartbeat.json", "kind": "age", "need": REQUIRED},
        {"key": "jobs", "label": "job queue",
         "path": "jobs", "kind": "dir", "need": REQUIRED},
        {"key": "board", "label": "job board",
         "path": "jobs", "kind": "board", "need": OPTIONAL},
        {"key": "halts", "label": "halted agents",
         "path": "stop", "kind": "halts", "need": OPTIONAL},
        {"key": "notices", "label": "notices",
         "path": "notices.jsonl", "kind": "notices", "need": OPTIONAL},
    ]


def count_lines(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return sum(1 for line in text.splitlines() if line.strip())


def read_registry(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, list):
        raise ValueError("registry has no agents list")
    drafts = sum(1 for a in agents if isinstance(a, dict) and a.get("draft") is True)
    hosted = sum(1 for a in agents if isinstance(a, dict) and a.get("hosted") is True)
    return "%d agents, %d draft, %d hosted" % (len(agents), drafts, hosted), {
        "agents": len(agents), "drafts": drafts, "hosted": hosted,
    }


def read_board(jobs_dir, ledger_path):
    """Where each job stands, the same way agents/jobs.mjs reads it.

    queued     a job file, no bell, no result
    running    a bell, no result yet
    done       a clean result (code 0, no signal)
    failed     a result with a nonzero code or a signal
    refused    the layer refused the spawn; nothing ran
    """
    bells = {}
    results = {}
    for filename in os.listdir(jobs_dir):
        full = os.path.join(jobs_dir, filename)
        if not filename.endswith(".json") or not os.path.isfile(full):
            continue
        job_id = filename[:-len(".result.json")] if filename.endswith(".result.json") else None
        if job_id is not None:
            try:
                with open(full, encoding="utf-8") as handle:
                    results[job_id] = json.load(handle) or {}
            except (OSError, json.JSONDecodeError):
                results[job_id] = {"unreadable": True}
            continue
        if filename.endswith(".job.json"):
            try:
                with open(full, encoding="utf-8") as handle:
                    json.load(handle)
            except (OSError, json.JSONDecodeError):
                results[filename[:-len(".job.json")]] = {"unreadable": True}
    if os.path.isfile(ledger_path):
        with open(ledger_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("event") == "bell" and "id" in event:
                    bells[str(event["id"])] = event

    counts = {"queued": 0, "running": 0, "done": 0, "failed": 0, "refused": 0, "unreadable": 0}
    for job_file in sorted(os.listdir(jobs_dir)):
        if not job_file.endswith(".job.json"):
            continue
        job_id = job_file[:-len(".job.json")]
        result = results.get(job_id)
        if result is None:
            counts["running" if job_id in bells else "queued"] += 1
            continue
        if result.get("unreadable"):
            counts["unreadable"] += 1
        elif result.get("refused"):
            counts["refused"] += 1
        elif result.get("signal") is not None:
            counts["failed"] += 1
        elif result.get("code") not in (0, None):
            counts["failed"] += 1
        elif result.get("code") == 0:
            counts["done"] += 1
        else:
            counts["done"] += 1
    total = sum(counts.values())
    detail = "%d job(s)" % total
    if total:
        detail += " — " + ", ".join("%d %s" % (counts[k], k) for k in
                                    ("queued", "running", "done", "failed", "refused") if counts[k])
    return detail, counts


def read_halts(stop_dir):
    """Who a person has paused. A halt holds work on the board; it is not a fault.

    An empty or absent directory means nothing is paused, not that the row is
    broken -- so this never fails a run.
    """
    names = sorted(p.name[:-len(".STOP")] for p in Path(stop_dir).glob("*.STOP"))
    if not names:
        return "none", {"halted": []}
    return "%d halted: %s" % (len(names), ", ".join(names)), {"halted": names}


def read_notices(path):
    """Count what the layer said, and how loud it was."""
    notes = alarms = suppressed = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("suppressed") is True:
            suppressed += 1
        if record.get("severity") == "alarm":
            alarms += 1
        else:
            notes += 1
    detail = "%d note(s), %d alarm(s)" % (notes, alarms)
    if suppressed:
        detail += ", %d repeated" % suppressed
    return detail, {"notes": notes, "alarms": alarms, "suppressed": suppressed}


def read_row(probe, root, stale_after, now):
    row = {
        "key": probe["key"], "label": probe["label"], "need": probe["need"],
        "path": probe["path"], "detail": "", "value": None,
    }
    path = root / probe["path"]

    if probe["kind"] == "dir":
        if not path.is_dir():
            row["status"] = "missing"
            return row
        files = sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".json")
        row["status"] = "ok"
        row["value"] = len(files)
        row["detail"] = "%d pending" % len(files)
        return row

    if probe["kind"] == "board":
        if not path.is_dir():
            row["status"] = "absent"
            return row

    if probe["kind"] == "halts":
        if not path.is_dir():
            row["status"] = "absent"
            return row
        row["detail"], row["value"] = read_halts(path)
        row["status"] = "halted" if row["value"]["halted"] else "ok"
        return row

    if not path.is_file() and probe["kind"] not in ("board",):
        row["status"] = "absent" if probe["need"] == OPTIONAL else "missing"
        return row

    try:
        if probe["kind"] == "registry":
            row["detail"], row["value"] = read_registry(path)
        elif probe["kind"] == "age":
            age = max(0.0, now - path.stat().st_mtime)
            row["value"] = round(age, 1)
            row["status"] = "stale" if age > stale_after else "ok"
            row["detail"] = "%.1f s ago" % age
            return row
        elif probe["kind"] == "board":
            row["detail"], row["value"] = read_board(path, root / "watchman.jsonl")
        elif probe["kind"] == "notices":
            row["detail"], row["value"] = read_notices(path)
        elif probe["kind"] == "lines":
            row["value"] = count_lines(path)
            row["detail"] = "%d lines" % row["value"]
        else:
            raise ValueError("unknown probe kind %r" % probe["kind"])
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        row["status"] = "unreadable"
        row["detail"] = str(exc)
        return row

    row["status"] = "ok"
    return row


def render(rows, root):
    width = max(len(r["label"]) for r in rows)
    lines = ["MetaOS agent layer — %s" % root]
    for r in rows:
        detail = r["detail"] or ("not installed" if r["status"] == "absent" else "-")
        lines.append("  %-*s  %-10s  %s" % (width, r["label"], r["status"], detail))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="meta-agent-status", add_help=True)
    parser.add_argument("--root", default=default_root())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stale-after", type=float, default=DEFAULT_STALE)
    parser.add_argument("--strict", action="store_true",
                        help="treat a stale heartbeat as a failure")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    now = time.time()
    rows = [read_row(p, root, args.stale_after, now) for p in probe_table()]

    failed = [r for r in rows if r["need"] == REQUIRED and r["status"] in ("missing", "unreadable")]
    if args.strict:
        failed += [r for r in rows if r["status"] == "stale"]
    result = {"root": str(root), "ok": not failed, "rows": rows}

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(rows, root))
        if failed:
            print()
            print("agent layer is not ready: %s" % ", ".join(r["key"] for r in failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
