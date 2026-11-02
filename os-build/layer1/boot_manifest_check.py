#!/usr/bin/env python3
"""boot_manifest_check.py — hold the boot manifest to the boot order table.

Reads `os-build/layer1/BOOT_ORDER.md` (the sequence) and `os-build/BOOT_MANIFEST.md`
(the consequences), recomputes the dependency closure, and fails on disagreement:

  - a service in one file and not the other,
  - an order row whose `needs` are not strictly earlier (the invariant BOOT_ORDER
    itself claims to enforce),
  - an `effective` fatal value that does not match the cascade computation,
  - the boot-line format missing from the manifest.

The point is finding 1 in the manifest: `fatal` on paper and fatal in effect are
different sets, and only the second one predicts whether a boot survives.

Exit: 0 in agreement, 1 on drift, 2 on a missing file.
"""

import json
import pathlib
import re
import sys

ORDER_FILE = "os-build/layer1/BOOT_ORDER.md"
MANIFEST_FILE = "os-build/BOOT_MANIFEST.md"


def read(path):
    p = pathlib.Path(path)
    if not p.is_file():
        print(f"boot_manifest: missing {path}", file=sys.stderr)
        sys.exit(2)
    return p.read_text()


def parse_order(text):
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        order = int(cells[0])
        service = cells[1].replace("*", "").strip()
        needs_raw = cells[2]
        needs = set() if needs_raw in ("—", "-", "") else {
            n.strip() for n in needs_raw.split(",") if n.strip()
        }
        rows[service] = {"order": order, "needs": needs, "fatal": cells[3].lower() == "yes"}
    return rows


def parse_manifest(text):
    rows = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        rows[cells[1]] = {"order": int(cells[0]), "effective": cells[4].replace("*", "")}
    return rows


def closure(service, rows, seen=None):
    seen = seen or set()
    for need in rows.get(service, {}).get("needs", ()):
        if need not in seen:
            seen.add(need)
            closure(need, rows, seen)
    return seen


def main():
    order = parse_order(read(ORDER_FILE))
    manifest = parse_manifest(read(MANIFEST_FILE))
    manifest_text = read(MANIFEST_FILE)
    failures = []

    if set(order) != set(manifest):
        only_order = sorted(set(order) - set(manifest))
        only_manifest = sorted(set(manifest) - set(order))
        if only_order:
            failures.append(f"missing from manifest: {only_order}")
        if only_manifest:
            failures.append(f"not in the boot order: {only_manifest}")

    # Invariant the boot order claims: every need is strictly earlier.
    for service, row in order.items():
        for need in row["needs"]:
            if need not in order:
                failures.append(f"{service} needs unknown service {need}")
            elif order[need]["order"] >= row["order"]:
                failures.append(
                    f"{service} (#{row['order']}) needs {need} (#{order[need]['order']}), "
                    "which is not earlier"
                )

    # Effective fatal: a service dies with the boot if any fatal service depends on it.
    fatal = {s for s, r in order.items() if r["fatal"]}
    effective = set(fatal)
    for service in order:
        if any(service in closure(f, order) for f in fatal):
            effective.add(service)

    for service in sorted(order):
        marked = manifest.get(service, {}).get("effective", "")
        should = "yes" if service in effective else "no"
        if marked != should:
            failures.append(f"{service}: manifest says effective={marked!r}, cascade says {should!r}")

    if "services degraded:" not in manifest_text:
        failures.append("boot line format ('services degraded:') missing from the manifest")

    # The generated JSON claims to be a rendering of these two documents. If it
    # drifts, a consumer (the image lane) reads a different boot order than the
    # one this checker just validated — the worst kind of agreement, because
    # both files pass on their own.
    json_path = pathlib.Path("os-build/boot-manifest.json")
    if not json_path.is_file():
        failures.append("boot-manifest.json missing (run gen_boot_manifest_json.py)")
    else:
        data = json.loads(json_path.read_text())
        by_id = {s.get("id"): s for s in data.get("services", [])}
        if set(by_id) != set(order):
            failures.append("boot-manifest.json service set differs from BOOT_ORDER.md")
        for name, row in order.items():
            entry = by_id.get(name)
            if not entry:
                continue
            if entry.get("order") != row["order"]:
                failures.append(f"json {name}: order {entry.get('order')} != {row['order']}")
            if sorted(entry.get("needs", [])) != sorted(row["needs"]):
                failures.append(f"json {name}: needs {entry.get('needs')} != {row['needs']}")
            if bool(entry.get("fatal_in_effect")) != (name in effective):
                failures.append(f"json {name}: fatal_in_effect disagrees with the closure")

    print(f"boot_manifest: {len(order)} services, fatal on paper={len(fatal)}, "
          f"fatal in effect={len(effective)}, json {'checked' if json_path.is_file() else 'missing'}")
    print(f"  effective-fatal adds: {sorted(effective - fatal)}")
    print(f"  truly degradable: {sorted(set(order) - effective)}")

    if failures:
        print("boot_manifest: DRIFT")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("boot_manifest: order, closure and manifest agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
