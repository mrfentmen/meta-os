#!/usr/bin/env bash
# RK-007 build proof: 4 userspace ELFs -> kernel ELF -> 0.11.17 BIOS disk image.
#
# Why this wrapper: `cargo` on this Mac resolves to Homebrew's stable, which has
# no `core` for x86_64-unknown-none. Pointing RUSTC/PATH at nightly is the whole
# difference between "can't find crate for core" and a linkable kernel. The
# image itself is built by the HOST-side `bootloader` crate (BiosBoot) — there
# is no `bootimage` flow in 0.11, and `bootimage` is not used here.
#
# Usage: os-build/rk007/build.sh            (writes logs/build.log via caller)
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 1

NIGHTLY_RUSTC="$(rustup which --toolchain nightly rustc 2>/dev/null || true)"
if [ -z "$NIGHTLY_RUSTC" ]; then
    echo "build: no nightly toolchain; run: rustup toolchain install nightly" >&2
    exit 1
fi
export RUSTC="$NIGHTLY_RUSTC"
export PATH="$(dirname "$NIGHTLY_RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly
echo "build: $(rustc --version)"

echo "build: userspace (hello, sleeper, crasher, readkey)"
( cd os-build/userspace/user && cargo build --target x86_64-unknown-none --bins ) || exit 1
for b in hello sleeper crasher readkey; do
    p="os-build/userspace/user/target/x86_64-unknown-none/debug/$b"
    [ -f "$p" ] || { echo "build: missing $p" >&2; exit 1; }
    echo "build: $b $(wc -c < "$p" | tr -d ' ') bytes"
done

echo "build: kernel (metaos-kernel, bootloader_api 0.11)"
( cd kernel && cargo build --target x86_64-unknown-none ) || exit 1
KERNEL="$ROOT/kernel/target/x86_64-unknown-none/debug/metaos-kernel"
[ -f "$KERNEL" ] || { echo "build: missing kernel ELF $KERNEL" >&2; exit 1; }
echo "build: kernel $(wc -c < "$KERNEL" | tr -d ' ') bytes"

echo "build: image (host-side bootloader 0.11.17 BiosBoot, no bootimage)"
( cd os-build/rk007/image-builder && cargo run --release --quiet -- \
    "$KERNEL" "$ROOT/os-build/rk007/disk.img" ) || exit 1
IMG="$ROOT/os-build/rk007/disk.img"
[ -f "$IMG" ] || { echo "build: image not created" >&2; exit 1; }
echo "build: image $(wc -c < "$IMG" | tr -d ' ') bytes"
echo "build: done"
