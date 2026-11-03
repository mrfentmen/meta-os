#!/bin/sh
set -e
python3 - <<'PY'
import json
d = json.load(open("config.json"))
assert d["service"] == "meta", d
assert d["port"] == 18900, d
assert d["enabled"] is True, d
PY
