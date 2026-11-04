#!/bin/sh
# check-icons.sh — every icon name the Meta desktop can show must resolve.
# Walks Icon= across all installed .desktop launchers (panel/dock/file
# manager all resolve through these plus the file-manager fixed set), then
# resolves each bare name via /usr/share/icons/metaos/index.theme (local
# dir first, then each Inherits parent on disk).
# Usage: check-icons.sh [ROOT]   (default /)
# Prints one PASS line, exits 1 on the first miss. No silenced failures.
set -eu
ROOT="${1:-/}"
THEME="$ROOT/usr/share/icons/metaos"
fail=0
ok=0

resolve() { # resolve <name>
  name="$1"
  case "$name" in
    /*) [ -f "$ROOT$name" ] && return 0 || return 1 ;;
  esac
  for ext in png svg xpm; do
    [ -f "$THEME/128x128/apps/$name.$ext" ] && return 0
  done
  inh=$(sed -n 's/^Inherits=//p' "$THEME/index.theme" | tr ',' ' ')
  for parent in $inh; do
    pdir="$ROOT/usr/share/icons/$parent"
    [ -d "$pdir" ] || continue
    if find "$pdir" -name "$name.png" -o -name "$name.svg" -o -name "$name.xpm" 2>/dev/null | grep -q .; then
      return 0
    fi
  done
  return 1
}

[ -f "$THEME/index.theme" ] || { echo "FAIL icons: $THEME/index.theme missing"; exit 1; }
grep -q '^\[Icon Theme\]' "$THEME/index.theme" || { echo "FAIL icons: index.theme has no [Icon Theme]"; exit 1; }
[ -d "$THEME/128x128/apps" ] || { echo "FAIL icons: $THEME/128x128/apps missing"; exit 1; }

names=$(grep -h '^Icon=' "$ROOT"/usr/share/applications/*.desktop 2>/dev/null | sed 's/^Icon=//' | sort -u)
# File-manager fixed set (thunar folder/mime/homedir icons; panel menu button).
names="$names
folder
folder-open
folder-remote
text-x-generic
application-x-executable
user-home
user-trash
user-trash-full
drive-harddisk
start-here
plank"

total=0
missed=""
for n in $names; do
  [ -n "$n" ] || continue
  total=$((total + 1))
  if resolve "$n"; then
    ok=$((ok + 1))
  else
    missed="$missed $n"
    fail=$((fail + 1))
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "PASS icons: $ok/$total names resolve (theme metaos + Inherits Papirus,elementary-xfce,hicolor)"
  exit 0
else
  echo "FAIL icons: $fail/$total miss:$missed"
  exit 1
fi
