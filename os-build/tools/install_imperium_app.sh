#!/bin/sh
# Install the Imperium console (Meta Vigiles / Ignis / Medicus) into an image.
#
# The dock has had an Imperium tile and a logo for a while, but the app it
# points at was never copied into the image: /usr/share/metaos/imperium did not
# exist, so the native shell had no UI to load and the tile fell back to the
# web page. This installs the frozen payload and its backend, then prints what
# landed so a failure is visible instead of silent.
#
# Usage: sh install_imperium_app.sh [ROOT]     (default /mnt)
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ISO="$HERE/../iso"
ROOT="${1:-/mnt}"
APPS="$ISO/payload-apps"

[ -d "$ROOT/usr" ] || { echo "install_imperium_app: no $ROOT/usr" >&2; exit 1; }
[ -f "$APPS/imperium/index.html" ] || {
  echo "install_imperium_app: payload missing at $APPS/imperium/index.html" >&2; exit 1; }

DEST="$ROOT/usr/share/metaos/imperium"
mkdir -p "$DEST" "$ROOT/usr/share/metaos/server"

# index.html, styles.css, manifest, icon, js/, vendor/
cp -R "$APPS/imperium/." "$DEST/"
# The assess backend the app starts on 127.0.0.1:8080.
if [ -d "$APPS/server" ]; then
  cp "$APPS/server/"*.mjs "$ROOT/usr/share/metaos/server/" 2>/dev/null || {
    echo "install_imperium_app: no .mjs in $APPS/server" >&2; exit 1; }
fi

# Receipt: name the files that prove the app can actually open, and refuse if
# the entry point or its scripts did not land.
fail=0
for rel in index.html styles.css js/app.js; do
  if [ -f "$DEST/$rel" ]; then
    echo "OK    /usr/share/metaos/imperium/$rel"
  else
    echo "MISS  /usr/share/metaos/imperium/$rel"
    fail=1
  fi
done
for rel in assess.mjs budget.mjs; do
  if [ -f "$ROOT/usr/share/metaos/server/$rel" ]; then
    echo "OK    /usr/share/metaos/server/$rel"
  else
    echo "MISS  /usr/share/metaos/server/$rel"
    fail=1
  fi
done

# The GTK shell and its launcher must exist, or the tile has nothing to run.
for rel in usr/share/metaos/apps/metaos-imperium.py \
           usr/share/applications/metaos-imperium.desktop; do
  if [ -f "$ROOT/$rel" ]; then
    echo "OK    /$rel"
  else
    echo "MISS  /$rel"
    fail=1
  fi
done

[ "$fail" = 0 ] || { echo "install_imperium_app: FAILED" >&2; exit 1; }
echo "install_imperium_app: done ($(find "$DEST" -type f | wc -l | tr -d ' ') files)"
