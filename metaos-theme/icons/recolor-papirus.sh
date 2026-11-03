#!/bin/sh
# Recolor Papirus folder/user-blue icons to Meta blue. Run on the ISO build host:
#   git clone --depth 1 https://github.com/PapirusDevelopmentTeam/papirus-icon-theme.git /tmp/papirus
#   ./recolor-papirus.sh /tmp/papirus/Papirus /usr/share/icons/MetaOS
# Scope: SIZE/places/{folder-blue*.svg,user-blue-*.svg} ONLY (exact list in
# ICONS.md). Symlinks (folder.svg -> folder-blue.svg etc.) are preserved with
# cp -a so aliases follow the recolor automatically. App icons that
# incidentally contain the same blue (solus logo, emily-is-away, ...) are OUT
# of scope and untouched.
# Map (luminance-matched pair, verified against Papirus 24x24/places):
#   front #5294e2 -> #1877F2 (Meta blue)
#   back  #4877b1 -> #1360C4 (Meta blue darkened by the same 0.81 luminance ratio)
set -e
SRC="${1:?papirus Papirus dir}"; DST="${2:?destination}"
mkdir -p "$DST"; cp -a "$SRC"/. "$DST"/
LIST="$(mktemp)"; find "$DST" -path '*/places/*' -type f \( -name 'folder-blue*.svg' -o -name 'user-blue-*.svg' \) -print > "$LIST"
xargs sed -i.bak -e 's/#5294e2/#1877F2/g' -e 's/#4877b1/#1360C4/g' < "$LIST"
find "$DST" -name '*.bak' -delete
LEFT=$(xargs grep -l '#5294e2\|#4877b1' < "$LIST" 2>/dev/null | wc -l); rm -f "$LIST"
echo "recolored $(grep -rl '#1877F2' "$DST" --include='*.svg' | wc -l) files -> $DST (unmapped source tones left in scope: $LEFT)"
