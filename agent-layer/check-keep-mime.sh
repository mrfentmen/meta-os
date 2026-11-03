#!/bin/sh
# check-keep-mime.sh — static cross-check of Hana KEEP vs MIME maps.
# Usage: sh agent-layer/check-keep-mime.sh (read-only).
# Per MIME type, compares canonical defaults/mimeapps.list against the drop-in
# mimeapps.list and the backing KEEP package in packages.txt. Prints
# MATCH/MISMATCH per entry. The application/pdf evince(canonical) vs
# atril(drop-in) split is an EXPECTED mismatch with a note (Xubuntu 24.04.5
# ships atril where KEEP lists evince); any mapped desktop with no KEEP
# backing and no known-substitute note is a real gap -> exit 1.
set -u
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
[ -f "$ROOT/agent-layer/install.sh" ] || ROOT="$(pwd)"
KEEP="$ROOT/os-build/metaos1-base/packages.txt"
CANON="$ROOT/os-build/metaos1-base/defaults/mimeapps.list"
DROP="$ROOT/agent-layer/desktop-entries/mimeapps.list"
FAIL=0
keep_has() { grep -qx "$1" "$KEEP" 2>/dev/null; }
val() { grep "^$2=" "$1" 2>/dev/null | tail -n 1 | cut -d= -f2; }
check() {
  type="$1"; keep_pkg="$2"; note_txt="$3"
  c="$(val "$CANON" "$type")"; d="$(val "$DROP" "$type")"
  [ -n "$c" ] || { echo "MISMATCH $type: canonical unmapped"; FAIL=1; return; }
  [ -n "$d" ] || { echo "MISMATCH $type: drop-in unmapped"; FAIL=1; return; }
  if [ "$c" = "$d" ]; then echo "MATCH $type: $c (canon==drop-in)";
  else echo "MISMATCH $type: canon=$c drop-in=$d ($note_txt)"; fi
  if keep_has "$keep_pkg"; then echo "MATCH $type: KEEP lists $keep_pkg";
  else echo "MISMATCH $type: $keep_pkg NOT in KEEP"; FAIL=1; fi
}
check "text/plain" "mousepad" "-"
check "image/png" "ristretto" "-"
check "image/jpeg" "ristretto" "-"
check "application/pdf" "evince" "expected: drop-in maps atril (ships in base), evince degraded-off NoDisplay=true"
# Uncovered desktop: every drop-in mapped desktop needs KEEP or atril backing.
for v in $(grep -E '^[A-Za-z0-9.+_-]+/[A-Za-z0-9.+_-]+=.*\.desktop$' "$DROP" | cut -d= -f2); do
  base="${v%.desktop}"
  if keep_has "$base" || [ "$base" = "atril" ]; then
    echo "MATCH desktop $v: covered (KEEP or known base substitute)"
  else
    echo "MISMATCH desktop $v: no KEEP package backs it"; FAIL=1
  fi
done
exit "$FAIL"
