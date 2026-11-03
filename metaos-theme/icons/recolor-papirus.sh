#!/bin/sh
# Recolor Papirus folder icons to Meta blue. Run on the ISO build host:
#   git clone --depth 1 https://github.com/PapirusDevelopmentTeam/papirus-icon-theme.git /tmp/papirus
#   ./recolor-papirus.sh /tmp/papirus/Papirus /usr/share/icons/MetaOS
# Replaces Papirus folder-blue (#5294e2 family) with Meta blue #1877F2.
set -e
SRC="${1:?papirus Papirus dir}"; DST="${2:?destination}"
mkdir -p "$DST"; cp -r "$SRC"/* "$DST"/
grep -rl "#5294e2" "$DST" | xargs sed -i '' 's/#5294e2/#1877F2/g' 2>/dev/null || \
grep -rl "#5294e2" "$DST" | xargs sed -i 's/#5294e2/#1877F2/g'
echo "recolored $(grep -rl '#1877F2' "$DST" | wc -l) files -> $DST"
