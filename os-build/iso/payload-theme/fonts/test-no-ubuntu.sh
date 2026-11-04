#!/bin/sh
# fonts/test-no-ubuntu.sh — fail when any installed font family name contains
# "Ubuntu" (R2-T1 task 17).
#
# Usage: sh test-no-ubuntu.sh [ROOT]   (default ROOT=/)
#
# Gates, all must pass:
#   1. fc-list : family (when fc-list exists — Linux target) names no Ubuntu
#      family.
#   2. No Ubuntu-named files under <ROOT>/usr/share/fonts.
#   3. This lane's own alias file (69-meta.conf) references no Ubuntu family,
#      so the generics can never resolve to one through us.
# fc-list/fc-cache do not exist on macOS; there gate 1 prints a note and the
# file-name + conf gates still run. Exit 0 PASS, 1 FAIL.
set -eu

ROOT="${1:-/}"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fail=0

if command -v fc-list >/dev/null 2>&1; then
  if fc-list : family 2>/dev/null | grep -qi ubuntu; then
    echo "FAIL no-ubuntu: fc-list reports an Ubuntu-named family:"
    fc-list : family 2>/dev/null | grep -i ubuntu | sort -u
    fail=1
  else
    echo "PASS no-ubuntu: fc-list names no Ubuntu family"
  fi
else
  echo "note no-ubuntu: fc-list absent on this host (macOS); family gate runs on the Linux target"
fi

if find "$ROOT/usr/share/fonts" -iname '*ubuntu*' 2>/dev/null | grep -q .; then
  echo "FAIL no-ubuntu: Ubuntu-named font files under $ROOT/usr/share/fonts:"
  find "$ROOT/usr/share/fonts" -iname '*ubuntu*' 2>/dev/null
  fail=1
else
  echo "PASS no-ubuntu: no Ubuntu-named files under $ROOT/usr/share/fonts"
fi

if grep -qi ubuntu "$HERE/69-meta.conf" 2>/dev/null; then
  echo "FAIL no-ubuntu: 69-meta.conf references an Ubuntu family" >&2
  fail=1
else
  echo "PASS no-ubuntu: 69-meta.conf names no Ubuntu family"
fi

if [ "$fail" -eq 0 ]; then echo "no-ubuntu: PASS"; else echo "no-ubuntu: FAIL" >&2; fi
exit "$fail"
