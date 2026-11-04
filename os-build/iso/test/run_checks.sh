#!/bin/bash
# MetaOS boot/installer lane — one command for every check that can run on
# a Mac or any non-root host. Milo/Pax can quote its summary line as-is.
#
#   os-build/iso/test/run_checks.sh           full local gate
#   SKIP_QEMU=1 os-build/iso/test/run_checks.sh   skip the QEMU dry frame
#
# Exit 0 only if every check passes. SKIPs are printed as SKIP, never PASS.
set -uo pipefail

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LANE=$(CDPATH= cd -- "$HERE/.." && pwd)
fails=0
skips=0
passes=0

step() { printf '\n== %s ==\n' "$*"; }
ok()   { passes=$((passes + 1)); printf 'PASS  %s\n' "$*"; }
bad()  { fails=$((fails + 1));  printf 'FAIL  %s\n' "$*"; }
skip() { skips=$((skips + 1)); printf 'SKIP  %s\n' "$*"; }

step "config validator"
if python3 "$LANE/tools/check_configs.py"; then
    ok "check_configs.py"
else
    bad "check_configs.py"
fi

step "installer slideshow (static, offline)"
if python3 "$LANE/tools/check_slideshow.py"; then
    ok "check_slideshow.py"
else
    bad "check_slideshow.py"
fi

step "shell syntax"
for pair in "provision.sh sh" "merge-layers.sh sh" "build-arm64-inner.sh sh" "metaos-install.sh sh" "finalize-iso-tree.sh sh" "grub-fix.sh sh" "calamares/meta-branding.sh sh" "build_iso.sh bash" "../tools/proof_iso.sh bash" "tools/vm_install_proof.sh bash" "test/run_checks.sh bash" "test/verify-base.test.sh bash" "test/base-layout.test.sh bash" "test/test_stages.sh bash"; do
    set -- $pair
    file="$LANE/$1"
    shell=$2
    if [ ! -f "$file" ]; then
        bad "$1 missing"
    elif "$shell" -n "$file"; then
        ok "$shell -n $1"
    else
        bad "$shell -n $1"
    fi
done

step "base-ISO verification logic (fixture, no network)"
if bash "$LANE/test/verify-base.test.sh"; then
    ok "verify-base fixture (match, mismatch, missing sums)"
else
    bad "verify-base fixture"
fi

step "base-layout detection (fixture, no ISO)"
if bash "$LANE/test/base-layout.test.sh"; then
    ok "base-layout fixture (single, layered, unknown)"
else
    bad "base-layout fixture"
fi

step "build-stage fixtures (mocked tools, no root, no mounts)"
if bash "$LANE/test/test_stages.sh"; then
    ok "test_stages fixture (arg parsing, gates, order, splash PNG)"
else
    bad "test_stages fixture"
fi

step "QMP harness plumbing (real QEMU framebuffer)"
if [ "${SKIP_QEMU:-0}" = "1" ]; then
    skip "vm_install_proof.sh --dry (SKIP_QEMU=1)"
elif ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    skip "vm_install_proof.sh --dry (qemu not installed)"
else
    tmp=$(mktemp -d)
    if "$LANE/tools/vm_install_proof.sh" --dry --work "$tmp/proof" >/dev/null; then
        if [ -s "$tmp/proof/00-harness-dry.png" ]; then
            ok "dry screendump captured ($(wc -c < "$tmp/proof/00-harness-dry.png" | tr -d ' ') bytes)"
        else
            bad "dry run produced no PNG"
        fi
    else
        bad "vm_install_proof.sh --dry"
    fi
    rm -rf "$tmp"
fi

step "summary"
printf '%d pass, %d fail, %d skip\n' "$passes" "$fails" "$skips"
if [ "$fails" -ne 0 ]; then
    printf 'LANE LOCAL GATE: FAIL\n'
    exit 1
fi
printf 'LANE LOCAL GATE: PASS on everything runnable here. ISO build + install remain UNRUN.\n'
