#!/bin/bash
# frames_boot.sh — boot /tmp/metaos.ext4 headless and capture the screen at
# several moments, so a login→desktop sequence can be inspected frame by frame.
# snapshot=on: the live image is never written. The VM is always killed.
set -u
IMAGE=/tmp/metaos.ext4
KERNEL=/tmp/meta-boot/vmlinuz
INITRD=/tmp/meta-boot/initrd.img
OUT=${OUT:-/tmp/metaos-frames}
mkdir -p "$OUT"

MON=$(mktemp -u /tmp/fr-mon.XXXXXX)
SER=$(mktemp -u /tmp/fr-ser.XXXXXX)
mkdir -p /tmp/metaos-frames

qemu-system-aarch64 \
  -M virt -cpu host -accel hvf -m 4096 -smp 4 \
  -kernel "$KERNEL" -initrd "$INITRD" \
  -append "root=/dev/vda rw console=ttyAMA0 console=tty0 plymouth.enable=0" \
  -drive "file=$IMAGE,if=virtio,format=raw,snapshot=${SNAP:-on}" \
  -device virtio-gpu-pci,xres=1920,yres=1080 \
  -device qemu-xhci -device usb-kbd -device usb-tablet \
  -netdev "user,id=n0,hostfwd=tcp::2223-:22" -device virtio-net-pci,netdev=n0 \
  -chardev "socket,id=c0,path=$SER,server=on,wait=off,logfile=$OUT/serial.log" \
  -serial chardev:c0 \
  -monitor "unix:$MON,server,nowait" \
  -display none &
PID=$!
echo "qemu pid=$PID"

shot() {
  local tag=$1
  local ppm="$OUT/frame-$tag.ppm"
  rm -f "$ppm"
  python3 - "$MON" "$ppm" <<'PY'
import socket, sys, time
mon, out = sys.argv[1], sys.argv[2]
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(mon); s.settimeout(5); time.sleep(0.3)
    try: s.recv(65536)
    except Exception: pass
    s.sendall(("screendump %s\n" % out).encode())
    time.sleep(0.8)
    try: s.recv(65536)
    except Exception: pass
    s.close()
except Exception as e:
    print("shot failed:", e)
PY
  if [ -s "$ppm" ]; then
    sips -s format png "$ppm" --out "$OUT/frame-$tag.png" >/dev/null 2>&1
    sips -Z 1280 "$OUT/frame-$tag.png" --out "$OUT/small-$tag.png" >/dev/null 2>&1
    echo "captured $tag"
  else
    echo "no frame at $tag"
  fi
}

for t in 20 40 60 90 130; do
  sleep $((t - ${LAST:-0}))
  LAST=$t
  shot "$t"
done

python3 - "$MON" <<'PY' 2>/dev/null || true
import socket, sys, time
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sys.argv[1]); s.settimeout(3); time.sleep(0.3)
    try: s.recv(65536)
    except Exception: pass
    s.sendall(b"system_powerdown\n"); time.sleep(0.5)
    s.close()
except Exception: pass
PY
sleep 2
kill "$PID" 2>/dev/null || true
sleep 1
kill -9 "$PID" 2>/dev/null || true
wait "$PID" 2>/dev/null || true
echo "--- serial tail ---"
tail -40 "$OUT/serial.log" 2>/dev/null
echo "frames in $OUT"
