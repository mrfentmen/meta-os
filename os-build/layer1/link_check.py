#!/usr/bin/env python3
"""link_check.py — relative links in the status documents must resolve.

A status page that links to a file nobody kept is the same failure as a citation to a
deleted log: it reads as evidence and is not. This checks the documents whose links are
part of the argument (status, records, proposals, indexes), not the whole repo.

External http(s) links and pure anchors are skipped: they are not in the repo's control.

Exit: 0 all relative links resolve, 1 a link is broken, 2 missing input.
Usage: link_check.py [--verbose]
"""

import pathlib
import re
import sys

DOCS = [
    "os-build/OS_STATUS.md",
    "os-build/KERNEL_STATUS.md",
    "os-build/SCOREBOARD.md",
    "os-build/ROOT_MANIFEST.md",
    "os-build/BOOT_MANIFEST.md",
    "os-build/SERVICE_FAILURE_TABLE.md",
    "os-build/USERSPACE_ABI.md",
    "os-build/USERSPACE_PROGRAMS.md",
    "os-build/QEMU_LIMITS.md",
    "os-build/ROWAN_PROPOSALS.md",
    "os-build/INDEX.md",
    "os-build/layer1/README.md",
    "os-build/proposals/README.md",
]
GLOBS = ["os-build/records/*.md", "os-build/proposals/*.md"]
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def main(argv):
    verbose = "--verbose" in argv
    docs = [pathlib.Path(d) for d in DOCS if pathlib.Path(d).is_file()]
    for pattern in GLOBS:
        docs += sorted(pathlib.Path(".").glob(pattern))
    if not docs:
        print("link_check: no documents found", file=sys.stderr)
        return 2

    broken, checked = [], 0
    for path in docs:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            for target in LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                checked += 1
                clean = target.split("#", 1)[0]
                resolved = (path.parent / clean).resolve()
                if not resolved.exists():
                    broken.append((path, number, target))
                    if verbose:
                        print(f"  broken {path}:{number}: {target}")

    print(f"link_check: {checked} relative links in {len(docs)} documents; {len(broken)} broken")
    for path, number, target in broken:
        print(f"  MISSING {path}:{number}: {target}")
    if broken:
        print("link_check: FAIL")
        return 1
    print("link_check: every relative link resolves")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
