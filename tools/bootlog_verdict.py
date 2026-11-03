"""bootlog_verdict.py — apply the boot claim checks to a parsed log.

Four checks, each reported by name, never collapsed into one boolean:

    alive             the K1 alive line is present
    three_programs    hello, sleeper and crasher are all named
    fault_isolation   a user page fault names the killed task
    panic_zero        the panic line count is zero
"""

from __future__ import annotations

import sys

from bootlog_parse import parse_file, parse_log

REQUIRED_PROGRAMS = ("hello", "sleeper", "crasher")


def evaluate(parsed: dict) -> dict:
    """Return {check: {passed, detail}} plus an overall `all_green` flag."""
    programs = set(parsed.get("programs") or [])
    checks = {
        "alive": {
            "passed": bool(parsed.get("alive")),
            "detail": parsed.get("alive_line") or "alive line missing",
        },
        "three_programs": {
            "passed": all(name in programs for name in REQUIRED_PROGRAMS),
            "detail": f"found {sorted(programs)}",
        },
        "fault_isolation": {
            "passed": bool(parsed.get("fault_isolation")),
            "detail": "user page fault names the killed task"
            if parsed.get("fault_isolation")
            else "no fault-isolation line",
        },
        "panic_zero": {
            "passed": parsed.get("panic_count", 0) == 0,
            "detail": f"panic count {parsed.get('panic_count', 0)}",
        },
    }
    return {"checks": checks, "all_green": all(c["passed"] for c in checks.values())}


def changed_checks(before: dict, after: dict) -> list[str]:
    """Names of checks whose passed state differs between two verdicts."""
    return [
        name
        for name, result in after["checks"].items()
        if before["checks"].get(name, {}).get("passed") != result["passed"]
    ]


def main(path: str) -> int:
    result = evaluate(parse_file(path))
    for name, check in result["checks"].items():
        print(f"{'PASS' if check['passed'] else 'FAIL'} {name}: {check['detail']}")
    return 0 if result["all_green"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: bootlog_verdict.py <serial-log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
