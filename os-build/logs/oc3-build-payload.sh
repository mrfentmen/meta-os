#!/bin/sh
# OC3 payload builder: reproducible WITH-theme tarball from any main tip.
# Usage: sh os-build/logs/oc3-build-payload.sh [TIP]   (default: origin/main)
# Output: os-build/logs/oc3-payload-WITH-theme-SNAPSHOT-<shorttip>.tar.gz + sha256 on stdout.
# No boot, no writes outside this lane's logs dir, no pushes. Needs: git, tar, sha256sum.
set -e
TIP=${1:-origin/main}
HERE=$(dirname "$0")
STAGE=$(mktemp -d /tmp/oc3build.XXXXXX)
trap 'rm -rf "$STAGE"' EXIT INT TERM
SHORT=$(git rev-parse --short "$TIP")
git archive "$TIP" metaos-theme iso/theme os-build/iso/payload-theme | tar -x -C "$STAGE"
mkdir -p "$STAGE/out/applications" "$STAGE/out/metaos/start" "$STAGE/out/metaos/demo" "$STAGE/out/metaos/help" "$STAGE/out/theme"
cp "$HERE"/oc3b-desktop/*.desktop "$STAGE/out/applications/"
cp "$HERE"/oc3b-desktop/tour.html "$STAGE/out/metaos/demo/"
cp "$HERE"/oc3b-help/help.html "$HERE"/oc3b-help/about.html "$STAGE/out/metaos/help/"
cp "$HERE"/OC3B-startpage.html "$STAGE/out/metaos/start/index.html"
cp -r "$STAGE"/metaos-theme "$STAGE"/iso "$STAGE"/os-build "$STAGE/out/theme/"
rm -rf "$STAGE/metaos-theme" "$STAGE/iso" "$STAGE/os-build"
cat > "$STAGE/out/SNAPSHOT.txt" <<EOF
OC3 WITH-theme payload — snapshot built by oc3-build-payload.sh
main tip: $(git rev-parse "$TIP")
UNDECLARED-theme snapshot unless the tip carries the declared complete pack.
EOF
OUT="os-build/logs/oc3-payload-WITH-theme-SNAPSHOT-${SHORT}.tar.gz"
tar -czf "$OUT" -C "$STAGE/out" .
echo "files: $(tar -tzf "$OUT" | grep -c -v '/$')"
echo "bytes: $OUT"
sha256sum "$OUT"
