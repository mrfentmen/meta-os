#!/usr/bin/env bash
# os-build/demo-capture.sh (R6-2) — DEMO INTERRUPT capture session.
# Boots the merged-tree image once under QEMU+VNC, captures serial log
# plus one screendump per DEMO_SCRIPT beat, named by beat. Real output
# only: a beat the tree cannot do is reported missing, never staged.
# Usage: sh os-build/demo-capture.sh   (writes os-build/logs/demo-beats/)
set -euo pipefail
cd "$(dirname "$0")/.."

NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
export PATH="$NIGHTLY:$PATH"

IMG="kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin"
OUT="os-build/logs/demo-beats"
MON="$(mktemp -u /tmp/demo-mon-XXXXXX)"
SER="$OUT/serial-all.txt"
mkdir -p "$OUT"
rm -f "$OUT"/beat*.ppm "$SER"

echo "== boot (VNC :42, serial+monitor) =="
qemu-system-x86_64 -drive format=raw,file="$IMG" -m 512M -no-reboot \
  -vnc :42 -serial "file:$SER" -monitor "unix:$MON,server,nowait" &
QEMU=$!
cleanup() { kill $QEMU 2>/dev/null || true; }
trap cleanup EXIT

hcp() { python3 -c "
import sys; sys.path.insert(0, 'os-build/tools')
from drive import connect, send
s = connect('$MON'); send(s, '$1'); s.close()"; }

wait_marker() { # $1 = grep pattern, $2 = beat file
  for i in $(seq 1 200); do
    if grep -aq "$1" "$SER" 2>/dev/null; then hcp "screendump $OUT/$2"; echo "beat $2 @ $1"; return 0; fi
    sleep 0.2
  done
  echo "beat $2 MISSING (marker '$1' never printed)"
}

wait_marker "META OS 0.1"            beat1-boot.ppm
wait_marker "0x600000000000"        beat2-ring3.ppm
wait_marker "sleeper: before sleep" beat3-programs.ppm
wait_marker "task killed"           beat4-fault.ppm
sleep 2
hcp "screendump $OUT/beat4b-after-fault.ppm"

echo "== beat 5: live shell =="
for i in $(seq 1 60); do grep -aq "commands:" "$SER" 2>/dev/null && break; sleep 2; done
python3 os-build/tools/drive.py --monitor "$MON" status
sleep 2; hcp "screendump $OUT/beat5-status.ppm"
python3 os-build/tools/drive.py --monitor "$MON" mem
sleep 2; hcp "screendump $OUT/beat5-mem.ppm"
python3 os-build/tools/drive.py --monitor "$MON" ps
sleep 2; hcp "screendump $OUT/beat5-ps.ppm"

echo "== beat 6: committed imperium record =="
for f in drill.log receipt.txt package-sent.json incident.json; do
  if [ -f "os-build/logs/R5-imperium/$f" ]; then cp -f "os-build/logs/R5-imperium/$f" "$OUT/beat6-$f"; echo "beat6-$f ok"; else echo "beat6-$f MISSING"; fi
done
grep -a "sim-6623d237a90b3d9d" "$OUT/beat6-receipt.txt" && echo "receipt id ok"

kill $QEMU 2>/dev/null || true
trap - EXIT
echo "== captures =="; ls -la "$OUT"
