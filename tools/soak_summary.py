"""soak_summary.py — three-line summary of a long soak log.

Reports duration (from an `Uptime: <n>s` line when present, else the
line count), the tick range, and the panic count. Nothing else.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

UPTIME_RE = re.compile(r"Uptime:\s*(\d+)s")
TICKS_RE = re.compile(r"ticks[= ](\d+)")
PANIC_RE = re.compile(r"META OS KERNEL - panic")


def summarise(text: str) -> dict:
    lines = text.splitlines()
    uptime = UPTIME_RE.search(text)
    ticks = [int(value) for value in TICKS_RE.findall(text)]
    panics = len(PANIC_RE.findall(text))
    return {
        "duration_seconds": int(uptime.group(1)) if uptime else None,
        "lines": len(lines),
        "tick_first": ticks[0] if ticks else None,
        "tick_last": ticks[-1] if ticks else None,
        "tick_delta": (ticks[-1] - ticks[0]) if ticks else None,
        "ticks_seen": len(ticks),
        "panics": panics,
    }


def render(summary: dict) -> str:
    duration = (
        f"{summary['duration_seconds']}s"
        if summary["duration_seconds"] is not None
        else f"{summary['lines']} lines"
    )
    if summary["tick_first"] is None:
        tick_range = "no ticks"
    else:
        tick_range = f"{summary['tick_first']}..{summary['tick_last']} (delta {summary['tick_delta']}, {summary['ticks_seen']} samples)"
    return "\n".join(
        [
            f"duration: {duration}",
            f"ticks: {tick_range}",
            f"panics: {summary['panics']}",
        ]
    ) + "\n"


def main(path: str) -> int:
    summary = summarise(Path(path).read_text(encoding="utf-8", errors="replace"))
    sys.stdout.write(render(summary))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: soak_summary.py <soak.log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
