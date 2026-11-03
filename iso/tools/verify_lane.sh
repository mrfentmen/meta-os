#!/usr/bin/env bash
# iso/tools/verify_lane.sh — the ISO lane gate, one command.
#
# Runs the static checker and every ISO test file. Nothing here boots, builds
# an image, or needs a VM; this is the gate that can run on any machine.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT" || exit 2

fail=0

echo "== static checker"
python3 iso/tools/check_iso_config.py || fail=1

echo
echo "== tests"
for t in tests/test_iso_*.py; do
  [ -f "$t" ] || continue
  printf '%-40s ' "$t"
  if python3 "$t" >/dev/null 2>&1; then
    echo "PASS"
  else
    echo "FAIL"
    python3 "$t" 2>&1 | tail -20
    fail=1
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "LANE GREEN"
else
  echo "LANE RED"
fi
exit "$fail"
