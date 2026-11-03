"""spec_validate.py — validate an Officina part spec dict.

A spec is the four dimensions the heatsink simulator takes. Every field
must be present, numeric, and inside the declared range. Errors name the
field, so a caller can show which number to fix. `bool` is refused as a
number on purpose: True is not a fin count.
"""

from __future__ import annotations

FIN_HEIGHT_MM = (5.0, 80.0)
FIN_THICKNESS_MM = (0.5, 3.0)
FIN_COUNT = (4, 30)
BASE_THICKNESS_MM = (2.0, 12.0)

REQUIRED = ("fin_height_mm", "fin_thickness_mm", "fin_count", "base_thickness_mm")
RANGES = {
    "fin_height_mm": FIN_HEIGHT_MM,
    "fin_thickness_mm": FIN_THICKNESS_MM,
    "fin_count": FIN_COUNT,
    "base_thickness_mm": BASE_THICKNESS_MM,
}


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_spec(spec) -> list[str]:
    """Return named errors; an empty list means the spec is valid."""
    if not isinstance(spec, dict):
        return ["spec: must be an object"]
    errors = []
    for field in REQUIRED:
        if field not in spec:
            errors.append(f"{field}: missing")
            continue
        value = spec[field]
        if not _is_number(value):
            errors.append(f"{field}: must be a number, got {type(value).__name__}")
            continue
        low, high = RANGES[field]
        if not low <= value <= high:
            errors.append(f"{field}: {value} outside [{low}, {high}]")
        if field == "fin_count" and not isinstance(value, int):
            errors.append(f"{field}: must be a whole number")
    return errors


def main() -> int:
    import json
    import sys

    if len(sys.argv) != 2:
        print("usage: spec_validate.py <spec.json>")
        return 2
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        errors = validate_spec(json.load(fh))
    for error in errors:
        print(error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
