#!/usr/bin/env bash
# os-build/layer1/clean_clone_check.sh — does main build from nothing but itself?
#
# Every kernel build so far ran in this working tree, with its staged userspace ELFs, its
# target dirs and whatever local state accumulated. A fresh machine has none of that, and
# the failure mode is ugly: it looks like a code error and it is not.
#
# This clones the current HEAD into a temp directory (committed files only — no working-tree
# changes, no ignored files), builds the userspace crate, builds the kernel image, boots it,
# and requires the K1 line. It does not run the node suite or the Goose corpus: those need
# tooling this script does not install, and their absence is not a build failure.
#
# Exit: 0 the clone builds and boots, 1 it does not, 2 setup failed.
# Usage: clean_clone_check.sh [git-ref]   (default: HEAD)
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 2
ROOT="$(pwd)"
REF="${1:-HEAD}"
TMP="$(mktemp -d)" || exit 2
trap 'rm -rf "$TMP"' EXIT

echo "clean_clone_check: cloning $REF into $TMP/clone"
git clone --quiet --shared "$ROOT" "$TMP/clone" || exit 2
( cd "$TMP/clone" && git checkout --quiet "$REF" ) || exit 2

NIGHTLY="$(rustup which --toolchain nightly rustc 2>/dev/null || true)"
if [ -z "$NIGHTLY" ]; then
    echo "clean_clone_check: no nightly toolchain" >&2
    exit 2
fi
export RUSTC="$NIGHTLY"
export PATH="$(dirname "$NIGHTLY"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly

echo "clean_clone_check: userspace bins"
if ! ( cd "$TMP/clone/os-build/userspace/user" && cargo build -q --target x86_64-unknown-none --bins ); then
    echo "clean_clone_check: FAIL (userspace bins)" >&2
    exit 1
fi

echo "clean_clone_check: kernel image"
if ! ( cd "$TMP/clone/kernel" && cargo bootimage 2>&1 | grep -q "Created bootimage" ); then
    echo "clean_clone_check: FAIL (kernel image)" >&2
    exit 1
fi

echo "clean_clone_check: boot"
LOG="$TMP/boot.txt"
qemu-system-x86_64 \
    -drive "format=raw,file=$TMP/clone/kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin" \
    -serial "file:$LOG" -display none -m 256M -no-reboot &
QPID=$!
sleep "${KERNEL_BOOT_SECONDS:-8}"
kill "$QPID" 2>/dev/null || true
wait "$QPID" 2>/dev/null || true

if grep -qF "META OS KERNEL - alive (K1)" "$LOG"; then
    echo "clean_clone_check: PASS — clone built and booted ($(wc -l < "$LOG" | tr -d ' ') serial lines)"
    exit 0
fi
echo "clean_clone_check: FAIL (no alive line in the clone's boot)" >&2
sed -n '1,15p' "$LOG" >&2
exit 1
