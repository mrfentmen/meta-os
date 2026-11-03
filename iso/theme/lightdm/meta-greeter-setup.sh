#!/usr/bin/env bash
# meta-greeter-setup.sh — give the login screen the wallpaper that fits it.
#
# LightDM starts X, then runs this, then draws the greeter. There is no
# session yet, so the desktop picker in meta-first-login cannot help: it runs
# after a password. This reads the mode the kernel reports for the connected
# output and copies the matching file to the stable name the greeter config
# points at.
#
#   meta-greeter-setup.sh
#
# Overrides, both for headless testing:
#   METAOS_THEME_DIR      where the greeter PNGs live (default /usr/share/metaos/theme)
#   METAOS_GREETER_SIZE   skip detection, use this WxH
#
# Exit 1 when no wallpaper exists at all: the greeter then keeps its previous
# backdrop, and the log line names why.
set -uo pipefail

THEME="${METAOS_THEME_DIR:-/usr/share/metaos/theme}"
SIZE="${METAOS_GREETER_SIZE:-}"

if [ -z "$SIZE" ]; then
  # /sys/class/drm/card*-*/modes is readable before any session exists. The
  # first line is the preferred mode, which is the panel's native size.
  for modes in /sys/class/drm/card*-*/modes; do
    [ -f "$modes" ] || continue
    SIZE=$(head -n 1 "$modes" 2>/dev/null | tr -d '[:space:]')
    [ -n "$SIZE" ] && break
  done
fi
[ -n "$SIZE" ] || SIZE=1920x1080

PICK="$THEME/greeter-wallpaper-$SIZE.png"
if [ ! -f "$PICK" ]; then
  PICK="$THEME/greeter-wallpaper.png"
fi
if [ ! -f "$PICK" ]; then
  echo "greeter: no wallpaper in $THEME" >&2
  exit 1
fi

TMP="$THEME/.greeter-active.$$"
if ! install -m 644 "$PICK" "$TMP"; then
  echo "greeter: could not stage $PICK" >&2
  rm -f "$TMP"
  exit 1
fi
if ! mv -f "$TMP" "$THEME/greeter-active.png"; then
  echo "greeter: could not replace the active wallpaper" >&2
  rm -f "$TMP"
  exit 1
fi

echo "greeter: screen $SIZE uses $(basename "$PICK")"
exit 0
