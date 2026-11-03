#!/bin/sh
set -e
test -f lib.py
test -f main.py
if grep -rq old_func . ; then echo "old name still present"; exit 1; fi
test "$(python3 main.py)" = "42"
