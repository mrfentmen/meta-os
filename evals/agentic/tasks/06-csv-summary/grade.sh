#!/bin/sh
set -e
python3 - <<'PY'
import csv, json, collections
rows = list(csv.DictReader(open("data.csv")))
tot = collections.Counter()
for r in rows:
    tot[r["region"]] += int(r["units"])
want = {"rows": len(rows), "total_units": sum(tot.values()), "top_region": tot.most_common(1)[0][0]}
got = json.load(open("summary.json"))
assert got == want, (got, want)
PY
