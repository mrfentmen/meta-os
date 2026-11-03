#!/bin/sh
cat > add.py <<'PY'
def add(a, b):
    return a + b + 1
PY
cat > test_add.py <<'PY'
from add import add
assert add(2, 3) == 5, "2+3"
assert add(0, 0) == 0, "0+0"
assert add(-4, 4) == 0, "-4+4"
print("tests ok")
PY
