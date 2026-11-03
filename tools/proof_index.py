"""proof_index.py — emit a Markdown index of boot logs in a directory.

Columns: filename, date named in the file (if any), first milestone
marker, panic count. Only `*.txt` and `*.log` files are logs; anything
else is skipped and counted, never silently dropped.
"""

from __future__ import annotations

import sys
from pathlib import Path

from bootlog_parse import parse_log

LOG_SUFFIXES = (".txt", ".log")


def scan_dir(directory: str | Path) -> dict:
    """Return {"rows": [...], "skipped": n}; rows sorted by filename."""
    directory = Path(directory)
    rows = []
    skipped = 0
    for path in sorted(directory.iterdir(), key=lambda p: p.name):
        if not path.is_file():
            continue
        if path.suffix not in LOG_SUFFIXES:
            skipped += 1
            continue
        parsed = parse_log(path.read_text(encoding="utf-8", errors="replace"))
        rows.append(
            {
                "file": path.name,
                "date": parsed["date"] or "—",
                "milestone": parsed["banner"] or "—",
                "panics": parsed["panic_count"],
            }
        )
    return {"rows": rows, "skipped": skipped}


def render(index: dict) -> str:
    lines = [
        "| File | Date | Milestone | Panics |",
        "|---|---|---|---:|",
    ]
    for row in index["rows"]:
        lines.append(f"| `{row['file']}` | {row['date']} | {row['milestone']} | {row['panics']} |")
    lines.append("")
    lines.append(f"{len(index['rows'])} log(s), {index['skipped']} non-log file(s) skipped")
    return "\n".join(lines) + "\n"


def main(directory: str) -> int:
    sys.stdout.write(render(scan_dir(directory)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: proof_index.py <log-directory>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
