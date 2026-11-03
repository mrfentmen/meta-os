#!/bin/bash
# Fixture test for base-layout detection in build_iso.sh --base-info.
#
# No ISO, no root, no network. Uses ISO_MOUNT so the detector reads a fake
# tree instead of a 5 GB image. Proves the three behaviours that decide
# whether a build is even attempted:
#   1. one casper/filesystem.squashfs            -> "single", supported
#   2. casper/install-sources.yaml + layers      -> "layered", NOT supported
#   3. something unrecognisable                  -> fails loudly, no guessing
set -uo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD="$HERE/../build_iso.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fails=0

check() {  # check <label> <expected-exit> <mount-dir> <text-that-must-appear>
    local label=$1 want_rc=$2 mount=$3 needle=$4 out rc
    out=$(ISO_MOUNT="$mount" bash "$BUILD" --base-info "$tmp/fake.iso" 2>&1)
    rc=$?
    if [ "$rc" -ne "$want_rc" ]; then
        printf 'FAIL  %s: wanted exit %s, got %s\n%s\n' "$label" "$want_rc" "$rc" "$out"
        fails=$((fails + 1))
        return
    fi
    if ! printf '%s' "$out" | grep -qF "$needle"; then
        printf 'FAIL  %s: output lacks %s\n%s\n' "$label" "$needle" "$out"
        fails=$((fails + 1))
        return
    fi
    printf 'PASS  %s (exit %s, saw %s)\n' "$label" "$rc" "$needle"
}

printf 'fake\n' > "$tmp/fake.iso"

mkdir -p "$tmp/single/casper"
: > "$tmp/single/casper/filesystem.squashfs"
check "single-squashfs base is supported" 0 "$tmp/single" "layout: single"

mkdir -p "$tmp/layered/casper"
: > "$tmp/layered/casper/minimal.standard.squashfs"
printf -- '- default: true\n  path: minimal.standard.squashfs\n' > "$tmp/layered/casper/install-sources.yaml"
check "layered base is flagged, not patched" 0 "$tmp/layered" "layout: layered"
check "layered base says NOT supported" 0 "$tmp/layered" "NOT supported by the single-rootfs recipe"

mkdir -p "$tmp/empty"
# No ISO_MOUNT, no readable listing: bsdtar on a text file must fail loudly.
out=$(bash "$BUILD" --base-info "$tmp/fake.iso" 2>&1)
rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qiE 'bsdtar|ERROR'; then
    printf 'PASS  unrecognisable base fails loudly (exit %s)\n' "$rc"
else
    printf 'FAIL  unrecognisable base: exit %s\n%s\n' "$rc" "$out"
    fails=$((fails + 1))
fi

if [ "$fails" -ne 0 ]; then
    printf '%d base-layout fixture check(s) failed\n' "$fails"
    exit 1
fi
printf 'base-layout fixture: all 4 behaviours hold\n'
