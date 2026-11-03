"""kernel_census.py — count lines per file under a source tree.

Reads source files as data and never writes to them. Default filter is
`.rs`; pass another extension set to census other trees. Hidden and
build directories are skipped.
"""

from __future__ import annotations

import sys
from pathlib import Path

SKIP_DIRS = {".git", "target", "node_modules", "__pycache__", "dist", "build"}


def count_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def census(tree: str | Path, extensions: tuple[str, ...] = (".rs",)) -> dict:
    """Return {"files": [{path, lines}], "total_lines", "skipped"}."""
    tree = Path(tree)
    files = []
    skipped = 0
    for path in sorted(tree.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(tree)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix not in extensions:
            skipped += 1
            continue
        files.append({"path": relative.as_posix(), "lines": count_lines(path)})
    return {
        "files": files,
        "total_lines": sum(entry["lines"] for entry in files),
        "skipped": skipped,
    }


def render(result: dict) -> str:
    lines = ["| File | Lines |", "|---|---:|"]
    for entry in result["files"]:
        lines.append(f"| `{entry['path']}` | {entry['lines']} |")
    lines.append("")
    lines.append(f"{len(result['files'])} file(s), {result['total_lines']} line(s), {result['skipped']} skipped")
    return "\n".join(lines) + "\n"


def main(tree: str, *extensions: str) -> int:
    exts = tuple(extensions) if extensions else (".rs",)
    sys.stdout.write(render(census(tree, exts)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: kernel_census.py <tree> [extension ...]")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], *sys.argv[2:]))
