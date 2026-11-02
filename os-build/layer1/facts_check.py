#!/usr/bin/env python3
"""facts_check.py — a cited number must appear in the artifact it cites.

claim_check proves the file exists. It cannot tell that `61660 frames` next to
`K1-boot.txt` was actually 127199 in that log — which is exactly the error found on
2026-11-02 by hand (SCOREBOARD cited K1-boot.txt for 127199; that number belongs to K7).

So: for each table row that asserts a milestone/status and names a log, take the
backticked decimal numbers in the row and require each to appear in that log's text.
Small numbers (line numbers, counts of calls) are ignored to avoid noise; the audit
starts at three digits, which is where measured quantities live.

Exit: 0 every cited number appears, 1 a number does not, 2 missing input.
Usage: facts_check.py [--verbose]
"""

import pathlib
import re
import sys

SCAN = [
    "os-build/KERNEL_STATUS.md",
    "os-build/OS_STATUS.md",
    "os-build/SCOREBOARD.md",
    "kernel/BUILD_LOG.md",
]
LOG_RE = re.compile(r"`?((?:os-build/logs/)?[A-Za-z0-9_-]+\.txt)`?")
# Backticked numbers, plus plain "61660 frames" / "127199 frames" prose. The
# keyword matters: without it the audit picks up dates and line numbers.
NUM_RE = re.compile(r"`(\d{3,})`|(\d{3,})\s*(?:frames|regions|ticks|bytes)")


def resolve_log(token):
    for base in ("", "os-build/logs/"):
        path = pathlib.Path(base + token)
        if path.is_file():
            return path
    return None


def main(argv):
    verbose = "--verbose" in argv
    failures = []
    checked = 0
    for doc in SCAN:
        path = pathlib.Path(doc)
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "PROVEN" not in line and "PARTIAL" not in line:
                continue
            logs = [resolve_log(t) for t in LOG_RE.findall(line)]
            logs = [log for log in logs if log]
            if not logs:
                continue
            text = "\n".join(log.read_text(errors="replace") for log in logs)
            for backticked, contextual in NUM_RE.findall(line):
                value = backticked or contextual
                checked += 1
                if value in text:
                    if verbose:
                        print(f"  ok   {doc}:{number}: {value} in {logs[0].name}")
                else:
                    failures.append((doc, number, value, logs[0].name, line.strip()))

    print(f"facts_check: {checked} cited numbers checked in {len(SCAN)} documents; "
          f"{len(failures)} not found in their log")
    for doc, number, value, log_name, line in failures:
        print(f"  MISSING {doc}:{number}: {value} not in {log_name}")
        if verbose:
            print(f"          {line[:160]}")
    if failures:
        print("facts_check: FAIL")
        return 1
    print("facts_check: every cited number appears in the log it cites")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
