"""ps_rows_parse.py — parse the kernel's ps table from a log.

One real row looks like:

    ps id 1 state Exited ticks_used 12 prio 3

An unknown state string is kept and flagged, never dropped: the row
existed on the machine, so the record keeps it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROW_RE = re.compile(
    r"ps id\s+(\d+)\s+state\s+(\S+)\s+ticks_used\s+(\d+)\s+prio\s+(\d+)"
)
KNOWN_STATES = {"Running", "Ready", "Sleeping", "Exited", "Blocked"}


def parse_rows(text: str) -> dict:
    rows = []
    flagged = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = ROW_RE.search(line)
        if not match:
            continue
        unknown = match.group(2) not in KNOWN_STATES
        row = {
            "pid": int(match.group(1)),
            "name": f"task-{match.group(1)}",
            "state": match.group(2),
            "ticks_used": int(match.group(3)),
            "prio": int(match.group(4)),
            "line": number,
        }
        rows.append(row)
        if unknown:
            flagged.append(row)
    return {"rows": rows, "flagged": flagged}


def render(result: dict) -> str:
    lines = ["| pid | state | ticks | prio |", "|---:|---|---:|---:|"]
    for row in result["rows"]:
        lines.append(f"| {row['pid']} | {row['state']} | {row['ticks_used']} | {row['prio']} |")
    lines.append("")
    lines.append(f"{len(result['rows'])} row(s), {len(result['flagged'])} flagged")
    return "\n".join(lines) + "\n"


def main(path: str) -> int:
    result = parse_rows(Path(path).read_text(encoding="utf-8", errors="replace"))
    sys.stdout.write(render(result))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: ps_rows_parse.py <log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
