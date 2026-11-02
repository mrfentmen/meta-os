#!/usr/bin/env python3
"""root_manifest_check.py — every path the root manifest names must exist.

`os-build/ROOT_MANIFEST.md` draws the line between OS and programs by listing paths. If a
directory is renamed or removed, the manifest silently keeps claiming it — and the line
between "the OS" and "a program" is the one document that must not drift quietly.

Only the first cell of each table row is checked (the path column). Backticked tokens with
a slash or a known artifact extension are treated as paths.

Exit: 0 all named paths exist, 1 one does not, 2 missing manifest.
Usage: root_manifest_check.py [--verbose]
"""

import pathlib
import re
import sys

MANIFEST = "os-build/ROOT_MANIFEST.md"
TOKEN_RE = re.compile(r"`([^`]+)`")
EXT = (".md", ".rs", ".txt", ".json", ".js", ".mjs", ".py", ".goose", ".html", ".css")


def pathish(token):
    token = token.strip()
    if token.startswith(("http://", "https://")):
        return False
    return "/" in token or token.endswith(EXT)


def main(argv):
    verbose = "--verbose" in argv
    path = pathlib.Path(MANIFEST)
    if not path.is_file():
        print(f"root_manifest_check: missing {MANIFEST}", file=sys.stderr)
        return 2

    checked, missing = 0, []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        stripped = line.lstrip()
        if not stripped.startswith("|") or re.match(r"^\|[\s:|-]+\|", stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first.lower().startswith(("path", "service", "#", "library")):
            continue
        for token in TOKEN_RE.findall(first):
            if not pathish(token):
                continue
            checked += 1
            target = token.rstrip("/")
            # The manifest groups crates as `crates/os-*`; a glob is a real claim
            # and is checked by expansion, not by treating the star as a name.
            if any(ch in target for ch in "*?["):
                found = bool(list(pathlib.Path(".").glob(target)))
            else:
                found = pathlib.Path(target).exists()
            if not found:
                missing.append((number, token))
                if verbose:
                    print(f"  missing {MANIFEST}:{number}: {token}")

    print(f"root_manifest_check: {checked} paths named; {len(missing)} missing")
    for number, token in missing:
        print(f"  MISSING line {number}: {token}")
    if missing:
        print("root_manifest_check: FAIL")
        return 1
    print("root_manifest_check: every path the manifest names exists")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
