"""log_diff_claims.py — which claim checks changed between two logs.

Compares two parsed boot logs through bootlog_verdict and lists only the
checks whose pass state changed. A check that did not change is silent.
"""

from __future__ import annotations

import sys
from pathlib import Path

from bootlog_parse import parse_log
from bootlog_verdict import changed_checks, evaluate


def diff_texts(before: str, after: str) -> list[str]:
    return changed_checks(evaluate(parse_log(before)), evaluate(parse_log(after)))


def render(names: list[str]) -> str:
    if not names:
        return "no claim checks changed\n"
    return "\n".join(f"changed: {name}" for name in names) + "\n"


def main(before_path: str, after_path: str) -> int:
    before = Path(before_path).read_text(encoding="utf-8", errors="replace")
    after = Path(after_path).read_text(encoding="utf-8", errors="replace")
    names = diff_texts(before, after)
    sys.stdout.write(render(names))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: log_diff_claims.py <before.log> <after.log>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
