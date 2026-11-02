#!/bin/sh
# boot-test.sh (OS-193..OS-204): the one-command build + boot + test
# pipeline. Build userspace, build the kernel image, boot it in
# QEMU, capture serial, grep the expected lines per milestone,
# PASS/FAIL each. Then the Goose suite and the Lobster proofs.
# Any failure exits nonzero LOUDLY (OS-195 proves it).
set -eu
export PATH="$HOME/.cargo/bin:/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin"
export RUSTC_BOOTSTRAP=1
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOGDIR="$ROOT/os-build/logs"
mkdir -p "$LOGDIR"
BOOTLOG="$LOGDIR/pipeline-boot.txt"
pass=0; fail=0
check() { # check <name> <pattern-file>
  if grep -aq -f "$1" "$BOOTLOG"; then echo "PASS: $2"; pass=$((pass+1)); else echo "FAIL: $2 (want: $(cat "$1" | head -2 | tr '\n' '|'))"; fail=$((fail+1)); fi
}
checkline() { # checkline <name> <fixed-string>
  if grep -aqF "$2" "$BOOTLOG"; then echo "PASS: $1"; pass=$((pass+1)); else echo "FAIL: $1 (want: $2)"; fail=$((fail+1)); fi
}

echo "== userspace =="
cd os-build/userspace/user
for pair in "hello:0x600000000000" "sleeper:0x610000000000" "crasher:0x620000000000" "readkey:0x630000000000"; do
  b=${pair%%:*}; base=${pair##*:}
  sed "s/= BASE/= $base/" link-base.ld > link.ld
  touch src/bin/$b.rs
  RUSTFLAGS="-C link-arg=-T$PWD/link.ld" cargo build -q --target x86_64-unknown-none --bin $b
done
cd "$ROOT"

echo "== kernel =="
cd kernel && cargo bootimage 2>&1 | tail -1; cd "$ROOT"
BIN=kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin

echo "== boot (serial to $BOOTLOG) =="
rm -f /tmp/pipe-qmp /tmp/pipe-pid
(qemu-system-x86_64 -drive format=raw,file=$BIN -nographic -no-reboot -m 512M -qmp unix:/tmp/pipe-qmp,server,nowait > "$BOOTLOG" 2>&1 & echo $! > /tmp/pipe-pid)
deadline=480; waited=0
while [ $waited -lt $deadline ]; do
  sleep 10; waited=$((waited+10))
  if grep -aq "sleeper: bad call refused" "$BOOTLOG" 2>/dev/null; then break; fi
done
if [ -e /tmp/pipe-qmp ]; then
  python3 -c "import socket,json; s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect('/tmp/pipe-qmp'); s.settimeout(10); s.recv(65536); s.sendall((json.dumps({'execute':'qmp_capabilities'})+'\n').encode()); s.recv(65536); s.sendall((json.dumps({'execute':'screendump','arguments':{'filename':'$LOGDIR/pipeline-screen.ppm'}})+'\n').encode()); print(s.recv(200))"
fi
kill $(cat /tmp/pipe-pid) 2>/dev/null || true

echo "== milestones =="
checkline "K1 alive" "META OS KERNEL - alive (K1)"
checkline "K2 banner" "META OS - milestone K3"
checkline "K2 console" "mem map:"
checkline "K3 uptime" "uptime 1s ticks 100"
checkline "K4 heap" "mem Box+Vec ok"
checkline "K4 summary" "mem summary: K4 up"
checkline "K5 interleave A" "A"
checkline "K5 interleave B" "B"
checkline "K5 sleep/wake" "C awake"
checkline "K6 hello" "HELLO FROM USERSPACE"
checkline "K6 sleeper" "sleeper: after sleep"
checkline "K6 bad call refused" "user bad syscall 99 refused"
checkline "K6 user fault kill" "task killed"
check "$ROOT/os-build/expected/K-all.txt" "K expected-line set"

echo "== goose suite =="
sh services/run-goose-tests.sh | tail -2

echo "== lobster proofs (checked, not just produced) =="
cd lobster
# Deterministic start: clear agent state and the bus channel.
rm -f homes/lobster-agent/note.txt homes/lobster-agent/refusals.txt
rm -f bus/general/*.txt
L=~/mcp-servers/toolchains/lobster-src/bin/lobster
$L hello.lobster | grep -q "HELLO FROM LOBSTER" && echo "PASS: lobster hello" || { echo "FAIL: lobster hello"; fail=$((fail+1)); }
$L memory.lobster | grep -q "first run" && echo "PASS: lobster memory-1" || { echo "FAIL: lobster memory-1"; fail=$((fail+1)); }
$L memory.lobster | grep -q "reads back" && echo "PASS: lobster memory-2" || { echo "FAIL: lobster memory-2"; fail=$((fail+1)); }
$L identity.lobster | grep -q "other home attempt: REFUSED" && echo "PASS: lobster identity" || { echo "FAIL: lobster identity"; fail=$((fail+1)); }
$L budget.lobster | grep -q "refusal recorded" && echo "PASS: lobster budget" || { echo "FAIL: lobster budget"; fail=$((fail+1)); }
$L agent-call.lobster 2>/dev/null | grep -q '"result":"hello from lobster"' && echo "PASS: lobster MCP call" || { echo "FAIL: lobster MCP call"; fail=$((fail+1)); }
cd "$ROOT"

echo "== flakes =="
date -u +%FT%TZ >> os-build/logs/flakes.txt
echo "pipeline: pass=$pass fail=$fail" | tee -a os-build/logs/flakes.txt
echo "PIPELINE pass=$pass fail=$fail"
[ "$fail" = 0 ]
