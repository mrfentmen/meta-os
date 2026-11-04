#!/bin/sh
# check-plymouth.sh — the shipped splash references only files that exist,
# names no Ubuntu art, and carries the Meta ink + Meta words.
# Static check, no boot. Frame count is reported, not gated: the payload
# ships 240 frames while task R2-T1-43 asks <=40 and apply.sh gates >=120;
# that initramfs-size-vs-smoothness call is still open (see report).
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
fail=0
ok() { echo "PASS plymouth: $1"; }
no() { echo "FAIL plymouth: $1"; fail=1; }
for theme in "$HERE/metaos" "$HERE/../splash"; do
  [ -d "$theme" ] || { no "theme dir missing: $theme"; continue; }
  label=$(basename "$theme")
  missing=0
  for ref in $(grep -o 'Image ("[^"]*\.png")' "$theme/metaos.script" 2>/dev/null | sed 's/Image ("//;s/")//'); do
    [ -f "$theme/$ref" ] || { missing=$((missing + 1)); echo "  missing: $theme/$ref"; }
  done
  [ "$missing" = 0 ] \
    && ok "$label refs exist (all Image refs on disk)" \
    || no "$label refs missing ($missing files)"
  if grep -rni 'ubuntu-logo\|ubuntu_logo\|ubuntu-text' "$theme" 2>/dev/null | grep -q .; then
    no "$label no-ubuntu: Ubuntu art reference present"
  else
    ok "$label no-ubuntu (no ubuntu-logo/ubuntu-text reference)"
  fi
  if grep -q '#070B16' "$theme/metaos.script" 2>/dev/null; then
    ok "$label ink #070B16 present"
  else
    no "$label ink #070B16 missing"
  fi
  if grep -q 'Loading into MetaOS' "$theme/metaos.script" 2>/dev/null; then
    ok "$label splash text reads Loading into MetaOS"
  else
    no "$label splash text missing"
  fi
done
n=$(ls "$HERE/metaos/frames"/frame-*.png 2>/dev/null | wc -l | tr -d ' ')
echo "INFO plymouth frames: $n files (<=40 asked, >=120 gated elsewhere; decision open)"
[ -f "$HERE/../splash/background.png" ] \
  && ok "splash background.png ships" \
  || no "splash background.png missing"
if [ "$fail" = 0 ]; then echo "check-plymouth: all PASS"; else echo "check-plymouth: $fail FAIL"; fi
exit $fail
