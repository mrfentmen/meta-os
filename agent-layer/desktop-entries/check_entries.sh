#!/bin/sh
# check_entries.sh — validate agent-layer/desktop-entries drop-in files.
# Usage: sh check_entries.sh [--check] [dir]
# --check: exit non-zero on any failure (for OS-4 verify_tree.sh).
# Validates every .desktop for the four required keys (Type, Name, Exec,
# Icon), a non-empty user-facing Comment, TryExec consistency (except the
# Bond byte-copy, which upstream ships without one), Categories presence,
# and no banned words (distro names, internal lane chatter, TODO markers).
# Icon *existence* is proven separately (theme names resolve via the
# papirus-icon-theme package; shipped files verified with test -f) — see
# the OS-3 report. This script never needs the image, a VM, or a mount.
set -eu
DIR=${2:-$(dirname "$0")}
FAIL=0
fail() { echo "entries-check FAIL: $1"; FAIL=1; }

BANNED="ubuntu xubuntu TODO FIXME XXX Hana KEEP OC1 OC2"
for f in "$DIR"/*.desktop; do
  [ -e "$f" ] || continue
  base=$(basename "$f")
  # meta-agent-status.desktop is a byte-copy of Bond's file: keys are
  # covered by tests/agent-layer/test_desktop_entries.py, not rewritten here.
  for key in Type Name Exec Icon; do
    grep -q "^$key=" "$f" || fail "$base missing required key: $key"
  done
  grep -q "^Comment=.." "$f" || fail "$base Comment missing or empty"
  grep -q "^Categories=.." "$f" || fail "$base Categories missing or empty"
  if [ "$base" != "meta-agent-status.desktop" ]; then
    exec_bin=$(sed -n 's/^Exec=//p' "$f" | head -1 | awk '{print $1}')
    try_bin=$(sed -n 's/^TryExec=//p' "$f" | head -1 | awk '{print $1}')
    [ -n "$exec_bin" ] || fail "$base Exec empty"
    [ "$try_bin" = "$exec_bin" ] || fail "$base TryExec ($try_bin) != Exec binary ($exec_bin)"
  fi
  for word in $BANNED; do
    if grep -qi "$word" "$f"; then fail "$base contains banned word: $word"; fi
  done
  echo "entries-check: OK $base"
done
if [ "${1:-}" = "--check" ]; then :; fi
echo "entries-check: done (failures=$FAIL)"
exit "$FAIL"
