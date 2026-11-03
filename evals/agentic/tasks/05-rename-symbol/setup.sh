#!/bin/sh
cat > lib.py <<'PY'
def old_func(items):
    return sum(items)
PY
cat > main.py <<'PY'
from lib import old_func
print(old_func([10, 20, 12]))
PY
