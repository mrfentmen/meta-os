"""gate_log_check.py — report which gate checks passed, by name.

Recognises the gate transcript's `PASS: <name>` / `FAIL: <name>` lines
and the closing `GATE GREEN n/n` line. A check that never appears is
neither passed nor failed; it is reported as missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHECK_RE = re.compile(r"^(PASS|FAIL):\s*(.+?)\s*$", re.M)
GREEN_RE = re.compile(r"GATE GREEN (\d+)/(\d+)")
EXPECTED_CHECKS = 7


def check_log(text: str) -> dict:
    checks = [{"name": name, "passed": status == "PASS"} for status, name in CHECK_RE.findall(text)]
    passed = [c["name"] for c in checks if c["passed"]]
    failed = [c["name"] for c in checks if not c["passed"]]
    green = GREEN_RE.search(text)
    expected = int(green.group(2)) if green else EXPECTED_CHECKS
    return {
        "checks": checks,
        "passed": passed,
        "failed": failed,
        "expected": expected,
        "green": len(passed) == expected and not failed,
        "missing": max(0, expected - len(checks)),
    }


def render(result: dict) -> str:
    lines = [f"{'PASS' if check['passed'] else 'FAIL'} {check['name']}" for check in result["checks"]]
    lines.append(f"{len(result['passed'])}/{result['expected']} passed")
    if result["missing"]:
        lines.append(f"{result['missing']} check(s) missing")
    return "\n".join(lines) + "\n"


def main(path: str) -> int:
    result = check_log(Path(path).read_text(encoding="utf-8", errors="replace"))
    sys.stdout.write(render(result))
    return 0 if result["green"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: gate_log_check.py <gate.log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
