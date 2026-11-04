#!/bin/bash
# proof_boot.sh — host-side regression guard for the Meta OS "black box" bug.
#
# Boots /tmp/metaos.ext4 DETACHED (no window), polls the framebuffer with
# `screendump` until it is not a single colour, saves the capture with the
# real resolution + UTC time in the filename, and FAILS LOUDLY if the screen
# stays a single colour.
#
# Usage:
#   sh os-build/tools/proof_boot.sh [--timeout 180] [--out DIR] [--keep]
#   sh os-build/tools/proof_boot.sh --image /tmp/metaos.ext4 --kernel K --initrd I
#
# Output: PASS/FAIL lines + the capture path. Exit 1 on any failure.
# The VM is killed on exit unless --keep is given. The image is booted with
# snapshot=on so this proof never writes to the live image.
set -eu

# --- defaults ---
IMAGE="/tmp/metaos.ext4"
KERNEL="/tmp/meta-boot/vmlinuz"
INITRD="/tmp/meta-boot/initrd.img"
TIMEOUT=180
KEEP=0
OUTDIR=""
SSH_PORT="2223"

while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2 ;;
    --kernel) KERNEL="$2"; shift 2 ;;
    --initrd) INITRD="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --out) OUTDIR="$2"; shift 2 ;;
    --keep) KEEP=1; shift ;;
    --ssh-port) SSH_PORT="$2"; shift 2 ;;
    -h|--help) echo "usage: sh proof_boot.sh [--timeout S] [--out DIR] [--keep] [--image F --kernel K --initrd I]"; exit 0 ;;
    *) echo "proof_boot: unknown flag $1" >&2; exit 2 ;;
  esac
done

HERE="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO="$(CDPATH= cd -- "$HERE/../.." && pwd)"
if [ -z "$OUTDIR" ]; then OUTDIR="$REPO/os-build/captures"; fi
mkdir -p "$OUTDIR"

QEMU="qemu-system-aarch64"
command -v "$QEMU" >/dev/null 2>&1 || { echo "proof_boot: FAIL: $QEMU not found" >&2; exit 2; }
[ -f "$IMAGE" ] || { echo "proof_boot: FAIL: image not found: $IMAGE" >&2; exit 2; }
[ -f "$KERNEL" ] || { echo "proof_boot: FAIL: kernel not found: $KERNEL" >&2; exit 2; }
[ -f "$INITRD" ] || { echo "proof_boot: FAIL: initrd not found: $INITRD" >&2; exit 2; }

MON="$(mktemp -u /tmp/proof-mon.XXXXXX)"
SER_SOCK="$(mktemp -u /tmp/proof-ser.XXXXXX)"
SER_LOG="$(mktemp /tmp/proof-serial.XXXXXX)"
PPM_TMP="$(mktemp /tmp/proof-fb.XXXXXX)"
QEMU_PID=""

cleanup() {
  if [ -n "$QEMU_PID" ] && kill -0 "$QEMU_PID" 2>/dev/null; then
    # Ask nicely first (journal-safe), then kill. Never leave a writer on ext4.
    python3 - "$MON" <<'PY' 2>/dev/null || true
import socket, sys, time
mon = sys.argv[1]
try:
  s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
  s.connect(mon); s.settimeout(3)
  time.sleep(0.2)
  try: s.recv(65536)
  except Exception: pass
  s.sendall(b"system_powerdown\n")
  time.sleep(0.5)
  try: s.recv(65536)
  except Exception: pass
  s.close()
except Exception:
  pass
PY
    sleep 2
    kill "$QEMU_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$QEMU_PID" 2>/dev/null || true
  fi
  rm -f "$PPM_TMP"
  if [ "$KEEP" = "0" ]; then
    rm -f "$MON" "$SER_SOCK" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "proof_boot: image=$IMAGE"
echo "proof_boot: kernel=$(basename "$KERNEL") initrd=$(basename "$INITRD") timeout=${TIMEOUT}s"
echo "proof_boot: monitor=$MON serial=$SER_LOG ssh=127.0.0.1:$SSH_PORT (detached, snapshot=on)"

# --- boot detached ---
# Mirrors /tmp/metaos-boot.sh but with -display none, a private monitor
# socket, a non-clashing SSH forward, and snapshot=on so the live image
# is never written by this proof.
"$QEMU" \
  -M virt -cpu host -accel hvf -m 4096 -smp 4 \
  -kernel "$KERNEL" -initrd "$INITRD" \
  -append "root=/dev/vda rw console=ttyAMA0 console=tty0 plymouth.enable=0" \
  -drive "file=$IMAGE,if=virtio,format=raw,snapshot=on" \
  -device virtio-gpu-pci,xres=1920,yres=1080 \
  -device qemu-xhci -device usb-kbd -device usb-tablet \
  -netdev "user,id=n0,hostfwd=tcp::${SSH_PORT}-:22" -device virtio-net-pci,netdev=n0 \
  -chardev "socket,id=c0,path=$SER_SOCK,server=on,wait=off,logfile=$SER_LOG" \
  -serial chardev:c0 \
  -monitor "unix:$MON,server,nowait" \
  -display none &
QEMU_PID=$!
echo "proof_boot: qemu pid=$QEMU_PID"

# wait for the monitor socket to appear
for i in $(seq 1 30); do
  if [ -S "$MON" ]; then break; fi
  if ! kill -0 "$QEMU_PID" 2>/dev/null; then
    echo "proof_boot: FAIL: qemu died during start (see $SER_LOG)" >&2
    exit 1
  fi
  sleep 1
done
[ -S "$MON" ] || { echo "proof_boot: FAIL: monitor never appeared at $MON" >&2; exit 1; }

hmp_screendump() {
  # $1 = output ppm path
  python3 - "$MON" "$1" <<'PY'
import socket, sys, time, os
mon, out = sys.argv[1], sys.argv[2]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(mon)
s.settimeout(5)
time.sleep(0.3)
try:
  s.recv(65536)
except Exception:
  pass
s.sendall(("screendump %s\n" % out).encode())
time.sleep(0.8)
try:
  s.recv(65536)
except Exception:
  pass
s.close()
PY
}

analyze_ppm() {
  # $1 = ppm path -> prints "W H UNIQUE MAXV" or "BAD ..."
  python3 - "$1" <<'PY'
import sys, re
p = sys.argv[1]
try:
  d = open(p, "rb").read()
except Exception as e:
  print("BAD cannot-read"); sys.exit(0)
m = re.match(rb'P6\n(\d+) (\d+)\n(\d+)\n', d)
if not m:
  print("BAD no-header"); sys.exit(0)
w, h, mx = int(m.group(1)), int(m.group(2)), int(m.group(3))
hdr = len(m.group(0))
pix = d[hdr:]
want = w * h * 3
if len(pix) < want:
  print("BAD short %dx%d" % (w, h)); sys.exit(0)
pix = pix[:want]
# sample to keep this cheap on 1920x1080
step = max(1, len(pix) // (3 * 20000))
uniq = set()
maxv = 0
for i in range(0, len(pix), 3 * step):
  uniq.add(pix[i:i+3])
  v = pix[i]
  if pix[i+1] > v: v = pix[i+1]
  if pix[i+2] > v: v = pix[i+2]
  if v > maxv: maxv = v
  if len(uniq) > 64:
    pass
print("%d %d %d %d" % (w, h, len(uniq), maxv))
PY
}

echo "proof_boot: polling framebuffer every 5s (single-colour = FAIL)..."
FOUND=0
FW=0; FH=0; FUNIQ=0; FMAX=0
ELAPSED=0
while [ "$ELAPSED" -lt "$TIMEOUT" ]; do
  sleep 5
  ELAPSED=$((ELAPSED + 5))
  if ! kill -0 "$QEMU_PID" 2>/dev/null; then
    echo "proof_boot: FAIL: qemu died after ${ELAPSED}s (see $SER_LOG)" >&2
    exit 1
  fi
  rm -f "$PPM_TMP"
  hmp_screendump "$PPM_TMP" 2>/dev/null || true
  if [ ! -s "$PPM_TMP" ]; then
    echo "proof_boot: ... ${ELAPSED}s: no frame yet"
    continue
  fi
  info="$(analyze_ppm "$PPM_TMP")"
  # shellcheck disable=SC2086
  set -- $info
  if [ "${1:-}" = "BAD" ]; then
    echo "proof_boot: ... ${ELAPSED}s: $info"
    continue
  fi
  FW="$1"; FH="$2"; FUNIQ="$3"; FMAX="$4"
  echo "proof_boot: ... ${ELAPSED}s: ${FW}x${FH} unique~${FUNIQ} max=${FMAX}"
  # non-black = max channel well above zero; non-single-colour = >5 distinct samples
  if [ "$FMAX" -lt 16 ]; then
    continue
  fi
  if [ "$FUNIQ" -le 5 ]; then
    continue
  fi
  FOUND=1
  break
done

if [ "$FOUND" -ne 1 ]; then
  echo "proof_boot: FAIL: framebuffer stayed single-colour/black after ${TIMEOUT}s" >&2
  echo "proof_boot: last=${FW}x${FH} unique~${FUNIQ} max=${FMAX} serial=$SER_LOG" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASE="proof-boot-${FW}x${FH}-${STAMP}"
cp -f "$PPM_TMP" "$OUTDIR/$BASE.ppm"
SAVED="$OUTDIR/$BASE.ppm"

# best-effort PNG for humans (PIL first, sips second, PPM alone if neither)
if python3 -c "from PIL import Image; Image.open('$SAVED').save('${SAVED%.ppm}.png')" 2>/dev/null; then
  SAVED_PNG="${SAVED%.ppm}.png"
  echo "proof_boot: PASS: framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
  echo "proof_boot: capture: $SAVED"
  echo "proof_boot: capture: $SAVED_PNG"
else
  if command -v sips >/dev/null 2>&1 && sips -s format png "$SAVED" --out "${SAVED%.ppm}.png" >/dev/null 2>&1; then
    echo "proof_boot: PASS: framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
    echo "proof_boot: capture: $SAVED"
    echo "proof_boot: capture: ${SAVED%.ppm}.png"
  else
    echo "proof_boot: PASS: framebuffer ${FW}x${FH} unique~${FUNIQ} (not single-colour)"
    echo "proof_boot: capture: $SAVED (no PNG converter available)"
  fi
fi
echo "proof_boot: serial: $SER_LOG monitor: $MON pid: $QEMU_PID"
exit 0
