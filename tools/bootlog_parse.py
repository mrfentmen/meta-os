"""bootlog_parse.py — read a QEMU serial boot log as data.

Extracted fields mirror the lines the kernel actually prints:

    META OS 0.1 (K6)                       banner
    META OS KERNEL - alive (K1)            alive line
    META OS KERNEL - panic                 panic line(s)
    readkey got 30 / enter seen, done=3    readkey events
    STATUS tasks=7 ticks=805 ...           status ticks
    Programs: hello sleeper crasher ...    programs
    INT user page-fault ... task killed    fault isolation

The parser never guesses: a missing field is None/false and the verdict
names it. Counts only otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BANNER_RE = re.compile(r"META OS [0-9.]+ \(K\d+\)|META OS - milestone K\d+")
ALIVE_RE = re.compile(r"META OS KERNEL - alive \(K\d+\)")
PANIC_RE = re.compile(r"META OS KERNEL - panic")
READKEY_RE = re.compile(r"readkey got (\d+)")
ENTER_RE = re.compile(r"readkey: enter seen, done got=(\d+)")
TICKS_RE = re.compile(r"ticks[= ](\d+)")
PROGRAMS_RE = re.compile(r"Programs:\s*(.+)")
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")
FAULT_RE = re.compile(r"INT user page-fault .*task killed")


def parse_log(text: str) -> dict:
    """Parse one log body into a flat record. Never raises on odd content."""
    lines = text.splitlines()
    banner = None
    alive_line = None
    panic_count = 0
    readkeys = []
    enter_got = None
    ticks = []
    programs = []
    fault_isolation = False
    date = None

    for number, line in enumerate(lines, start=1):
        if banner is None and BANNER_RE.search(line):
            banner = line.strip()
        if alive_line is None and ALIVE_RE.search(line):
            alive_line = line.strip()
        if PANIC_RE.search(line):
            panic_count += 1
        match = READKEY_RE.search(line)
        if match:
            readkeys.append({"key": int(match.group(1)), "line": number})
        match = ENTER_RE.search(line)
        if match:
            enter_got = int(match.group(1))
        for tick in TICKS_RE.findall(line):
            ticks.append(int(tick))
        match = PROGRAMS_RE.search(line)
        if match:
            programs = [word for word in match.group(1).split() if word]
        if FAULT_RE.search(line):
            fault_isolation = True
        if date is None:
            match = DATE_RE.search(line)
            if match:
                date = match.group(1)

    if panic_count:
        verdict = "failing"
    elif alive_line is None:
        verdict = "missing-alive"
    else:
        verdict = "pass"

    return {
        "banner": banner,
        "alive": alive_line is not None,
        "alive_line": alive_line,
        "panic_count": panic_count,
        "readkeys": readkeys,
        "enter_seen": enter_got is not None,
        "enter_got": enter_got,
        "ticks": ticks,
        "programs": programs,
        "fault_isolation": fault_isolation,
        "date": date,
        "verdict": verdict,
        "lines": len(lines),
    }


def parse_file(path: str | Path) -> dict:
    return parse_log(Path(path).read_text(encoding="utf-8", errors="replace"))


def main(path: str) -> int:
    record = parse_file(path)
    print(f"banner: {record['banner']}")
    print(f"alive: {record['alive']}")
    print(f"panics: {record['panic_count']}")
    print(f"readkeys: {len(record['readkeys'])}")
    print(f"ticks: {record['ticks']}")
    print(f"verdict: {record['verdict']}")
    return 0 if record["verdict"] == "pass" else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: bootlog_parse.py <serial-log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
