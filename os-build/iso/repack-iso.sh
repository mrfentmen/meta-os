#!/bin/sh
# MetaOS 1.0 — final step of the byte-build: burn the patched ISO tree
# (output of os-build/iso/merge-layers.sh) back into a bootable ISO.
#
# Usage: BASE_ISO=/path/base.iso TREE=/path/patched-tree OUT=/path/metaos-1.0.iso ./repack-iso.sh
# Optional: EXPECTED_SHA256=<hex> (default: the pinned Xubuntu 24.04.5 sum
# from os-build/iso/BASE_FACTS.md). Set EXPECTED_SHA256=skip to bypass.
#
# Method: xorriso loads the base ISO as the template (its El Torito +
# isolinux/syslinux boot images are replayed untouched), replaces the
# whole file tree with the patched tree, and writes OUT. The base ISO is
# never modified. Fails loudly on any check failure.
#
# Pax test record (2026-11-03): mechanism verified end-to-end on a
# synthetic bootable base ISO + patched tree built for the purpose —
# happy path burns with the El Torito record replayed and kept, stale
# layered files deleted, volid set; wrong base SHA refused; layered
# stray in tree refused; missing filesystem.squashfs refused. NOT yet
# run on the real 24.04.5 base (needs Del's ISO file on the build host)
# and NOT a boot proof: first boot of a repacked image is proven in a
# VM, not by this script's checks.
set -eu
BASE_ISO="${BASE_ISO:?base iso path}"
TREE="${TREE:?patched tree dir}"
OUT="${OUT:?output iso path}"
EXPECTED_SHA256="${EXPECTED_SHA256:-4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81}"

[ -f "$BASE_ISO" ] || { echo "FAIL: base iso not found: $BASE_ISO"; exit 1; }
[ -d "$TREE/casper" ] || { echo "FAIL: tree has no casper/ dir: $TREE"; exit 1; }
[ -f "$TREE/casper/filesystem.squashfs" ] || { echo "FAIL: tree has no casper/filesystem.squashfs (run merge-layers.sh first)"; exit 1; }
for stray in "$TREE"/casper/minimal.squashfs "$TREE"/casper/minimal.standard.squashfs "$TREE"/casper/minimal.standard.live.squashfs; do
  [ ! -e "$stray" ] || { echo "FAIL: layered file still in tree: $stray"; exit 1; }
done

if [ "$EXPECTED_SHA256" != "skip" ]; then
  echo "=== verify base iso sha256 ==="
  ACTUAL=$(sha256sum "$BASE_ISO" | awk '{print $1}')
  [ "$ACTUAL" = "$EXPECTED_SHA256" ] || { echo "FAIL: base iso sha256 $ACTUAL != expected $EXPECTED_SHA256"; exit 1; }
  echo "sha256 OK: $ACTUAL"
fi

echo "=== burn: base template + patched tree ==="
rm -f "$OUT"
# -map MERGES into the base session: a file that exists only in the base
# would survive into the product. The patched tree is the full base tree
# with deliberate removals (the layered squashfs set above all), so the
# exact delete set is: base-session files that the tree does NOT carry.
# The El Torito catalog + boot image paths are protected: replay
# rewrites them from the base session's records, and merge-layers never
# modifies them (grub-fix touches grub.cfg only, which -map overlays).
TMPD=$(mktemp -d)
xorriso -osirrox off -indev "$BASE_ISO" -find / -type f -exec lsdl 2>/dev/null \
  | sed -n "s/.*'\(\/.*\)'.*/\1/p" | sort -u > "$TMPD/base-files.txt"
( cd "$TREE" && find . -type f | sed 's|^\.|/|' | sort -u ) > "$TMPD/tree-files.txt"
set -- -indev "$BASE_ISO" -outdev "$OUT"
comm -23 "$TMPD/base-files.txt" "$TMPD/tree-files.txt" | while read -r victim; do
  echo "$victim"
done > "$TMPD/delete.txt"
while read -r victim; do set -- "$@" -rm "$victim" --; done < "$TMPD/delete.txt"
echo "deleting $(wc -l < "$TMPD/delete.txt") stale file(s) from the base session"
set -- "$@" -map "$TREE" / -boot_image any replay -boot_image any keep -volid "METAOS_1_0" --
xorriso "$@" 2>&1 | tail -3
rm -rf "$TMPD"

echo "=== verify output ==="
[ -f "$OUT" ] || { echo "FAIL: no output written"; exit 1; }
LISTING=$(xorriso -osirrox off -indev "$OUT" -find / -exec lsdl 2>/dev/null || true)
echo "$LISTING" | grep -q "filesystem.squashfs" || { echo "FAIL: output lacks casper/filesystem.squashfs"; exit 1; }
if echo "$LISTING" | grep -q "minimal.standard"; then echo "FAIL: output still carries layered squashfs"; exit 1; fi
BOOT=$(xorriso -indev "$OUT" -report_el_torito plain 2>/dev/null | grep -c "El Torito boot img" || true)
[ "$BOOT" -ge 1 ] || { echo "FAIL: output has no El Torito boot record"; exit 1; }
echo "el-torito records: $BOOT"
du -h "$OUT" | awk '{print "size: " $1}'
sha256sum "$OUT" | awk '{print "sha256: " $1}'
echo "REPACK-DONE"
