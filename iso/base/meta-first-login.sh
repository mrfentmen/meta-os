#!/usr/bin/env bash
# iso/base/meta-first-login.sh — give the logged-in user the MetaOS desktop.
#
# The installer copies the theme and the dock items into /usr/share/metaos.
# It cannot copy them into a home directory, because the account does not
# exist yet when Calamares runs: the user types the name during install. So
# the per-user work happens here, once, at first login.
#
#   meta-first-login.sh [--dry-run] [--force]
#
# Idempotent: a marker file in $XDG_CONFIG_HOME stops the second run. Nothing
# here needs root.
set -uo pipefail

DRY=0
FORCE=0
fail=0

usage() {
  cat <<'USAGE'
usage: meta-first-login.sh [--dry-run] [--force]

  --dry-run   print what would change, write nothing
  --force     apply again even if the marker says it is done
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --force)   FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "first-login: unknown argument $1" >&2; usage >&2; exit 2 ;;
  esac
done

[ -n "${HOME:-}" ] || { echo "first-login: HOME is not set" >&2; exit 2; }
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
SHARE="${METAOS_SHARE:-/usr/share/metaos}"
MARKER="$CONF/metaos/first-login.done"

if [ -f "$MARKER" ] && [ "$FORCE" != "1" ]; then
  echo "first-login: already applied ($MARKER)"
  exit 0
fi

# The dock items are the frozen five. If the install tree is absent the base
# image was never applied, and silently doing nothing would hide that.
DOCK_SRC="$SHARE/dock"
if [ ! -d "$DOCK_SRC" ]; then
  echo "first-login: $DOCK_SRC is missing (run iso/tools/apply.sh first)" >&2
  exit 1
fi
dock_count=$(find "$DOCK_SRC" -maxdepth 1 -name '*.dockitem' | wc -l | tr -d ' ')
if [ "$dock_count" = "0" ]; then
  echo "first-login: $DOCK_SRC holds no .dockitem files" >&2
  exit 1
fi

run() {
  if [ "$DRY" = "1" ]; then
    echo "would run  $*"
  else
    "$@"
  fi
}

echo "first-login: user ${USER:-unknown}, config $CONF"

# 1. Dock items, into the real home rather than a guessed one.
dock_dst="$CONF/plank/dock1/launchers"
run mkdir -p "$dock_dst"
for f in "$DOCK_SRC"/*.dockitem; do
  [ -f "$f" ] || continue
  if [ "$DRY" = "1" ]; then
    echo "would install  $dock_dst/$(basename "$f")"
  else
    cp -f "$f" "$dock_dst/$(basename "$f")" || fail=1
  fi
done

# 2. Wallpaper, for every backdrop property Xfce has, whatever the monitor is
#    called. Setting only monitor0 works on the machine it was written for and
#    nowhere else.
WALL="$SHARE/theme/meta-wallpaper.png"
if [ ! -f "$WALL" ]; then
  echo "first-login: $WALL is missing" >&2
  fail=1
elif ! command -v xfconf-query >/dev/null 2>&1; then
  echo "first-login: xfconf-query not found, backdrop not set (outside Xfce?)" >&2
else
  props=$(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep '/backdrop/.*last-image$' || true)
  if [ -z "$props" ]; then
    # No backdrop property yet: create the one a fresh Xfce profile uses.
    run xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -n -t string -s "$WALL"
  else
    while IFS= read -r prop; do
      [ -n "$prop" ] || continue
      run xfconf-query -c xfce4-desktop -p "$prop" -s "$WALL"
    done <<< "$props"
  fi
fi

# 3. GTK colours, only if the user has not chosen their own.
CSS_SRC="$SHARE/theme/gtk.css"
CSS_DST="$CONF/gtk-3.0/gtk.css"
if [ ! -f "$CSS_SRC" ]; then
  echo "first-login: $CSS_SRC is missing" >&2
  fail=1
elif [ -f "$CSS_DST" ] && [ "$FORCE" != "1" ]; then
  echo "first-login: keeping the existing $CSS_DST"
else
  run mkdir -p "$(dirname "$CSS_DST")"
  if [ "$DRY" = "1" ]; then
    echo "would install  $CSS_DST"
  else
    cp -f "$CSS_SRC" "$CSS_DST" || fail=1
  fi
fi

# 4. The marker, so the second login is quiet.
if [ "$DRY" = "1" ]; then
  echo "would write  $MARKER"
else
  mkdir -p "$(dirname "$MARKER")" && : > "$MARKER" || fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "first-login: finished with errors" >&2
  exit 1
fi
echo "first-login: desktop applied"
exit 0
