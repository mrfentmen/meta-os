"""receipt_validate.py — shape checks for model receipt JSONL lines.

A receipt is one JSON object per line. The real files in
os-build/logs/wave3-model-proofs carry:

    ts, kind, model, surface, usage{...}, latency_ms, est_cost_usd

Older task text calls `surface` "endpoint" and `est_cost_usd` "estimate";
both names are accepted, and the canonical `surface`/`est_cost_usd`
spelling is what the shipped logs use.

Rules:
  * model is a non-empty string
  * surface (or endpoint) is a non-empty string
  * latency_ms is a non-negative integer
  * a Spark model must carry a numeric dollar estimate; any other model
    must carry null (no invented spend for a lane that does not bill)

Errors name the 1-based line number. Counts only otherwise.
"""

from __future__ import annotations

import json
import sys

SPARK_MARKER = "spark"


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_line(raw: str, number: int) -> list[str]:
    """Return findings for one line; an empty list means the line is valid."""
    try:
        record = json.loads(raw)
    except json.JSONDecodeError:
        return [f"line {number}: not valid JSON"]
    if not isinstance(record, dict):
        return [f"line {number}: receipt must be a JSON object"]

    errors: list[str] = []
    model = record.get("model")
    if not isinstance(model, str) or not model.strip():
        errors.append(f"line {number}: model must be a non-empty string")

    endpoint = record.get("surface", record.get("endpoint"))
    if not isinstance(endpoint, str) or not endpoint.strip():
        errors.append(f"line {number}: surface/endpoint must be a non-empty string")

    latency = record.get("latency_ms")
    if not _is_int(latency) or latency < 0:
        errors.append(f"line {number}: latency_ms must be a non-negative integer")

    estimate = record.get("est_cost_usd", record.get("estimate"))
    spark = isinstance(model, str) and SPARK_MARKER in model.lower()
    if spark:
        if not isinstance(estimate, (int, float)) or isinstance(estimate, bool):
            errors.append(f"line {number}: a Spark receipt must carry a numeric est_cost_usd")
    elif estimate is not None:
        errors.append(f"line {number}: a non-Spark receipt must carry a null est_cost_usd")
    return errors


def validate_text(text: str) -> dict:
    """Validate a whole file body. Blank trailing lines are ignored."""
    errors: list[str] = []
    lines = 0
    for index, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        lines += 1
        errors.extend(validate_line(raw, index))
    return {"lines": lines, "errors": errors, "ok": not errors}


def main(path: str) -> int:
    with open(path, "r", encoding="utf-8") as fh:
        result = validate_text(fh.read())
    for error in result["errors"]:
        print(error)
    print(f"{result['lines']} receipt line(s), {len(result['errors'])} error(s)")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: receipt_validate.py <receipts.jsonl>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
