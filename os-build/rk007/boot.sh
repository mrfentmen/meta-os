#!/usr/bin/env bash
# RK-007 boot proof: boot the 0.11 BIOS image in QEMU, capture serial verbatim,
# take two screendumps through the QEMU monitor, convert both to PNG, stop.
# Usage: os-build/rk007/boot.sh [seconds-before-first-shot] [seconds-before-quit]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT" || exit 1
IMG="os-build/rk007/disk.img"
LOGDIR="os-build/rk007/logs"; mkdir -p "$LOGDIR"
SER="$LOGDIR/RK-007-serial.txt"; QLOG="$LOGDIR/RK-007-qemu.log"
FIRST="${1:-8}"; QUIT="${2:-18}"
rm -f "$SER" "$QLOG" "$LOGDIR"/RK-007-shot-*.ppm "$LOGDIR"/RK-007-shot-*.png "$LOGDIR/mon.sock"
qemu-system-x86_64 -drive "format=raw,file=$IMG" -serial "file:$SER" \
  -display none -m 512M -no-reboot -monitor "unix:$LOGDIR/mon.sock,server,nowait" > "$QLOG" 2>&1 &
QPID=$!
shot() {
  python3 - "$LOGDIR/mon.sock" "$1" "${2:-}" <<'PY'
import socket, sys, time
sock, cmd, out = sys.argv[1], sys.argv[2], sys.argv[3]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(10)
for _ in range(60):
    try: s.connect(sock); break
    except OSError: time.sleep(0.2)
time.sleep(0.4)
try: s.recv(65536)
except Exception: pass
line = ("screendump %s\n" % out) if cmd == "screendump" else (cmd + "\n")
s.sendall(line.encode())
time.sleep(1.2)
try: print(s.recv(65536).decode(errors="replace").strip())
except Exception as e: print("monitor:", e)
PY
}
sleep "$FIRST"
shot screendump "$LOGDIR/RK-007-shot-1.ppm"
sleep "$(( QUIT - FIRST ))"
shot screendump "$LOGDIR/RK-007-shot-2.ppm"
shot quit
sleep 1
kill "$QPID" 2>/dev/null || true
wait "$QPID" 2>/dev/null || true
# PNG is a lossless conversion of the PPM QEMU wrote; both are kept on disk,
# the PNGs are what gets committed (the PPMs are 2.7 MB each).
for n in 1 2; do
    sips -s format png "$LOGDIR/RK-007-shot-$n.ppm" --out "$LOGDIR/RK-007-shot-$n.png" >/dev/null 2>&1 || true
done
echo "serial: $SER ($(wc -l < "$SER" 2>/dev/null | tr -d ' ') lines, $(wc -c < "$SER" 2>/dev/null | tr -d ' ') bytes)"
ls -l "$LOGDIR"/RK-007-shot-* 2>/dev/null | awk '{print $9": "$5" bytes"}'
