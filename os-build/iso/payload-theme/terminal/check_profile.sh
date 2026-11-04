#!/bin/sh
# check_profile.sh — validate the MetaOS terminal profile copies.
# Usage: sh check_profile.sh [--check]
# --check: exit non-zero on any failure (for OS-4 verify_tree.sh).
# Checks both copies (payload-theme + metaos-theme mirror) for:
#   key=value parse, no duplicate keys, no unknown keys,
#   no stock-distro-named font, required keys present, identical copies.
set -eu
HERE=$(dirname "$0")
FAIL=0
warn() { echo "profile-check: $1"; }
fail() { echo "profile-check FAIL: $1"; FAIL=1; }

KNOWN="ColorUseTheme ColorBackground ColorForeground ColorPalette BackgroundOpacity FontName"
for f in "$HERE/metaos-terminal-profile.txt" \
         "$HERE/../../../../metaos-theme/terminal/metaos-terminal-profile.txt"; do
  [ -f "$f" ] || { fail "missing file: $f"; continue; }
  # unknown keys + duplicates + malformed lines (skip blanks, # comments, [section])
  seen=""
  lineno=0
  while IFS= read -r line || [ -n "$line" ]; do
    lineno=$((lineno + 1))
    case "$line" in ""|\#*|\[*\]) continue;; esac
    case "$line" in *=*) key=${line%%=*};; *) fail "$f:$lineno not key=value: $line"; continue;; esac
    case " $KNOWN " in *" $key "*) :;; *) fail "$f:$lineno unknown key: $key";; esac
    case " $seen " in *" $key "*) fail "$f:$lineno duplicate key: $key";; esac
    seen="$seen $key"
  done < "$f"
  for k in ColorBackground ColorForeground ColorPalette FontName; do
    case " $seen " in *" $k "*) :;; *) fail "$f missing required key: $k";; esac
  done
  if grep -qi "ubuntu" "$f"; then fail "$f contains a banned distro string"; fi
  echo "profile-check: OK $f (keys:$seen )"
done
if cmp -s "$HERE/metaos-terminal-profile.txt" \
          "$HERE/../../../../metaos-theme/terminal/metaos-terminal-profile.txt"; then
  echo "profile-check: OK both copies identical"
else
  fail "payload-theme and metaos-theme copies differ"
fi
if [ "${1:-}" = "--check" ]; then :; fi
warn "done (failures=$FAIL)"
exit "$FAIL"
