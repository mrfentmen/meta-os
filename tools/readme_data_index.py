"""readme_data_index.py — Markdown table from docs/readme-data.

Columns: name, status, proof pointer. Reads the JSON files as data; a
malformed file is reported by name, never skipped silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def scan(directory: str | Path) -> dict:
    directory = Path(directory)
    rows = []
    errors = []
    for path in sorted(directory.glob("*.json"), key=lambda p: p.name):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        rows.append(
            {
                "file": path.name,
                "name": data.get("name", "—"),
                "status": data.get("status", "—"),
                "proof": data.get("proof", "—"),
            }
        )
    return {"rows": rows, "errors": errors}


def render(result: dict) -> str:
    lines = ["| Program | Status | Proof |", "|---|---|---|"]
    for row in result["rows"]:
        lines.append(f"| {row['name']} | {row['status']} | {row['proof']} |")
    for error in result["errors"]:
        lines.append(f"| {error} | — | — |")
    return "\n".join(lines) + "\n"


def main(directory: str | None = None) -> int:
    target = Path(directory) if directory else Path(__file__).resolve().parents[1] / "docs" / "readme-data"
    result = scan(target)
    sys.stdout.write(render(result))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
