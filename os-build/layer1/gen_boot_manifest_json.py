#!/usr/bin/env python3
"""gen_boot_manifest_json.py — emit the machine-readable boot manifest.

The image lane consumes the boot manifest (`os-build/face/` reads it), and a
Markdown table is not a data format. This writes `os-build/boot-manifest.json`
from the two documents that already exist, computing effective fatality through
the dependency closure so a consumer cannot repeat the 7-vs-9 mistake.

Source of truth stays the documents; this is a rendering of them, and
`boot_manifest_check.py` fails if the JSON and the documents disagree.

Usage: gen_boot_manifest_json.py  (from the repo root)
"""

import json
import pathlib
import sys

ORDER = "os-build/layer1/BOOT_ORDER.md"
MANIFEST = "os-build/BOOT_MANIFEST.md"
OUT = "os-build/boot-manifest.json"
BOOT_LINE = "meta-os 0.1  (K6)  <n> services degraded: <comma-separated ids>"


def parse_rows(text, min_cells):
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < min_cells or not cells[0].isdigit():
            continue
        rows.append(cells)
    return rows


def main():
    order_text = pathlib.Path(ORDER).read_text()
    manifest_text = pathlib.Path(MANIFEST).read_text()

    order = {}
    for cells in parse_rows(order_text, 4):
        needs_raw = cells[2]
        order[cells[1].replace("*", "").strip()] = {
            "order": int(cells[0]),
            "needs": [] if needs_raw in ("—", "-", "") else [
                n.strip() for n in needs_raw.split(",") if n.strip()
            ],
            "fatal": cells[3].lower() == "yes",
        }
    loses = {cells[1]: cells[5] for cells in parse_rows(manifest_text, 6)}

    def closure(name, seen):
        for need in order.get(name, {}).get("needs", []):
            if need not in seen:
                seen.add(need)
                closure(need, seen)
        return seen

    fatal = {n for n, r in order.items() if r["fatal"]}
    effective = set(fatal) | {
        n for n in order if any(n in closure(f, set()) for f in fatal)
    }

    services = []
    for name in sorted(order, key=lambda n: order[n]["order"]):
        services.append({
            "order": order[name]["order"],
            "id": name,
            "needs": order[name]["needs"],
            "fatal_on_paper": order[name]["fatal"],
            "fatal_in_effect": name in effective,
            "loss": loses.get(name, ""),
        })

    doc = {
        "generated_from": [ORDER, MANIFEST],
        "note": ("Effective fatality is computed through the dependency closure. "
                 "A non-fatal service that a fatal service needs stops the boot too."),
        "boot_line": BOOT_LINE,
        "counts": {
            "services": len(services),
            "fatal_on_paper": len(fatal),
            "fatal_in_effect": len(effective),
        },
        "services": services,
    }
    pathlib.Path(OUT).write_text(json.dumps(doc, indent=2) + "\n")
    print(f"gen_boot_manifest_json: wrote {OUT} ({len(services)} services, "
          f"{len(effective)} fatal in effect)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
