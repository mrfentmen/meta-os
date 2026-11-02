"""schema_index.py — emit a Markdown index of schemas and validators.

Paths and record names only: no file contents. A record name is a
schema's ``$id`` when it has one, else the filename stem. Validators are
the ``*_validate.py`` / ``*_validate.mjs`` modules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    "target",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".wrangler",
}
SCHEMA_SUFFIX = ".schema.json"
VALIDATOR_SUFFIXES = ("_validate.py", "_validate.mjs")


def _record_name(path: Path) -> str:
    if path.name.endswith(SCHEMA_SUFFIX):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return path.name
        if isinstance(doc, dict) and isinstance(doc.get("$id"), str):
            return doc["$id"]
        return path.name[: -len(SCHEMA_SUFFIX)]
    for suffix in VALIDATOR_SUFFIXES:
        if path.name.endswith(suffix):
            return path.name[: -len(suffix)]
    return path.stem


def scan(root: Path | str) -> list[dict]:
    """Return one entry per schema or validator under root, sorted by path."""
    root = Path(root).resolve()
    entries: list[dict] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.name.endswith(SCHEMA_SUFFIX):
            kind = "schema"
        elif path.name.endswith(VALIDATOR_SUFFIXES):
            kind = "validator"
        else:
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "kind": kind,
                "record": _record_name(path),
            }
        )
    entries.sort(key=lambda entry: entry["path"])
    return entries


def render(entries: list[dict]) -> str:
    lines = ["| Path | Kind | Record |", "|---|---|---|"]
    for entry in entries:
        lines.append(f"| `{entry['path']}` | {entry['kind']} | `{entry['record']}` |")
    return "\n".join(lines) + "\n"


def main(root: str | None = None) -> int:
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    entries = scan(root)
    sys.stdout.write(render(entries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
