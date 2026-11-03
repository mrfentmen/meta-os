#!/usr/bin/env bash
# iso/tools/precut.sh — the one command before an ISO cut.
#
# A cut needs three answers, and they live in three different tools:
# is the tree sound, do the documents tell the truth about it, and is the
# release actually done. This asks all three and prints one verdict.
#
#   iso/tools/precut.sh                 strict: every box must be closed
#   iso/tools/precut.sh --allow-open    a test cut with open boxes is allowed
#
# Exit 0 only on GO.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT" || exit 2

ALLOW_OPEN=0
case "${1:-}" in
  --allow-open) ALLOW_OPEN=1 ;;
  "") ;;
  -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
  *) echo "precut: unknown argument $1" >&2; exit 2 ;;
esac

fail=0
log="$(mktemp "${TMPDIR:-/tmp}/metaos-precut.XXXXXX")"
root=""
cleanup() { rm -f "$log"; [ -n "$root" ] && rm -rf "$root"; }
trap cleanup EXIT

echo "== lane"
if iso/tools/verify_lane.sh >"$log" 2>&1; then
  echo "LANE GREEN"
else
  echo "LANE RED"
  tail -20 "$log"
  fail=1
fi

echo "== agent layer"
root="$(mktemp -d "${TMPDIR:-/tmp}/metaos-precut-root.XXXXXX")"
mkdir -p "$root/etc" "$root/usr"
# Stage into a throwaway root and check it: this proves the image would get the
# runtime, the units and the cadence, not that a branch once said it would.
if sh agent-layer/stage.sh "$root" >"$log" 2>&1 \
   && sh agent-layer/stage.sh "$root" --check >>"$log" 2>&1; then
  echo "AGENT LAYER GREEN"
else
  echo "AGENT LAYER RED"
  tail -10 "$log"
  fail=1
fi
rm -rf "$root"
root=""

echo "== agent drills"
if node agents/drills.mjs >"$log" 2>&1; then
  echo "DRILLS PASS"
else
  echo "DRILLS FAIL"
  tail -10 "$log"
  fail=1
fi

echo "== claims"
if python3 iso/tools/check_claims.py >"$log" 2>&1; then
  echo "$(grep -c '^OK' "$log" || true) claim(s) match the tree"
else
  grep -E '^(STALE|MISSING|ERROR)' "$log" | head -10
  fail=1
fi

echo "== release"
python3 iso/tools/release_gate.py --json >"$log" 2>/dev/null || true
counts=$(python3 -c 'import json,sys
try:
    c = json.load(open(sys.argv[1]))["counts"]
    print("%d %d" % (c["closed"], c["open"]))
except Exception:
    print("? ?")' "$log")
closed="${counts%% *}"
open="${counts##* }"
echo "$closed closed, $open open"

echo
if [ "$fail" -ne 0 ]; then
  echo "CUT: NO-GO — the lane or its documents are wrong"
  exit 1
fi
if [ "$open" != "0" ]; then
  if [ "$ALLOW_OPEN" = "1" ]; then
    echo "CUT: GO for a test cut — $open release box(es) still open"
    exit 0
  fi
  echo "CUT: NO-GO — $open release box(es) open (use --allow-open for a test cut)"
  exit 1
fi
echo "CUT: GO — lane green, every claim true, every box closed"
exit 0
