#!/usr/bin/env python3
"""claim_check.py — every "proven" claim must cite a file that exists.

The repo's status documents are built on citations: "PROVEN — os-build/logs/K1-boot.txt".
That is the right shape, and nothing has ever checked that the cited file still exists or
that a claim carries a citation at all. A dead citation reads exactly like a live one.

What this does, per line of the status documents:

  - skip headings and lines that negate the claim ("not proven", "unproven", "NOT PROVEN");
  - for a line containing proven/PROVEN, require at least one backticked path;
  - every backticked path must resolve on disk (globs are expanded, directories allowed);
  - report a claim with no citation as "uncited", and a citation that resolves to
    nothing as "dead".

It checks existence, not truth. A file can exist and say the opposite of the sentence
citing it; only reading does that. This is the cheap half of the audit, and it is the half
that decays silently.

Usage: claim_check.py [--verbose]   (from the repo root)
Exit: 0 all claims cited and resolvable, 1 otherwise, 2 missing input.
"""

import pathlib
import re
import sys

SCAN = [
    "os-build/OS_STATUS.md",
    "os-build/KERNEL_STATUS.md",
    "os-build/SCOREBOARD.md",
    "os-build/ROOT_MANIFEST.md",
    "os-build/QEMU_LIMITS.md",
    "os-build/USERSPACE_ABI.md",
    "os-build/USERSPACE_PROGRAMS.md",
    "os-build/BOOT_MANIFEST.md",
    "os-build/SERVICE_FAILURE_TABLE.md",
    "os-build/ROWAN_PROPOSALS.md",
    "kernel/BUILD_LOG.md",
    "kernel/README.md",
]
RECORDS = "os-build/records"

NEGATIONS = ("not proven", "unproven", "not boot-proven", "never proven", "not claimed")
PATH_RE = re.compile(r"`([^`\s]+)`")
PATHISH = re.compile(r"(os-build/|kernel/|services/|crates/|agents/|aegis/|tests/|docs/)")
ARTIFACT_EXT = (".txt", ".png", ".json", ".md", ".rs", ".py", ".sh",
                ".goose", ".mjs", ".ppm")


def is_pathish(token):
    if token.startswith(("http://", "https://")):
        return False
    if PATHISH.search(token) and "/" in token:
        return True
    # Bare artifact names are how the logs are cited in milestone tables
    # (`K1-boot.txt`, `K2-boot.png`). Without this the audit reports a citation
    # as missing precisely because it is written the way the docs actually do.
    return token.endswith(ARTIFACT_EXT) and " " not in token and len(token) < 120


def resolves(token):
    if any(ch in token for ch in "*?["):
        return bool(list(pathlib.Path(".").glob(token)))
    clean = token.rstrip(".,;:")
    for base in ("", "os-build/logs/", "kernel/src/", "kernel/"):
        if pathlib.Path(base + clean).exists():
            return True
    return False


def main(argv):
    verbose = "--verbose" in argv
    files = [f for f in SCAN if pathlib.Path(f).is_file()]
    if pathlib.Path(RECORDS).is_dir():
        files += sorted(str(p) for p in pathlib.Path(RECORDS).glob("*.md"))
    if not files:
        print("claim_check: no status documents found", file=sys.stderr)
        return 2

    uncited, dead, checked = [], [], 0
    for path in files:
        for number, line in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
            low = line.lower()
            if "proven" not in low:
                continue
            if any(neg in low for neg in NEGATIONS):
                continue
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            # Only claims that assert something: a table row or a bullet. Prose
            # that defines the status word, or describes a plan ("proven by
            # write → reboot → read"), is not a claim about a file.
            is_row = stripped.startswith("|") and not re.match(r"^\|[\s:|-]+\|", stripped)
            is_bullet = stripped.startswith(("- ", "* "))
            if not (is_row or is_bullet):
                continue
            checked += 1
            tokens = [t for t in PATH_RE.findall(line) if is_pathish(t)]
            existing = [t for t in tokens if resolves(t)]
            missing = [t for t in tokens if not resolves(t)]
            for token in missing:
                dead.append((path, number, token, line.strip()))
            if not existing:
                uncited.append((path, number, line.strip()))

    print(f"claim_check: {checked} proven/PROVEN lines in {len(files)} documents; "
          f"{len(dead)} dead citations, {len(uncited)} uncited claims")

    for path, number, token, line in dead:
        print(f"  dead   {path}:{number}: {token}")
        if verbose:
            print(f"         {line[:160]}")
    for path, number, line in uncited:
        print(f"  uncited {path}:{number}: {line[:120]}")

    if dead or uncited:
        print("claim_check: FAIL")
        return 1
    print("claim_check: every claim cites a file that exists")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
