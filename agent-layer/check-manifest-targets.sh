#!/bin/sh
# check-manifest-targets.sh — manifest TARGETS vs tree, both directions.
# Usage: sh agent-layer/check-manifest-targets.sh (read-only, no systemd).
# Exit 1 on GHOST (TARGETS key with no file on disk) or ORPHAN (shipped file
# under agent-layer/units/ or agent-layer/desktop-entries/ with no TARGETS
# row — OC1 would never copy it).
set -u
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" >/dev/null 2>&1 && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
[ -f "$ROOT/agent-layer/manifest.py" ] || ROOT="$(pwd)"
MF="$ROOT/agent-layer/manifest.py"
FAIL=0
KEYS="$(mktemp)"
grep -o '"agent-layer/[^"]*"' "$MF" > "$KEYS" || true
while read -r q; do
  rel=$(printf '%s' "$q" | tr -d '"')
  if [ -f "$ROOT/$rel" ]; then echo "OK ghost-check: $rel present";
  else echo "GHOST: TARGETS lists $rel but no such file"; FAIL=1; fi
done < "$KEYS"
for f in "$ROOT/agent-layer/units/"* "$ROOT/agent-layer/desktop-entries/"*; do
  [ -f "$f" ] || continue
  rel="agent-layer/${f##*/agent-layer/}"
  if grep -qF "\"$rel\"" "$KEYS"; then echo "OK orphan-check: $rel listed";
  else echo "ORPHAN: $rel on disk but missing from TARGETS"; FAIL=1; fi
done
rm -f "$KEYS"
exit "$FAIL"
