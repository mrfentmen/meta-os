#!/usr/bin/env python3
"""Scan every os-build status file for numbers this branch can decide.

A "claim" here is a number tied to something countable in the tree: how many
crates exist, and how many files and lines the kernel source has. Everything
else a status file says -- pass counts, spend, gate results, prose verdicts --
needs the run that produced it, so this tool does not pretend to judge it.

    python3 os-build/tools/cross_lane_claims.py            summary, exit 1 on a contradiction
    python3 os-build/tools/cross_lane_claims.py --check    same, CI style
    python3 os-build/tools/cross_lane_claims.py --write    regenerate the report file
    python3 os-build/tools/cross_lane_claims.py --table    every row

Rules, and why each one exists. Each was added because the loose version
flagged something that was not a claim:

  * `N crates` only counts when not followed by `/`. The table row
    `| 1 crates/os-boot | ... |` is a list index, not a count.
  * A line that already carries STALE / CURRENT / CONTRADICTED / MATCH is an
    audit of a number, not a claim about it. Judging those flags the
    corrections as errors.
  * A kernel measurement is only read from the paired form
    `N files, M lines`. A line count on its own is usually something else:
    `serial 1086 lines panic 0` is a boot capture, `276 lines with worked
    examples` is a document.
  * There is no `N test files` rule. That phrase means `tests/`, per-crate
    test files, or ISO-only files depending on the file; a guess would be noise.

Exit codes: 0 clean, 1 a claim is contradicted, 2 the scan could not run.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERDICT_WORDS = re.compile(r"\b(STALE|CURRENT|CONTRADICTED|MATCH|UNCHECKABLE)\b")

# One measurement, two numbers: `13 files, 5833 lines`. Anything looser caught
# boot logs and prose, so the pair is required.
KERNEL_PAIR = re.compile(r"\b(\d+)\s+files?,?\s+([\d,]{3,})\s+lines\b")
CRATES = re.compile(r"(?<![\w.])(\d+)\s+crates\b(?!\s*/)")

REPORT_PATH = Path("os-build/CROSS_LANE_CLAIM_SCAN.md")
SCAN_GLOBS = ("os-build/*STATUS*.md", "os-build/*_STATUS*.md")
EXTRA_FILES = ("PROGRAM_PROOF_LEDGER.md", "README_AUDIT_BOND.md")


def tree_values(root: Path) -> dict[str, tuple[int | None, str]]:
    """The facts every claim is measured against, read from the tree itself."""
    crates = len([p for p in (root / "crates").glob("*/") if p.is_dir()]) or None
    kernel = sorted((root / "kernel" / "src").glob("*.rs"))
    lines = None
    if kernel:
        lines = sum(
            len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            for p in kernel
        )
    return {
        "crates": (crates, "crates/*/"),
        "kernel lines": (lines, "kernel/src/*.rs"),
        "kernel files": (len(kernel) or None, "kernel/src/*.rs"),
    }


def is_kernel_source_claim(line: str) -> bool:
    """A kernel source measurement, not a boot log that happens to count lines."""
    low = line.lower()
    if "kernel" not in low:
        return False
    return not any(word in low for word in ("serial", "panic", "boot log", "ticks"))


def scan(root: Path = Path(".")) -> tuple[list[dict], dict]:
    values = tree_values(root)
    files = sorted(
        {p for pattern in SCAN_GLOBS for p in root.glob(pattern)}
        | {root / "os-build" / name for name in EXTRA_FILES}
    )
    files = [f for f in files if f.is_file()]

    rows: list[dict] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), 1):
            if VERDICT_WORDS.search(line):
                continue
            found: list[tuple[str, int]] = []
            for match in CRATES.finditer(line):
                # `1 crates/os-boot` is a row number, not a count.
                if match.end() < len(line) and line[match.end()] == "/":
                    continue
                found.append(("crates", int(match.group(1))))
            if is_kernel_source_claim(line):
                for match in KERNEL_PAIR.finditer(line):
                    found.append(("kernel files", int(match.group(1))))
                    found.append(("kernel lines", int(match.group(2).replace(",", ""))))

            for label, said in found:
                actual = values[label][0]
                if actual is None:
                    continue
                rows.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "label": label,
                        "said": said,
                        "actual": actual,
                        "verdict": "MATCH" if said == actual else "CONTRADICTED",
                        "text": line.strip(),
                    }
                )

    counts = {"MATCH": 0, "CONTRADICTED": 0}
    for row in rows:
        counts[row["verdict"]] += 1
    return rows, {"values": values, "counts": counts, "files": files}


def render(rows: list[dict], meta: dict) -> str:
    values, counts = meta["values"], meta["counts"]
    out = [
        "# Cross-lane claim scan — 2026-11-03",
        "",
        "Generated by `os-build/tools/cross_lane_claims.py`. Do not hand-edit:",
        "run the tool and commit what it writes.",
        "",
        "Only numbers with a tree-side definition are judged here. A status file's",
        "pass counts, spend and gate results need the run that produced them, and",
        "are listed at the bottom as out of scope rather than guessed at.",
        "",
        "## Tree values",
        "",
        "| Metric | Value | Base |",
        "|---|---|---|",
    ]
    for label, (value, base) in values.items():
        out.append(f"| {label} | {'missing' if value is None else value} | `{base}` |")
    out += [
        "",
        "## Counts",
        "",
        "| Verdict | Rows |",
        "|---|---|",
        f"| **MATCH** | {counts['MATCH']} |",
        f"| **CONTRADICTED** | {counts['CONTRADICTED']} |",
        f"| files scanned | {len(meta['files'])} |",
        "",
        "## Rows",
        "",
        "| File:line | Claim | Says | Tree | Verdict |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        out.append(
            f"| `{row['file']}:{row['line']}` | {row['label']} | {row['said']} "
            f"| {row['actual']} | **{row['verdict']}** |"
        )
    if not rows:
        out.append("| — | — | — | — | no countable claims found |")

    contradicted = [r for r in rows if r["verdict"] == "CONTRADICTED"]
    out += ["", "## What is contradicted", ""]
    if contradicted:
        for row in contradicted:
            out.append(
                f"- `{row['file']}:{row['line']}` — says {row['said']} {row['label']}; "
                f"tree has {row['actual']}. \"{row['text'][:120]}\""
            )
    else:
        out.append("- nothing this scan can decide.")
    out += [
        "",
        "## Rules, and why each one is there",
        "",
        "| Rule | Reason |",
        "|---|---|",
        "| `N crates` not followed by `/` | `| 1 crates/os-boot |` is a table row number, not a count |",
        "| skip a line carrying STALE / CURRENT / CONTRADICTED / MATCH | that row is an audit of the number, not a claim of it |",
        "| kernel numbers only from `N files, M lines` | `serial 1086 lines panic 0` is a boot capture; `276 lines` is prose |",
        "| kernel line must mention `kernel`, not serial/panic | a capture is a measurement of a boot, not of the source |",
        "| no `N test files` rule | the phrase means `tests/`, per-crate, or ISO-only depending on the file |",
        "",
        "## Not decidable from this branch",
        "",
        "- Pass/fail counts, spend and gate results: these need the run, not a file count.",
        "- Claims pinned to another branch's tip. A status file naming a commit is a",
        "  record of that commit, not a statement about this tree.",
        "- Prose verdicts: \"complete\", \"all five\", \"proven\".",
        "- A line count written without its file count. That is a claim, but not one",
        "  this scan can tell apart from a log capture, so it stays unjudged.",
        "",
    ]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="tree to measure (default: .)")
    parser.add_argument("--write", action="store_true", help="regenerate the report file")
    parser.add_argument("--check", action="store_true", help="CI mode: quiet, exit 1 on a contradiction")
    parser.add_argument("--table", action="store_true", help="print every row")
    args = parser.parse_args(argv)

    root = Path(args.root)
    if not (root / "os-build").is_dir():
        print(f"claim scan: no os-build under {root.resolve()}", file=sys.stderr)
        return 2

    rows, meta = scan(root)
    counts = meta["counts"]

    if args.write:
        (root / REPORT_PATH).write_text(render(rows, meta), encoding="utf-8")
        print(f"wrote {REPORT_PATH}")

    if args.table or not args.check:
        for label, (value, base) in meta["values"].items():
            print(f"  {label:<14} {str(value):>6}   {base}")
        print()
        for row in rows:
            print(
                f"  {row['verdict']:<12} {row['file']}:{row['line']}  "
                f"{row['label']} says {row['said']} tree {row['actual']}"
            )

    print(
        f"\nCLAIMS: {counts['CONTRADICTED']} contradicted, {counts['MATCH']} match, "
        f"{len(meta['files'])} file(s) scanned"
    )
    return 1 if counts["CONTRADICTED"] else 0


if __name__ == "__main__":
    sys.exit(main())
