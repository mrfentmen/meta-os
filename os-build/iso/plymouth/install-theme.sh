#!/bin/sh
# install-theme.sh — install the Meta plymouth theme into a root.
# Usage: install-theme.sh <root>   (ROOT=/ for the running system)
# Copies os-build/iso/plymouth/metaos, writes [Daemon] Theme=metaos,
# creates the metaos-text fallback theme, and points the text.plymouth
# alternative at it (direct symlink; update-alternatives needs a live
# dpkg database, which a staged root does not have).
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT="${1:-/}"
[ -d "$ROOT/usr" ] || { echo "install-theme: $ROOT is not a root" >&2; exit 1; }
mkdir -p "$ROOT/usr/share/plymouth/themes/metaos"
cp -f "$HERE/metaos/metaos.plymouth" "$HERE/metaos/metaos.script" \
      "$HERE/metaos/background.png" "$HERE/metaos/meta-m.png" \
      "$HERE/metaos/progress.png" "$ROOT/usr/share/plymouth/themes/metaos/"
mkdir -p "$ROOT/usr/share/plymouth/themes/metaos/frames"
cp -f "$HERE/metaos/frames/"frame-*.png "$ROOT/usr/share/plymouth/themes/metaos/frames/"
mkdir -p "$ROOT/etc/plymouth"
printf '[Daemon]\nTheme=metaos\nShowDelay=0\nDeviceTimeout=8\n' > "$ROOT/etc/plymouth/plymouthd.conf"
mkdir -p "$ROOT/usr/share/plymouth/themes/metaos-text"
cat > "$ROOT/usr/share/plymouth/themes/metaos-text/metaos-text.plymouth" <<'EOF'
[Plymouth Theme]
Name=Meta OS Text
Description=Meta OS fallback text boot (no stock art)
ModuleName=text
EOF
mkdir -p "$ROOT/etc/alternatives"
ln -sfn /usr/share/plymouth/themes/metaos-text/metaos-text.plymouth \
  "$ROOT/etc/alternatives/text.plymouth"
n=$(ls "$ROOT/usr/share/plymouth/themes/metaos/frames"/frame-*.png | wc -l | tr -d ' ')
echo "install-theme: metaos ($n frames), metaos-text fallback, text.plymouth -> metaos-text"
