#!/usr/bin/env python3
"""failure_table_check.py — coverage and shape check for the service failure table.

`os-build/SERVICE_FAILURE_TABLE.md` claims a row per boot-table service, each with a
contract citation. This verifies exactly that, and nothing about whether the
symptoms are right — only a boot can judge those.

Fails when: a service in BOOT_ORDER.md has no row, a row names a service that is not
in the boot order, a row has no citation, or a non-"contract silent" row does not
cite a real file path. Exits 0 when the table covers all 22 services.

Usage: failure_table_check.py  (from the repo root)
"""

import pathlib
import re
import sys

ORDER = "os-build/layer1/BOOT_ORDER.md"
TABLE = "os-build/SERVICE_FAILURE_TABLE.md"


def read(path):
    p = pathlib.Path(path)
    if not p.is_file():
        print(f"failure_table: missing {path}", file=sys.stderr)
        sys.exit(2)
    return p.read_text()


def boot_ids(text):
    ids = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and cells[0].isdigit():
            ids.append(cells[1].replace("*", "").strip())
    return ids


def main():
    ids = boot_ids(read(ORDER))
    table = read(TABLE)
    failures = []

    # Rows are the markdown lines whose first cell is a bare service id.
    rows = {}
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not re.fullmatch(r"[a-z][a-z0-9_-]*", cells[0]):
            continue
        rows[cells[0]] = cells

    missing = [s for s in ids if s not in rows]
    extra = [s for s in rows if s not in ids]
    if missing:
        failures.append(f"no row for: {missing}")
    if extra:
        failures.append(f"row for a service not in the boot order: {extra}")

    for service, cells in rows.items():
        contract, silent, symptom = cells[1], cells[2].lower(), cells[3]
        if not contract:
            failures.append(f"{service}: empty contract column")
            continue
        if not symptom:
            failures.append(f"{service}: empty symptom column")
        if silent.startswith("yes"):
            continue
        # A non-silent row must cite a file that exists.
        for path in re.findall(r"`?(services/[A-Za-z0-9_./-]+)", contract):
            clean = path.rstrip("`")
            if not pathlib.Path(clean).exists():
                failures.append(f"{service}: cites missing file {clean}")

    print(f"failure_table: {len(rows)} rows for {len(ids)} services, "
          f"{sum(1 for c in rows.values() if c[2].lower().startswith('yes'))} contracts silent")

    if failures:
        print("failure_table: DRIFT")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("failure_table: every boot service has a row and a citation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
