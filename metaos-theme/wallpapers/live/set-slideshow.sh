#!/bin/sh
# Xfce backdrop slideshow through the 12 ASCII loop frames.
# No extra packages: uses xfconf-query on the live session.
# Usage: set-slideshow.sh [frames-dir]
FRAMES="${1:-/usr/share/backgrounds/meta-ascii-loop}"
n=0
for f in "$FRAMES"/loop-*.png; do
  xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/workspace0/last-image -s "$f" 2>/dev/null
  n=$((n+1)); sleep 2
done
echo "cycled $n frames (demo pass; live version runs as a session daemon)"
