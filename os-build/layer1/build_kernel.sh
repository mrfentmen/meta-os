#!/usr/bin/env bash
# os-build/layer1/build_kernel.sh — build the kernel image and gate on the K1 line.
#
# Why a wrapper: this Mac has two Rust toolchains and `cargo` resolves to Homebrew's, which has
# no `core` for x86_64-unknown-none. Pointing RUSTC and PATH at nightly is the difference
# between "can't find crate for core" and a bootable image, and nobody should have to
# rediscover that from a compiler error at 2 AM.
#
# Exit codes: 0 built and K1 line present, 1 build failed, 2 built but the proof line is missing.
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 1

NIGHTLY_RUSTC="$(rustup which --toolchain nightly rustc 2>/dev/null || true)"
if [ -z "$NIGHTLY_RUSTC" ]; then
    echo "build_kernel: no nightly toolchain; run: rustup toolchain install nightly" >&2
    exit 1
fi
export RUSTC="$NIGHTLY_RUSTC"
export PATH="$(dirname "$NIGHTLY_RUSTC"):$HOME/.cargo/bin:$PATH"
export RUSTUP_TOOLCHAIN=nightly

# os-boot is the boot-assets crate in the same workspace; a broken member should
# stop the image build here, with its own name, instead of surfacing later as a
# confusing kernel error. It is a check, not part of the image link.
if ! cargo check -q -p os-boot; then
    echo "build_kernel: os-boot crate does not compile" >&2
    exit 1
fi
echo "build_kernel: os-boot crate ok"

if ! command -v bootimage >/dev/null 2>&1; then
    echo "build_kernel: bootimage missing; run: cargo install bootimage --locked" >&2
    exit 1
fi
for component in rust-src llvm-tools-preview; do
    rustup component add "$component" --toolchain nightly >/dev/null 2>&1 || true
done

echo "build_kernel: $(rustc --version)"
( cd kernel && cargo bootimage ) || exit 1

BIN="kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin"
[ -f "$BIN" ] || { echo "build_kernel: no image at $BIN" >&2; exit 1; }
echo "build_kernel: image $(shasum -a 256 "$BIN" | cut -d' ' -f1)"

mkdir -p os-build/logs
LOG="${KERNEL_LOG:-os-build/logs/K1-boot.txt}"
rm -f "$LOG"
qemu-system-x86_64 -drive "format=raw,file=$BIN" -serial "file:$LOG" \
    -display none -m 256M -no-reboot &
QPID=$!
# The kernel never exits; QEMU is stopped after the log has had time to fill.
sleep "${KERNEL_BOOT_SECONDS:-12}"
kill "$QPID" 2>/dev/null || true
wait "$QPID" 2>/dev/null || true

if [ ! -s "$LOG" ]; then
    echo "build_kernel: boot produced no serial output at $LOG" >&2
    exit 2
fi
echo "build_kernel: serial log $LOG ($(wc -l < "$LOG" | tr -d ' ') lines)"
if grep -qF "META OS KERNEL - alive (K1)" "$LOG"; then
    echo "build_kernel: K1 PROVEN — alive line present"
    exit 0
fi
echo "build_kernel: K1 NOT PROVEN — alive line missing from $LOG" >&2
sed -n '1,20p' "$LOG" >&2
exit 2
