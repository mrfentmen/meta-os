#!/bin/sh
set -e
python3 - <<'PY'
import json, collections
d = json.load(open("counts.json"))
c = collections.Counter()
for line in open("app.log"):
    parts = line.split()
    if len(parts) > 1:
        c[parts[1].lower()] += 1
want = {"error": c["error"], "warn": c["warn"], "info": c["info"]}
assert d == want, (d, want)
assert want == {"error": 3, "warn": 2, "info": 3}, want
PY
