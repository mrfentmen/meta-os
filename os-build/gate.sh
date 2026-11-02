#!/usr/bin/env bash
# os-build/gate.sh (R4-1) — one command: toolchain, userspace, kernel,
# headless boot, typed help+status via drive.py, assert proof lines.
# Exits non-zero on any miss. Adapted from Buffy's Appendix B in
# os-build/PAX_12H.md (colon-split pairs so it also runs under zsh).
set -euo pipefail
cd "$(dirname "$0")/.."

NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
export PATH="$NIGHTLY:$PATH"
export RUSTC_BOOTSTRAP=1
FLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie"

echo "== toolchain =="
cargo --version
qemu-system-x86_64 --version | head -1

echo "== userspace =="
cd os-build/userspace/user
for pair in "hello:0x600000000000" "sleeper:0x610000000000" "crasher:0x620000000000"; do
  b=${pair%%:*}; base=${pair##*:}
  sed "s/0x620000000000/$base/" link.ld > "/tmp/link-$b.ld"
  RUSTFLAGS="$FLAGS -C link-arg=-T/tmp/link-$b.ld" cargo build --target x86_64-unknown-none --bin "$b"
done
cd ../../..

echo "== kernel =="
(cd kernel && cargo bootimage)

echo "== boot =="
LOG="$(mktemp /tmp/gate-boot-XXXXXX)"; MON="$(mktemp -u /tmp/gate-mon-XXXXXX)"
IMG="kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin"
qemu-system-x86_64 -drive format=raw,file="$IMG" -display none -no-reboot -m 512M \
  -serial "file:$LOG" -monitor "unix:$MON,server,nowait" &
QEMU=$!
deadline=480; waited=0
while [ $waited -lt $deadline ]; do
  sleep 10; waited=$((waited+10))
  if grep -aq "sleeper: bad call refused" "$LOG" 2>/dev/null; then break; fi
done
python3 os-build/tools/drive.py --monitor "$MON" help status
sleep 5
kill $QEMU 2>/dev/null || true
sleep 1

echo "== assert ($LOG) =="
fail=0
check() { grep -aq "$1" "$LOG" && echo "  ok   $2" || { echo "  FAIL $2"; fail=1; }; }
check "META OS KERNEL - alive"   "K1 alive"
check "mem summary: K4 up"       "K4 memory"
check "HELLO FROM USERSPACE"     "K6 ring 3"
check "user exit code 0"         "K6 clean exit"
check "task killed"              "K6 fault isolation"
check "commands: status help"    "shell answered"
check "STATUS tasks="            "status reported live state"
if grep -aq "loader refused" "$LOG"; then echo "  FAIL userspace refused"; fail=1; fi
if [ $fail -eq 0 ]; then echo "GATE GREEN ($LOG)"; else echo "GATE RED ($LOG)"; exit 1; fi
