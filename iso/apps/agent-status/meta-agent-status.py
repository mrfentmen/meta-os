#!/usr/bin/env python3
"""meta-agent-status — report what the local agent layer is doing.

Reads files. Writes nothing. Starts nothing. Every number printed here is
read from a file on disk, and a file that is absent is reported absent.

    meta-agent-status [--root DIR] [--json] [--stale-after SECONDS]

The root defaults to $METAOS_ROOT, or /opt/metaos when that is unset.
Freshness is the heartbeat file's modification time, not a field inside it.

Exit codes
    0  every required row was read
    1  a required row is missing or unreadable
    2  bad usage
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_ROOT = "/opt/metaos"
DEFAULT_STALE = 10.0
REQUIRED = "required"
OPTIONAL = "optional"


def probe_table():
    """Every row this tool knows how to read. Paths are relative to the root."""
    return [
        {"key": "registry", "label": "agent registry",
         "path": "agents/registry.json", "kind": "registry", "need": REQUIRED},
        {"key": "heartbeat", "label": "watchman heartbeat",
         "path": "agents/watchman.heartbeat.json", "kind": "age", "need": REQUIRED},
        {"key": "jobs", "label": "job queue",
         "path": "agents/jobs", "kind": "dir", "need": REQUIRED},
        {"key": "gym", "label": "gym ledger",
         "path": "agents/gym-ledger.jsonl", "kind": "lines", "need": OPTIONAL},
        {"key": "inbox", "label": "handsfree inbox",
         "path": "handsfree/inbox.txt", "kind": "lines", "need": OPTIONAL},
        {"key": "refusals", "label": "handsfree refusals",
         "path": "handsfree/inbox.txt.refusals.jsonl", "kind": "lines", "need": OPTIONAL},
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

    if not path.is_file():
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
    parser.add_argument("--root", default=os.environ.get("METAOS_ROOT", DEFAULT_ROOT))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stale-after", type=float, default=DEFAULT_STALE)
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    now = time.time()
    rows = [read_row(p, root, args.stale_after, now) for p in probe_table()]

    failed = [r for r in rows if r["need"] == REQUIRED and r["status"] in ("missing", "unreadable")]
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
