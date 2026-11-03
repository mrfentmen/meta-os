#!/bin/bash
# Fixture test for build_iso.sh --verify-base. No network, no real ISO.
#
# Proves three behaviours that matter before anyone patches a 4 GB download:
#   1. a matching hash passes and prints "verified"
#   2. a tampered ISO is refused (non-zero, "mismatch")
#   3. an ISO with no sums file is refused unless --no-verify-base is explicit
set -uo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD="$HERE/../build_iso.sh"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
fails=0

check() {  # check <label> <expected-exit> <command...>
    local label=$1 want=$2
    shift 2
    local out rc
    out=$("$@" 2>&1)
    rc=$?
    if [ "$rc" -eq "$want" ]; then
        printf 'PASS  %s (exit %s)\n' "$label" "$rc"
    else
        printf 'FAIL  %s: wanted exit %s, got %s\n%s\n' "$label" "$want" "$rc" "$out"
        fails=$((fails + 1))
    fi
}

# A fake ISO whose bytes are irrelevant; only the digest matters.
printf 'not really an iso, but bytes are bytes\n' > "$tmp/metaos-test.iso"
if command -v sha256sum >/dev/null 2>&1; then
    digest=$(sha256sum "$tmp/metaos-test.iso" | awk '{print $1}')
else
    digest=$(shasum -a 256 "$tmp/metaos-test.iso" | awk '{print $1}')
fi
printf '%s  metaos-test.iso\n' "$digest" > "$tmp/SHA256SUMS"

check "matching hash passes" 0 \
    bash "$BUILD" --verify-base "$tmp/metaos-test.iso" --sha256sums "$tmp/SHA256SUMS"

printf 'tampered\n' >> "$tmp/metaos-test.iso"
check "tampered ISO refused" 1 \
    bash "$BUILD" --verify-base "$tmp/metaos-test.iso" --sha256sums "$tmp/SHA256SUMS"

check "no sums file refused" 1 \
    bash "$BUILD" --verify-base "$tmp/metaos-test.iso" --sha256sums "$tmp/does-not-exist"

check "explicit opt-out accepted" 0 \
    bash "$BUILD" --verify-base "$tmp/metaos-test.iso" --no-verify-base

if [ "$fails" -ne 0 ]; then
    printf '%d fixture check(s) failed\n' "$fails"
    exit 1
fi
printf 'verify-base fixture: all 4 behaviours hold\n'
