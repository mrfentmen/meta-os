#!/bin/bash
# MetaOS 1.0 -- boot + installer lane build driver.
#
# Three modes, in the order the 12-hour plan uses them:
#
#   --check                     validate configs + report tool readiness.
#                               Runs anywhere, including this Mac.
#   --root <cubic-root>         provision a Cubic chroot, stop there.
#                               Then press Generate in Cubic, by hand.
#   --iso <base.iso> [--out F]  full patch on a Linux host as root:
#                               extract, unsquash, provision, re-squash,
#                               rebuild the ISO with its boot images
#                               replayed, print the sha256.
#
# Claim label: WRITTEN, UNRUN. XORRISO/mksquashfs are not on the build Mac;
# --check is the only mode proven locally.
set -euo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$HERE/../.." && pwd)   # meta-os/
WORK_DEFAULT="$HERE/work"

say()  { printf 'build_iso: %s\n' "$*"; }
die()  { printf 'build_iso: ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
    exit "${1:-2}"
}

# ------------------------------------------------------------------- check
check_mode() {
    local failures=0
    say "checking configs with tools/check_configs.py"
    if python3 "$HERE/tools/check_configs.py"; then
        say "configs: PASS"
    else
        say "configs: FAIL"
        failures=$((failures + 1))
    fi

    say "tool readiness (build modes need root on Linux):"
    for t in xorriso unsquashfs mksquashfs chroot sha256sum; do
        if have "$t"; then
            printf '  %-12s %s\n' "$t" "$(command -v "$t")"
        else
            printf '  %-12s MISSING\n' "$t"
        fi
    done
    if [ "$(uname -s)" = "Linux" ] && [ "$(id -u)" = "0" ]; then
        say "host: Linux + root -- build modes available"
    else
        say "host: $(uname -s), uid $(id -u) -- build modes NOT available here (expected on the Mac)"
    fi
    say "claim labels: configs=LOCAL-CHECK, ISO=UNRUN, install=PENDING Linux host"
    return "$failures"
}

# -------------------------------------------------------------------- root
root_mode() {
    local root=$1
    [ -d "$root" ] || die "--root $root does not exist"
    [ "$(id -u)" = "0" ] || die "--root mode needs root"
    say "provisioning Cubic chroot: $root"
    sh "$HERE/provision.sh" "$root"
    say "done. In Cubic: press Generate, then run the VM proof against the new ISO."
    say "expected output name: metaos-1.0-amd64.iso"
}

# --------------------------------------------------------------------- iso
iso_mode() {
    local base=$1 out=$2
    [ -f "$base" ] || die "base ISO not found: $base"
    [ "$(uname -s)" = "Linux" ] || die "--iso mode needs Linux (xorriso + chroot)"
    [ "$(id -u)" = "0" ] || die "--iso mode needs root"
    for t in xorriso unsquashfs mksquashfs chroot; do
        have "$t" || die "missing tool: $t (apt-get install xorriso squashfs-tools)"
    done

    local work="$WORK_DEFAULT"
    rm -rf "$work"
    mkdir -p "$work/iso_root" "$work/squashfs_root"

    say "extracting $base -> $work/iso_root"
    xorriso -osirrox on -indev "$base" -extract / "$work/iso_root" 2>&1 | tail -2
    chmod -R u+w "$work/iso_root"

    local sq=""
    for cand in "$work/iso_root/casper/filesystem.squashfs" "$work/iso_root/live/filesystem.squashfs"; do
        [ -f "$cand" ] && sq=$cand && break
    done
    [ -n "$sq" ] || die "no casper/live filesystem.squashfs inside $base"

    local comp
    comp=$(unsquashfs -s "$sq" | awk -F': *' '/^Compression/ {print $2; exit}')
    say "base squashfs: $sq (compression: ${comp:-unknown})"

    say "unsquashing (this is the slow step)"
    unsquashfs -d "$work/squashfs_root" -f "$sq" >/dev/null

    say "provisioning the unpacked root"
    sh "$HERE/provision.sh" "$work/squashfs_root"

    say "re-squashing"
    case "$comp" in
        zstd) local mksq_args=(-comp zstd -Xcompression-level 15) ;;
        gzip) local mksq_args=(-comp gzip) ;;
        *)    local mksq_args=(-comp xz -Xbcj x86) ;;
    esac
    mksquashfs "$work/squashfs_root" "$sq" -noappend -b 131072 -no-progress "${mksq_args[@]}" >/dev/null
    # Ubuntu's casper checks this file for the extracted size.
    if [ -d "$work/iso_root/casper" ]; then
        du -sx --block-size=1 "$work/squashfs_root" | awk '{print $1}' \
            > "$work/iso_root/casper/filesystem.size"
    fi

    say "refreshing md5sum.txt"
    if [ -f "$work/iso_root/md5sum.txt" ]; then
        ( cd "$work/iso_root" && find . -type f ! -name md5sum.txt -print0 | xargs -0 md5sum > md5sum.txt )
    fi

    mkdir -p "$(dirname "$out")"
    say "rebuilding ISO -> $out (boot images replayed from the base)"
    # `-boot_image any replay` reuses the base ISO's El Torito + hybrid MBR
    # instead of hand-writing isohybrid args per Ubuntu release. This is the
    # recipe that survives base-ISO layout changes.
    xorriso -indev "$base" -outdev "$out" \
        -boot_image any replay \
        -overwrite on \
        -rm_r / -- -map "$work/iso_root" / \
        -commit 2>&1 | tail -5

    [ -f "$out" ] || die "xorriso produced no output at $out"
    ( cd "$(dirname "$out")" && sha256sum "$(basename "$out")" | tee "$(basename "$out").sha256" )
    say "ISO built. Next: tools/vm_install_proof.sh --iso $out"
}

# -------------------------------------------------------------------- main
MODE=""
BASE_ISO=""
OUT="$HERE/metaos-1.0-amd64.iso"
CUBIC_ROOT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --check) MODE=check ;;
        --root) MODE=root; CUBIC_ROOT=${2:-}; shift || true ;;
        --iso) MODE=iso; BASE_ISO=${2:-}; shift || true ;;
        --out) OUT=${2:-}; shift || true ;;
        -h|--help) usage 0 ;;
        *) die "unknown argument: $1 (try --help)" ;;
    esac
    shift
done

case "$MODE" in
    check) check_mode ;;
    root)  root_mode "$CUBIC_ROOT" ;;
    iso)   iso_mode "$BASE_ISO" "$OUT" ;;
    *)     usage 2 ;;
esac
