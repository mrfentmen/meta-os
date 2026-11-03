"""receipt_check.py — count-only checks over a receipts JSONL file.

Delegates the per-line rules to server/queue/receipt_validate.py so the
Spark estimate rule has exactly one implementation. Prints counts and
line-numbered findings; never prints receipt contents.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "receipt_validate", ROOT / "server" / "queue" / "receipt_validate.py"
)
receipt_validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt_validate)


def check(text: str) -> dict:
    """Return {"lines", "valid", "errors"} with line-numbered errors."""
    result = receipt_validate.validate_text(text)
    errors = result["errors"]
    return {
        "lines": result["lines"],
        "valid": result["lines"] - len(errors),
        "errors": errors,
    }


def main(path: str) -> int:
    with open(path, "r", encoding="utf-8") as fh:
        result = check(fh.read())
    for error in result["errors"]:
        print(error)
    print(f"{result['lines']} line(s), {result['valid']} valid, {len(result['errors'])} error(s)")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: receipt_check.py <receipts.jsonl>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
