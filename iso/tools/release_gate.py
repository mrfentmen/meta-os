#!/usr/bin/env python3
"""release_gate.py — read the 1.0 checklist and name every open box.

The checklist is the release gate: a cut is only as good as the boxes it can
close. This reads that file as it is, groups the boxes by the milestone
heading above them, and prints the open ones with a line number so nobody has
to page through the document to find them.

    python3 iso/tools/release_gate.py                 the real checklist
    python3 iso/tools/release_gate.py --report        always exit 0
    python3 iso/tools/release_gate.py --json          for a script
    python3 iso/tools/release_gate.py --all           closed boxes too
    python3 iso/tools/release_gate.py --file PATH     another checklist

Exit 0 when every box is closed (or --report was passed), 1 when boxes are
open, 2 on bad usage. It reads; it writes nothing.
"""

import json
import re
import sys
from pathlib import Path

ISO = Path(__file__).resolve().parents[1]
DEFAULT = ISO.parent / "os-build" / "METAOS_1.0_RELEASE_CHECKLIST.md"

BOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+(.*)$")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")


def parse(text):
    lines = text.splitlines()
    section = "(before any heading)"
    entries = []
    i = 0
    while i < len(lines):
        line = lines[i]

        heading = HEADING.match(line)
        if heading:
            section = heading.group(1).strip()
            i += 1
            continue

        box = BOX.match(line)
        if not box:
            i += 1
            continue

        closed = box.group(1).lower() == "x"
        body = box.group(2).strip()
        start = i + 1
        j = i + 1
        # A wrapped box continues on following indented lines. Stop at a blank
        # line, a heading, or the next box.
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip() or BOX.match(nxt) or HEADING.match(nxt):
                break
            if nxt.startswith(" ") or nxt.startswith("\t"):
                body += " " + nxt.strip()
                j += 1
                continue
            break

        entries.append({"line": start, "section": section,
                        "closed": closed, "text": body})
        i = j

    return entries


def summarise(entries):
    sections = []
    for entry in entries:
        if not sections or sections[-1]["section"] != entry["section"]:
            sections.append({"section": entry["section"], "closed": 0, "open": 0})
        sections[-1]["closed" if entry["closed"] else "open"] += 1
    return sections


def main(argv):
    path = DEFAULT
    as_json = False
    show_all = False
    report_only = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--file" and i + 1 < len(argv):
            path = Path(argv[i + 1]).expanduser()
            i += 2
        elif arg == "--json":
            as_json = True
            i += 1
        elif arg == "--all":
            show_all = True
            i += 1
        elif arg == "--report":
            report_only = True
            i += 1
        elif arg in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        else:
            print("gate: unknown argument %s" % arg, file=sys.stderr)
            return 2

    if not path.is_file():
        print("gate: checklist not found: %s" % path, file=sys.stderr)
        return 2

    entries = parse(path.read_text(encoding="utf-8"))
    if not entries:
        print("gate: no boxes found in %s" % path, file=sys.stderr)
        return 2

    sections = summarise(entries)
    open_boxes = [e for e in entries if not e["closed"]]
    closed = len(entries) - len(open_boxes)

    if as_json:
        print(json.dumps({
            "file": str(path),
            "counts": {"total": len(entries), "closed": closed, "open": len(open_boxes)},
            "sections": sections,
            "open": open_boxes,
            "closed": [e for e in entries if e["closed"]],
        }, indent=2))
    else:
        print("release gate: %s" % path)
        width = max(len(s["section"]) for s in sections)
        for s in sections:
            total = s["closed"] + s["open"]
            print("  %-*s  %d/%d closed%s" % (width, s["section"], s["closed"], total,
                                              "" if s["open"] else "  <- done"))
        print()
        print("%d box(es): %d closed, %d open" % (len(entries), closed, len(open_boxes)))
        if open_boxes:
            print()
            for entry in open_boxes:
                print("OPEN  line %-4d [%s] %s"
                      % (entry["line"], entry["section"], entry["text"]))
        if show_all and closed:
            print()
            for entry in entries:
                if entry["closed"]:
                    print("DONE  line %-4d [%s] %s"
                          % (entry["line"], entry["section"], entry["text"]))
        print()
        print("GATE: %s" % ("GREEN — every box closed" if not open_boxes
                            else "RED — %d box(es) open" % len(open_boxes)))

    if report_only:
        return 0
    return 1 if open_boxes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
