"""fetch_screen_parse.py — extract the fetch screen fields from a log.

The kernel's fetch screen prints:

    Tasks: 8
    Mem: frames_free 126430 frames_total 126509 heap_free 255K heap_total 512K

A section missing those lines returns a named missing-field list instead
of zeroes, so a reader can tell "no data" from "zero".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TASKS_RE = re.compile(r"Tasks:\s*(\d+)")
FRAMES_RE = re.compile(r"frames_free\s+(\d+)\s+frames_total\s+(\d+)")
HEAP_RE = re.compile(r"heap_free\s+(\d+)K\s+heap_total\s+(\d+)K")


def parse_section(text: str) -> dict:
    tasks = TASKS_RE.search(text)
    frames = FRAMES_RE.search(text)
    heap = HEAP_RE.search(text)
    missing = []
    if not tasks:
        missing.append("tasks")
    if not frames:
        missing.append("frames")
    if not heap:
        missing.append("heap")
    return {
        "tasks": int(tasks.group(1)) if tasks else None,
        "frames_free": int(frames.group(1)) if frames else None,
        "frames_total": int(frames.group(2)) if frames else None,
        "heap_free_k": int(heap.group(1)) if heap else None,
        "heap_total_k": int(heap.group(2)) if heap else None,
        "missing": missing,
    }


def main(path: str) -> int:
    record = parse_section(Path(path).read_text(encoding="utf-8", errors="replace"))
    print(f"tasks: {record['tasks']}")
    print(f"frames: {record['frames_free']}/{record['frames_total']}")
    print(f"heap K: {record['heap_free_k']}/{record['heap_total_k']}")
    if record["missing"]:
        print(f"missing: {', '.join(record['missing'])}")
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: fetch_screen_parse.py <log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
